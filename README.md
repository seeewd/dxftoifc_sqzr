# POC_2D_TO_BIM

정리된 DXF 평면도 → 구조 부재(기둥) 인식 → IFC4 출력. Phase 1(기둥 풀패스 + UI + 디버그 로그).

> 빌드 소스(명세)는 `docs/spec/`(진입 `00_overview.md`), 전략은 `docs/PROJECT_CONTEXT.md`, 변경이력은 `docs/updates/`, 가드레일·트리거는 `CLAUDE.md`(루트).

## 설치
```bash
pip install -r requirements.txt
```

## 실행
```bash
# 1) DXF Stage0 분석 (read-only)
PYTHONUTF8=1 python -m src.analyze_dxf data/지하주차장_1층_평면도.dxf

# 2) 파이프라인 단독 실행 → out/model.ifc, out/model_ir.json, out/debug.log
PYTHONUTF8=1 python -m src.run --config config.yaml

# 3) UI + 백엔드
PYTHONUTF8=1 python -m uvicorn backend.app:app --reload
#   → http://127.0.0.1:8000
```
> **Windows 콘솔 한글 깨짐 방지로 `PYTHONUTF8=1` 필수.**

## 파이프라인
`Stage0`(load.py, 로드·평탄화·층/노이즈 필터) → `Stage1`(columns.py, 기둥 추출·dedup) →
`Stage2`(levels.py) → `Stage4`(ir.py, IR 빌드·층 복제) → `Stage5`(ifc_writer.py, IFC4) →
`Stage6`(report.py, 검증·요약). IR(`model_ir.json`)이 단일 진실원.

## 산출물
- `out/model.ifc` — IFC4 (Bonsai/Revit로 검증)
- `out/model_ir.json` — IR (모든 부재 `src` 보존)
- `out/debug.log` — 단계별 디버그 로그 + `[SUMMARY]`

## 범용 인식 (M1)
도면 한정이 아닌 범용 엔진: 업로드 시 `/analyze`가 **인벤토리**(레이어 유효성·블록/그룹·자동제안)를 내고,
UI에서 **요소 소스규칙**(`column_source`/`wall_source` = layer|block|path)으로 기둥/벽 위치를 지목한다.
기둥 **프로파일 감지**(사각/원) 지원. 같은 평면이 여러 벌이면 *이동불변 서명*으로 자동 1벌 병합.

## 참고: 이전 도면 결과 (data/지하주차장_평면도_210416.dxf, B2 — 이 repo의 샘플과는 다른 도면, 벤치마크 참고용)
- **기둥**: raw 3792 = 같은 평면 4벌 인스턴스 → 병합 → **948개**(500×700:864, 700×700:38, 600×600:36, 1100×600:10), IFC PASS.
- **벽(베타)**: `wall_source=layer:WAL` → 선분 5055 → 공간인덱스 평행쌍 페어링 → **~1195벽**(주력 두께 150/190/200/250), IfcWall PASS.
- 현재 repo의 샘플(`지하주차장_1층_평면도.dxf`)은 아직 `/analyze-dxf`로 실측되지 않았다. 위 수치를 이 도면 기준으로 가정하지 말 것.

## 알려진 한계
- Stage5 IFC 생성: 기둥+벽 합 2천여 부재에서 ~80s(부재별 표현 생성). RepresentationMap 재사용으로 최적화 여지.
- 벽: 비-벽 평행선의 잔여 단발 노이즈(두께 클러스터링/표현감지로 개선 예정). MLINE·폭폴리라인·해치 표현 미지원. 정션은 끝점스냅까지(갭연장·교차분할 미구현).
- 기둥 이형(L/다각형) 프로파일, 다중 평면 선택 UI, 그리드/슬래브/보/문창 미구현.
