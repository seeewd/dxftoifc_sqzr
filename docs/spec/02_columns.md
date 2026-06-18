# SPEC 02 — Stage1: 기둥 추출 (표현-무관)

구현: `src/columns.py` (+ 후보 수집은 01_stage0 `load.py`). 산출: `Column` 리스트.

## 두 검출기 (출처 무관, 같은 파이프라인 합류)
**(A) 블록 검출기** (`column_source.mode = block|path`, nested)
- 재귀 중 리프 INSERT 이름/경로가 매처 매칭 + 블록 외곽 footprint ∈ [`column_footprint_min_mm`(200), `max`(2000)] → `LeafColumn`.
- 크기·중심은 블록정의 외곽 bbox(`_footprint`, TEXT·DEFPOINT 제외).

**(B) 생기하 검출기** (`mode = layer|path`, flat) — `_cluster_columns(geoms,cfg)` (load.py)
- CIRCLE → 원 기둥(지름∈범위).
- 닫힌 LWPOLYLINE → bbox = footprint.
- LINE/열린폴리 → 세그먼트 분해 후 `_cluster_segments`: **끝점 근접 union-find**(snap 80mm) → 컴포넌트 bbox = footprint.
  - **원칙 필터: 한 변(선분)이 `fp_max` 초과면 제외.** (그리드선/해치 스팬이 컴포넌트를 거대블롭으로 잇는 것 방지 — 도면 무관 일반 규칙.)
- raw 기둥은 `LeafColumn(matrix=identity, local_center=WCS중심, root_idx=geom의 root)`.

## 좌표·사이즈 산출 `_extract(LeafColumn)` (columns.py)
- **위치 = 외곽 bbox 중심을 변환** `M.transform(local_center)` (삽입점 아님).
- **각도 = 변환행렬 +X축** `atan2(xaxis.y, xaxis.x)` (생기하 identity → 0°/직교 가정; 회전 raw 기둥은 미지원).
- **사이즈 = local_w/d × 스케일**(transform_direction 크기), 10mm 반올림. 원이면 `r`.

## dedup & 적재 `extract_columns(candidates, cfg)`
- **위치격자 dedup**: key `(round(x/dedup_tol), round(y/dedup_tol))` 첫 1개만(평면병합 후 잔여 겹침 안전망).
- `Column{id,x_mm,y_mm,rot_deg,w_mm,d_mm,profile,r_mm,floor_tag,src_*}`. `size_key`= `WxD` 또는 `R{r}`.
- 로그: 타입별 카운트, 좌표범위, 의심 종횡비(>6:1) WARNING.

## 프로파일 → IFC (상세 04_ir_ifc)
`profile=='circle'` → `IfcCircleProfileDef(r)`, 아니면 `IfcRectangleProfileDef(w,d)`.

## 구조형식 주의 (07_findings)
**벽식 아파트엔 기둥 없음**(벽이 구조체). 라멘/지하주차장/필로티만 기둥. 레이어명 `COL`이 벽식에선 구조벽일 수 있음 → 요소 기대치는 구조형식 의존.
