import re
from collections import Counter

import ezdxf

from .load import _direct_roots, _footprint, _traverse

FLOOR_RE = re.compile(r"(지하\s*\d+\s*층|B\d+F)", re.IGNORECASE)
DEFAULT_LAYER_NAMES = {"0", "defpoints", "defpoint"}


XREF_BIND_RE = re.compile(r"\$\d+\$")


def _short_name(name):
    """Strip xref-bind prefixes. AutoCAD xref binds produce either
    'XREF|Layer' (classic) or 'XREF$N$Layer' (bound/anonymous suffix, N
    incrementing per nesting level) - take the last real segment either way."""
    if not name:
        return name
    return XREF_BIND_RE.split(name.split("|")[-1])[-1]


def extract_inventory(path):
    doc = ezdxf.readfile(path)

    layer_counter = Counter()
    block_counter = Counter()
    direct_count = 0
    nested_leaf_count = 0

    def on_insert(e, matrix, path_segs, root_idx):
        layer_counter[e.dxf.layer] += 1
        block_counter[e.dxf.name] += 1

    def on_geom(e, matrix, path_segs, root_idx):
        nonlocal direct_count, nested_leaf_count
        layer_counter[e.dxf.layer] += 1
        if root_idx == -1:
            direct_count += 1
        else:
            nested_leaf_count += 1

    _traverse(doc, {}, on_insert=on_insert, on_geom=on_geom, geom_types=())

    paradigm = "flat" if direct_count >= nested_leaf_count else "nested"

    total = sum(layer_counter.values())
    default_count = sum(c for name, c in layer_counter.items() if (name or "").lower() in DEFAULT_LAYER_NAMES)
    layer_default_ratio = (default_count / total) if total else 0.0
    layer_state = "dumped" if layer_default_ratio > 0.4 else "meaningful"

    layers = [
        {"name": name, "short": _short_name(name), "count": count,
         "valid": (name or "").lower() not in DEFAULT_LAYER_NAMES}
        for name, count in layer_counter.most_common()
    ]

    blocks = []
    for name, count in block_counter.most_common():
        blk = doc.blocks.get(name) if name in doc.blocks else None
        fp = _footprint(blk, True, ["DEFPOINT", "DEFPOINTS"]) if blk is not None else None
        blocks.append({
            "name": name,
            "count": count,
            "w": round(fp["w"]) if fp else None,
            "d": round(fp["d"]) if fp else None,
            "profile": fp["profile"] if fp else None,
        })

    floors = []
    for name, count in block_counter.items():
        m = FLOOR_RE.search(name)
        if m:
            floors.append({"name": name, "hint": m.group(1), "count": count})

    short_lower = sorted({(l["short"] or "").lower() for l in layers})
    column_layer_hits = [n for n in short_lower if ("기둥" in n) or ("col" in n)]
    if column_layer_hits and layer_state == "meaningful":
        column_suggestion = {"mode": "layer", "values": column_layer_hits}
    else:
        column_suggestion = {"mode": "block", "values": ["기둥", "col"]}

    wall_layer_hits = [n for n in short_lower if ("wal" in n) or ("벽" in n)]
    wall_suggestion = {"mode": "layer", "values": wall_layer_hits}

    insert_name_counter = Counter(e.dxf.name for e in _direct_roots(doc))
    plane_hint = [{"name": name, "count": count} for name, count in insert_name_counter.most_common()]

    return {
        "units": doc.header.get("$INSUNITS"),
        "floors": floors,
        "paradigm": paradigm,
        "layer_state": layer_state,
        "layer_default_ratio": round(layer_default_ratio, 3),
        "layers": layers,
        "blocks": blocks,
        "suggestions": {"column": column_suggestion, "wall": wall_suggestion},
        "plane_hint": plane_hint,
        "layer_total": len(layer_counter),
        "block_total": len(block_counter),
    }
