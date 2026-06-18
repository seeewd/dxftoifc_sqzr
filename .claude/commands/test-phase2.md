---
description: dxf_to_ifc Phase2(벽) 수용 기준 검증
allowed-tools: Bash(python:*), Bash(python3:*), Read, Glob, Grep
---

`docs/spec/03_walls.md`, `04_ir_ifc.md`, `07_findings.md` 기준으로 벽 인식과 IfcWall 출력을 검증한다. Phase1 산출이 먼저 정상이어야 의미가 있다.

콘솔:
```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8
```

## 체크리스트
1. **후보 선분** — `wall_source`가 layer/block/path 또는 빈 값 accept_all로 동작. LINE/LWPOLYLINE이 세그먼트로 분해됨.
2. **kept_roots 적용** — 기둥 평면병합으로 채택된 root 밖 중복평면 선분이 제외됨. 기둥이 없으면 전체를 대상으로 함.
3. **공간인덱스 페어링** — 전조합이 아니라 grid 근접 질의 후 평행각/두께범위/겹침비 필터로 쌍을 만듦.
4. **센터라인/두께** — centerline 길이와 thickness가 IR `walls`에 들어가고 길이<max(min_length,두께)는 제외됨.
5. **정션 클린업** — 공선 병합과 코너 연장 로그가 있음. 완전한 개구부 복원은 현재 미구현 한계로 분리 보고.
6. **IFC IfcWall** — IfcWall 수가 IR walls와 일치하고 두께별 IfcWallType이 재사용됨.
7. **로그/요약** — 페어 수, 병합 수, 코너연장 수, 두께분포, 미페어 선분 수가 확인됨.

## 벤치마크 주의
예시 도면 `_210416`은 `wall_source=layer:WAL`에서 약 1195벽이 기대된다. 다른 도면은 절대수보다 두께 분포와 페어링 자기일치로 판정한다.

## 출력
표: `항목 | PASS/FAIL/미검증 | 근거`. 마지막에 "기둥+벽 IFC 데모 가능 여부"를 한 줄로 판정한다.
