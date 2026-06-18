---
description: dxf_to_ifc 구현/확장 오케스트레이션 — 현재 docs/spec 기준
argument-hint: "[stage0|phase1|phase2|ui|all (기본 all)]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(pip:*), Bash(uvicorn:*), Bash(git:*), Read, Glob, Grep, Edit, MultiEdit, Write
---

이건 `dxf_to_ifc` 구현 핸드오프 마스터 프롬프트다. 목표는 현재 `dxf_to_ifc/docs/spec/` 기준을 재현·확장하는 것이다. 그린필드 React BIM 툴이나 `DDA_BIM` Pset 작업으로 범위를 넓히지 마라.

## 시작 전
1. 작업 루트가 상위 폴더면 `dxf_to_ifc/`로 들어간다.
2. `CLAUDE.md` → `docs/spec/00_overview.md` → 필요한 `01_stage0`~`07_findings` 순으로 읽는다.
3. `git status --short`로 기존 변경을 확인하고, 사용자가 만든 변경을 되돌리지 않는다.
4. `git remote -v`로 push 대상이 설정되어 있는지 확인한다. 없으면 커밋만 하고 사용자에게 보고한다.
5. 입력 DXF는 `/analyze-dxf` 또는 `python -m src.analyze_dxf <file>`로 먼저 분석한다.

## 현재 구현 기준
- Stage0: `src/load.py`, `inventory.py`, `mapping.py`.
- Stage1: `src/columns.py`.
- Stage3: `src/walls.py`.
- Stage4~6: `src/ir.py`, `ifc_writer.py`, `report.py`, `run.py`.
- UI: `backend/app.py` + `frontend/index.html`.

현재 완료 기준이 아닌 것:
- React/Vite 워크벤치, web-ifc/three/r3f 3D preview.
- `DDA_BIM.DDA_Data`/`DDA_Project` Pset.
- root+cluster Jaccard 평면병합.
- 개구부/그리드/슬래브/보/문창.

## 절대 가드레일
- **2-패러다임 통합:** 모형공간 직계(flat)와 중첩 블록(nested)을 둘 다 WCS로 수집한다.
- **인벤토리 먼저:** 레이어/블록/경로를 전수 보고, 요소 소스는 `column_source`/`wall_source`로 표현한다.
- **기하가 진실:** 크기·형상·위치·각도는 이름이 아니라 WCS 기하에서 측정한다. TEXT/DEFPOINT는 footprint에서 제외한다.
- **평면병합:** nested 복사 평면은 root별 이동불변 서명으로 1벌만 채택한다. flat 다중평면은 현재 선택 UI가 없으므로 그대로 출력되는 한계로 보고한다.
- **벽:** 공간인덱스 평행쌍 페어링, 길이/두께 필터, 공선 병합, 코너 연장을 유지한다.
- **IR 단일 진실원:** `out/model_ir.json`이 기준이고 IFC는 mm→m 직렬화다. 모든 부재 `src`를 보존한다.
- 콘솔 한글: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.

## 진행 순서
각 단계는 게이트 PASS 직후 바로 커밋·푸시한다. 여러 단계를 모아서 한 번에 커밋하지 않는다. 절차는 아래 "커밋·푸시 규약" 참고.

### A. Stage0
`_collect_geometry` 직계+중첩 수집, `extract_inventory`, `make_matcher`, `_collapse_duplicate_plans`.
- 게이트: flat/nested 도면 모두 0개가 되지 않음, `plane_hint`/suggestions가 UI에 쓸 수 있음, nested 복사 root가 병합됨.
- 게이트 PASS → 커밋·푸시 (커밋 메시지 예: `stage0: nested 평면병합 root 서명 추가`).

### B. Phase1 기둥
블록 footprint와 생기하 클러스터가 같은 `Column` 흐름으로 합류한다.
- 게이트: `/test-phase1`. 기둥 중복 없음, 프로파일 사각/원, IFC4 로드 PASS, `[SUMMARY]` 일치.
- 게이트 PASS → 커밋·푸시 (커밋 메시지 예: `phase1: 기둥 사각/원 프로파일 dedup`).

### C. Phase2 벽
`load_wall_lines(kept_roots)` → `extract_walls` → IfcWall.
- 게이트: `/test-phase2`. 공간인덱스 페어링, 두께 분포, 정션 로그, IfcWall 수가 IR과 일치.
- 게이트 PASS → 커밋·푸시 (커밋 메시지 예: `phase2: 벽 공간인덱스 페어링 + 정션 클린업`).

### D. UI
FastAPI + 단일 HTML 플로우 유지.
- 게이트: `/verify-poc-ui`. 업로드, `/analyze`, 칩 매핑, `/run` SSE, 다운로드가 동작한다.
- 게이트 PASS → 커밋·푸시 (커밋 메시지 예: `ui: 업로드~다운로드 SSE 플로우`).

## 커밋·푸시 규약
기능 하나(위 A~D 중 한 게이트)가 PASS할 때마다 바로 커밋하고 푸시한다. 미완성/FAIL 상태는 커밋하지 않는다.
1. 해당 게이트 체크리스트/`[SUMMARY]`가 PASS인지 먼저 확인한다.
2. `git status --short`로 변경 파일을 확인한다. 관계없는 산출물(`out/`, 캐시 등)이 섞여 있으면 제외한다.
3. `git add -A` (또는 관련 파일만 명시).
4. `git commit -m "<stage>: <한 줄 요약>"`.
5. `git push`. 원격이 없거나 push 실패면 커밋은 유지한 채 사용자에게 보고하고 다음 단계로 넘어가지 않는다.
6. 한 커밋에는 한 게이트 분량만 담는다. 다음 단계로 넘어가기 전에 push까지 끝낸다.

## 문서 동기화
코드 변경이 현재 계약을 바꾸면 `docs/spec/NN_*.md`를 먼저 현재 상태로 갱신하고, 왜 바꿨는지는 `docs/updates/NNNN_*.md`에 남긴다. 이 동기화도 같은 커밋에 포함해 같이 푸시한다.
