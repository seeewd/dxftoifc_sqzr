---
description: dxf_to_ifc 입력 DXF Stage0 분석 — 인벤토리/패러다임/평면병합/소스 제안
argument-hint: "[dxf 경로 (생략 시 dxf_to_ifc/config.yaml 또는 data/*.dxf)]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(pip:*), Read, Glob, Grep
---

입력 DXF를 읽기 전용으로 분석해 `dxf_to_ifc` Stage0 근거를 뽑는다. 코드를 고치지 말고 사실만 리포트한다. 기준은 `docs/spec/01_stage0.md`와 `07_findings.md`다.

## 대상 파일
- 상위 폴더에서 실행 중이면 먼저 `dxf_to_ifc/`로 들어간다.
- 인자 `$ARGUMENTS`가 있으면 그 파일을 쓴다.
- 없으면 `config.yaml`의 `input_dxf`를 우선하고, 없으면 `data/*.dxf`를 찾는다. 여러 개면 어느 것인지 물어라.
- CLI: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m src.analyze_dxf <파일>`.

## 반드시 출력할 것
1. **헤더 사실** — DXF 버전, 단위, 레이어/블록 수, modelspace 직계 INSERT 수, layout viewport 유무.
2. **패러다임** — flat / nested / mixed. 모형공간 직계 비-INSERT와 중첩 리프를 둘 다 카운트한다.
3. **인벤토리** — 레이어 사용수와 유효성, 블록 이름/개수/샘플 footprint, 그룹 경로 키워드.
4. **평면 인스턴스** — nested root별 이동불변 서명으로 같은 평면 복사본이 있는지 본다. flat 다중평면은 현재 자동병합 대상이 아니며, 다중평면 선택 UI 미구현 한계로 보고한다.
5. **기둥 소스 제안** — `column_source` mode/values. 레이어가 의미 있으면 layer, 죽었으면 block/path를 제안한다.
6. **기둥 카탈로그** — 후보 footprint W×D/R. TEXT와 DEFPOINT는 제외하고 이름 숫자는 신뢰하지 않는다.
7. **벽 소스 제안** — `wall_source` mode/values. WAL/WALL/벽류 레이어, 또는 필요하면 path/block 후보를 제안한다.
8. **노이즈/한계** — DEFPOINT, 날짜·수정류 블록, flat 다중평면, 벽식 `COL` 오인 위험.

## 가드레일
- 위치=bbox 중심, 각도=합성 +X축, 크기=외곽 bbox.
- 레이어/블록명은 힌트일 뿐이고 요소별로 신호가 다를 수 있다.
- Y밴드 폴백으로 층을 자르지 않는다. 출력 층은 `levels`가 결정한다.
- 분석만 한다. 추출/IFC 생성은 `/run-poc`.

## 보고 형식
표 + 핵심 결론 3~5줄 + 권고 config 조각:
```yaml
column_source: { mode: ..., values: [...] }
wall_source:   { mode: ..., values: [...] }
```
