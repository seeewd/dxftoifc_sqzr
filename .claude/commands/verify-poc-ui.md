---
description: dxf_to_ifc 단일 HTML UI 플로우 검증
argument-hint: "[시나리오 설명 (기본: upload→analyze→run→download)]"
allowed-tools: Bash(uvicorn:*), Bash(python:*), Bash(npx:*), Bash(playwright:*), Read, Glob
---

현재 UI는 FastAPI + `frontend/index.html` 단일 파일이다. React 작업면이나 3D preview를 기대하지 말고, `docs/spec/05_ui.md`의 실제 계약을 브라우저 증거로 검증한다.

## 절차
1. 상위 폴더라면 `dxf_to_ifc/`로 들어간다.
2. 서버 실행:
   ```bash
   PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m uvicorn backend.app:app --port 8000 --reload
   ```
3. 브라우저/Playwright로 `http://127.0.0.1:8000` 접속.
4. 시나리오: `$ARGUMENTS`가 있으면 그 흐름, 없으면 `DXF 업로드 → /analyze 인벤토리 → 매핑 칩 확인 → /run SSE 로그 → 다운로드`.
5. 화면 크기 1280×800, 390×844에서 스크린샷 또는 육안 증거를 남긴다.
6. 콘솔 에러와 네트워크 실패를 수집한다.

## PASS 기준
- `/analyze` 결과가 단위, paradigm, 레이어/블록 후보, 자동제안으로 UI에 반영됨.
- 기둥/벽 source mode와 후보 칩 선택이 config에 반영됨.
- `/run` 로그가 실시간으로 흐르고 완료 시 `[SUMMARY]`와 다운로드 링크가 보임.
- `model.ifc`, `model_ir.json`, `debug.log` 다운로드 가능.
- 1280×800/390×844에서 텍스트 겹침·잘린 버튼·가로 overflow가 없음.

## 현재 비기준
3D preview, web-ifc, DDA_BIM Pset 표시, React 워크벤치 레이아웃은 현재 `dxf_to_ifc` UI 완료 기준이 아니다.

## 보고 형식
`항목 | PASS/FAIL/미검증 | 근거(스크린샷/콘솔/요약)` 표와 "시연 가능 여부" 한 줄.
