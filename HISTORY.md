# 개발 히스토리

## 2026-09-01~2026-09-02

### 초기 요구사항

- UR3 CB3가 PC 없이 PolyScope에서 단독 실행
- PLC와 시작/완료 handshake
- 공압 그리퍼 사용
- 현장에서 포인트 수정 가능
- P3는 작업별 접근 방향이 다름
  - 빈 박스 배치: 측면
  - 제품 투입: 위
  - 완성박스 재파지: 측면

### V1~V3

- 단일 `.script` 중심 구현
- 티칭 메뉴 추가
- Installation 변수 저장 방식 검토
- 초기에 그리퍼 I/O 종류를 Tool DO로 잘못 추정한 적이 있었음
- 이후 사용자 확인으로 일반 Control Box DO로 수정

### V4

- 일반 Control Box DI/DO 사용
- 모든 이동 포인트마다 PLC START/DONE handshake
- P2 밑판 접기와 P3 뚜껑 닫기는 PLC가 다음 START를 주지 않는 방식으로 인터록
- 문제점: TCP pose 중심 이동이라 서로 다른 station 사이에서 로봇 자체 관절 자세가 좋지 않은 경로를 선택할 수 있었음

### V5

- 티칭 시 TCP pose와 6축 joint posture 저장
- `qnear` 기반 IK branch 유지
- 장거리 `MOVEJ`, 작업점 근처 `MOVEL` hybrid 도입
- 문제점: 끝점 IK branch만 보정해도 station-to-station 경로 전체를 보장하지 못함

### V6

- 사용자 정의 HOME joint posture 도입
- 서로 다른 작업 위치 사이 장거리 이동을 HOME 경유 `MOVEJ`로 변경
- 작업점 주변에만 짧은 `MOVEL` 사용

### V7

- HOME + 각 작업점 TCP/joint posture 저장 구조
- 좌표가 약 ±100 mm 변경되더라도 해당 포인트만 재티칭 가능하도록 설계
- 현재 pose 기준 approach IK를 다시 계산
- 실제 UR3 CB3 / PolyScope 3.15.8 팬던트에서 `getj()` 함수 미정의 컴파일 오류 확인
- 상태: `COMPILE_BLOCKED`

### V8

- 모든 `getj()` 호출을 `get_actual_joint_positions()`로 수정
- HOME 경유 MOVEJ / 작업점 주변 MOVEL 구조 유지
- 문제점: `HOME`, `APPROACH`, 실제 작업점, `RETRACT` 각각에 START/DONE이 들어가 한 사이클에 약 29회의 handshake를 요구
- 사용자가 요구한 것은 보조 경로가 아니라 **실제 공정 위치마다 1회의 START/DONE**임을 재확인

### V9

- PLC handshake 단위를 **공정 위치 7개**로 수정
- HOME / APPROACH / RETRACT는 UR 내부 경로로만 사용하고 별도 START/DONE 제거
- 한 사이클 START/DONE = 정확히 7회
- P2는 HOLD 위치에 도착하면 DONE 후 그대로 유지하며, PLC가 밑판 접기를 완료한 뒤 다음 START가 들어와야 P2를 이탈
- P3 제품 투입 단계는 제품 투입/해제 후 lid backoff까지 완료한 시점에 DONE
- PLC는 뚜껑 닫기가 끝날 때까지 다음 START를 보류하고, 다음 START에서 완성 박스를 측면 재파지
- 마지막 P4 배치는 배치/이탈/HOME 복귀 후 DONE
- `get_actual_joint_positions()` 수정 유지
- 기존 `packing2`를 덮어쓰지 않도록 installation 이름을 `UR3_PACKING_V9`로 독립
- V9 script handshake 구조 오프라인 검사: `PASS`
- V9 URP/installation gzip XML 구조 검사: `PASS`
- 사용자 제공 실제에 가까운 Installation Variables에서 HOME + 7개 작업점 + I/O 값이 실제 `.variables` 파일에 저장되는 것을 확인
- P3 제품투입 local `-Z` 100 mm 접근점에서 실제 팬던트 `MOTION BLOCKED` 확인

### V10 (현재)

- V9의 전체 구조는 유지하고 실제 데이터 검토에서 확인된 3개 항목만 최소 수정
- `P3_PRODUCT_INSERT`의 접근/이탈 거리만 100 mm → **70 mm**로 변경
- 나머지 작업점은 기존 `PACK_CLEARANCE=0.100 m` 유지
- 7개 접근점 IK를 사이클 시작에 모두 선계산하지 않고 **각 공정 STEP 직전 해당 STEP만 검사**하도록 변경
- 뒤쪽 STEP의 IK 문제가 P1 시작 전에 전체 사이클을 막지 않도록 수정
- 저장된 I/O 설정이 유효하면 프로그램 시작 직후 `PACK_DO_POINT_DONE`을 LOW로 초기화
- I/O 수정 후에도 새 DONE 출력에 LOW를 다시 적용
- PLC 계약은 1사이클 정확히 7회 START/DONE으로 유지
- HOME / APPROACH / RETRACT는 내부 경로로 유지
- HOME 경유 MOVEJ / 작업점 주변 MOVEL / Standard Control Box DI/DO / `get_actual_joint_positions()` 유지
- 사용자가 제공한 거의 실제 HOME + 7개 작업점 + I/O 값을 `UR3_PACKING_V10.variables`에 보존
- 오프라인 7 START / 7 DONE 검사: `PASS`
- URP/installation gzip XML parse: `PASS`
- 실제 V10 PolyScope parser / PLC / 전체 모션: `NOT_VERIFIED`
- V10 이전 실물 시험에서 관절 한계 또는 비정상 정지는 사용자 관찰상 `NOT_OBSERVED`

### ROS Natural Motion Preview v0.1~v0.3 (실물 전 시각 검증, 생산 런타임과 분리)

목적은 생산 URScript를 즉시 변경하는 것이 아니라, **실물 구동 전 ROS/RViz에서 자연스러운 자세와 접근/후퇴를 먼저 확인**하는 것입니다.

확정 입력:

- UR3 CB3 / ROS 2 Jazzy
- factory calibration: `/home/rosystem/ur3_factory_calibration.yaml`
- 실제 joint posture 8개: HOME + 공정점 7개
- 흡착기: 원통 Ø20 mm, 길이 80 mm(어댑터 포함), tool0 중심 일치, `+Z`
- TCP: 흡착면 중심 = `tool0 +Z 80 mm`
- 작업점 정지: 3초
- 접근/후퇴 목표: TCP local `-Z 100 mm`
- 속도 튜닝: 현재 범위에서 제외
- 사용자 조건: 각 작업점에서 100 mm 후퇴 시 주변 설비 충돌 없음

v0.2 구현:

- 사용자 joint posture → MoveIt FK → 작업 pose 복원
- 같은 작업 pose에 대해 multi-seed IK 후보 생성
- 이전 자세 연속성, shoulder/elbow 급변, wrist 불필요 회전, 관절 중앙 여유, 원래 티칭 자세 prior로 후보 score
- 5차 minimum-jerk joint interpolation
- Ø20×80 mm suction marker 시각화
- 실물 제어 경로 없음

실제 v0.2 런타임 결과:

- `P1_BOX_PICK`: work IK 28 / approach IK 27
- `P2_BOTTOM_HOLD`: work IK 14 / approach IK 17
- `P3_BOX_PLACE`: work IK 24 / approach IK 25
- `P4_PRODUCT_PICK`: work IK 26 / approach IK 30
- `P3_PRODUCT_INSERT`: exact local `-Z 100 mm` approach에서 IK candidate 0 → fail-closed 종료

v0.3 수정:

- exact 100 mm collision-aware IK를 최우선 유지
- 실패 시 100 mm kinematic-only IK를 추가 확인하여 원인 분류
- **미리보기에서만** 95, 90, 85 ... 40 mm 순으로 가장 긴 collision-aware 직선 후퇴를 탐색
- 축소 시 `PREVIEW ONLY fallback`과 실제 사용 거리를 명시
- 40 mm까지도 없으면 fail-closed
- 기존 PC에 실제 `controller_manager`, `servo_node`, UR controller가 살아 있던 점을 반영해 `ROS_DOMAIN_ID=77` 격리 권장
- v0.3 실제 Ubuntu 재실행: `NOT_VERIFIED`
- 실제 UR3 motion: `NOT_ATTEMPTED`

주의: preview의 `step_mode`는 APPROACH/WORK/RETRACT 단위 디버그용이며, **V10의 실제 PLC 공정 handshake 7회 계약을 변경하지 않습니다.**

## 주의

V4에서 사용자가 티칭했던 값은 제출된 `packing2.variables`에서 확인되지 않았습니다. 당시 파일에는 타임스탬프 외 `PACK_*` 저장값이 없었으므로 해당 좌표는 이 저장소에 복구하지 못했습니다.
