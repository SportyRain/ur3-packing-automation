# ROS Natural Motion Preview 기록

## 목적

실물 UR3를 움직이기 전에 ROS 2 Jazzy / MoveIt / RViz에서 포장 동작의 자세와 접근/후퇴 경로를 확인합니다. 이 기능은 **V9 PolyScope standalone 배포 로직을 대체하거나 변경하지 않습니다.**

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
- approach/retract 목표: TCP local `-Z 100 mm`
- 속도 튜닝: 현재 범위에서 제외
- 주변 설비 모델: 아직 없음
- 사용자 조건: 각 작업점에서 100 mm 후퇴 시 주변 설비 충돌 없음

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

## 자세 생성 원리

1. 기존 관절각을 MoveIt FK에 넣어 각 작업점의 `tool0` pose를 복원합니다.
2. 고정 TCP offset(`+Z 80 mm`)이므로 동일 `tool0` pose를 유지하면 동일 흡착 TCP pose가 유지됩니다.
3. 여러 IK seed에서 후보를 생성합니다.
4. 아래 score로 가장 연속적인 자세를 선택합니다.
   - 이전 자세와의 joint 이동량
   - shoulder/elbow 급격한 branch 전환 억제
   - wrist 불필요 회전 억제
   - 관절 한계 중앙 여유
   - 원래 티칭자세를 약한 prior로 유지
5. 작업 pose에서 TCP local `-Z`로 100 mm 이동한 pose의 IK를 approach/retract로 계산합니다.
6. RViz 재생은 5차 minimum-jerk 시간 스케일링을 사용합니다.

## v0.2 실제 ROS 런타임 evidence

실제 Ubuntu에서 preview node를 직접 실행하여 MoveIt FK/IK 서비스 연결까지 확인했습니다.

```text
P1_BOX_PICK:          work=28, approach=27
P2_BOTTOM_HOLD:       work=14, approach=17
P3_BOX_PLACE:         work=24, approach=25
P4_PRODUCT_PICK:      work=26, approach=30
P3_PRODUCT_INSERT:    exact 100 mm approach IK candidate = 0
```

`P3_PRODUCT_INSERT`에서 `RuntimeError: No IK candidate found for target pose`로 fail-closed 종료했습니다.

판정:

- FK/IK 연결: `VERIFIED`
- P1~P4 work/approach IK: `VERIFIED`
- P3_PRODUCT_INSERT work pose까지: 진입 성공
- P3_PRODUCT_INSERT exact 100 mm axial approach: `BLOCKED`
- 실제 UR3 motion: `NOT_ATTEMPTED`

## v0.3 변경

100 mm 목표는 유지하지만, **ROS 미리보기만 중단되지 않도록** 다음 fallback을 추가했습니다.

1. 100 mm collision-aware IK 시도
2. 실패 시 100 mm collision check off IK로 원인 분류
3. 미리보기에서만 95 → 90 → 85 → ... → 40 mm 순으로 가장 긴 collision-aware 직선 clearance 탐색
4. 축소된 경우 `PREVIEW ONLY fallback`과 사용 거리 출력
5. 40 mm까지도 없으면 fail-closed

이 fallback 거리는 실물 배포 승인값이 아닙니다.

### ROS 그래프 격리

실행 당시 동일 ROS domain에서 실제 UR 관련 노드가 다수 살아 있었습니다.

예: `controller_manager`, `scaled_joint_trajectory_controller`, `passthrough_trajectory_controller`, `servo_node`, `/ur3` 등.

따라서 preview는 다음처럼 별도 domain 사용을 권장합니다.

```bash
ROS_DOMAIN_ID=77 ros2 launch ur3_natural_motion_preview preview.launch.py
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

## V9와의 관계

- V9 production PLC 계약: **공정점 7개 START/DONE**
- HOME/APPROACH/RETRACT: 내부 경로
- preview `step_mode`: APPROACH/WORK/RETRACT를 따로 멈춰보는 **디버그 기능**
- 따라서 preview step_mode의 DONE은 실제 PLC 계약으로 해석하지 않습니다.

## 현재 상태

- Preview source: `ros/ur3_natural_motion_preview/`
- Version: `0.3.0`
- static Python parse: `PASS`
- degree→radian config: `PASS`
- v0.2 actual ROS runtime: `PARTIAL_PASS`
- v0.3 patched runtime: `NOT_VERIFIED`
- physical robot command: `NONE`
- physical robot motion: `NOT_ATTEMPTED`
