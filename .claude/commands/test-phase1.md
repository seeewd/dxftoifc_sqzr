---
description: dxf_to_ifc Phase1(기둥+IR+IFC+로그) 수용 기준 검증
allowed-tools: Bash(python:*), Bash(python3:*), Bash(pytest:*), Read, Glob, Grep
---

`docs/spec/00_overview.md`, `01_stage0.md`, `02_columns.md`, `04_ir_ifc.md` 기준으로 실제 산출물을 검증한다. 못 돌렸으면 FAIL이 아니라 "미검증"으로 표시한다.

콘솔:
```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8
```

필요하면 먼저:
```bash
python -m src.run --config config.yaml
```

## 체크리스트
1. **중복 없는 기둥 추출** — IR `columns` 위치 중복 0. Stage0 평면병합 로그와 Stage1 dedup 전/후 카운트 확인.
2. **프로파일/카탈로그 자기일치** — `profile`이 rect/circle로 들어가고, w/d/r가 도면 기하와 맞음. 예시 도면 `_210416`이면 948개와 `{500x700,700x700,600x600,1100x600}` 기대.
3. **소스 규칙 동작** — `column_source.mode`가 layer/block/path에서 동작. block footprint 또는 생기하 검출기 중 해당 도면에 맞는 경로가 사용됨.
4. **위치·각도·크기** — 위치=bbox 중심, 각도=합성 +X축 회전, IR mm → IFC m 변환 일치.
5. **IFC4 검증** — `ifcopenshell.open('out/model.ifc')` 성공, schema=IFC4, IfcProject/Site/Building/Storey 존재, IfcColumn 수가 IR과 일치.
6. **층 복제** — levels N개 또는 repeat_floors 사용 시 storey와 부재 복제가 맞음.
7. **로그** — `out/debug.log` 존재, 단계별 로그와 `[SUMMARY]` 존재, WARNING/ERROR에 출처가 있음.
8. **UI 기본 플로우** — 업로드 → `/analyze` 인벤토리 → 요소 매핑 칩 → 레벨 → 실행 → 로그스트림 → 다운로드.

## 검증 스니펫
```bash
python -c "import json;from collections import Counter;d=json.load(open('out/model_ir.json',encoding='utf-8'));print('cols',len(d['columns']));print(Counter((c.get('profile'),int(c.get('w_mm',0)),int(c.get('d_mm',0)),int(c.get('r_mm',0))) for c in d['columns']))"
python -c "import ifcopenshell as I,json;m=I.open('out/model.ifc');d=json.load(open('out/model_ir.json',encoding='utf-8'));print(m.schema,len(m.by_type('IfcColumn')),len(d['columns']),len(m.by_type('IfcBuildingStorey')))"
```

## 출력
표: `항목 | PASS/FAIL/미검증 | 근거`. 마지막에 "도면 넣으면 기둥이 IFC로 선다" 충족 여부를 한 줄로 판정한다.
