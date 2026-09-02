# UR3 Packaging Automation

UR3 CB3 / PolyScope 3.15.x 기반 개인용 포장 자동화 프로젝트입니다.

> 이 저장소는 `ur3_visual_servoing` 및 Physical AI 프로젝트와 **완전히 별개의 개인용 작업**입니다.

## 현재 기준

- 현재 canonical 버전: **V10**
- 로봇: UR3 CB3 / PolyScope 3.15.x
- 운전 목표: 배포 후 PC/ROS 없이 PolyScope 단독 운전
- PLC handshake: **실제 공정 위치 7개에 대해서만 START 1회 -> 해당 공정 동작 전체 -> DONE 1회**
- HOME / APPROACH / RETRACT: UR 내부 경로이며 별도 START/DONE 없음
- 그리퍼: 일반 Control Box DO
- 장거리 자세전환: HOME 경유 `MOVEJ`
- 작업점 주변 짧은 접근/이탈: `MOVEL`
- 현장 위치 변경: 약 ±100 mm 수준은 해당 포인트 재티칭을 전제로 설계
- installation 이름: `UR3_PACKING_V10`로 독립하여 기존 `packing2`와 이름 충돌 방지
- V10 변경: P3 제품투입 접근/이탈만 70 mm, 각 STEP 직전 IK 검사, 시작 직후 DONE LOW 초기화

## V10 PLC 공정 handshake

한 사이클은 정확히 7개의 공정 handshake로 구성합니다.

1. `P1_BOX_PICK` — 새 박스 측면 파지 후 안전 이탈
2. `P2_BOTTOM_HOLD` — 밑판 접기 HOLD 위치 도착 후 DONE, 그 자리 유지
3. `P3_EMPTY_BOX_PLACE` — PLC 밑판 접기 완료 후 다음 START로 P2 이탈 및 빈 박스 배치
4. `P4_PRODUCT_PICK` — 제품 상부 파지 후 안전 이탈
5. `P3_PRODUCT_INSERT` — 제품 투입/해제 후 70 mm lid backoff까지 이동한 뒤 DONE
6. `P3_FINISHED_BOX_PICK` — PLC 뚜껑 닫기 완료 후 다음 START로 완성 박스를 측면 재파지
7. `P4_FINISHED_BOX_PLACE` — 완성 박스 배치/이탈/HOME 복귀 후 DONE

HOME/APPROACH/RETRACT는 공정 내부 경로이며 PLC 신호를 추가로 요구하지 않습니다.

## ROS Natural Motion Preview

실물 구동 전 동작 확인을 위한 **ROS 2 Jazzy + MoveIt + RViz 전용 미리보기**를 별도로 관리합니다.

```text
ros/ur3_natural_motion_preview/
```

현재 상태는 다음처럼 구분합니다.

- canonical source: **v0.4.0**
- 실제 ROS runtime 검증 완료 candidate: **v0.7.0**
- 최신 구현 candidate: **v0.8.0 — Hybrid VIA + Wrist Coordination**
- production V10 변경: 없음
- 실제 UR3 command path: 없음

공통 기준:

- 사용자 제공 HOME + 공정점 7개 실제 관절 자세를 FK로 TCP pose로 복원
- Ø20 × 80 mm 공압 흡착기, `tool0 +Z`, TCP `+80 mm`
- V10 기준 clearance: `P3_PRODUCT_INSERT=70 mm`, 나머지 공정점 `100 mm`
- 작업점 정지: 3초
- 실제 controller/servo graph와 분리하기 위해 `ROS_DOMAIN_ID=77` 권장

### v0.7 실제 런타임 결과

- sequential IK branch propagation: `VERIFIED`
- `IK_BRANCH_REPAIRED`: 실제 동작 확인
- v0.6에서 검출된 P3 finished-pick wrist 급점프를 그대로 통과시키지 않도록 개선
- P4_PRODUCT_PICK: show path 0.82 scale에서 연결
- P3_PRODUCT_INSERT: show path 0.28 scale에서 연결
- P3_FINISHED_BOX_PICK: Cartesian show route는 `BLOCKED_NO_IK`, preview-only direct fallback 사용
- 해당 fallback은 J5 peak-to-peak 약 `152.2°`로 wrist motion 집중 문제가 남음
- HOME_RETURN: soft joint envelope에서 Whole-body 취소

### v0.8 candidate

v0.8은 실패한 두 구간만 전용 경로로 보강합니다.

- `P3_FINISHED_BOX_PICK`: `CLEARANCE VIA -> WRIST TRANSITION VIA -> PRE-PICK VIA -> 100 mm APPROACH`
- fallback IK: 이전 q 연속성 + J4/J5/J6 과도 회전 억제 weighted score
- `HOME_RETURN`: `UNWIND VIA -> HOME`
- v0.7 branch continuity / joint-specific Whole-body 구조 유지
- static/pure tests: `18 PASSED`
- actual ROS runtime: `NOT_VERIFIED`

상세 기록:

- [`docs/version-notes/ROS_PREVIEW_V07_CONTINUOUS_WHOLE_BODY.md`](docs/version-notes/ROS_PREVIEW_V07_CONTINUOUS_WHOLE_BODY.md)
- [`docs/version-notes/ROS_PREVIEW_V08_HYBRID_VIA_WRIST_COORDINATION.md`](docs/version-notes/ROS_PREVIEW_V08_HYBRID_VIA_WRIST_COORDINATION.md)

> Preview 내부 TRANSIT/APPROACH/WORK/RETRACT/VIA는 디버그/경로 설계 개념입니다. 실제 V10의 PLC 계약은 여전히 **공정 위치 7개 START/DONE**입니다.

## 현재 배포 파일

```text
deploy/current/
  UR3_PACKING_V10.urp
  UR3_PACKING_V10.script
  UR3_PACKING_V10.installation
  UR3_PACKING_V10.variables

releases/
  UR3_PACKING_V10_READY.zip
```

## 검증 상태

- V10 script 논리/handshake 개수 오프라인 검사: `PASS`
- V10 URP/installation gzip XML 구조: `PASS`
- P3 제품투입 70 mm 전용 clearance 반영: `PASS_STATIC`
- 각 STEP 직전 IK 검사 구조: `PASS_STATIC`
- 프로그램 시작 시 DONE LOW 초기화: `PASS_STATIC`
- 기존 `packing2` 이름 충돌 제거: `PASS`
- Installation Variables 실제 `.variables` 파일 저장: `VERIFIED_ON_V9_DATA`
- ROS Natural Motion Preview v0.2: `PARTIAL_PASS`
- ROS Natural Motion Preview v0.7 Continuous Whole-Body runtime: `VERIFIED_WITH_REMAINING_ROUTE_LIMITATIONS`
- ROS Natural Motion Preview v0.8 Hybrid VIA candidate: `IMPLEMENTED / 18_TESTS_PASS / RUNTIME_NOT_VERIFIED`
- 실제 V10 PolyScope parser acceptance: `NOT_VERIFIED`
- 전원 재부팅 후 installation variable persistence: `NOT_VERIFIED`
- 실제 V10 PLC handshake: `NOT_VERIFIED`
- 실제 V10 전체 로봇 모션: `NOT_VERIFIED`

실물 검증 전에는 낮은 속도에서 단계별로 확인하십시오.
