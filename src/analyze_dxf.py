import glob
import sys
from collections import Counter

import ezdxf
import yaml

from .inventory import extract_inventory
from .load import _direct_roots, _is_noise, load_columns


def _resolve_input(arg):
    if arg:
        return arg
    try:
        with open("config.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        if cfg.get("input_dxf"):
            return cfg["input_dxf"]
    except FileNotFoundError:
        pass
    candidates = sorted(glob.glob("data/*.dxf"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise SystemExit(f"data/*.dxf 여러 개 발견, 경로를 지정하라: {candidates}")
    raise SystemExit("입력 DXF를 찾을 수 없다. 경로를 인자로 넘기거나 config.yaml의 input_dxf를 설정하라.")


def _load_config():
    try:
        with open("config.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _header_facts(doc):
    msp = doc.modelspace()
    direct_inserts = [e for e in msp if e.dxftype() == "INSERT"]
    layouts = [name for name in doc.layouts.names() if name != "Model"]
    has_viewport = False
    for name in layouts:
        layout = doc.layouts.get(name)
        if any(e.dxftype() == "VIEWPORT" for e in layout):
            has_viewport = True
            break
    return {
        "dxfversion": doc.dxfversion,
        "insunits": doc.header.get("$INSUNITS"),
        "layer_total": len(doc.layers),
        "block_total": len(doc.blocks),
        "direct_insert_count": len(direct_inserts),
        "paper_layouts": layouts,
        "has_viewport": has_viewport,
    }


def _column_catalog(candidates):
    counter = Counter()
    for c in candidates:
        if c.profile == "circle":
            key = ("circle", round(c.r))
        else:
            key = ("rect", round(c.w), round(c.d))
        counter[key] += 1
    return counter


def _print_report(path, doc, header, inv, columns):
    print(f"=== Stage0 분석: {path} ===\n")

    print("[헤더 사실]")
    print(f"  DXF version       : {header['dxfversion']}")
    print(f"  단위 (INSUNITS)    : {header['insunits']}")
    print(f"  레이어/블록 수      : {header['layer_total']} / {header['block_total']}")
    print(f"  modelspace 직계 INSERT : {header['direct_insert_count']}")
    print(f"  layout viewport     : {'있음' if header['has_viewport'] else '없음'} ({header['paper_layouts']})")
    print()

    print("[패러다임]")
    print(f"  paradigm: {inv['paradigm']}  (직계 vs 중첩 리프 비교)")
    print()

    print("[인벤토리]")
    print(f"  layer_state={inv['layer_state']} (default_ratio={inv['layer_default_ratio']})")
    print("  레이어 (상위 15):")
    for l in inv["layers"][:15]:
        print(f"    {l['name']!r:30s} count={l['count']:5d} valid={l['valid']}")
    print("  블록 (상위 15, count desc):")
    for b in inv["blocks"][:15]:
        prof = f"{b['profile']} {b['w']}x{b['d']}" if b["profile"] else "-"
        print(f"    {b['name']!r:30s} count={b['count']:5d} footprint={prof}")
    print()

    print("[평면 인스턴스]")
    roots = _direct_roots(doc)
    noise_skipped = sum(1 for e in doc.modelspace() if e.dxftype() == "INSERT" and _is_noise(e.dxf.name))
    print(f"  modelspace 직계 root 수(노이즈 제외)={len(roots)}, 노이즈 스킵={noise_skipped}")
    for h in inv["plane_hint"][:10]:
        print(f"    root block {h['name']!r}: {h['count']}회")
    print(f"  기둥 후보 기준 평면병합: raw={columns['raw_count']} -> merged={columns['merged_count']}"
          f" (kept_roots={sorted(columns['kept_roots'])})")
    for w in columns["warnings"]:
        print(f"    WARNING: {w}")
    print()

    print("[기둥 소스 제안]")
    print(f"  {inv['suggestions']['column']}")
    print(f"  실제 사용 source (config.yaml 우선): {columns['source']}")
    print()

    print("[기둥 카탈로그] (병합 후 후보 기준, footprint 측정)")
    catalog = _column_catalog(columns["candidates"])
    for key, count in catalog.most_common():
        if key[0] == "circle":
            print(f"    circle r={key[1]:5d}mm : {count}개")
        else:
            print(f"    rect {key[1]:5d}x{key[2]:5d}mm : {count}개")
    print()

    print("[벽 소스 제안]")
    print(f"  {inv['suggestions']['wall']}")
    print()

    print("[노이즈/한계]")
    print("  - DEFPOINT/Defpoints, 날짜·수정류 블록은 노이즈로 스킵됨(_is_noise).")
    print("  - flat 다중평면(같은 평면이 Y로 나란히)은 현재 자동병합 대상이 아님 — 다중평면 선택 UI 미구현.")
    print("  - 레이어/블록명은 힌트일 뿐이다. 벽식 구조에서 'COL' 레이어가 구조벽일 수 있음.")
    print()

    print("[권고 config 조각]")
    print("column_source:")
    print(f"  mode: {inv['suggestions']['column']['mode']}")
    print(f"  values: {inv['suggestions']['column']['values']}")
    print("wall_source:")
    print(f"  mode: {inv['suggestions']['wall']['mode']}")
    print(f"  values: {inv['suggestions']['wall']['values']}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = _resolve_input(argv[0] if argv else None)
    cfg = _load_config()

    doc = ezdxf.readfile(path)
    header = _header_facts(doc)
    inv = extract_inventory(path)
    source = cfg.get("column_source") or inv["suggestions"]["column"]
    run_cfg = dict(cfg)
    run_cfg["column_source"] = source
    columns = load_columns(doc, run_cfg)

    _print_report(path, doc, header, inv, columns)


if __name__ == "__main__":
    main()
