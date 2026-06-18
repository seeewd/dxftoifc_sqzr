import logging
import time
from collections import Counter

import ifcopenshell

log = logging.getLogger("dxf_to_ifc.report")


def validate_and_summarize(ifc_path, ir, ifc_meta, t0):
    warnings = []
    try:
        m = ifcopenshell.open(ifc_path)
    except Exception as e:
        warnings.append(f"IFC open 실패: {e}")
        m = None

    validation = "FAIL"
    if m is not None:
        has_project = bool(m.by_type("IfcProject"))
        has_storey = bool(m.by_type("IfcBuildingStorey"))
        ifc_columns = m.by_type("IfcColumn")
        ifc_walls = m.by_type("IfcWall")
        missing_repr = [e.GlobalId for e in (ifc_columns + ifc_walls)
                        if not e.Representation or not e.ObjectPlacement]
        validation = "PASS" if (has_project and has_storey and not missing_repr) else "FAIL"
        for gid in missing_repr:
            warnings.append(f"Representation/Placement 누락: {gid}")
        if m.schema != "IFC4":
            warnings.append(f"schema 불일치: {m.schema}")
        if len(ifc_columns) != len(ir["columns"]):
            warnings.append(f"IfcColumn 개수 불일치: IFC={len(ifc_columns)} IR={len(ir['columns'])}")
            validation = "FAIL"
        if len(ifc_walls) != len(ir["walls"]):
            warnings.append(f"IfcWall 개수 불일치: IFC={len(ifc_walls)} IR={len(ir['walls'])}")
            validation = "FAIL"

    elapsed = time.time() - t0

    col_types = Counter()
    for c in ir["columns"]:
        key = f"R{c['r_mm']}" if c["profile"] == "circle" else f"{c['w_mm']}x{c['d_mm']}"
        col_types[key] += 1
    wall_types = Counter(w.get("thickness_mm") for w in ir["walls"])

    summary = (
        f"[SUMMARY] columns={len(ir['columns'])}{dict(col_types)} "
        f"walls={len(ir['walls'])}{dict(wall_types)} "
        f"recenter={ir['meta']['recenter_offset_mm']} "
        f"levels={len(ir['levels'])} "
        f"ifc_entities={ifc_meta.get('total_entities')} "
        f"validation={validation} warnings={len(warnings)} "
        f"time={elapsed:.1f}s"
    )
    log.info(summary)
    print(summary)
    for w in warnings:
        log.warning(w)

    return {"validation": validation, "warnings": warnings, "summary": summary, "elapsed": elapsed}
