# 업데이트 작업 명세서 (UPDATE specs)

> **빌드 소스는 `docs/spec/`(현재 최종 상태 스냅샷)다.** 빌드/재현은 거기서 한다.
> 여기 `docs/updates/`는 **변경 근거·이력**(왜 바꿨나)일 뿐 — **빌드에 불필요.** 디프를 재생해 빌드하지 않는다.
>
> **재현:** `docs/spec/00_overview.md`부터 01~07 읽고 그대로 구현. updates는 결정 배경이 궁금할 때만 참조.

## 작성 규칙 (트리거 "업뎃해" 시 자동)
- 파일명: `NNNN_slug.md` (4자리 일련번호 + 케밥 슬러그). 한 작업 = 한 파일.
- 필수 섹션: **왜(문제) / 원인 / 무엇을·어떻게(변경: 파일·함수·CONFIG) / 검증 / 재현 / 한계·다음.**
- 각 항목은 "어느 `docs/spec/` 모듈을 갱신했는지" 명시. **spec 모듈 제자리 수정이 우선, updates는 이력.**

## 목록
| # | 제목 | 날짜 | 범위 |
|---|---|---|---|
| 0001 | [벽 정션 클린업(공선병합+코너연장)](0001_wall-junction-cleanup.md) | 2026-06-17 | walls.py, preview.py |
| 0002 | [대상 층(target_floor) 제거](0002_remove-target-floor.md) | 2026-06-17 | load/ir/report/run/config/frontend |
