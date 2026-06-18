# SPEC 01 — Stage0: 로드·통합수집·인벤토리·평면병합

구현: `src/load.py`, `src/inventory.py`, `src/mapping.py`. 산출: 기둥 후보 + 벽 선분 + 인벤토리.

## 통합 기하 수집 `_collect_geometry(doc, cfg, predicate, types)` (load.py) ★
리프 raw 기하를 **WCS**로 수집 — **모형공간 직계 + 중첩 블록 둘 다**.
- 직계: `for e in msp` 중 비-INSERT → `predicate(layer, [])` 통과 시 채택. `root_idx = -1`.
- 중첩: 직계 INSERT부터 재귀. **변환 합성 = `Matrix44.chain(child.matrix44(), parent_M)`** (ezdxf 속성재작성 의존 금지). 리프 좌표=WCS, `root_idx` = 최상위 INSERT 인덱스. 깊이가드 `depth_guard`(10).
- 노이즈 블록(`_is_noise`: 날짜6자리 접두/“수정·추가·두께수정”)·DEFPOINT는 스킵.
- 리턴 dict: `{type, layer, handle, root_idx, closed, pts:[(x,y)], center, r}` (LINE/LWPOLYLINE/CIRCLE).
- *과거 버그: 직계를 누락해 flat 도면을 0개로 읽었음 → 직계 반드시 포함.*

## 소스 규칙 `make_matcher(source)` (mapping.py)
`source = {mode: layer|block|path, values:[...]}` → `match(leaf_name, path_segments, layer)->bool` (부분일치).
- layer: 리프 레이어가 values 포함 / block: 리프 블록명 / path: 경로 세그먼트.
- values 비면 mode별 DEFAULT(block/path=`["기둥","col"]`, layer=없음).

## 기둥 후보 추출 `load_columns(cfg)` (load.py)
두 검출기 결과를 합침(상세 02_columns):
- **블록 검출기**: 재귀 중 리프 INSERT가 매처(block/path) 매칭 + 블록 외곽 footprint∈[min,max] → `LeafColumn`.
- **생기하 검출기**(mode layer/path): `_collect_geometry`로 매칭 raw 기하 모아 `_cluster_columns`.
- 그 후 **평면 병합** → 반환. (층 필터 없음 — UPDATE 0002.)

### footprint `_footprint(blk, exclude_text, exclude_layers)`
블록정의 직계 외곽 bbox. **TEXT 제외 + `footprint_exclude_layers`(DEFPOINT(S)) 제외.** 프로파일 감지: 외곽이 CIRCLE 주도면 `circle`(반지름), 아니면 `rect`(bbox). 리턴 `{w,d,center,profile,r}`.

## 평면 인스턴스 병합 `_collapse_duplicate_plans(candidates,cfg)` ★
같은 평면이 여러 벌 인스턴스된 경우 1벌만 채택(중복 출력 방지).
- root_idx별 그룹 → **이동불변 서명** `_plan_signature` = `frozenset{ (round((x-minx)/tol), round((y-miny)/tol), w, d) }` (자기 bbox 기준 상대좌표+사이즈).
- 서명 동일 root = 동일 평면 복사본 → 첫 1벌만. **서명 다른 평면 2개↑ 남으면 "단일층 아님" WARNING**(유저 평면선택 필요 — 미구현).
- 주의: **flat 패러다임은 모두 root_idx=-1**이라 *서로 다른 평면이 Y로 나란히 쌓인 경우는 병합 안 됨*(현재 한계; 입력이 N벌이면 출력도 N벌 = 충실 재현). nested 복사본만 병합.

## floor_tag (provenance only, 필터 아님)
`floor_tag` = 경로 최근접 `CON-\d+-B?F`(B1/B2) 또는 `untagged`. **출력 필터로 쓰지 않음**(UPDATE 0002에서 `target_floor` 층필터 제거). `src`에 출처 메타로만 보존. 출력 층 이름은 ④ `levels`가 결정(04_ir_ifc). 다중평면 분리는 별도 작업(미구현).

## 인벤토리 `extract_inventory(path)` (inventory.py) → /analyze
직계+중첩 전수 카운트(과거 직계누락 버그 수정). 리턴:
- `units`(INSUNITS), `floors`[{name,hint}](블록명 지하N층/BNF), `paradigm`('flat' if 직계≥중첩 else 'nested'),
- `layer_state`('dumped' if 기본레이어 비율>0.4 else 'meaningful'), `layer_default_ratio`,
- `layers`[{name,short(xref접두제거),count,valid}], `blocks`[{name,count,w,d,profile}],
- `suggestions`: column(레이어에 기둥/col 있고 meaningful→layer, 아니면 block) / wall(레이어에 wal/wall/벽→layer),
- `plane_hint`[{name,count}](MSP직계 이름빈도→다중평면 힌트), `layer_total`,`block_total`.

## 가드레일
- 배치(paper layout) 무시, **모형공간만**. 좌표 거대값 → recenter(IR 단계).
- 분석 CLI: `python -m src.analyze_dxf [dxf]` (`PYTHONUTF8=1`).
