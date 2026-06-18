import logging
import math
import os

import numpy as np
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.context as context
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.project as project
import ifcopenshell.api.root as root
import ifcopenshell.api.spatial as spatial
import ifcopenshell.api.type as type_api
import ifcopenshell.api.unit as unit

log = logging.getLogger("dxf_to_ifc.ifc_writer")


def _placement_matrix(x_m, y_m, z_m, rot_deg):
    """Column-major 4x4: col0=X axis, col1=Y axis, col2=Z axis, col3=translation."""
    rad = math.radians(rot_deg)
    c, s = math.cos(rad), math.sin(rad)
    m = np.eye(4)
    m[0, 0], m[0, 1] = c, -s
    m[1, 0], m[1, 1] = s, c
    m[0, 3], m[1, 3], m[2, 3] = x_m, y_m, z_m
    return m


def write_ifc(ir, cfg):
    schema = cfg.get("ifc_schema", "IFC4")
    f = project.create_file(schema)

    proj = root.create_entity(f, ifc_class="IfcProject", name="dxf_to_ifc")
    length_unit = unit.add_si_unit(f, unit_type="LENGTHUNIT")
    angle_unit = unit.add_si_unit(f, unit_type="PLANEANGLEUNIT")
    unit.assign_unit(f, units=[length_unit, angle_unit])

    model_ctx = context.add_context(f, context_type="Model")
    body_ctx = context.add_context(f, context_type="Model", context_identifier="Body",
                                    target_view="MODEL_VIEW", parent=model_ctx)

    site = root.create_entity(f, ifc_class="IfcSite", name="Site")
    building = root.create_entity(f, ifc_class="IfcBuilding", name="Building")
    aggregate.assign_object(f, products=[site], relating_object=proj)
    aggregate.assign_object(f, products=[building], relating_object=site)

    storeys = {}
    elevations = {}
    heights = {}
    for lv in ir["levels"]:
        storey = root.create_entity(f, ifc_class="IfcBuildingStorey", name=lv["name"])
        storey.Elevation = lv["elevation_mm"] / 1000.0
        aggregate.assign_object(f, products=[storey], relating_object=building)
        storeys[lv["name"]] = storey
        elevations[lv["name"]] = lv["elevation_mm"]
        heights[lv["name"]] = lv["height_mm"]

    column_types = {}
    counts = {}
    missing = []

    for col in ir["columns"]:
        storey = storeys.get(col["level"])
        if storey is None:
            log.warning(f"레벨 없음, 스킵: {col['id']}")
            missing.append(col["id"])
            continue

        w_mm, d_mm, r_mm = col.get("w_mm"), col.get("d_mm"), col.get("r_mm")
        if col["profile"] == "circle":
            if not r_mm:
                log.warning(f"반지름 0, 스킵: {col['id']}")
                missing.append(col["id"])
                continue
            type_key = ("circle", r_mm)
        else:
            if not w_mm or not d_mm:
                log.warning(f"크기 0, 스킵: {col['id']}")
                missing.append(col["id"])
                continue
            type_key = ("rect", w_mm, d_mm)

        ctype_key = type_key + (col["level"],)
        col_type = column_types.get(ctype_key)
        if col_type is None:
            col_type = root.create_entity(f, ifc_class="IfcColumnType", predefined_type="COLUMN",
                                           name=f"COL-{'-'.join(str(p) for p in type_key)}")
            if type_key[0] == "circle":
                profile = f.create_entity("IfcCircleProfileDef", ProfileType="AREA", ProfileName=None,
                                           Position=None, Radius=r_mm / 1000.0)
            else:
                profile = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", ProfileName=None,
                                           Position=None, XDim=w_mm / 1000.0, YDim=d_mm / 1000.0)
            depth_m = heights[col["level"]] / 1000.0
            rep = geometry.add_profile_representation(f, context=body_ctx, profile=profile, depth=depth_m)
            geometry.assign_representation(f, product=col_type, representation=rep)
            column_types[ctype_key] = col_type

        column = root.create_entity(f, ifc_class="IfcColumn", predefined_type="COLUMN", name=col["id"])
        type_api.assign_type(f, related_objects=[column], relating_type=col_type)
        spatial.assign_container(f, products=[column], relating_structure=storey)
        matrix = _placement_matrix(col["x_mm"] / 1000.0, col["y_mm"] / 1000.0,
                                    elevations[col["level"]] / 1000.0, col["rot_deg"])
        geometry.edit_object_placement(f, product=column, matrix=matrix)
        counts[type_key] = counts.get(type_key, 0) + 1

    wall_types = {}
    wall_counts = {}

    for w in ir["walls"]:
        storey = storeys.get(w["level"])
        if storey is None:
            log.warning(f"레벨 없음, 스킵: {w['id']}")
            missing.append(w["id"])
            continue

        thickness_mm = w.get("thickness_mm")
        sx, sy = w["start_mm"]
        ex, ey = w["end_mm"]
        length_mm = math.hypot(ex - sx, ey - sy)
        if not thickness_mm or length_mm <= 0:
            log.warning(f"두께/길이 0, 스킵: {w['id']}")
            missing.append(w["id"])
            continue

        wall_type = wall_types.get(thickness_mm)
        if wall_type is None:
            wall_type = root.create_entity(f, ifc_class="IfcWallType", predefined_type="STANDARD",
                                            name=f"WALL-{thickness_mm}")
            wall_types[thickness_mm] = wall_type

        wall = root.create_entity(f, ifc_class="IfcWall", predefined_type="STANDARD", name=w["id"])
        type_api.assign_type(f, related_objects=[wall], relating_type=wall_type, should_map_representations=False)
        spatial.assign_container(f, products=[wall], relating_structure=storey)

        profile = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", ProfileName=None,
                                   Position=None, XDim=length_mm / 1000.0, YDim=thickness_mm / 1000.0)
        depth_m = heights[w["level"]] / 1000.0
        rep = geometry.add_profile_representation(f, context=body_ctx, profile=profile, depth=depth_m)
        geometry.assign_representation(f, product=wall, representation=rep)

        mx, my = (sx + ex) / 2.0, (sy + ey) / 2.0
        rot_deg = math.degrees(math.atan2(ey - sy, ex - sx))
        matrix = _placement_matrix(mx / 1000.0, my / 1000.0, elevations[w["level"]] / 1000.0, rot_deg)
        geometry.edit_object_placement(f, product=wall, matrix=matrix)
        wall_counts[thickness_mm] = wall_counts.get(thickness_mm, 0) + 1

    out_dir = cfg.get("out_dir", "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model.ifc")
    f.write(path)

    return {
        "path": path,
        "total_entities": len(list(f)),
        "columns": sum(counts.values()),
        "walls": sum(wall_counts.values()),
        "types": counts,
        "wall_types": wall_counts,
        "missing": missing,
    }
