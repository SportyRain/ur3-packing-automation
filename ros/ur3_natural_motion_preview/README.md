# UR3 Natural Motion Preview v0.4 — Performance Motion

ROS 2 Jazzy + MoveIt + RViz에서 실물 UR3를 움직이지 않고 포장 동작을 시각 검증합니다.

## v0.4 핵심

기존 v0.3은 관절 목표 사이를 부드럽게 보간했기 때문에 속도 변화는 부드러워도 경로 자체가 로봇처럼 보였습니다.

v0.4는 별도의 Motion Style Layer를 추가합니다.

```text
작업 TCP
  ↓
Motion Style Layer
  ↓
Cartesian cubic Bezier 장거리 이동
  ↓
손목 방향 선행 정렬
  ↓
continuous IK
  ↓
Cartesian 직선 APPROACH / RETRACT
  ↓
minimum-jerk 시간 진행
  ↓
RViz
```

지원 style:

- SIDE_PICK
- LOW_APPROACH
- SIDE_PLACE
- TOP_PICK
- TOP_INSERT

작업점의 정확한 TCP 위치/방향은 기존 티칭 관절각으로 FK 복원한 값을 그대로 유지합니다.
바뀌는 것은 작업점 사이의 이동 경로입니다.

장거리 TRANSIT는 두 내부 control point를 사용하는 cubic Bezier 아치 경로입니다.
orientation은 위치 도착보다 먼저 목표 방향에 가까워져 마지막 순간 wrist snap을 줄입니다.
APPROACH / RETRACT는 Cartesian 직선 pose를 샘플링하고 이전 IK 해를 seed로 연속 IK를 계산합니다.

## 비교 실행

Performance:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur_projects/ur3_preview_ws/install/setup.bash && ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=performance
```

기존 방식:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur_projects/ur3_preview_ws/install/setup.bash && ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=baseline
```

RViz의 `/preview/path`에 계획된 TCP 경로도 표시합니다.

## 안전/검증 경계

- 실물 UR command path: 없음
- URScript / RTDE / trajectory controller / robot IP 연결: 없음
- V10 기준: P3_PRODUCT_INSERT는 local -Z 70 mm, 나머지 공정점은 100 mm
- 각 공정의 목표 clearance가 불가능하면 preview-only fallback 정책 유지
- 주변 설비 3D geometry가 없으므로 performance arc의 실제 설비 충돌은 NOT_VERIFIED
- v0.4 실제 Ubuntu ROS 2 Jazzy runtime: NOT_VERIFIED
- 실제 UR3 motion: NOT_ATTEMPTED
