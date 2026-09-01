# UR3 Packaging Automation

UR3 CB3 / PolyScope 3.15.x 기반 개인용 포장 자동화 프로젝트입니다.

> 이 저장소는 `ur3_visual_servoing` 및 Physical AI 프로젝트와 **완전히 별개의 개인용 작업**입니다.

## 현재 기준

- 현재 canonical 버전: **V7**
- 로봇: UR3 CB3 / PolyScope 3.15.x
- 운전 목표: 배포 후 PC/ROS 없이 PolyScope 단독 운전
- PLC handshake: **모든 실제 이동 포인트마다 START 1회 -> 1개 이동 -> DONE 1회**
- 그리퍼: 일반 Control Box DO
- 장거리 자세전환: HOME 경유 `MOVEJ`
- 작업점 주변 짧은 접근/이탈: `MOVEL`
- 현장 위치 변경: 약 ±100 mm 수준은 해당 포인트 재티칭을 전제로 설계

## 왜 HOME + MOVEJ인가

P3/P4처럼 두 끝점이 각각 도달 가능하더라도 장거리 `MOVEL`은 중간 Cartesian pose를 강제하기 때문에 UR3의 어깨/팔꿈치/손목이 물리적으로 만들기 어려운 자세를 요구할 수 있습니다.

따라서 서로 다른 station 사이에서는 사용자가 티칭한 안전한 `HOME_Q`를 경유하고, joint-space `MOVEJ`로 이동합니다. 접촉 작업 직전/직후의 짧은 구간만 `MOVEL`을 사용합니다.

## 작업 시퀀스

1. P1 새 박스 측면 파지
2. P2 밑판 접기 위치 HOLD
3. P3 빈 박스 측면 배치
4. P4 제품 상부 파지
5. P3 제품 상부 투입
6. P3 완성 박스 측면 재파지
7. P4 완성 박스 배출 위치에 배치

P2 밑판 접기와 P3 뚜껑 닫기는 별도 process-done I/O를 추가하지 않고, PLC가 공정 완료 전까지 **다음 START를 주지 않는 방식**으로 인터록합니다.

## 저장소 구조

```text
deploy/current/       현재 팬던트 배포 기준 파일
deploy/*.zip          USB 배포용 묶음
releases/             V4~V7 USB 배포 패키지
docs/version-notes/   버전별 상세 메모
docs/                 시퀀스 / I/O / 티칭 / 설치 문서
HISTORY.md            V1~V7 변경 이력
PROJECT_STATE.md      현재 검증 상태
```

## 중요한 상태

현재 V7의 **파일 구조 및 설계는 준비됨** 상태입니다. 실제 팬던트 parser acceptance, 실제 I/O 극성, 실제 HOME/관절 경로 및 실물 자동 사이클은 아직 `NOT_VERIFIED`입니다.

실물 검증 전에는 낮은 속도에서 포인트별로 확인하십시오.
