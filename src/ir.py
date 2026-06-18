import json
import logging
import os

log = logging.getLogger("dxf_to_ifc.ir")


def build_ir(cfg, columns, levels, walls):
    walls = walls or []
    xs = [c["x_mm"] for c in columns] + [w["start_mm"][0] for w in walls] + [w["end_mm"][0] for w in walls]
    ys = [c["y_mm"] for c in columns] + [w["start_mm"][1] for w in walls] + [w["end_mm"][1] for w in walls]

    if cfg.get("recenter", True) and (xs or ys):
        offset_x = (max(xs) + min(xs)) / 2 if xs else 0
        offset_y = (max(ys) + min(ys)) / 2 if ys else 0
    else:
        offset_x = offset_y = 0

    ir_columns = []
    for lv in levels:
        for c in columns:
            ic = dict(c)
            ic["id"] = f"{c['id']}_{lv['name']}"
            ic["x_mm"] = round(c["x_mm"] - offset_x, 1)
            ic["y_mm"] = round(c["y_mm"] - offset_y, 1)
            ic["level"] = lv["name"]
            ir_columns.append(ic)

    ir_walls = []
    for lv in levels:
        for w in walls:
            iw = dict(w)
            iw["id"] = f"{w['id']}_{lv['name']}"
            iw["start_mm"] = [round(w["start_mm"][0] - offset_x, 1), round(w["start_mm"][1] - offset_y, 1)]
            iw["end_mm"] = [round(w["end_mm"][0] - offset_x, 1), round(w["end_mm"][1] - offset_y, 1)]
            iw["level"] = lv["name"]
            ir_walls.append(iw)

    log.info(f"IR 빌드: 레벨={len(levels)} 기둥={len(ir_columns)} 벽={len(ir_walls)} recenter_offset=({offset_x:.1f},{offset_y:.1f})")

    return {
        "meta": {
            "source": cfg.get("input_dxf"),
            "units": cfg.get("units", "mm"),
            "recenter_offset_mm": [offset_x, offset_y],
            "build_elements": cfg.get("build_elements", {}),
        },
        "levels": levels,
        "columns": ir_columns,
        "walls": ir_walls,
    }


def save_ir(ir, cfg):
    out_dir = cfg.get("out_dir", "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_ir.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ir, f, ensure_ascii=False, indent=2)
    return path


def load_ir(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
