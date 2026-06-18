---
description: dxf_to_ifc config 실행 + [SUMMARY]와 산출물 확인
argument-hint: "[config 경로 (기본 config.yaml)]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(uvicorn:*), Read, Glob
---

파이프라인을 실행하고 결과를 검증한다. 코드 변경 없이 실행·진단만 한다. 상위 폴더에서 실행 중이면 먼저 `dxf_to_ifc/`로 들어간다.

콘솔 한글:
```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8
```

## 실행
- config: `$ARGUMENTS`가 있으면 그 경로, 없으면 `config.yaml`.
- 엔트리: `python -m src.run --config <config>`.
- `src/run.py`가 없으면 대상 루트가 틀린 것이다. `dxf_to_ifc/`인지 확인한다.

## 확인 순서
1. 종료 코드 0.
2. `[SUMMARY]` 블록: `columns=... walls=... recenter=... levels=... IFC entities=... validation=... warnings=...`.
3. 산출물: `out/model.ifc`, `out/model_ir.json`, `out/debug.log`.
4. IR 정합성: `model_ir.json`의 column/wall 수가 SUMMARY와 일치하고, 부재 `src`가 보존됨.
5. IFC 정합성: `ifcopenshell.open()` 성공, schema=IFC4, IfcProject/Site/Building/Storey 존재, IfcColumn/IfcWall 수가 IR과 일치.
6. WARNING 집계: 대표 원인과 출처를 짚는다.

## 보고 형식
SUMMARY 핵심 줄을 인용하고, 추출 수가 합리적인지 숫자로 판정한다. `DDA_BIM` Pset이나 3D preview는 현재 `dxf_to_ifc` 완료 기준이 아니므로 실패로 치지 않는다.

## UI 실행이 필요하면
```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m uvicorn backend.app:app --port 8000 --reload
```
그 뒤 `/analyze`, `/run`, `/download` 계약을 확인한다.
