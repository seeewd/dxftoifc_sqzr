import logging
import math

log = logging.getLogger("dxf_to_ifc.walls")


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length else (1.0, 0.0)


def _parallel(ua, ub, tol_deg):
    dot = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))
    return math.degrees(math.acos(abs(dot))) <= tol_deg


class _Grid:
    """Uniform-cell spatial index over segment midpoints, queried with a
    1-ring neighborhood so candidate lookup stays near-O(1) instead of O(n^2)."""

    def __init__(self, cell):
        self.cell = cell
        self.buckets = {}

    def _key(self, pt):
        return (math.floor(pt[0] / self.cell), math.floor(pt[1] / self.cell))

    def insert(self, idx, seg):
        mid = ((seg["a"][0] + seg["b"][0]) / 2, (seg["a"][1] + seg["b"][1]) / 2)
        self.buckets.setdefault(self._key(mid), []).append(idx)

    def query(self, seg):
        mid = ((seg["a"][0] + seg["b"][0]) / 2, (seg["a"][1] + seg["b"][1]) / 2)
        cx, cy = self._key(mid)
        result = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                result.extend(self.buckets.get((cx + dx, cy + dy), []))
        return result


def _perp_dist_and_overlap(a, b, ua):
    """Project b onto a's (origin=a.a, axis=ua) frame: d = signed perpendicular
    distance (averaged over b's endpoints), [lo,hi] = overlap of a's [0,len_a]
    with b's projected range, ratio = overlap / shorter segment's length."""
    p0 = a["a"]
    nx, ny = -ua[1], ua[0]

    def proj(pt):
        return (pt[0] - p0[0]) * ua[0] + (pt[1] - p0[1]) * ua[1]

    def perp(pt):
        return (pt[0] - p0[0]) * nx + (pt[1] - p0[1]) * ny

    b_p0, b_p1 = proj(b["a"]), proj(b["b"])
    b_lo, b_hi = min(b_p0, b_p1), max(b_p0, b_p1)
    d = (perp(b["a"]) + perp(b["b"])) / 2

    lo = max(0.0, b_lo)
    hi = min(a["len"], b_hi)
    overlap_len = max(0.0, hi - lo)
    shorter = min(a["len"], b["len"])
    ratio = overlap_len / shorter if shorter else 0.0
    return d, lo, hi, ratio


def _pair_segments(segments, cfg):
    tmin = cfg.get("wall_thickness_min_mm", 100)
    tmax = cfg.get("wall_thickness_max_mm", 600)
    ang_tol = cfg.get("wall_parallel_tol_deg", 1)
    overlap_min = cfg.get("wall_overlap_min_ratio", 0.3)
    min_len = cfg.get("wall_min_length_mm", 150)
    min_seg_len = max(tmin, 150)

    segs = []
    for s in segments:
        length = _dist(s["a"], s["b"])
        if length < min_seg_len:
            continue
        segs.append({**s, "len": length})
    segs.sort(key=lambda s: -s["len"])

    grid = _Grid(cell=max(2000, tmax * 3))
    for i, s in enumerate(segs):
        grid.insert(i, s)

    used = [False] * len(segs)
    walls = []
    unpaired = 0

    for i, a in enumerate(segs):
        if used[i]:
            continue
        ua = _unit(a["a"], a["b"])
        best = None
        best_ratio = 0.0
        for j in grid.query(a):
            if j == i or used[j]:
                continue
            b = segs[j]
            ub = _unit(b["a"], b["b"])
            if not _parallel(ua, ub, ang_tol):
                continue
            d, lo, hi, ratio = _perp_dist_and_overlap(a, b, ua)
            if not (tmin <= abs(d) <= tmax):
                continue
            if ratio < overlap_min or ratio <= best_ratio:
                continue
            best_ratio = ratio
            best = (j, d, lo, hi)

        if best is None:
            unpaired += 1
            continue

        j, d, lo, hi = best
        used[i] = True
        used[j] = True
        nx, ny = -ua[1], ua[0]
        half = d / 2
        sx = a["a"][0] + ua[0] * lo + nx * half
        sy = a["a"][1] + ua[1] * lo + ny * half
        ex = a["a"][0] + ua[0] * hi + nx * half
        ey = a["a"][1] + ua[1] * hi + ny * half
        length = math.hypot(ex - sx, ey - sy)
        thickness = round(abs(d) / 10) * 10
        if length < max(min_len, thickness):
            continue
        walls.append({"start": (sx, sy), "end": (ex, ey), "thickness_mm": thickness})

    log.info(f"벽 페어 {len(walls)} (미페어 선분 {unpaired})")
    return walls


def _merge_collinear(walls, ang_tol, perp_tol, gap):
    """Group walls on the same line (direction + quantized perpendicular
    offset) and same thickness bucket, then bridge gaps <= gap along the
    direction axis (recovers door/jamb fragmentation without merging across
    real openings)."""
    groups = {}
    for w in walls:
        u = _unit(w["start"], w["end"])
        ang = math.degrees(math.atan2(u[1], u[0])) % 180
        ang_key = round(ang / max(ang_tol, 0.5))
        nx, ny = -u[1], u[0]
        c = w["start"][0] * nx + w["start"][1] * ny
        c_key = round(c / perp_tol) if perp_tol else round(c)
        t_key = round(w["thickness_mm"] / 50)
        groups.setdefault((ang_key, c_key, t_key), []).append(w)

    merged = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(dict(group[0]))
            continue

        ref = group[0]
        u = _unit(ref["start"], ref["end"])
        origin = ref["start"]
        nx, ny = -u[1], u[0]

        def proj(pt):
            return (pt[0] - origin[0]) * u[0] + (pt[1] - origin[1]) * u[1]

        def perp(pt):
            return (pt[0] - origin[0]) * nx + (pt[1] - origin[1]) * ny

        pieces = []
        perps = []
        for w in group:
            p0, p1 = proj(w["start"]), proj(w["end"])
            pieces.append((min(p0, p1), max(p0, p1), w["thickness_mm"]))
            perps.append(perp(w["start"]))
            perps.append(perp(w["end"]))
        c_avg = sum(perps) / len(perps)
        pieces.sort()

        runs = []
        cur_lo, cur_hi, cur_t = pieces[0]
        cur_len = cur_hi - cur_lo
        for lo, hi, t in pieces[1:]:
            if lo - cur_hi <= gap:
                seg_len = hi - lo
                if seg_len > cur_len:
                    cur_t = t
                    cur_len = seg_len
                cur_hi = max(cur_hi, hi)
            else:
                runs.append((cur_lo, cur_hi, cur_t))
                cur_lo, cur_hi, cur_t, cur_len = lo, hi, t, hi - lo
        runs.append((cur_lo, cur_hi, cur_t))

        for lo, hi, t in runs:
            sx, sy = origin[0] + u[0] * lo + nx * c_avg, origin[1] + u[1] * lo + ny * c_avg
            ex, ey = origin[0] + u[0] * hi + nx * c_avg, origin[1] + u[1] * hi + ny * c_avg
            merged.append({"start": (sx, sy), "end": (ex, ey), "thickness_mm": t})

    return merged


def _line_intersect(p1, d1, p2, d2):
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denom) < 1e-9:
        return None
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t = (dx * d2[1] - dy * d2[0]) / denom
    s = (dx * d1[1] - dy * d1[0]) / denom
    return (p1[0] + t * d1[0], p1[1] + t * d1[1]), s


def _join_corners(walls, extend_max, ang_tol_perp=20, margin=200):
    """For each wall endpoint, extend/trim onto the nearest non-parallel
    wall's centerline if the intersection is within extend_max and lands
    inside (+-margin) that wall's own span. Replaces a plain endpoint-average
    snap, which can't close gaps wider than the snap radius."""
    items = [dict(w) for w in walls]
    dirs = [_unit(w["start"], w["end"]) for w in items]
    lens = [_dist(w["start"], w["end"]) for w in items]

    moved = 0
    for i, w in enumerate(items):
        for end_name in ("start", "end"):
            pt = w[end_name]
            best_pt = None
            best_dist = extend_max
            for j, w2 in enumerate(items):
                if j == i:
                    continue
                dot = max(-1.0, min(1.0, abs(dirs[i][0] * dirs[j][0] + dirs[i][1] * dirs[j][1])))
                if math.degrees(math.acos(dot)) < ang_tol_perp:
                    continue
                res = _line_intersect(pt, dirs[i], w2["start"], dirs[j])
                if res is None:
                    continue
                ipt, s = res
                if not (-margin <= s <= lens[j] + margin):
                    continue
                d = _dist(pt, ipt)
                if d <= best_dist:
                    best_dist = d
                    best_pt = ipt
            if best_pt is not None:
                w[end_name] = best_pt
                moved += 1

    return items, moved


def extract_walls(segments, cfg):
    walls = _pair_segments(segments, cfg)

    perp_tol = cfg.get("dedup_tol_mm", 100) / 2
    gap = cfg.get("wall_join_gap_mm", 300)
    merged = _merge_collinear(walls, cfg.get("wall_parallel_tol_deg", 1), perp_tol, gap)
    log.info(f"공선병합 {len(merged)}")

    joined, moved = _join_corners(merged, cfg.get("wall_join_extend_mm", 400))
    log.info(f"코너연장 {moved}끝점")

    degenerate = sum(1 for w in joined if _dist(w["start"], w["end"]) < 10)
    if degenerate:
        log.warning(f"코너연장 후 길이<10mm로 축소된 벽 {degenerate}개 제외")
    joined = [w for w in joined if _dist(w["start"], w["end"]) >= 10]

    thickness_counts = {}
    result = []
    for k, w in enumerate(joined):
        result.append({
            "id": f"W{k + 1:05d}",
            "start_mm": [round(w["start"][0], 1), round(w["start"][1], 1)],
            "end_mm": [round(w["end"][0], 1), round(w["end"][1], 1)],
            "thickness_mm": w["thickness_mm"],
        })
        thickness_counts[w["thickness_mm"]] = thickness_counts.get(w["thickness_mm"], 0) + 1

    log.info(f"벽 최종 {len(result)}, 두께분포={thickness_counts}")
    return result
