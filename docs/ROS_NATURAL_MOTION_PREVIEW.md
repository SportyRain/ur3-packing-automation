# ROS Natural Motion Preview 기록

## 목적

실물 UR3를 움직이기 전에 ROS 2 Jazzy / MoveIt / RViz에서 포장 동작의 자세와 접근/후퇴 경로를 확인합니다. 이 기능은 **V10 PolyScope standalone 배포 로직을 대체하거나 변경하지 않습니다.**

## 확정된 입력

### 로봇

- UR3 CB3 / Classic
- ROS 2 Jazzy
- factory calibration: `/home/rosystem/ur3_factory_calibration.yaml`

### 공압 흡착기

- 형태: 원통형 공압 흡착기
- 직경: 20 mm
- 길이: 80 mm, 어댑터 포함
- 장착: tool0 중심과 일치
- 방향: `tool0 +Z`
- TCP: 흡착면 중심 = `tool0 +Z 0.080 m`

### 작업 규칙

- 사용자 제공 실제 관절 자세: HOME + 공정점 7개, 총 8개
- 실제 작업점 정지 시간: 3초
- V10 기준 approach/retract: `P3_PRODUCT_INSERT=70 mm`, 나머지 공정점 `100 mm`
- 속도 튜닝: 현재 범위에서 제외
- 주변 설비 모델: 아직 없음

## 실제 기준 관절각 (degree)

```text
HOME                  [   2.61,  -70.43, -110.80,  -85.86,   90.46, -33.06 ]
P1 BOX PICK           [ 115.73,  -88.33, -123.03,  -55.28,   87.39, -33.05 ]
P2 BOTTOM HOLD        [  46.00, -107.85,  -81.28,  -80.83,   88.97,  46.68 ]
P3 BOX PLACE          [ -13.91, -123.81, -116.06,   50.80,  101.38,  45.39 ]
P4 PRODUCT PICK       [ -66.94, -124.02,  -60.14,  -81.42,   93.65,  45.39 ]
P3 PRODUCT INSERT     [ -11.29, -108.37,  -59.93, -100.80,   88.99,  45.47 ]
P3 FINISHED BOX PICK  [ -16.11, -104.28,  -93.57, -165.55, -108.52,  46.02 ]
P4 BOX PLACE          [ -51.00, -132.90,  -65.43, -173.55,  -48.15,  52.98 ]
```

## v0.2~v0.3 기준 자세 생성

1. 기존 관절각을 MoveIt FK에 넣어 각 작업점의 `tool0` pose를 복원합니다.
2. 고정 TCP offset(`+Z 80 mm`)이므로 동일 `tool0` pose를 유지하면 동일 흡착 TCP pose가 유지됩니다.
3. 여러 IK seed에서 후보를 생성합니다.
4. 이전 자세 연속성, shoulder/elbow branch, wrist 회전, 관절 중앙 여유, 원래 티칭자세 prior로 score합니다.
5. 작업 pose의 local `-Z` clearance pose에서 approach/retract IK를 계산합니다.

## v0.2 실제 ROS 런타임 evidence

```text
P1_BOX_PICK:          work=28, approach=27
P2_BOTTOM_HOLD:       work=14, approach=17
P3_BOX_PLACE:         work=24, approach=25
P4_PRODUCT_PICK:      work=26, approach=30
P3_PRODUCT_INSERT:    exact 100 mm approach IK candidate = 0
```

판정:

- FK/IK 연결: `VERIFIED`
- P1~P4 work/approach IK: `VERIFIED`
- P3_PRODUCT_INSERT exact 100 mm axial approach: `BLOCKED`
- 실제 UR3 motion: `NOT_ATTEMPTED`

이 결과와 실제 데이터 검토를 반영해 생산 V10은 `P3_PRODUCT_INSERT`만 70 mm로 변경되었습니다.

## v0.4 Performance Motion

사용자 피드백은 기존 joint-to-joint minimum-jerk 재생이 여전히 너무 로봇처럼 보인다는 것이었습니다. 따라서 v0.4는 **시간 프로파일만 부드럽게 하는 방식에서 경로 자체를 설계하는 방식**으로 확장했습니다.

### Motion Style Layer

공정별 style:

```text
P1_BOX_PICK            SIDE_PICK
P2_BOTTOM_HOLD         LOW_APPROACH
P3_BOX_PLACE           SIDE_PLACE
P4_PRODUCT_PICK        TOP_PICK
P3_PRODUCT_INSERT      TOP_INSERT
P3_FINISHED_BOX_PICK   SIDE_PICK
P4_BOX_PLACE           SIDE_PLACE
```

### 장거리 TRANSIT

- 시작 TCP와 도착 APPROACH TCP는 그대로 유지
- 두 내부 control point를 자동 생성
- Cartesian cubic Bezier curve로 lift + arc 경로 생성
- 공정별 `lift_m`, `arc_side_m` 값 사용
- 각 pose sample을 이전 IK 해로 seed하여 branch continuity 유지
- 내부 VIA는 PLC point가 아니며 중간 정지하지 않음

### 손목 orientation

- quaternion SLERP 사용
- 위치 진행률보다 orientation 진행률을 앞당김
- 목표 위치 직전에 wrist가 갑자기 돌아가는 동작을 줄이는 목적

### APPROACH / RETRACT

- 작업점과 clearance point 사이를 Cartesian 직선 pose sample로 생성
- 각 sample을 continuous IK로 해결
- TRANSIT처럼 장식 arc를 넣지 않음
- 실제 공정점 TCP 위치/방향은 변경하지 않음

### 재생

- TRANSIT: sampled continuous IK q path + Catmull-Rom + minimum-jerk 진행률
- APPROACH/RETRACT: sampled q polyline + minimum-jerk 진행률
- `motion_style:=performance`와 `motion_style:=baseline` 비교 지원

### RViz path 표시

```text
/preview/path
```

계획된 TCP path를 LINE_STRIP marker로 표시하여 baseline과 performance path 형태를 눈으로 비교할 수 있습니다.

## 실행

Performance:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur_projects/ur3_preview_ws/install/setup.bash && ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=performance
```

Baseline:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur_projects/ur3_preview_ws/install/setup.bash && ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=baseline
```

## 안전 경계

Preview package에는 다음 실물 제어 경로가 없습니다.

- UR robot IP 연결
- `FollowJointTrajectory`
- ros2_control controller command
- URScript sender
- Dashboard client
- RTDE client

사용하는 것은 FK/IK service, `/joint_states` 시각화, RViz marker뿐입니다.

주변 테이블/박스/설비의 3D collision geometry는 아직 없으므로, performance arc가 실제 설비와 충돌하지 않는다는 판정은 **NOT_VERIFIED**입니다.

## V10과의 관계

- V10 production PLC 계약: **공정점 7개 START/DONE**
- HOME/APPROACH/RETRACT/내부 performance VIA: 공정 내부 경로
- preview `step_mode`: 내부 경로를 따로 멈춰보는 디버그 기능
- 따라서 preview의 DONE은 실제 PLC 계약으로 해석하지 않습니다.

## 현재 상태

- Preview source: `ros/ur3_natural_motion_preview/`
- Version: `0.4.0`
- production reference: `V10`
- static Python parse: `PASS`
- performance math endpoint tests: `PASS_STATIC`
- physical command path: `NONE_STATIC_VERIFIED`
- v0.4 actual ROS runtime: `NOT_VERIFIED`
- scene collision validation: `NOT_VERIFIED`
- physical robot motion: `NOT_ATTEMPTED`
