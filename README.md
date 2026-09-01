# UR3 Packaging Automation

UR3 CB3 / PolyScope 3.15.x 기반 개인용 포장 자동화 프로젝트입니다.

> 이 저장소는 `ur3_visual_servoing` 및 Physical AI 프로젝트와 **별개의 독립 작업**입니다.

## 목표

- UR3 + PLC + 공압 그리퍼를 이용한 박스 포장 자동화
- PC/ROS 없이 최종적으로 UR 컨트롤러 단독 운전
- 각 이동 포인트마다 PLC `START` / UR `DONE` handshake
- 현장에서 팬던트로 I/O 주소 및 티칭 포인트 수정 가능
- 장거리 자세전환은 Cartesian 좌표 직선 추종이 아니라 관절 자세를 고려한 HOME 경유 `MOVEJ`
- 작업점 근처의 짧은 접근/이탈만 `MOVEL`

## 현재 canonical 버전

`V7`이 현재 기준 버전입니다.

주요 특징:

- HOME 안전 자세 티칭
- 작업점마다 TCP pose + 실제 6축 joint posture 저장
- P1~P4 장거리 전환은 HOME을 경유한 joint-space `MOVEJ`
- 작업점 주변 짧은 접근/이탈은 `MOVEL`
- 약 100 mm 수준의 현장 위치 변경 시 해당 포인트만 재티칭 가능
- 일반 Control Box DI/DO 사용
- PLC point-by-point handshake 유지

## 포장 시퀀스

1. P1: 새 박스 측면 파지
2. P2: 밑판 접기 위치 HOLD
3. P3: 빈 박스 측면 배치
4. P4: 제품 상부 파지
5. P3: 제품 상부 투입
6. P3: 완성 박스 측면 재파지
7. P4: 완성 박스 배출 위치에 배치

자세한 내용은 `docs/SEQUENCE.md`를 참고하십시오.

## 디렉터리

```text
deploy/current/        현재 팬던트 배포 기준 파일
archive/v4~v7/         개발 중 생성된 과거 패키지

docs/
  SEQUENCE.md
  IO_CONFIGURATION.md
  TEACHING_AND_KINEMATICS.md

HISTORY.md              버전별 변경 이력
PROJECT_STATE.md        현재 검증 상태
```

## 검증 상태

현재 파일 구조와 설계는 작성되어 있지만 실제 팬던트/실물 동작은 별도 검증이 필요합니다.

상태 표기는 다음을 사용합니다.

- `VERIFIED`: 실제 증거로 확인
- `NOT_VERIFIED`: 아직 실물 검증 전
- `BLOCKED`: 조건 미충족으로 진행 차단

현재 자세한 상태는 `PROJECT_STATE.md`를 참고하십시오.
