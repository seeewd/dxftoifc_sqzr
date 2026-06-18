# SPEC 03 — Stage3: 벽 추출 (평행쌍 페어링 + 정션 클린업)

구현: `src/walls.py` + 선분수집 `load.load_wall_lines`. 산출: `Wall{start,end,thickness_mm}` 리스트.

## 선분 수집 `load_wall_lines(cfg, kept_roots)` (load.py)
- `_collect_geometry`(직계+중첩)로 `wall_source` 매칭 LINE/LWPOLYLINE → 세그먼트.
- `wall_source.values` 비면 **평면 전체 선분**(accept_all).
- `kept_roots` (기둥 평면병합으로 채택된 root 집합) 밖 root는 제외(중복평면 배제). 기둥 없으면 None=전체.
- **벽 면이 여러 레이어에 분산될 수 있음 → 멀티 레이어 values 지원**(예 WAL+FIN; 벽식 구조벽은 COL). 해치(INSUL 등)는 평행쌍 안 됨.

## 페어링 `extract_walls(segments, cfg)`
1. 짧은 선분(≥max(tmin,150)) 만 대상.
2. **공간 인덱스** `_Grid(cell=max(2000, tmax*3))` — 근접 후보만 질의(전조합 O(n²) 금지).
3. 긴 선부터, 각 선 a에 대해 후보 b 검사:
   - `_parallel(a,b,tol)` 각도차 ≤ `wall_parallel_tol_deg`(1°),
   - `_perp_dist_and_overlap`: 수직거리 d ∈ [`wall_thickness_min`(100), `max`(600)], 겹침비 ≥ `wall_overlap_min_ratio`(0.3).
   - 겹침비 최대인 b 채택, 둘 다 used.
4. 센터라인 = a직선에서 +반두께(부호) 오프셋, 겹침구간 [lo,hi]. **길이필터: 길이 < max(`wall_min_length_mm`(150), 두께) 제외.**
5. 두께 = round(d/10)*10.

## 정션 클린업 ★ (UPDATE 0001)
페어 직후 2단계:
1. **공선 병합 `_merge_collinear(walls, ang_tol, perp_tol=dedup_tol/2, gap=wall_join_gap_mm)`**
   - 같은 직선(방향 ang_tol, 원점기준 수직거리 c를 perp_tol 양자화) + 같은 두께(50버킷) 그룹.
   - 방향축 투영 → **갭 ≤ gap(300) 조각 이어붙임.** (개구부/면끊김 토막 복원; 큰 창은 안 이음.)
2. **코너 교차연장 `_join_corners(walls, extend_max=wall_join_extend_mm)`**
   - 각 끝점에 대해 **비평행(≥20°) 다른 벽 센터라인과 교차점** 계산. 끝점~교차점 ≤ extend_max(400) & 교차점이 상대 벽 범위(±margin) → **끝점을 교차점으로 이동.**
   - L: 양 벽 끝점이 같은 교차점. T: 스템 끝점이 크로스 센터라인 위로. (구 `_snap_endpoints` 대체.)
- 이후 벽 id 재부여.

## 두께별 타입 → IFC (04_ir_ifc)
두께별 `IfcWallType`(STANDARD). 센터라인 L×두께 사각 프로필을 중점에 각도배치 후 height extrude.

## 로그
`페어 N → 공선병합 M → 코너연장 K끝점`, 두께분포, 미페어 선분 수.

## 한계 / 다음 (07_findings 참조)
- 개구부에서 벽 단편화(이중선 끊김) — gap(300)으로 작은 끊김만 브리지. **개구부 인식(IfcOpeningElement)은 미구현.**
- 완전 연결 아님(일부 갭/단편 잔존). 장기: **영역/스켈레톤 기반**(이중선→벽영역→중심축)이 정션·개구부에 견고.
- `_join_corners` O(n²) — 대형 도면 공간인덱스 최적화 여지.
