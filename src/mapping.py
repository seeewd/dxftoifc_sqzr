DEFAULT_VALUES = {
    "block": ["기둥", "col"],
    "path": ["기둥", "col"],
    "layer": [],
}


def make_matcher(source):
    """source = {mode: layer|block|path, values:[...]}
    Returns match(leaf_name, path_segments, layer) -> bool (substring match)."""
    mode = (source or {}).get("mode", "block")
    values = (source or {}).get("values") or DEFAULT_VALUES.get(mode, [])
    values_lower = [v.lower() for v in values if v]

    def match(leaf_name, path_segments, layer):
        if not values_lower:
            return False
        if mode == "layer":
            target = (layer or "").lower()
        elif mode == "path":
            target = " ".join(path_segments or []).lower()
        else:  # block
            target = (leaf_name or "").lower()
        return any(v in target for v in values_lower)

    return match
