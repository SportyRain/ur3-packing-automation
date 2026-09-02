# UR3 Natural Motion Preview v0.3

실물 UR3를 움직이지 않고 ROS 2 Jazzy + RViz에서 실제 작업 자세 기반의 자연스러운 패킹 동작을 확인합니다.

## 반영 조건

- UR3 CB3 / `ur_type:=ur3`
- factory calibration: `/home/rosystem/ur3_factory_calibration.yaml`
- 사용자 제공 실제 관절 자세 8개
- 공압 흡착기 Ø20 mm × 80 mm
- `tool0 +Z`, 중심 일치
- TCP = `tool0 +Z 0.080 m`
- 각 작업점 TCP local `-Z`로 100 mm 접근/후퇴
- 실제 작업점 정지 3초
- 속도 튜닝은 현재 범위에서 제외
- 100 mm 후퇴 시 충돌 없음: 사용자 조건
- 주변 설비 geometry는 아직 없음

## 자세 최적화

기존 관절각은 최종 답으로 고정하지 않습니다.

`기존 관절각 → MoveIt FK → tool0/TCP pose 복원 → multi-seed IK → 최적 posture 선택`

점수는 이전 자세와의 연속성, shoulder/elbow 급변 억제, wrist 불필요 회전 억제, 관절 중앙 여유, 기존 티칭자세에 대한 약한 prior를 사용합니다.

`APPROACH/RETRACT`는 작업 pose의 local `-Z 100 mm`에서 자동 IK 계산합니다.

## 안전 경계

이 패키지는 실제 UR 제어 경로를 포함하지 않습니다.

사용:
- `/compute_fk`
- `/compute_ik`
- `/joint_states`
- `/preview/gripper`
- `/preview/state`
- `/preview/done`
- `/preview/start_next`

사용하지 않음:
- UR robot IP
- ros2_control command
- trajectory controller action
- URScript
- Dashboard
- RTDE

`preview.launch.py`는 UR description + robot_state_publisher + MoveIt move_group만 실행하며 `ur_control.launch.py`를 실행하지 않습니다.

## 설치

ZIP을 `~/Downloads`에 둔 기준:

```bash
rm -rf ~/ur_projects/ur3_preview_ws/src/ur3_natural_motion_preview && mkdir -p ~/ur_projects/ur3_preview_ws/src && cd ~/ur_projects/ur3_preview_ws/src && unzip -o ~/Downloads/ur3_natural_motion_preview_v0.3.zip && cd .. && rosdep install --from-paths src --ignore-src -r -y && colcon build --symlink-install
```

## 자동 전체 재생

```bash
source ~/ur_projects/ur3_preview_ws/install/setup.bash && ros2 launch ur3_natural_motion_preview preview.launch.py
```

순서:

```text
HOME
→ P1 APPROACH → P1 BOX PICK [3 s] → P1 RETRACT
→ P2 APPROACH → P2 BOTTOM HOLD [3 s] → P2 RETRACT
→ P3 BOX PLACE ...
→ P4 PRODUCT PICK ...
→ P3 PRODUCT INSERT ...
→ P3 FINISHED BOX PICK ...
→ P4 BOX PLACE ...
→ HOME
```

## PLC처럼 한 위치씩 확인

```bash
source ~/ur_projects/ur3_preview_ws/install/setup.bash && ros2 launch ur3_natural_motion_preview preview.launch.py step_mode:=true loop:=false
```

다른 터미널:

```bash
source ~/ur_projects/ur3_preview_ws/install/setup.bash && ros2 service call /preview/start_next std_srvs/srv/Trigger "{}"
```

`step_mode`에서는 APPROACH, WORK, RETRACT 각각 정지 후 `/preview/done=true`가 됩니다. 이 모드는 경로 디버깅용이며, 실제 V9의 PLC 계약(공정 위치 7개 START/DONE)과 동일한 운전 계약이 아닙니다.

## 상태

- 입력 관절값 8개: VERIFIED
- degree→radian: VERIFIED
- gripper Ø20×80 / TCP +80 mm: IMPLEMENTED
- 100 mm local -Z 접근/후퇴: IMPLEMENTED
- 작업점 3초 정지: IMPLEMENTED
- multi-seed IK posture scoring: IMPLEMENTED
- minimum-jerk interpolation: VERIFIED
- Python syntax: VERIFIED
- 실제 로봇 명령 경로 부재: STATIC_VERIFIED
- Ubuntu ROS 2 Jazzy runtime: NOT_VERIFIED
- 실제 UR3 motion: NOT_ATTEMPTED


## v0.3 변경점

`P3_PRODUCT_INSERT`에서 exact TCP local `-Z 100 mm` 접근점의 IK가 0개인 실제 런타임 로그를 반영했습니다.

정책:

1. 100 mm collision-aware IK 우선
2. 실패하면 100 mm kinematic-only IK로 원인 분류
3. 미리보기에서만 95, 90, 85 ... mm 순으로 가장 긴 collision-aware 직선 후퇴를 탐색
4. 40 mm 미만까지도 없으면 fail-closed
5. 축소된 경우 터미널에 `PREVIEW ONLY fallback` 경고와 실제 사용 거리(mm)를 출력

이 fallback은 **실물 적용 승인값이 아닙니다.** ROS에서 동작을 보기 위한 미리보기용입니다.

### 중요: 실제 ROS 그래프와 완전 격리

현재 PC에 `controller_manager`, `servo_node`, 실제 UR 관련 노드가 이미 실행 중인 것이 확인되었습니다.
따라서 이 미리보기는 반드시 별도 ROS Domain에서 실행하는 것을 권장합니다.

```bash
export ROS_DOMAIN_ID=77
```

자동 재생:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur_projects/ur3_preview_ws/install/setup.bash && ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py
```

이렇게 하면 기존 실제 로봇 그래프와 discovery 자체가 분리됩니다.
