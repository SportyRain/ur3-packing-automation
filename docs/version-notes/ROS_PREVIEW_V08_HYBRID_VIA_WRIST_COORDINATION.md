# ROS Natural Motion Preview v0.8 — Hybrid VIA + Wrist Coordination

## 배경

v0.7 실제 ROS 2 Jazzy 런타임에서 branch continuity repair는 동작했고, v0.6에서 관측된 J4/J5/J6의 대형 sample jump는 더 이상 그대로 통과하지 않았습니다.

그러나 두 문제가 남았습니다.

### P3_FINISHED_BOX_PICK

Cartesian show route를 다음 scale까지 줄였지만 후반부에서 계속 `NO_IK`가 발생했습니다.

```text
1.00 → NO_IK
0.82 → NO_IK
0.64 → NO_IK
0.46 → NO_IK
0.28 → NO_IK
```

최종적으로 preview-only direct joint fallback을 사용했고, 해당 fallback의 peak-to-peak joint participation은 다음과 같았습니다.

```text
J1  15.7°
J2  30.5°
J3  86.5°
J4  38.5°
J5 152.2°
J6   2.5°
```

즉 branch jump는 억제됐지만 J5가 과도하게 큰 자세 변화를 담당했습니다.

### HOME_RETURN

HOME 복귀 base path가 soft joint envelope를 넘어 Whole-body layer가 취소되었습니다.

## v0.8 핵심 전략

v0.8은 전체 trajectory를 다시 크게 바꾸지 않고, 실패한 두 구간에만 전용 경로 전략을 사용합니다.

## 1. P3_FINISHED_BOX_PICK — HYBRID VIA

```text
현재 RETRACT 자세
      ↓
CLEARANCE VIA
      ↓
WRIST TRANSITION VIA
      ↓
PRE-PICK VIA
      ↓
기존 100 mm APPROACH
      ↓
WORK
```

목적:

- 먼저 위/옆으로 이동해 wrist transition 공간 확보
- 위치 이동과 큰 orientation 변화를 같은 순간에 강제하지 않음
- 열린 중간 공간에서 J4/J5/J6 orientation 변화 분산
- target TCP pose와 정밀 100 mm approach 계약은 그대로 유지

Hybrid VIA가 continuous IK를 만들지 못하면 기존 v0.7 show-path scale retry로 돌아가고, 그것도 실패할 때만 weighted direct fallback을 사용합니다.

## 2. Wrist-aware weighted fallback IK

fallback candidate score 우선순위:

1. 실제 이전 q와의 연속성
2. J4/J5/J6의 큰 회전 억제
3. 기존 reference posture는 약한 prior로만 사용

목적은 동일 TCP pose에서 가능한 여러 IK branch 중 한 wrist joint에 회전이 몰리는 해를 덜 선호하는 것입니다.

## 3. HOME_RETURN — UNWIND VIA

```text
현재 자세
    ↓
UNWIND VIA
    ↓
HOME
```

HOME을 한 번에 연결하지 않고 J4/J5/J6를 HOME 쪽으로 부분 정렬하는 중간 joint VIA를 둡니다.

목적:

- wrist winding을 shoulder/elbow 복귀와 한 순간에 몰지 않음
- HOME 복귀 중 한 관절의 과도한 회전 집중 감소
- v0.7 sequential branch propagation 구조 유지

## 그대로 유지하는 항목

- Production reference: V10
- PLC contract: 공정점 7개 START/DONE
- P3_PRODUCT_INSERT clearance: 70 mm
- 나머지 공정점 clearance: 100 mm
- WORK hold: 3초
- 작업 TCP pose: 기존 티칭 FK pose 유지
- ROS_DOMAIN_ID=77 격리 권장
- Precision APPROACH / SETTLE / WORK / RETRACT에 Whole-body layer 미적용
- 실제 UR robot IP / URScript / RTDE / controller command path 추가 없음

## 정적 검증

- Python static parse: PASS
- pure tests: 18 passed
- weighted fallback score가 큰 wrist winding 후보를 더 불리하게 평가: PASS
- HOME joint interpolation endpoint preservation: PASS
- Hybrid VIA source paths present: PASS
- hardware command path static check: NONE

## 현재 상태

- v0.7 ROS 2 Jazzy runtime: `VERIFIED`
- v0.7 branch repair: `VERIFIED`
- v0.7 P3_FINISHED_BOX_PICK Cartesian route: `BLOCKED_NO_IK`
- v0.7 direct fallback: `WORKING_BUT_J5_DOMINANT`
- v0.7 HOME_RETURN: `BLOCKED_BY_SOFT_ENVELOPE`
- v0.8 Hybrid VIA implementation: `IMPLEMENTED`
- v0.8 wrist-aware fallback selection: `IMPLEMENTED`
- v0.8 HOME UNWIND VIA: `IMPLEMENTED`
- v0.8 static/pure tests: `18 PASSED`
- v0.8 actual Ubuntu ROS 2 Jazzy runtime: `NOT_VERIFIED`
- scene/workcell collision validation: `NOT_VERIFIED`
- physical robot motion: `NOT_ATTEMPTED`

## 배포 경계

이 문서는 ROS preview candidate의 기록입니다. Production V10 URP/script/installation/variables와 실제 PLC handshake 계약은 변경하지 않습니다. v0.8 실제 ROS runtime 검증 전까지 canonical preview source는 기존 verified/recorded source와 구분합니다.
