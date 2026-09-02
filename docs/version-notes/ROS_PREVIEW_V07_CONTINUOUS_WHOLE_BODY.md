# ROS Natural Motion Preview v0.7 — Continuous Whole-Body

## 배경

v0.6 실제 ROS 런타임 로그에서 7개 작업점 IK/clearance 생성과 Whole-body participation 동작은 확인되었습니다.

특히 다음은 정상 확인되었습니다.

- P1_BOX_PICK: clearance 100 mm
- P2_BOTTOM_HOLD: clearance 100 mm
- P3_BOX_PLACE: clearance 100 mm
- P4_PRODUCT_PICK: clearance 100 mm
- P3_PRODUCT_INSERT: V10 기준 clearance 70 mm
- P3_FINISHED_BOX_PICK: clearance 100 mm
- P4_BOX_PLACE: clearance 100 mm
- P2_BOTTOM_HOLD J5 participation: 1.8° → 8.7°

하지만 `P3_FINISHED_BOX_PICK_TRANSIT`에서 인접 sample jump가 다음처럼 검출되었습니다.

```text
J4 = 65.4°
J5 = 58.2°
J6 = 87.6°
```

추가 Whole-body gesture 자체보다 훨씬 큰 값이므로 v0.7은 IK branch continuity를 먼저 해결하도록 구조를 변경했습니다.

## v0.7 핵심 변경

- 각 작업점에서 독립적으로 선택한 endpoint q를 강제로 이어 붙이는 방식 제거
- 이전 구간의 실제 마지막 q를 다음 구간 시작 q로 그대로 전달
- 작업점 TCP pose는 authoritative 유지
- 기존 work/approach q는 IK seed/reference로만 사용
- per-sample IK branch jump guard 추가
  - J1/J2/J3: 24°
  - J4/J5: 30°
  - J6: 34°
- 이전 q seed에서 branch jump 발생 시 local wrist/shoulder/elbow seed 후보 탐색
- 연속 branch 후보가 없으면 Cartesian show arc를 단계적으로 축소
- 모두 실패하면 preview-only dense joint transit fallback
- Whole-body objective를 모든 관절 동일 8°에서 관절별 목표로 변경
  - LIVELY: `[5, 7, 7, 5, 4, 4]°`
  - SHOWMAN: `[8, 10, 10, 7, 6, 5]°`
- 이미 충분히 움직이는 관절은 추가 choreography를 넣지 않음
- 작업별 Whole-body 강도 자동 축소
  - P3_PRODUCT_INSERT: 35%
  - P3_FINISHED_BOX_PICK: 70%
  - P4_BOX_PLACE: 60%
  - HOME: 60%
- Whole-body candidate가 envelope/jump guard를 넘으면 `100% → 75% → 50% → 25%`로 자동 축소
- Precision APPROACH / SETTLE / WORK / RETRACT에는 Whole-body layer를 적용하지 않음

## 검증

- Python static parse: PASS
- pure trajectory tests: 15 passed
- v0.6에서 관측된 `65.4° / 58.2° / 87.6°` wrist jump를 branch guard unit test가 거부함: PASS
- endpoint-preserving Whole-body choreography: PASS
- joint-specific participation objective: PASS
- 실제 UR command path 정적 검사: NONE
- 실제 Ubuntu ROS 2 Jazzy v0.7 runtime: NOT_VERIFIED
- workcell collision validation: NOT_VERIFIED
- physical robot motion: NOT_ATTEMPTED

## 상태

이 문서는 v0.7 candidate 구현 기록입니다. 실제 ROS runtime 검증 전까지 production V10 파일은 변경하지 않으며, 기존 production PLC 계약 7회 START/DONE도 변경하지 않습니다.
