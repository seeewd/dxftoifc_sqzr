# UPDATE 0001 — 벽 정션 클린업 (공선 병합 + 코너 교차연장)

- 날짜: 2026-06-17
- 범위: `src/walls.py` (Stage3 후처리). 진단도구 `src/preview.py` 신설.
- 상태: `[구현]`
- 선행: 코어 3종 MD(CLAUDE / DEV_SPEC / PROJECT_CONTEXT) + UPDATE 0000 이하 순차.

## 왜 (문제)
컨트롤 테스트(`test/test.dxf`, COL 레이어만 = 벽식 아파트 구조벽, 벽 332개)에서 **벽이 "끊긴 조각들의 집합"**으로 나옴. 스샷(`test/CAD*.png` vs `ifc*.png`) 확인:
- **L코너 갭**: 두 벽이 모서리에서 안 만나고 ≈벽두께(150mm) 벌어짐.
- **T접합 깨짐**: 스템과 크로스 분리.
- **긴 벽 단편/소실**: 면이 직각벽·개구부로 끊겨 일부만 페어.

## 원인 (근본)
per-pair **overlap 구간에만 센터라인**을 그림 → 교차부에서 한쪽 면이 끊기면 센터라인이 코너 전에 멈춤. 기존 정션 처리는 *끝점 평균 스냅(100mm)* 뿐이라 두께(150mm)>스냅(100mm)이라 코너도 못 붙임. 즉 **교차부·끊김 복원 부재.**

## 무엇을 / 어떻게 (변경)
`src/walls.py`에 정션 클린업 2단계 추가, `extract_walls`가 페어링 직후 호출:

1. **`_merge_collinear(walls, ang_tol, perp_tol, gap)`** — ① 공선 병합
   - 같은 직선(방향 `ang_tol`, 원점기준 수직거리 `c`를 `perp_tol`로 양자화) + 같은 두께(50mm 버킷) 벽을 그룹화.
   - 방향축 투영 후 **갭 ≤ `gap` 인 조각들을 하나로 이어붙임** → 개구부/면끊김 토막 복원.
2. **`_join_corners(walls, extend_max)`** — ② 코너 교차연장
   - 각 벽 끝점에 대해 **비평행(≥20°) 다른 벽 센터라인과의 교차점**을 구해, 끝점~교차점 거리 ≤ `extend_max` 이고 교차점이 상대 벽 범위 내(±margin)면 **끝점을 교차점으로 이동**(연장/트림).
   - L: 양 벽 끝점이 같은 교차점으로. T: 스템 끝점이 크로스 센터라인 위로.
   - 기존 `_snap_endpoints`(평균 스냅)는 제거(대체).

### 신규 CONFIG
```yaml
wall_join_gap_mm: 300      # 공선 병합 최대 갭 (문틀 끊김은 잇고, 큰 개구부는 남김)
wall_join_extend_mm: 400   # 코너 연장 최대 거리
```
`perp_tol = dedup_tol_mm/2` (기본 50mm) 사용.

## 검증 (`test/test.dxf`, COL)
- 페어 332 → **공선병합 304** → **코너연장 265끝점 이동.** 최종 벽 304, 두께 150/130/120/180.
- 오버레이(`src/preview.py`로 생성, 회색=원본/빨강=인식): 코너 닫힘·연결성 크게 개선(`out/test_overlay.png` before → `out/test_overlay2.png` after).
- 파킹·정석 회귀: 영향은 Stage3 후처리뿐(소스/페어링 로직 불변).

## 재현 방법
```python
# 파이프라인은 동일. config에 wall_join_* 추가(기본값 내장).
# 진단 오버레이:
from src.preview import render_overlay; from src.ir import load_ir
render_overlay(cfg, load_ir('out/model_ir.json'), 'out/overlay.png')
```

## 한계 / 다음
- 여전히 일부 단편·갭 잔존(완전 연결 아님). `gap`(300)이 작은 개구부는 잇고 큰 창은 남김 — 개구부 인식(IfcOpeningElement)은 미구현.
- 장기: **영역/스켈레톤 기반**(이중선→벽 영역→중심축)이 정션·개구부에 더 견고(후보).
- `_join_corners` 현재 O(n²)(끝점×벽). 대형 도면은 공간인덱스로 최적화 여지.
