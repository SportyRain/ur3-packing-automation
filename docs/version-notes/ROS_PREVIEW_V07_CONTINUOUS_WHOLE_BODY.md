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

## 정적 검증

- Python static parse: PASS
- pure trajectory tests: 15 passed
- v0.6에서 관측된 `65.4° / 58.2° / 87.6°` wrist jump를 branch guard unit test가 거부함: PASS
- endpoint-preserving Whole-body choreography: PASS
- joint-specific participation objective: PASS
- 실제 UR command path 정적 검사: NONE

## 실제 ROS 런타임 — 2026-09-03

사용자가 Ubuntu / ROS 2 Jazzy에서 `ROS_DOMAIN_ID=77`, `motion_style:=lively`로 실행한 로그를 기준으로 v0.7 runtime을 검증했습니다.

### VERIFIED

- `P1_BOX_PICK_TRANSIT`: CONTINUOUS_WHOLE_BODY 실행
- `P2_BOTTOM_HOLD_TRANSIT`: CONTINUOUS_WHOLE_BODY 실행
- `P3_BOX_PLACE_TRANSIT`: CONTINUOUS_WHOLE_BODY 실행
- `P4_PRODUCT_PICK_TRANSIT`: 1.00 경로에서 NO_IK 후 0.82로 축소하여 branch-continuous IK 성공
- `P3_PRODUCT_INSERT_TRANSIT`: 1.00/0.82/0.64/0.46 실패 후 0.28에서 branch-continuous IK 성공
- `P3_FINISHED_BOX_PICK_TRANSIT`: v0.6의 대형 wrist jump 대신 다수의 `IK_BRANCH_REPAIRED`가 작동하여 인접 sample 이동을 제한
- `P4_BOX_PLACE_TRANSIT`: CONTINUOUS_WHOLE_BODY 실행

### 남은 문제

`P3_FINISHED_BOX_PICK_TRANSIT`은 branch repair 자체는 동작했지만 Cartesian show path는 끝까지 연결되지 않았습니다.

- scale 1.00: 후반 NO_IK
- scale 0.82: 후반 NO_IK
- scale 0.64: 후반 NO_IK
- scale 0.46: 후반 NO_IK
- scale 0.28: NO_IK
- 최종 `PREVIEW ONLY branch-safe direct joint transit` 사용

fallback 경로의 peak-to-peak 참여도:

```text
J1  15.7°
J2  30.5°
J3  86.5°
J4  38.5°
J5 152.2°
J6   2.5°
```

따라서 대형 branch jump 문제는 개선됐지만 J5에 회전이 과도하게 집중되는 문제는 남았습니다.

HOME_RETURN도 base path가 soft joint envelope를 넘어 Whole-body layer가 취소되었습니다.

### v0.7 최종 판정

- ROS 2 Jazzy runtime: `VERIFIED`
- branch continuity repair: `VERIFIED`
- v0.6 wrist branch jump regression: `RESOLVED_BY_GUARD/REPAIR`
- P3_FINISHED_BOX_PICK Cartesian show route: `BLOCKED_NO_IK`
- P3_FINISHED_BOX_PICK direct fallback: `WORKING_BUT_J5_DOMINANT`
- HOME_RETURN whole-body: `BLOCKED_BY_SOFT_ENVELOPE`
- workcell collision validation: `NOT_VERIFIED`
- physical robot motion: `NOT_ATTEMPTED`

## 상태

v0.7은 **runtime verified intermediate candidate**입니다. Production V10 파일과 실제 PLC 공정 handshake 7회 계약은 변경하지 않습니다. 남은 두 문제는 v0.8에서 전용 Hybrid VIA / wrist coordination 전략으로 다룹니다.
