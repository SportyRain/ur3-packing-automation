# UR3 Packaging Automation

UR3 CB3 / PolyScope 3.15.x 기반 개인용 포장 자동화 프로젝트입니다.

> 이 저장소는 `ur3_visual_servoing` 및 Physical AI 프로젝트와 **완전히 별개의 개인용 작업**입니다.

## 현재 기준

- 현재 canonical 버전: **V9**
- 로봇: UR3 CB3 / PolyScope 3.15.x
- 운전 목표: 배포 후 PC/ROS 없이 PolyScope 단독 운전
- PLC handshake: **실제 공정 위치 7개에 대해서만 START 1회 -> 해당 공정 동작 전체 -> DONE 1회**
- HOME / APPROACH / RETRACT: UR 내부 경로이며 별도 START/DONE 없음
- 그리퍼: 일반 Control Box DO
- 장거리 자세전환: HOME 경유 `MOVEJ`
- 작업점 주변 짧은 접근/이탈: `MOVEL`
- 현장 위치 변경: 약 ±100 mm 수준은 해당 포인트 재티칭을 전제로 설계
- installation 이름: `UR3_PACKING_V9`로 독립하여 기존 `packing2`와 이름 충돌 방지

## V9 PLC 공정 handshake

한 사이클은 정확히 7개의 공정 handshake로 구성합니다.

1. `P1_BOX_PICK` — 새 박스 측면 파지 후 안전 이탈
2. `P2_BOTTOM_HOLD` — 밑판 접기 HOLD 위치 도착 후 DONE, 그 자리 유지
3. `P3_EMPTY_BOX_PLACE` — PLC 밑판 접기 완료 후 다음 START로 P2 이탈 및 빈 박스 배치
4. `P4_PRODUCT_PICK` — 제품 상부 파지 후 안전 이탈
5. `P3_PRODUCT_INSERT` — 제품 투입/해제 후 뚜껑 닫기 가능한 backoff까지 이동한 뒤 DONE
6. `P3_FINISHED_BOX_PICK` — PLC 뚜껑 닫기 완료 후 다음 START로 완성 박스 측면 재파지
7. `P4_FINISHED_BOX_PLACE` — 완성 박스 배치/이탈/HOME 복귀 후 DONE

따라서 V8처럼 HOME/APPROACH/RETRACT마다 PLC 신호를 요구하지 않습니다.

## 현재 배포 파일

```text
deploy/current/
  UR3_PACKING_V9.urp
  UR3_PACKING_V9.script
  UR3_PACKING_V9.installation
  UR3_PACKING_V9.variables

releases/
  UR3_PACKING_V9_STEP_HANDSHAKE_READY.zip
```

## 검증 상태

- V9 script 논리/handshake 개수 오프라인 검사: `PASS`
- V9 URP/installation gzip XML 구조: `PASS`
- 기존 `packing2` 이름 충돌 제거: `PASS`
- 실제 PolyScope parser acceptance: `NOT_VERIFIED`
- installation variable persistence: `NOT_VERIFIED`
- 실제 PLC handshake: `NOT_VERIFIED`
- 실제 로봇 모션: `NOT_VERIFIED`

실물 검증 전에는 낮은 속도에서 단계별로 확인하십시오.
