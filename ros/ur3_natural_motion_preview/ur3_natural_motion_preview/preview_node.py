#!/usr/bin/env python3
from __future__ import annotations

import math
import random
import threading
import time
from pathlib import Path

import rclpy
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Point, PoseStamped
from moveit_msgs.msg import RobotState
from moveit_msgs.srv import GetPositionFK, GetPositionIK
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker, MarkerArray
import yaml

from .trajectory import (
    catmull_rom,
    cubic_bezier3,
    posture_score,
    quat_slerp,
    quintic_smoothstep,
    sample_polyline,
    unwrap_near,
)

SUCCESS = 1


def quat_rotate(qx, qy, qz, qw, v):
    x, y, z = v
    tx = 2.0 * (qy*z - qz*y)
    ty = 2.0 * (qz*x - qx*z)
    tz = 2.0 * (qx*y - qy*x)
    return (
        x + qw*tx + (qy*tz - qz*ty),
        y + qw*ty + (qz*tx - qx*tz),
        z + qw*tz + (qx*ty - qy*tx),
    )


def copy_pose(src):
    out = PoseStamped()
    out.header = src.header
    out.pose.position.x = src.pose.position.x
    out.pose.position.y = src.pose.position.y
    out.pose.position.z = src.pose.position.z
    out.pose.orientation.x = src.pose.orientation.x
    out.pose.orientation.y = src.pose.orientation.y
    out.pose.orientation.z = src.pose.orientation.z
    out.pose.orientation.w = src.pose.orientation.w
    return out


def translate_local_z(pose, dz):
    out = copy_pose(pose)
    q = pose.pose.orientation
    dx, dy, dz_world = quat_rotate(q.x, q.y, q.z, q.w, (0.0, 0.0, dz))
    out.pose.position.x += dx
    out.pose.position.y += dy
    out.pose.position.z += dz_world
    return out


def pose_xyz(p):
    return (p.pose.position.x, p.pose.position.y, p.pose.position.z)


def pose_quat(p):
    return (
        p.pose.orientation.x,
        p.pose.orientation.y,
        p.pose.orientation.z,
        p.pose.orientation.w,
    )


def pose_from_components(frame_id, xyz, quat):
    p = PoseStamped()
    p.header.frame_id = frame_id
    p.pose.position.x, p.pose.position.y, p.pose.position.z = xyz
    p.pose.orientation.x, p.pose.orientation.y, p.pose.orientation.z, p.pose.orientation.w = quat
    return p


class NaturalPreview(Node):
    def __init__(self):
        super().__init__("ur3_natural_motion_preview")
        self.declare_parameter("workpoint_file", "")
        self.declare_parameter("step_mode", False)
        self.declare_parameter("loop", True)
        self.declare_parameter("motion_style", "")

        path = Path(str(self.get_parameter("workpoint_file").value))
        if not path.exists():
            raise RuntimeError(f"workpoint_file not found: {path}")

        self.step_mode = bool(self.get_parameter("step_mode").value)
        self.loop = bool(self.get_parameter("loop").value)

        with path.open("r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.joint_names = list(self.cfg["joint_names"])
        self.points = list(self.cfg["workpoints"])
        self.motion = dict(self.cfg["motion"])
        self.tool = dict(self.cfg["tool"])
        self.reference = {
            p["name"]: [float(x) for x in p["positions_rad"]]
            for p in self.points
        }
        self.point_cfg = {p["name"]: dict(p) for p in self.points}
        self.order = [p["name"] for p in self.points]

        requested_style = str(self.get_parameter("motion_style").value).strip()
        self.style_mode = requested_style or str(self.motion.get("style_mode", "performance"))
        if self.style_mode not in ("baseline", "performance"):
            raise RuntimeError("motion_style must be baseline or performance")

        self.approach = float(self.motion.get("clearance_desired_m", self.motion["approach_retract_m"]))
        self.min_preview_clearance = float(self.motion.get("clearance_min_preview_m", 0.040))
        self.clearance_step = float(self.motion.get("clearance_search_step_m", 0.005))
        self.allow_reduced_clearance = bool(self.motion.get("preview_allow_reduced_clearance", True))
        self.hold_s = float(self.motion["work_hold_s"])
        self.segment_duration = float(self.motion["segment_duration_s"])
        self.rate_hz = float(self.motion["preview_rate_hz"])
        self.seed_count = int(self.motion["candidate_seed_count"])
        self.transit_samples = int(self.motion.get("transit_samples", 22))
        self.linear_samples = int(self.motion.get("linear_samples", 12))
        self.performance_cfg = dict(self.motion.get("performance", {}))

        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/preview/gripper", 1)
        self.path_marker_pub = self.create_publisher(MarkerArray, "/preview/path", 1)
        self.state_pub = self.create_publisher(String, "/preview/state", 10)
        self.done_pub = self.create_publisher(Bool, "/preview/done", 10)
        self.start_srv = self.create_service(Trigger, "/preview/start_next", self._start_next)

        self.fk = self.create_client(GetPositionFK, "/compute_fk")
        self.ik = self.create_client(GetPositionIK, "/compute_ik")

        self.q_current = list(self.reference["HOME"])
        self.sequence = []
        self.seq_index = 0
        self.moving = False
        self.done = self.step_mode
        self.finished = False
        self.segment_t = 0.0
        self.hold_t = 0.0
        self.current_path = [list(self.q_current)]
        self.planned_path_xyz = []

        self.publish_joint(self.q_current)
        self.publish_markers()
        self.publish_done()
        self.publish_state("WAITING_FOR_MOVEIT")
        self.create_timer(0.5, self.publish_markers)
        self.create_timer(0.5, self.publish_path_marker)

    def publish_joint(self, q):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self.joint_names)
        msg.position = [float(x) for x in q]
        self.joint_pub.publish(msg)

    def publish_state(self, text):
        msg = String()
        msg.data = str(text)
        self.state_pub.publish(msg)

    def publish_done(self):
        msg = Bool()
        msg.data = bool(self.done)
        self.done_pub.publish(msg)

    def publish_markers(self):
        arr = MarkerArray()
        cyl = Marker()
        cyl.header.frame_id = "tool0"
        cyl.header.stamp = self.get_clock().now().to_msg()
        cyl.ns = "suction_tool"
        cyl.id = 1
        cyl.type = Marker.CYLINDER
        cyl.action = Marker.ADD
        cyl.pose.position.z = float(self.tool["length_m"]) / 2.0
        cyl.pose.orientation.w = 1.0
        cyl.scale.x = float(self.tool["diameter_m"])
        cyl.scale.y = float(self.tool["diameter_m"])
        cyl.scale.z = float(self.tool["length_m"])
        cyl.color.r, cyl.color.g, cyl.color.b, cyl.color.a = 0.15, 0.55, 0.85, 0.95
        cyl.frame_locked = True
        arr.markers.append(cyl)

        tcp = Marker()
        tcp.header.frame_id = "tool0"
        tcp.header.stamp = self.get_clock().now().to_msg()
        tcp.ns = "suction_tool"
        tcp.id = 2
        tcp.type = Marker.SPHERE
        tcp.action = Marker.ADD
        tcp.pose.position.z = float(self.tool["length_m"])
        tcp.pose.orientation.w = 1.0
        tcp.scale.x, tcp.scale.y, tcp.scale.z = 0.024, 0.024, 0.008
        tcp.color.r, tcp.color.g, tcp.color.b, tcp.color.a = 0.90, 0.25, 0.15, 0.95
        tcp.frame_locked = True
        arr.markers.append(tcp)
        self.marker_pub.publish(arr)

    def publish_path_marker(self):
        if not self.planned_path_xyz:
            return
        arr = MarkerArray()
        line = Marker()
        line.header.frame_id = "base_link"
        line.header.stamp = self.get_clock().now().to_msg()
        line.ns = "planned_tcp_path"
        line.id = 10
        line.type = Marker.LINE_STRIP
        line.action = Marker.ADD
        line.pose.orientation.w = 1.0
        line.scale.x = 0.006
        line.color.r, line.color.g, line.color.b, line.color.a = 0.95, 0.75, 0.15, 0.90
        for xyz in self.planned_path_xyz:
            pt = Point()
            pt.x, pt.y, pt.z = xyz
            line.points.append(pt)
        arr.markers.append(line)
        self.path_marker_pub.publish(arr)

    def robot_state_for(self, q):
        rs = RobotState()
        rs.joint_state.name = list(self.joint_names)
        rs.joint_state.position = [float(x) for x in q]
        return rs

    def call_fk(self, q):
        req = GetPositionFK.Request()
        req.header.frame_id = "base_link"
        req.fk_link_names = ["tool0"]
        req.robot_state = self.robot_state_for(q)
        future = self.fk.call_async(req)
        while rclpy.ok() and not future.done():
            time.sleep(0.004)
        res = future.result()
        if res is None or int(res.error_code.val) != SUCCESS or not res.pose_stamped:
            raise RuntimeError("MoveIt FK failed for tool0")
        return res.pose_stamped[0]

    def call_ik(self, pose, seed_q, avoid_collisions=True):
        req = GetPositionIK.Request()
        req.ik_request.group_name = "ur_manipulator"
        req.ik_request.robot_state = self.robot_state_for(seed_q)
        req.ik_request.avoid_collisions = bool(avoid_collisions)
        req.ik_request.ik_link_name = "tool0"
        req.ik_request.pose_stamped = pose
        req.ik_request.timeout = Duration(sec=0, nanosec=200_000_000)
        future = self.ik.call_async(req)
        while rclpy.ok() and not future.done():
            time.sleep(0.004)
        res = future.result()
        if res is None or int(res.error_code.val) != SUCCESS:
            return None
        mapping = dict(zip(list(res.solution.joint_state.name), list(res.solution.joint_state.position)))
        if not all(n in mapping for n in self.joint_names):
            return None
        return [float(mapping[n]) for n in self.joint_names]

    def seed_bank(self, reference_q, previous_q):
        seeds = [list(reference_q), list(previous_q)]
        rng = random.Random(330370)
        for _ in range(max(0, self.seed_count - len(seeds))):
            seeds.append([rng.uniform(-math.pi, math.pi) for _ in range(6)])
        return seeds

    def best_ik(self, pose, reference_q, previous_q, avoid_collisions=True):
        candidates = []
        seen = set()
        for seed in self.seed_bank(reference_q, previous_q):
            q = self.call_ik(pose, seed, avoid_collisions=avoid_collisions)
            if q is None:
                continue
            q = unwrap_near(q, previous_q)
            key = tuple(round(x, 5) for x in q)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(q)
        if not candidates:
            raise RuntimeError("No IK candidate found for target pose")
        ranked = sorted(
            ((posture_score(q, previous_q, reference_q), q) for q in candidates),
            key=lambda x: x[0],
        )
        return ranked[0][1], len(candidates)

    def try_best_ik(self, pose, reference_q, previous_q, avoid_collisions=True):
        try:
            return self.best_ik(pose, reference_q, previous_q, avoid_collisions=avoid_collisions)
        except RuntimeError:
            return None, 0

    def continuous_ik_path(self, poses, start_q, reference_q, label):
        q_path = [list(start_q)]
        q_prev = list(start_q)
        for i, pose in enumerate(poses[1:], start=1):
            q = self.call_ik(pose, q_prev, avoid_collisions=True)
            if q is not None:
                q = unwrap_near(q, q_prev)
            else:
                q, _ = self.try_best_ik(pose, reference_q, q_prev, avoid_collisions=True)
            if q is None:
                raise RuntimeError(f"{label}: continuous IK failed at sample {i}/{len(poses)-1}")
            q_path.append(list(q))
            q_prev = list(q)
        return q_path

    def resolve_clearance_pose(self, work_pose, work_q, previous_q, label, desired=None):
        desired = float(self.approach if desired is None else desired)
        desired_pose = translate_local_z(work_pose, -desired)
        q, count = self.try_best_ik(desired_pose, work_q, previous_q, avoid_collisions=True)
        if q is not None:
            return q, desired_pose, desired, count, f"EXACT_{int(round(desired*1000))}MM"

        q_nc, _ = self.try_best_ik(desired_pose, work_q, previous_q, avoid_collisions=False)
        target_mm = int(round(desired*1000.0))
        reason = (
            f"{target_mm}mm has IK but no collision-aware IK"
            if q_nc is not None else
            f"{target_mm}mm has no IK solution"
        )
        self.get_logger().warning(f"{label}: {reason}. Preview clearance fallback search starts.")
        if not self.allow_reduced_clearance:
            raise RuntimeError(f"{label}: exact {desired*1000:.0f} mm local -Z clearance unavailable")

        distance = desired - self.clearance_step
        while distance + 1e-12 >= self.min_preview_clearance:
            pose = translate_local_z(work_pose, -distance)
            q, count = self.try_best_ik(pose, work_q, previous_q, avoid_collisions=True)
            if q is not None:
                self.get_logger().warning(
                    f"{label}: PREVIEW ONLY fallback uses {distance*1000:.0f} mm instead of {desired*1000:.0f} mm."
                )
                return q, pose, distance, count, "REDUCED_PREVIEW_CLEARANCE"
            distance -= self.clearance_step
        raise RuntimeError(f"{label}: no collision-aware axial clearance IK down to {self.min_preview_clearance*1000:.0f} mm")

    def linear_pose_path(self, start_pose, end_pose, samples):
        p0, p1 = pose_xyz(start_pose), pose_xyz(end_pose)
        q0, q1 = pose_quat(start_pose), pose_quat(end_pose)
        out = []
        for i in range(samples):
            u = i / float(max(1, samples-1))
            xyz = tuple((1-u)*a + u*b for a, b in zip(p0, p1))
            quat = quat_slerp(q0, q1, u)
            out.append(pose_from_components("base_link", xyz, quat))
        return out

    def style_params(self, target_name):
        styles = dict(self.performance_cfg.get("styles", {}))
        p = dict(styles.get(target_name, {}))
        return {
            "type": p.get("type", "TRANSFER"),
            "lift_m": float(p.get("lift_m", self.performance_cfg.get("default_lift_m", 0.100))),
            "arc_side_m": float(p.get("arc_side_m", self.performance_cfg.get("default_arc_side_m", 0.030))),
        }

    def performance_transit_pose_path(self, start_pose, end_pose, target_name):
        p0, p3 = pose_xyz(start_pose), pose_xyz(end_pose)
        q0, q3 = pose_quat(start_pose), pose_quat(end_pose)
        prm = self.style_params(target_name)
        lift, side = prm["lift_m"], prm["arc_side_m"]

        dx, dy = p3[0]-p0[0], p3[1]-p0[1]
        horizontal = math.hypot(dx, dy)
        if horizontal < 1e-6:
            nx, ny = 0.0, 0.0
        else:
            nx, ny = -dy/horizontal, dx/horizontal

        ztop = max(p0[2], p3[2])
        c1 = (p0[0]+0.28*dx+side*nx, p0[1]+0.28*dy+side*ny, ztop+lift)
        c2 = (p0[0]+0.72*dx-0.35*side*nx, p0[1]+0.72*dy-0.35*side*ny, ztop+0.78*lift)
        lead = float(self.performance_cfg.get("orientation_lead", 0.72))

        out = []
        for i in range(self.transit_samples):
            u = i / float(max(1, self.transit_samples-1))
            xyz = cubic_bezier3(p0, c1, c2, p3, u)
            ou = quintic_smoothstep(min(1.0, u/max(0.05, lead)))
            quat = quat_slerp(q0, q3, ou)
            out.append(pose_from_components("base_link", xyz, quat))
        return out

    def qpath_xyz(self, q_path):
        pts = []
        for q in q_path:
            try:
                pts.append(pose_xyz(self.call_fk(q)))
            except Exception:
                pass
        return pts

    def prepare(self):
        self.get_logger().info(f"Waiting for MoveIt FK/IK services... motion_style={self.style_mode}")
        if not self.fk.wait_for_service(timeout_sec=20.0):
            raise RuntimeError("/compute_fk not available")
        if not self.ik.wait_for_service(timeout_sec=20.0):
            raise RuntimeError("/compute_ik not available")

        self.publish_state("OPTIMIZING")
        home_q = list(self.reference["HOME"])
        home_pose = self.call_fk(home_q)
        solved = {}
        previous_q = list(home_q)

        for name in self.order[1:]:
            ref_q = self.reference[name]
            work_pose = self.call_fk(ref_q)
            best_work, n_work = self.best_ik(work_pose, ref_q, previous_q, avoid_collisions=True)
            desired_clearance = float(
                self.point_cfg[name].get("clearance_override_m", self.approach)
            )
            app_q, app_pose, clearance, n_app, status = self.resolve_clearance_pose(
                work_pose, best_work, previous_q, name, desired=desired_clearance
            )
            solved[name] = {
                "reference_q": ref_q,
                "work_q": best_work,
                "work_pose": work_pose,
                "approach_q": app_q,
                "approach_pose": app_pose,
                "clearance": clearance,
                "clearance_status": status,
            }
            self.get_logger().info(
                f"{name}: work_candidates={n_work}, approach_candidates={n_app}, "
                f"clearance={clearance*1000:.0f}mm, style={self.style_params(name)['type']}"
            )
            previous_q = list(app_q)

        sequence = [{"name":"HOME_START", "kind":"HOME", "q_path":[home_q], "hold_s":0.5}]
        q_cursor, pose_cursor = list(home_q), home_pose

        for name in self.order[1:]:
            item = solved[name]
            app_q, app_pose = list(item["approach_q"]), item["approach_pose"]
            work_q, work_pose = list(item["work_q"]), item["work_pose"]
            clearance_mm = int(round(item["clearance"]*1000.0))

            if self.style_mode == "performance":
                transit_poses = self.performance_transit_pose_path(pose_cursor, app_pose, name)
                transit_q = self.continuous_ik_path(transit_poses, q_cursor, app_q, f"{name}_PERFORMANCE_TRANSIT")
            else:
                transit_q = [list(q_cursor), list(app_q)]

            app_poses = self.linear_pose_path(app_pose, work_pose, self.linear_samples)
            app_linear_q = self.continuous_ik_path(app_poses, app_q, work_q, f"{name}_LINEAR_APPROACH")
            ret_poses = self.linear_pose_path(work_pose, app_pose, self.linear_samples)
            ret_linear_q = self.continuous_ik_path(ret_poses, work_q, app_q, f"{name}_LINEAR_RETRACT")

            sequence.extend([
                {"name":f"{name}_TRANSIT_{self.style_mode.upper()}", "kind":"TRANSIT", "q_path":transit_q, "hold_s":0.0},
                {"name":f"{name}_APPROACH_{clearance_mm}MM", "kind":"APPROACH", "q_path":app_linear_q, "hold_s":0.0},
                {"name":name, "kind":"WORK", "q_path":[work_q], "hold_s":self.hold_s},
                {"name":f"{name}_RETRACT_{clearance_mm}MM", "kind":"RETRACT", "q_path":ret_linear_q, "hold_s":0.0},
            ])
            q_cursor, pose_cursor = list(app_q), app_pose

        if self.style_mode == "performance":
            home_poses = self.performance_transit_pose_path(pose_cursor, home_pose, "HOME")
            home_qpath = self.continuous_ik_path(home_poses, q_cursor, home_q, "HOME_PERFORMANCE_TRANSIT")
        else:
            home_qpath = [list(q_cursor), list(home_q)]

        sequence.extend([
            {"name":f"HOME_RETURN_{self.style_mode.upper()}", "kind":"TRANSIT", "q_path":home_qpath, "hold_s":0.0},
            {"name":"HOME_END", "kind":"HOME", "q_path":[home_q], "hold_s":0.5},
        ])
        self.sequence = sequence

        self.planned_path_xyz = []
        for seg in self.sequence:
            if len(seg["q_path"]) > 1:
                self.planned_path_xyz.extend(self.qpath_xyz(seg["q_path"]))

        self.seq_index = 0
        self.q_current = list(home_q)
        self.current_path = [list(home_q)]
        self.publish_joint(self.q_current)
        self.publish_state(f"READY:{self.style_mode.upper()}")
        self.done = self.step_mode
        self.publish_done()
        self.publish_path_marker()

        if not self.step_mode:
            self.start_segment(1)
        self.create_timer(1.0/self.rate_hz, self.tick)

    def start_segment(self, idx):
        self.seq_index = idx
        self.segment_t = 0.0
        self.hold_t = 0.0
        self.current_path = [list(q) for q in self.sequence[idx]["q_path"]]
        self.moving = True
        self.publish_state(f"MOVING:{self.sequence[idx]['name']}")

    def _start_next(self, request, response):
        del request
        if not self.sequence:
            response.success, response.message = False, "not ready"
            return response
        if not self.step_mode:
            response.success, response.message = False, "step_mode=false"
            return response
        if self.moving:
            response.success, response.message = False, "already moving"
            return response
        if self.finished:
            if not self.loop:
                response.success, response.message = False, "finished"
                return response
            self.finished = False
            self.seq_index = 0
            self.q_current = list(self.sequence[0]["q_path"][-1])

        nxt = self.seq_index + 1
        if nxt >= len(self.sequence):
            if self.loop:
                nxt = 0
            else:
                self.finished = True
                response.success, response.message = False, "finished"
                return response

        self.done = False
        self.publish_done()
        self.start_segment(nxt)
        response.success = True
        response.message = f"START accepted -> {self.sequence[nxt]['name']}"
        return response

    def finish_current(self):
        target = self.sequence[self.seq_index]
        self.q_current = list(target["q_path"][-1])
        self.publish_joint(self.q_current)
        if self.step_mode:
            self.moving = False
            self.done = True
            self.publish_done()
            self.publish_state(f"DONE:{target['name']}")
        else:
            self.publish_state(f"HOLD:{target['name']}")

    def auto_advance(self):
        nxt = self.seq_index + 1
        if nxt >= len(self.sequence):
            if not self.loop:
                self.finished = True
                self.moving = False
                self.publish_state("FINISHED")
                return
            nxt = 0
        self.start_segment(nxt)

    def tick(self):
        if not self.sequence:
            return
        if not self.moving:
            self.publish_joint(self.q_current)
            return

        dt = 1.0/self.rate_hz
        target = self.sequence[self.seq_index]
        q_path = self.current_path

        if len(q_path) <= 1:
            self.segment_t = self.segment_duration
            self.q_current = list(q_path[-1])
        elif self.segment_t < self.segment_duration:
            self.segment_t = min(self.segment_duration, self.segment_t + dt)
            s = quintic_smoothstep(self.segment_t/self.segment_duration)
            if target["kind"] in ("APPROACH", "RETRACT"):
                self.q_current = sample_polyline(q_path, s)
            else:
                self.q_current = catmull_rom(q_path, s)
            self.publish_joint(self.q_current)
            return

        if self.hold_t == 0.0:
            self.finish_current()
            if self.step_mode:
                return

        hold = float(target.get("hold_s", 0.0))
        self.hold_t += dt
        self.publish_joint(self.q_current)
        if self.hold_t >= hold:
            self.auto_advance()


def main(args=None):
    rclpy.init(args=args)
    node = NaturalPreview()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        node.prepare()
        while rclpy.ok():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
