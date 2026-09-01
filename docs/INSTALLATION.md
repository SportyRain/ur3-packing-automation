# 팬던트 설치 및 최초 설정

## 배포 파일

`deploy/current/`의 다음 파일이 현재 기준입니다.

```text
packing2.installation
packing2.variables
UR3_PACKING_V7.script
UR3_PACKING_V7.urp
```

또는 `releases/UR3_PACKING_V7_PERSISTENT_HOME_READY.zip`을 풀어 사용합니다.

## 최초 설정 순서

1. `packing2.installation`을 로드합니다.
2. `UR3_PACKING_V7.urp`를 로드합니다.
3. 프로그램 시작 메뉴에서 PLC START DI, UR DONE DO, Gripper A/B DO와 gripper mode를 확인합니다.
4. HOME 안전 관절자세를 티칭합니다.
5. 7개 작업점을 순서대로 티칭합니다.
6. 낮은 속도에서 PLC START/DONE을 한 포인트씩 검증합니다.

## HOME

HOME은 factory zero pose가 아닙니다. 실제 셀에서 팔이 과도하게 펴지지 않고 손목도 관절 한계 근처가 아니며 P1~P4 방향으로 이동하기 쉬운 중앙 안전 자세를 직접 티칭합니다.

## 티칭값 변경

현장 기구 위치가 약 ±100 mm 바뀌는 경우 해당 작업점만 `Modify`하여 다시 티칭하도록 설계했습니다. 새 TCP pose와 실제 joint posture를 함께 저장합니다.

## 주의

V4 시절 티칭값은 사용자가 제공한 `packing2.variables`에서 복구되지 않았습니다. 제출된 파일에는 timestamp만 있었고 `PACK_*` 값은 없었습니다. 따라서 V7 최초 실사용에서는 HOME + 7개 작업점을 다시 티칭해야 합니다.
