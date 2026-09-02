#!/usr/bin/env python3
from __future__ import annotations

import math
import random
import threading
import time
from pathlib import Path

import rclpy
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import RobotState
from moveit_msgs.srv import GetPositionFK, GetPositionIK
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker, MarkerArray
import yaml

from .trajectory import interpolate, posture_score

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

def translate_local_z(pose, dz):
    out = PoseStamped()
    out.header = pose.header
    out.pose.position.x = pose.pose.position.x
    out.pose.position.y = pose.pose.position.y
    out.pose.position.z = pose.pose.position.z
    out.pose.orientation = pose.pose.orientation
    q = pose.pose.orientation
    dx, dy, dz_world = quat_rotate(q.x, q.y, q.z, q.w, (0.0, 0.0, dz))
    out.pose.position.x += dx
    out.pose.position.y += dy
    out.pose.position.z += dz_world
    return out

class NaturalPreview(Node):
    def __init__(self):
        super().__init__("ur3_natural_motion_preview")
        self.declare_parameter("workpoint_file", "")
        self.declare_parameter("step_mode", False)
        self.declare_parameter("loop", True)

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
        self.order = [p["name"] for p in self.points]
        self.approach = float(self.motion.get("clearance_desired_m", self.motion["approach_retract_m"]))
        self.min_preview_clearance = float(self.motion.get("clearance_min_preview_m", 0.040))
        self.clearance_step = float(self.motion.get("clearance_search_step_m", 0.005))
        self.allow_reduced_clearance = bool(self.motion.get("preview_allow_reduced_clearance", True))
        self.hold_s = float(self.motion["work_hold_s"])
        self.segment_duration = float(self.motion["segment_duration_s"])
        self.rate_hz = float(self.motion["preview_rate_hz"])
        self.seed_count = int(self.motion["candidate_seed_count"])

        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/preview/gripper", 1)
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
        self.q_start = list(self.q_current)

        self.publish_joint(self.q_current)
        self.publish_markers()
        self.publish_done()
        self.publish_state("WAITING_FOR_MOVEIT")
        self.create_timer(0.5, self.publish_markers)

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
        cyl.color.r = 0.15
        cyl.color.g = 0.55
        cyl.color.b = 0.85
        cyl.color.a = 0.95
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
        tcp.scale.x = 0.024
        tcp.scale.y = 0.024
        tcp.scale.z = 0.008
        tcp.color.r = 0.90
        tcp.color.g = 0.25
        tcp.color.b = 0.15
        tcp.color.a = 0.95
        tcp.frame_locked = True
        arr.markers.append(tcp)

        self.marker_pub.publish(arr)

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
            time.sleep(0.005)
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
            time.sleep(0.005)
        res = future.result()
        if res is None or int(res.error_code.val) != SUCCESS:
            return None
        mapping = dict(zip(
            list(res.solution.joint_state.name),
            list(res.solution.joint_state.position)})
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
            key = tuple(round(x, 5) for x in q)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(q)

        if not candidates:
            raise RuntimeError("No IK candidate found for target pose")

        ranked = sorted(
            ((posture_score(q, previous_q, reference_q), q) for q in candidates),
            key=lambda x: x[0]
        )
        return ranked[0][1], len(candidates)

    def try_best_ik(self, pose, reference_q, previous_q, avoid_collisions=True):
        try:
            q, count = self.best_ik(
                pose, reference_q, previous_q,
                avoid_collisions=avoid_collisions
            )
            return q, count
        except RuntimeError:
            return None, 0

    def resolve_clearance_pose(self, work_tool0, work_q, previous_q, label):
        """Prefer exact 100 mm local -Z. For preview only, search shorter reachable retreat."""
        desired = float(self.approach)

        desired_pose = translate_local_z(work_tool0, -desired)
        q, count = self.try_best_ik(
            desired_pose, work_q, previous_q, avoid_collisions=True
        )
        if q is not None:
            return q, desired, count, "EXACT_100MM"

        q_nc, count_nc = self.try_best_ik(
            desired_pose, work_q, previous_q, avoid_collisions=False
        )
        if q_nc is not None:
            reason = "100mm has IK but no collision-aware IK"
        else:
            reason = "100mm has no IK solution"

        self.get_logger().warning(
            f"{label}: {reason}. Preview clearance fallback search starts."
        )

        if not self.allow_reduced_clearance:
            raise RuntimeError(
                f"{label}: exact {desired*1000:.0f} mm local -Z clearance unavailable"
            )

        distance = desired - self.clearance_step
        while distance + 1e-12 >= self.min_preview_clearance:
            pose = translate_local_z(work_tool0, -distance)
            q, count = self.try_best_ik(
                pose, work_q, previous_q, avoid_collisions=True
            )
            if q is not None:
                self.get_logger().warning(
                    f"{label}: PREVIEW ONLY fallback uses "
                    f"{distance*1000:.0f} mm instead of {desired*1000:.0f} mm."
                )
                return q, distance, count, "REDUCED_PREVIEW_CLEARANCE"
            distance -= self.clearance_step

        raise RuntimeError(
            f"{label}: no collision-aware axial clearance IK from "
            f"{desired*1000:.0f} mm down to {self.min_preview_clearance*1000:.0f} mm"
        )

    def prepare(self):
        self.get_logger().info("Waiting for MoveIt FK/IK services...")
        if not self.fk.wait_for_service(timeout_sec=20.0):
            raise RuntimeError("/compute_fk not available")
        if not self.ik.wait_for_service(timeout_sec=20.0):
            raise RuntimeError("/compute_ik not available")

        self.publish_state("OPTIMIZING")
        sequence = []
        home_ref = self.reference["HOME"]
        previous = list(home_ref)
        sequence.append({
            "name": "HOME_START",
            "q": list(home_ref),
            "hold_s": 0.5,
            "kind": "HOME"
        })

        for name in self.order[1:]:
            ref_q = self.reference[name]
            work_tool0 = self.call_fk(ref_q)

            best_work, n_work = self.best_ik(work_tool0, ref_q, previous)

            # Desired clearance is 100 mm along suction TCP local -Z.
            # If exact 100 mm has no collision-aware IK, preview-only fallback
            # searches the longest shorter straight retreat, never silently.
            best_approach, clearance_used, n_app, clearance_status = self.resolve_clearance_pose(
                work_tool0, best_work, previous, name
            )
            clearance_mm = int(round(clearance_used * 1000.0))

            sequence += [
                {
                    "name": f"{name}_APPROACH_{clearance_mm}MM",
                    "q": best_approach,
                    "hold_s": 0.0,
                    "kind": "APPROACH",
                    "clearance_m": clearance_used,
                    "clearance_status": clearance_status,
                },
                {
                    "name": name,
                    "q": best_work,
                    "hold_s": self.hold_s,
                    "kind": "WORK"
                },
                {
                    "name": f"{name}_RETRACT_{clearance_mm}MM",
                    "q": best_approach,
                    "hold_s": 0.0,
                    "kind": "RETRACT",
                    "clearance_m": clearance_used,
                    "clearance_status": clearance_status,
                },
            ]

            self.get_logger().info(
                f"{name}: IK candidates work={n_work}, approach={n_app}, "
                f"clearance={clearance_used*1000:.0f}mm, status={clearance_status}"
            )
            previous = best_approach

        sequence.append({
            "name": "HOME_END",
            "q": list(home_ref),
            "hold_s": 0.5,
            "kind": "HOME"
        })
        self.sequence = sequence

        self.seq_index = 0
        self.q_current = list(self.sequence[0]["q"])
        self.q_start = list(self.q_current)
        self.publish_joint(self.q_current)
        self.publish_state("READY")
        self.done = self.step_mode
        self.publish_done()

        if not self.step_mode:
            self.moving = True
            self.seq_index = 1
            self.q_start = list(self.q_current)
            self.publish_state(f"MOVING:{self.sequence[self.seq_index]['name']}")

        self.create_timer(1.0 / self.rate_hz, self.tick)

    def _start_next(self, request, response):
        del request
        if not self.sequence:
            response.success = False
            response.message = "not ready"
            return response
        if not self.step_mode:
            response.success = False
            response.message = "step_mode=false"
            return response
        if self.moving:
            response.success = False
            response.message = "already moving"
            return response
        if self.finished:
            if not self.loop:
                response.success = False
                response.message = "finished"
                return response
            self.finished = False
            self.seq_index = 0
            self.q_current = list(self.sequence[0]["q"])

        nxt = self.seq_index + 1
        if nxt >= len(self.sequence):
            if self.loop:
                nxt = 0
            else:
                self.finished = True
                response.success = False
                response.message = "finished"
                return response

        self.seq_index = nxt
        self.segment_t = 0.0
        self.hold_t = 0.0
        self.q_start = list(self.q_current)
        self.moving = True
        self.done = False
        self.publish_done()
        self.publish_state(f"MOVING:{self.sequence[self.seq_index]['name']}")
        response.success = True
        response.message = f"START accepted -> {self.sequence[self.seq_index]['name']}"
        return response

    def finish_current(self):
        target = self.sequence[self.seq_index]
        self.q_current = list(target["q"])
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
        self.seq_index = nxt
        self.segment_t = 0.0
        self.hold_t = 0.0
        self.q_start = list(self.q_current)
        self.publish_state(f"MOVING:{self.sequence[self.seq_index]['name']}")

    def tick(self):
        if not self.sequence:
            return
        if not self.moving:
            self.publish_joint(self.q_current)
            return

        dt = 1.0 / self.rate_hz
        target = self.sequence[self.seq_index]

        if self.segment_t < self.segment_duration:
            self.segment_t = min(
                self.segment_duration, self.segment_t + dt
            )
            u = self.segment_t / self.segment_duration
            self.q_current = interpolate(self.q_start, target["q"], u)
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
