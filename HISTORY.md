# 개발 히스토리

## 2026-09-01

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

### V7 (현재)

- HOME + 각 작업점 TCP/joint posture 영구 저장 구조
- 좌표가 약 ±100 mm 변경되더라도 해당 포인트만 재티칭 가능하도록 설계
- 현재 pose 기준 approach IK를 다시 계산
- 기존 로봇 설치에서 사용하던 `Box_Gripper1` TCP / Payload 0.5 kg 정보를 설치 파일에 반영
- 기존 Physical AI 저장소와 완전히 분리하여 독립 프로젝트로 관리

## 주의

V4에서 사용자가 티칭했던 값은 제출된 `packing2.variables`에서 확인되지 않았습니다. 당시 파일에는 타임스탬프 외 `PACK_*` 저장값이 없었으므로 해당 좌표는 이 저장소에 복구하지 못했습니다.
