import logging
import math
import re
from collections import Counter

log = logging.getLogger("dxf_to_ifc.columns")

FLOOR_TAG_RE = re.compile(r"CON-\d+-B\d*F", re.IGNORECASE)


def _floor_tag(path):
    for seg in reversed(path or []):
        m = FLOOR_TAG_RE.search(seg)
        if m:
            return m.group(0)
    return "untagged"


def _extract(leaf):
    """Position = transformed footprint bbox center (not insert point).
    Angle = composed transform's +X axis. Size = local w/d scaled by the
    transform's axis lengths, rounded to 10mm."""
    pos = leaf.matrix.transform((leaf.local_center[0], leaf.local_center[1], 0))
    xaxis = leaf.matrix.transform_direction((1, 0, 0))
    yaxis = leaf.matrix.transform_direction((0, 1, 0))
    rot = math.degrees(math.atan2(xaxis.y, xaxis.x))
    scale_x = math.hypot(xaxis.x, xaxis.y)
    scale_y = math.hypot(yaxis.x, yaxis.y)

    if leaf.profile == "circle":
        r_mm = round(leaf.r * scale_x / 10) * 10
        w_mm = d_mm = r_mm * 2
    else:
        w_mm = round(leaf.w * scale_x / 10) * 10
        d_mm = round(leaf.d * scale_y / 10) * 10
        r_mm = None

    return {
        "x_mm": pos.x, "y_mm": pos.y, "rot_deg": round(rot, 2),
        "w_mm": w_mm, "d_mm": d_mm, "r_mm": r_mm, "profile": leaf.profile,
    }


def extract_columns(candidates, cfg):
    """Position-grid dedup (safety net for residual overlap after plan merge),
    then build Column records with provenance preserved in src."""
    tol = cfg.get("dedup_tol_mm", 100)
    seen = set()
    columns = []
    size_counts = Counter()
    xs, ys = [], []

    for leaf in candidates:
        ext = _extract(leaf)
        key = (round(ext["x_mm"] / tol), round(ext["y_mm"] / tol))
        if key in seen:
            continue
        seen.add(key)

        size_key = f"R{ext['r_mm']}" if ext["profile"] == "circle" else f"{ext['w_mm']}x{ext['d_mm']}"
        if ext["profile"] != "circle" and ext["w_mm"] and ext["d_mm"]:
            ratio = max(ext["w_mm"], ext["d_mm"]) / max(min(ext["w_mm"], ext["d_mm"]), 1)
            if ratio > 6:
                log.warning(f"의심 종횡비 {ratio:.1f}:1 — handle={leaf.handle}")

        col = {
            "id": f"C{len(columns) + 1:05d}",
            "x_mm": round(ext["x_mm"], 1), "y_mm": round(ext["y_mm"], 1),
            "rot_deg": ext["rot_deg"], "profile": ext["profile"],
            "w_mm": ext["w_mm"], "d_mm": ext["d_mm"], "r_mm": ext["r_mm"],
            "size_key": size_key,
            "src": {
                "mode": leaf.source_mode, "path": leaf.path, "handle": leaf.handle,
                "layer": leaf.layer, "floor_tag": _floor_tag(leaf.path),
            },
        }
        columns.append(col)
        size_counts[size_key] += 1
        xs.append(ext["x_mm"])
        ys.append(ext["y_mm"])

    if xs:
        log.info(f"기둥 dedup 후 {len(columns)}개, 좌표범위 x=[{min(xs):.0f},{max(xs):.0f}] y=[{min(ys):.0f},{max(ys):.0f}]")
    for size_key, count in size_counts.most_common():
        log.info(f"  {size_key}: {count}개")

    return columns
