# I/O 설정

I/O 주소는 현장에서 바뀔 수 있으므로 고정하지 않고 시작 메뉴에서 수정할 수 있습니다.

## 사용 I/O

- `PACK_DI_POINT_START`: PLC -> UR 시작 신호, 일반 DI
- `PACK_DO_POINT_DONE`: UR -> PLC 완료 신호, 일반 DO
- `PACK_DO_GRIP_A`: 그리퍼 A, 일반 DO
- `PACK_DO_GRIP_B`: 그리퍼 B, 일반 DO
- `PACK_GRIPPER_MODE`: OPEN/CLOSE 극성 선택

기본 예시는 다음과 같지만 실제 배선에 맞춰 변경합니다.

```text
DI0 = PLC START
DO2 = UR DONE
DO0 = GRIPPER A
DO1 = GRIPPER B
```

UR DONE, GRIPPER A, GRIPPER B는 서로 다른 DO 주소여야 합니다.
