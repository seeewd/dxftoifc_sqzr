# SPEC 04 — Levels · IR · IFC · 검증

구현: `src/levels.py`, `src/ir.py`, `src/ifc_writer.py`, `src/report.py`. 오케스트레이션 `src/run.py`.

## Stage2 레벨 `build_levels(cfg)` (levels.py)
- `levels`[{name,elevation_mm,height_mm}] 파싱. `repeat_floors.enabled`면 N개 스택 생성(start_elevation_mm + i*height_mm, prefix). 레벨0개→기본 삽입+WARNING. 중복 EL WARNING.

## Stage4 IR `build_ir(cfg, columns, levels, walls)` (ir.py) — 단일 진실원
- **recenter**: 전 부재(기둥+벽) bbox 중심 offset 계산, 좌표에서 빼고 `meta.recenter_offset_mm`에 기록(원좌표 역산).
- **층 복제**: 인식한 단일 평면을 각 레벨에 복제, 각 부재에 `level` 태그.
- 스키마:
```json
{ "meta":{source,units,recenter_offset_mm,build_elements},
  "levels":[{name,elevation_mm,height_mm}],
  "columns":[{id,x_mm,y_mm,rot_deg,profile,w_mm,d_mm,(r_mm),level,src:{block,path,handle,floor_tag}}],
  "walls":[{id,start_mm:[x,y],end_mm:[x,y],thickness_mm,level,src:{source,handle}}] }
```
- 모든 부재 `src` 보존. `save_ir`/`load_ir` (out/model_ir.json, UTF-8).

## Stage5 IFC `write_ifc(ir, cfg)` (ifc_writer.py) — IFC4, ifcopenshell.api
- 좌표 **mm→m ×0.001**. 위계 `IfcProject→IfcSite→IfcBuilding→IfcBuildingStorey`(레벨별, Elevation 설정).
- 단위: `unit.add_si_unit` LENGTHUNIT+PLANEANGLEUNIT, `unit.assign_unit`. 컨텍스트 Model/Body.
- **기둥 → IfcColumn**: 사이즈/형상별 `IfcColumnType`(predefined COLUMN). 프로파일 사각=`IfcRectangleProfileDef(w,d)`/원=`IfcCircleProfileDef(r)` → `geometry.add_profile_representation(depth=층고)` → `assign_representation`. 배치 `edit_object_placement`(4×4: x,y,z=EL + Z회전 `_placement_matrix`). `spatial.assign_container`(Storey).
- **벽 → IfcWall**: 두께별 `IfcWallType`(STANDARD). 센터라인 길이 L × 두께 T `IfcRectangleProfileDef` → height extrude, 중점에 각도 배치. 컨테이너 동일.
- 0크기/레벨없음 → WARNING+스킵. 저장 out/model.ifc. 리턴 meta{path,total_entities,columns,walls,types,missing}.

## Stage6 검증 `validate_and_summarize(ifc_path, ir, ifc_meta, t0)` (report.py)
- IfcProject/Storey 존재, 모든 IfcColumn·IfcWall에 Representation+ObjectPlacement 확인(누락 WARNING).
- 종료 `[SUMMARY]`: columns(타입별), walls(두께별), recenter, levels, IFC entities, validation PASS/FAIL, warnings, 소요.

## run.py `run_pipeline(cfg, stream_queue=None)`
setup_logging → (column) load_columns→kept_roots→extract_columns → (wall) load_wall_lines(kept_roots)→extract_walls → build_levels → build_ir → save_ir → write_ifc → validate_and_summarize. 미구현요소 WARNING 스킵.
엔트리: `python -m src.run --config config.yaml`.
