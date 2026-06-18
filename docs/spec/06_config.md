# SPEC 06 — CONFIG 레퍼런스 (데이터 계약)

UI가 생성하거나 손수 편집. `config.yaml`(CLI) 또는 `/run`의 `{config}`(UI). 전체 키:

```yaml
input_dxf: "data/plan.dxf"      # ezdxf로 읽는 입력 (DWG 아님)
units: mm                       # INSUNITS 자동감지, 유저 확정
# target_floor: 제거됨(UPDATE 0002). 출력 층은 levels가 결정, floor_tag는 provenance.
ifc_schema: "IFC4"

build_elements:                 # 인식 요소 토글
  column: true                  # [구현]
  wall:   true                  # [구현/베타]
  grid: false  slab: false  beam: false  opening: false   # [미구현] 스킵

# ── 요소 소스 (signal-agnostic, UI 칩 선택) ──
column_source: { mode: layer|block|path, values: [...] }   # 비면 mode별 디폴트
wall_source:   { mode: layer|block|path, values: [...] }   # 비면 평면 전체 선분; 멀티값 가능(WAL+FIN 등)

# ── 레벨 (인식 평면을 각 레벨에 복제) ──
levels: [ { name: "1F", elevation_mm: 0, height_mm: 3500 } ]
repeat_floors: { enabled: false, count: 1, start_elevation_mm: 0, height_mm: 3500, name_prefix: "F" }

# ── 기둥 파라미터 ──
column_footprint_min_mm: 200
column_footprint_max_mm: 2000   # 생기하 클러스터에서 한 변>이 값 선분 제외(블롭 방지)
footprint_exclude_text: true
footprint_exclude_layers: ["DEFPOINT","DEFPOINTS"]
column_name_patterns: ["기둥","col"]   # column_source 없을 때 폴백(block)

# ── 벽 파라미터 ──
wall_thickness_min_mm: 100
wall_thickness_max_mm: 600
wall_parallel_tol_deg: 1.0
wall_overlap_min_ratio: 0.3
wall_min_length_mm: 150          # 짧은 칸막이 보존; 길이<두께도 제외
wall_join_gap_mm: 300            # 정션: 공선 조각 병합 최대 갭
wall_join_extend_mm: 400         # 정션: 코너 교차연장 최대 거리

# ── 좌표/디버그/출력 ──
recenter: true
dedup_tol_mm: 100               # 위치격자 dedup + 평면서명 양자화 + (perp_tol=½)
depth_guard: 10
log_level: "DEBUG"              # DEBUG|INFO|WARNING
out_dir: "out"
```

## 주의
- `floor_container_hint`, `con_floor_tag` = **도면 한정 잔재**(쓰지 말 것; 층분리는 평면병합+소스로). UI에 노출 안 함.
- 도면 한정 키워드를 CONFIG 1급 필드로 박지 말 것 — `*_source.values`로 일반화.
