# UPDATE 0002 — "대상 층"(target_floor) 제거

- 날짜: 2026-06-17
- 범위: `src/load.py`, `src/ir.py`, `src/report.py`, `src/run.py`, `config.yaml`, `frontend/index.html`
- 갱신 spec: `01_stage0`, `04_ir_ifc`, `05_ui`, `06_config`
- 상태: `[구현]`

## 왜 (문제)
UI "② 대상 평면 → 대상 층" 드롭다운이 **B1/B2만** 뜨고 분석 후 멋대로 바뀜. 정체 추적 결과:
- 드롭다운은 `inventory._detect_floors`가 **블록 이름을 `지하[1-9]층|B[1-9]F` 정규식으로 스캔**해 채움. 못 찾으면 **fallback `[B1,B2]`**(주차장 유물). 지상 아파트엔 매칭 없어 항상 B1/B2.
- `target_floor`의 실제 효과는 **단 한 곳**: `load.py` 기둥 후보를 `floor_tag in (untagged, target_floor)`로 필터 — 즉 경로에 `CON-\d+-B?F` 태그 박힌 기둥(주차장 동골조)에만 작동. **벽·IFC 출력층·일반도면엔 무의미.** 출력 층 이름은 `levels`(④)가 정함.

## 원인 (근본)
`target_floor`/floor 필터/`floor_container_hint`는 **주차장(라멘) 파일 전용 잔재**. 범용 엔진에 1급 필드로 남아 혼란만 줌. (가드레일: 도면 한정 키워드 박지 말 것.)

## 무엇을 / 어떻게 (변경)
- **`load.py`**: 층 필터 삭제 → `kept = candidates`. `floor_tag`는 계산·`src`보존(provenance)하되 **필터로 안 씀**. `dropped`/타층제외 로그 제거.
- **`ir.py`**: `meta.target_floor` 제거. **`report.py`**: `[SUMMARY]`의 `floor=` 제거. **`run.py`**: 시작 로그 `대상층` 제거. **`config.yaml`**: `target_floor` 키 제거.
- **`frontend/index.html`**: ② 대상 평면 카드(대상층 드롭다운·planeNote) 삭제, analyze 핸들러의 targetFloor 채우기·"발견 층" 표시 삭제, `buildConfig.target_floor` 삭제. (매핑 카드가 ②로.)

## 검증 (무회귀)
- **파킹(nested):** 기둥 948 **변화 없음** — B1F 골조는 *평면병합*에서 이미 정리돼 필터 제거 영향 0. floor_tag 분포 untagged 938 + B2 10.
- **정석(flat):** 기둥 66 + 벽 310, IFC PASS.

## 재현 방법
- config에서 `target_floor` 빼면 됨(이제 무시). 파이프라인 동일. UI는 대상층 카드 없음.

## 한계 / 다음
- 진짜 "대상 평면 선택"(도면에 distinct 평면 여러 벌일 때 1개 고르기)은 **여전히 미구현.** floor_tag/`con_floor_tag`도 잔재로 남음(주차장 provenance 용도) — 후속 정리 후보.
