# SPEC 00 — Overview (빌드 진입점)

> **이 `docs/spec/`가 빌드 소스다.** 각 모듈 = "현재 최종 상태" 스냅샷. 이것만 읽고 그대로 구현하면 현재 기능이 재현된다.
> `docs/updates/`는 *근거·이력*(왜 바꿨나)일 뿐 빌드에 불필요. `docs/PROJECT_CONTEXT.md`는 전략(왜).

## 한 줄
**범용** DXF 평면도 → 구조 부재(기둥·벽) 인식 → 유효 IFC4 출력. + 모노톤 입력/매핑 UI + 디버그 로그.

## 스택
Python3 · `ezdxf`(파싱/블록순회/Matrix44) · `ifcopenshell`(+api) · `shapely`,`numpy` · `fastapi`+`uvicorn` · 단일 HTML/CSS/JS · (검증) `matplotlib`(오버레이), Bonsai/Revit(뷰어).
**Windows 콘솔 한글: `PYTHONUTF8=1` 필수.**

## 설계 철학 (절대 원칙)
1. **인벤토리 먼저, 판별 나중.** 도면 열면 레이어/블록/그룹을 전수 추출 → 요소가 어디 있나 정함.
2. **Signal-agnostic + 유저 가이드.** 부재 출처 = `{mode: layer|block|path, values}`. 자동제안 후 **유저 확정**(UI 칩 클릭).
3. **기하가 진실, 이름은 거짓.** 크기·형상·위치·각도는 변환된 WCS 기하에서 측정. 이름 숫자 불신. (레이어명도 요소종류를 속일 수 있음 — 벽식 아파트 `COL`=구조벽.)
4. **2-패러다임.** 기하는 *중첩 블록(nested)* 또는 *모형공간 직계(flat)* — **둘 다 수집.**
5. **안정신호=기하·색 / 불안정=레이어·블록이름**(사무소마다 다름).

## 파이프라인
```
DXF ─[Stage0] 통합수집(직계+중첩,WCS)+인벤토리+평면병합   → 01_stage0  (load/inventory/mapping)
     [Stage1] 기둥 인식(블록 or 생기하, 프로파일)          → 02_columns (columns)
     [Stage2] 레벨 전개                                    → 04_ir_ifc  (levels)
     [Stage3] 벽 인식(평행쌍 페어링 + 정션 클린업)          → 03_walls   (walls)
     [Stage4] IR 빌드 + 층 복제 (IR=단일 진실원)            → 04_ir_ifc  (ir)
     [Stage5] IFC4 출력 (IR 직렬화, mm→m)                  → 04_ir_ifc  (ifc_writer)
     [Stage6] 검증 + [SUMMARY]                              → 04_ir_ifc  (report)
오케스트레이션: run.py(run_pipeline) · 로깅: logsetup.py · UI: 05_ui · 설정: 06_config
```

## 핵심 가드레일 (요약 — 상세는 각 모듈)
- 위치=변환된 외곽 bbox **중심**(삽입점 아님), 각도=합성변환 +X축. 펼치기는 `Matrix44.chain(child, parent)`.
- 크기= 외곽 bbox(**TEXT·DEFPOINT 제외**). 프로파일 사각/원 감지.
- **평면 인스턴스 중복 병합**(이동불변 서명) — 같은 평면 여러벌 → 1벌.
- 벽: 레이어 가지치기 + **공간인덱스 평행쌍**(전조합 금지) + 정션 클린업(공선병합+코너연장).
- IR(JSON) 단일 진실원, 모든 부재 `src`(출처·handle) 보존. recenter 후 출력.
- 디버그 로그(콘솔+파일+UI SSE), WARNING/ERROR에 출처, 종료 `[SUMMARY]`.
- 미구현(그리드/슬래브/보/문창) UI 비활성+스킵.

## 빌드 순서
1) **06_config** 훑기(데이터 계약) → 2) **01→02→03→04→05** 순서로 각 모듈=각 src 구현 → 3) **07_findings**는 실측 함정 회피용 참조.

## 수용 기준 (현재)
- [x] 기둥 중복없이 추출(평면병합+위치dedup), 프로파일(사각/원), IFC4 PASS.
- [x] 벽 평행쌍→센터라인·두께·타입, 정션 클린업(코너 닫힘), IfcWall PASS.
- [x] 2-패러다임(nested 주차장 948기둥 / flat 정석 레이어:COL).
- [x] UI: 업로드→인벤토리 자동제안→칩 매핑→레벨→실행→로그스트림→다운로드.
- [ ] 개구부 인식, 다중평면 선택 UI, 그리드/슬래브 — 미구현.

## 파일 구조
```
CLAUDE.md(루트, 가드레일·트리거)   README.md   config.yaml   requirements.txt
docs/spec/00..07   docs/updates/   docs/PROJECT_CONTEXT.md
backend/app.py   frontend/index.html
src/ load inventory mapping columns levels walls ir ifc_writer report logsetup run preview analyze_dxf
out/ model.ifc model_ir.json debug.log
```
