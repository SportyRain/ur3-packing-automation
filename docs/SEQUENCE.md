# 포장 동작 시퀀스

## PLC 기본 계약

모든 실제 로봇 이동은 같은 handshake를 사용합니다.

```text
START LOW
-> PLC START HIGH
-> UR3가 정확히 한 이동 포인트 실행
-> 해당 포인트의 그리퍼 동작이 있으면 실행
-> UR DONE HIGH
-> PLC START LOW
-> UR DONE LOW
-> 다음 포인트 대기
```

## 작업 순서

### P1 새 박스

HOME -> P1 APPROACH -> P1 PICK + CLOSE -> P1 RETRACT -> HOME

### P2 밑판 접기

HOME -> P2 APPROACH -> P2 HOLD

P2 HOLD 완료 후 PLC가 밑판 접기 공정을 수행합니다. 밑판 접기가 완료되기 전에는 다음 START를 주지 않습니다.

P2 HOLD -> P2 RETRACT -> HOME

### P3 빈 박스 배치

HOME -> P3 BOX APPROACH -> P3 BOX PLACE + OPEN -> P3 BOX RETRACT -> HOME

### P4 제품 파지

HOME -> P4 PRODUCT APPROACH -> P4 PRODUCT PICK + CLOSE -> RETRACT -> HOME

### P3 제품 투입 및 뚜껑

HOME -> P3 PRODUCT ABOVE -> P3 PRODUCT INSERT + OPEN -> P3 LID BACKOFF

P3 LID BACKOFF 완료 후 PLC가 뚜껑 닫기 공정을 수행합니다. 완료 전에는 다음 START를 주지 않습니다.

P3 LID BACKOFF -> HOME

### P3 완성박스 재파지

HOME -> P3 FIN APPROACH -> P3 FIN PICK + CLOSE -> RETRACT -> HOME

### P4 완성박스 배출

HOME -> P4 BOX APPROACH -> P4 BOX PLACE + OPEN -> RETRACT -> HOME
