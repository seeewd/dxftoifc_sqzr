# CLAUDE.md — dxf_to_ifc wrapper

이 폴더는 현재 `dxf_to_ifc` 작업을 둘러싼 상위 래퍼다. 실제 구현 루트는 `dxf_to_ifc/`이고, 빌드 소스는 `dxf_to_ifc/docs/spec/`다.

## 먼저 읽을 것
1. `dxf_to_ifc/CLAUDE.md` — 프로젝트 가드레일·운영·업데이트 트리거.
2. `dxf_to_ifc/docs/spec/00_overview.md` → 필요한 `01_stage0`~`07_findings`.
3. `ONE_SHOT_POC_BUILD_PROMPT.md` — 새 세션용 압축 지시문.

상위의 오래된 `POC_2D_TO_BIM_DEV_SPEC.md`, `PROJECT_CONTEXT.md`는 이력/참고다. 현재 구현 기준과 충돌하면 `dxf_to_ifc/docs/spec/`가 이긴다.

## 현재 범위
**범용 DXF 평면도 → 구조 부재(기둥·벽) 인식 → IFC4 출력**. UI는 FastAPI + 단일 HTML/CSS/JS다.

구현된 기준:
- Stage0: flat/nested 통합 수집, 인벤토리, signal-agnostic 소스 규칙, root 서명 기반 nested 평면병합.
- Stage1: 기둥 블록 footprint + 생기하 검출, 사각/원 프로파일, 위치 dedup.
- Stage3: 벽 평행쌍 페어링 + 정션 클린업 베타.
- Stage4~6: IR(JSON) → IFC4 → `[SUMMARY]`.
- UI: `/analyze`, `/run` SSE 로그, `/download`.

현재 완료 기준이 아닌 것:
- React/Vite 작업면 UI, web-ifc/three/r3f 3D preview.
- `DDA_BIM` Pset.
- root+cluster Jaccard 평면병합.
- 개구부/그리드/슬래브/보/문창 인식.

## 실행
```bash
cd dxf_to_ifc
pip install -r requirements.txt
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m src.run --config config.yaml
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m uvicorn backend.app:app --port 8000 --reload
```

## 핵심 가드레일
- 특정 도면 처리기가 아니라 범용 인식 엔진이다.
- 도면을 열면 인벤토리 먼저, 판별은 나중.
- 부재 출처는 `{mode: layer|block|path, values}`로 표현하고, 자동제안 후 유저가 확정한다.
- 기하가 진실이다. 이름·레이어명은 힌트일 뿐이다.
- 모형공간 직계와 중첩 블록을 모두 수집한다.
- 평면 중복은 root 이동불변 서명으로 병합한다. flat 다중평면 선택은 아직 미구현이다.
- IR(JSON)이 단일 진실원이고 IFC는 IR 직렬화다.
- 문서 동기화가 필요하면 `dxf_to_ifc/docs/spec/`를 먼저 현재 상태 스냅샷으로 갱신하고, 변경 이력은 `docs/updates/`에 남긴다.

## 하네스 맵
상위 `.claude/commands/`는 `dxf_to_ifc/`를 대상으로 쓰는 편의 하네스다.
- `/analyze-dxf` — 입력 DXF Stage0 분석.
- `/run-poc` — config 실행과 산출물 확인.
- `/test-phase1` — 기둥·IR·IFC·로그 검증.
- `/test-phase2` — 벽 페어링·IfcWall 검증.
- `/verify-poc-ui` — 단일 HTML UI 플로우 검증.
- `/build-poc` — 현재 스펙 기준 구현/확장 오케스트레이션.

`BIM_TOOL_HARNESS/`는 별도 웹 BIM 저작 툴 하네스다. 현재 `dxf_to_ifc` 산출물은 `DDA_BIM` 없는 IFC4 형상 출력이므로, 그 툴에서는 우선 외부 IFC 형상뷰로 열고 Pset 기반 파라메트릭 복원은 후속 연동 목표로 본다.

## Git 워크플로우
- 기능 하나(`/build-poc`의 stage0/phase1/phase2/ui 게이트 중 하나)가 PASS할 때마다 바로 `git add` → `git commit` → `git push`한다. 모아서 한 번에 커밋하지 않는다.
- 게이트 체크리스트나 `[SUMMARY]`가 FAIL이거나 미검증이면 커밋하지 않는다.
- 커밋 메시지는 어떤 단계에서 무엇을 바꿨는지 한 줄로 쓴다 (예: `phase1: 기둥 사각/원 프로파일 dedup`).
- push 실패(원격 미설정, 충돌 등)는 사용자에게 즉시 보고하고 다음 단계로 넘어가지 않는다.

## 작업 규약
직설적·근거 기반. 빈 칭찬/과장 금지. 맞으면 "맞다", 합리적이면 "합리적이다", 틀리면 틀리다고 명확히.
