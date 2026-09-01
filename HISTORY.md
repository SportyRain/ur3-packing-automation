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

### V9 (현재)

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
- 실제 팬던트 parser/변수 persistence/PLC/실물 동작: `NOT_VERIFIED`

## 주의

V4에서 사용자가 티칭했던 값은 제출된 `packing2.variables`에서 확인되지 않았습니다. 당시 파일에는 타임스탬프 외 `PACK_*` 저장값이 없었으므로 해당 좌표는 이 저장소에 복구하지 못했습니다.
