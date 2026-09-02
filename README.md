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

실물 구동 전 동작 확인을 위한 **ROS 2 Jazzy + MoveIt + RViz 전용 미리보기**를 별도로 보관합니다.

```text
ros/ur3_natural_motion_preview/
```

- 현재 preview 버전: **v0.3.0**
- 실제 V10 배포 로직을 대체하지 않음
- URScript/RTDE/trajectory controller/robot IP 제어 경로 없음
- 사용자 제공 8개 실제 관절 자세를 FK로 TCP pose로 복원
- Ø20 × 80 mm 공압 흡착기, `tool0 +Z`, TCP `+80 mm`
- 각 작업점에서 TCP local `-Z` 방향 100 mm approach/retract 목표
- 작업점 정지: 3초
- 자세 선택: multi-seed IK + 관절 연속성/손목 회전/관절여유 score
- v0.2 실측 런타임에서 `P3_PRODUCT_INSERT`의 exact 100 mm approach IK가 0개로 확인됨
- v0.3은 **미리보기에서만** 95→40 mm까지 가장 긴 도달 가능한 직선 clearance를 탐색하고 명시적 경고
- 실제 controller/servo 그래프와 섞이지 않도록 `ROS_DOMAIN_ID=77` 권장

상세 상태와 런타임 기록은 [`docs/ROS_NATURAL_MOTION_PREVIEW.md`](docs/ROS_NATURAL_MOTION_PREVIEW.md)를 봅니다.

> Preview의 `step_mode`는 APPROACH/WORK/RETRACT를 한 단계씩 검사하는 디버그 기능입니다. 실제 V10의 PLC 계약은 여전히 **공정 위치 7개 START/DONE**입니다.

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
- 실제 V10 PolyScope parser acceptance: `NOT_VERIFIED`
- 전원 재부팅 후 installation variable persistence: `NOT_VERIFIED`
- 실제 V10 PLC handshake: `NOT_VERIFIED`
- 실제 V10 전체 로봇 모션: `NOT_VERIFIED`

실물 검증 전에는 낮은 속도에서 단계별로 확인하십시오.
