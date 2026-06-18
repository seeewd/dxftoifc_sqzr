import logging

log = logging.getLogger("dxf_to_ifc.levels")


def build_levels(cfg):
    levels = list(cfg.get("levels") or [])
    repeat = cfg.get("repeat_floors") or {}

    if repeat.get("enabled"):
        count = repeat.get("count", 1)
        start = repeat.get("start_elevation_mm", 0)
        height = repeat.get("height_mm", 3500)
        prefix = repeat.get("name_prefix", "F")
        levels = [
            {"name": f"{prefix}{i + 1}", "elevation_mm": start + i * height, "height_mm": height}
            for i in range(count)
        ]

    if not levels:
        levels = [{"name": "1F", "elevation_mm": 0, "height_mm": 3500}]
        log.warning("레벨이 비어있어 기본값(1F, EL0, H3500)을 사용한다.")

    seen = {}
    for lv in levels:
        el = lv["elevation_mm"]
        if el in seen:
            log.warning(f"레벨 elevation 중복: {lv['name']} EL{el} (기존 {seen[el]})")
        seen[el] = lv["name"]

    return levels
