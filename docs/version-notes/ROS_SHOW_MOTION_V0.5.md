# ROS Show Motion Preview v0.5

## 목적

기존 v0.4 Performance Motion을 더 재미있는 시연 동작으로 확장하되, V10 생산 공정의 작업 TCP와 PLC 계약은 변경하지 않습니다.

## 모드

- `CLEAN`: 작은 arc, 추가 gesture 없음
- `LIVELY`: 기본값. 3D S-curve, PICK 후 CHECK_LIFT, precision SETTLE, HOME finale
- `SHOWMAN`: 더 큰 S-curve와 CHECK_LIFT, presentation hold, 더 큰 finale

## 정밀 구간

재미있는 동작은 TRANSIT 구간에만 추가합니다. WORK TCP는 기존 티칭 joint의 MoveIt FK 결과를 그대로 유지합니다.

- `P3_PRODUCT_INSERT`: V10 기준 local -Z 70 mm
- 나머지 공정점: local -Z 100 mm
- WORK hold: 3초

PICK 후 CHECK_LIFT 대상:

- `P1_BOX_PICK`
- `P4_PRODUCT_PICK`
- `P3_FINISHED_BOX_PICK`

## v0.4.1 안정화 포함

- 경로 계산 중 HOME `/joint_states` 20 Hz heartbeat
- RViz RobotModel TF 유지
- planned path용 반복 FK 제거
- expressive path continuous IK 실패 시 경로 크기 자동 축소
- 끝까지 실패하면 해당 TRANSIT만 preview-only direct joint transit로 경고 후 진행

## 검증 상태

- Python syntax parse: `PASS`
- trajectory unit tests: `6 passed`
- 실제 UR command 관련 금지 경로 정적 검사: `PASS`
- ROS 2 Jazzy v0.5 실제 runtime: `NOT_VERIFIED`
- 추가 S-curve / CHECK_LIFT의 실제 workcell collision: `NOT_VERIFIED`
- actual robot command: `NONE`
- actual robot motion: `NOT_ATTEMPTED`

## 실행

```bash
ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=lively
```

```bash
ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=showman
```

```bash
ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py motion_style:=clean
```

과거 `baseline`은 `clean`, `performance`는 `lively` alias로 유지합니다.
