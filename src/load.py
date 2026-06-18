import math
import re
from dataclasses import dataclass, field

import ezdxf
from ezdxf import bbox as ezdxf_bbox
from ezdxf.math import Matrix44

from .mapping import make_matcher

NOISE_PREFIX_RE = re.compile(r"^\d{6,}")
NOISE_KEYWORDS = ("수정", "추가", "두께수정")


def _is_noise(name):
    if not name:
        return False
    if NOISE_PREFIX_RE.match(name):
        return True
    return any(k in name for k in NOISE_KEYWORDS)


def _direct_roots(doc):
    """Direct (modelspace-level) INSERT entities, noise excluded. Index in this
    list is the stable root_idx used everywhere else in this module."""
    msp = doc.modelspace()
    return [e for e in msp if e.dxftype() == "INSERT" and not _is_noise(e.dxf.name)]


def _walk(doc, block, matrix, path, root_idx, depth, depth_guard, on_insert, on_geom, geom_types):
    if depth > depth_guard:
        return
    for e in block:
        dxftype = e.dxftype()
        if dxftype == "INSERT":
            name = e.dxf.name
            if _is_noise(name):
                continue
            child_matrix = Matrix44.chain(e.matrix44(), matrix)
            child_path = path + [name]
            if on_insert:
                on_insert(e, child_matrix, child_path, root_idx)
            child_block = doc.blocks.get(name) if name in doc.blocks else None
            if child_block is not None:
                _walk(doc, child_block, child_matrix, child_path, root_idx, depth + 1,
                      depth_guard, on_insert, on_geom, geom_types)
        elif on_geom and (not geom_types or dxftype in geom_types):
            on_geom(e, matrix, path, root_idx)


def _traverse(doc, cfg, on_geom=None, geom_types=(), on_insert=None):
    """Single shared recursive walk over modelspace direct + nested geometry.
    root_idx=-1 for modelspace-direct non-INSERT entities; otherwise the index
    of the top-level INSERT this leaf descends from (see _direct_roots)."""
    depth_guard = (cfg or {}).get("depth_guard", 10)
    msp = doc.modelspace()
    identity = Matrix44()

    for e in msp:
        if e.dxftype() == "INSERT":
            continue
        if on_geom and (not geom_types or e.dxftype() in geom_types):
            on_geom(e, identity, [], -1)

    for root_idx, e in enumerate(_direct_roots(doc)):
        matrix = Matrix44.chain(e.matrix44(), identity)
        path = [e.dxf.name]
        if on_insert:
            on_insert(e, matrix, path, root_idx)
        block = doc.blocks.get(e.dxf.name) if e.dxf.name in doc.blocks else None
        if block is not None:
            _walk(doc, block, matrix, path, root_idx, 1, depth_guard, on_insert, on_geom, geom_types)


def _geom_record(e, matrix, root_idx):
    dxftype = e.dxftype()
    if dxftype == "LINE":
        a = matrix.transform(e.dxf.start)
        b = matrix.transform(e.dxf.end)
        return {"type": "LINE", "layer": e.dxf.layer, "handle": e.dxf.handle,
                "root_idx": root_idx, "closed": False,
                "pts": [(a.x, a.y), (b.x, b.y)], "center": None, "r": None}
    if dxftype == "LWPOLYLINE":
        pts = [matrix.transform((x, y, 0)) for x, y in e.get_points("xy")]
        return {"type": "LWPOLYLINE", "layer": e.dxf.layer, "handle": e.dxf.handle,
                "root_idx": root_idx, "closed": bool(e.closed),
                "pts": [(p.x, p.y) for p in pts], "center": None, "r": None}
    if dxftype == "CIRCLE":
        c = matrix.transform(e.dxf.center)
        edge = matrix.transform_direction((e.dxf.radius, 0, 0))
        r = math.hypot(edge.x, edge.y)
        return {"type": "CIRCLE", "layer": e.dxf.layer, "handle": e.dxf.handle,
                "root_idx": root_idx, "closed": True,
                "pts": [], "center": (c.x, c.y), "r": r}
    return None


def _collect_geometry(doc, cfg, predicate, types=("LINE", "LWPOLYLINE", "CIRCLE")):
    """Collect raw leaf geometry (WCS) matching predicate(layer, path_segments).
    Covers modelspace-direct (flat) and nested-block (nested) leaves alike."""
    results = []

    def on_geom(e, matrix, path, root_idx):
        if not predicate(e.dxf.layer, path):
            return
        rec = _geom_record(e, matrix, root_idx)
        if rec:
            results.append(rec)

    _traverse(doc, cfg, on_geom=on_geom, geom_types=types)
    return results


def _footprint(blk, exclude_text=True, exclude_layers=None):
    """Block definition's direct-entity outer bbox. TEXT and excluded layers
    (e.g. DEFPOINT) are dropped before measuring so labels don't inflate size.
    Profile is 'circle' when a single CIRCLE explains most of the bbox area,
    else 'rect'."""
    exclude_layers = {l.lower() for l in (exclude_layers or [])}
    ents = []
    for e in blk:
        if e.dxftype() == "INSERT":
            continue
        if exclude_text and e.dxftype() in ("TEXT", "MTEXT"):
            continue
        if (e.dxf.layer or "").lower() in exclude_layers:
            continue
        ents.append(e)
    if not ents:
        return None

    box = ezdxf_bbox.extents(ents, fast=True)
    if not box.has_data:
        return None
    minx, miny, _ = box.extmin
    maxx, maxy, _ = box.extmax
    w = maxx - minx
    d = maxy - miny
    center = ((minx + maxx) / 2, (miny + maxy) / 2)

    profile = "rect"
    r = None
    circles = [e for e in ents if e.dxftype() == "CIRCLE"]
    if circles and w > 0 and d > 0:
        biggest = max(circles, key=lambda c: c.dxf.radius)
        circle_area = math.pi * biggest.dxf.radius ** 2
        bbox_area = w * d
        if circle_area / bbox_area > 0.55:
            profile = "circle"
            r = biggest.dxf.radius
            center = (biggest.dxf.center.x, biggest.dxf.center.y)
            w = d = r * 2

    return {"w": w, "d": d, "center": center, "profile": profile, "r": r}


@dataclass
class LeafColumn:
    matrix: Matrix44
    local_center: tuple
    w: float
    d: float
    r: float
    profile: str
    root_idx: int
    handle: str
    path: list = field(default_factory=list)
    layer: str = None
    source_mode: str = "block"

    def world_center(self):
        p = self.matrix.transform((self.local_center[0], self.local_center[1], 0))
        return (p.x, p.y)


def _block_columns(doc, cfg, matcher):
    """Block detector: recurse INSERTs, match leaf block name/path, measure the
    matched block's own footprint."""
    exclude_layers = cfg.get("footprint_exclude_layers", ["DEFPOINT", "DEFPOINTS"])
    exclude_text = cfg.get("footprint_exclude_text", True)
    fp_min = cfg.get("column_footprint_min_mm", 200)
    fp_max = cfg.get("column_footprint_max_mm", 2000)
    results = []

    def on_insert(e, matrix, path, root_idx):
        name = e.dxf.name
        if not matcher(name, path, e.dxf.layer):
            return
        blk = doc.blocks.get(name) if name in doc.blocks else None
        if blk is None:
            return
        fp = _footprint(blk, exclude_text, exclude_layers)
        if not fp:
            return
        size = fp["r"] * 2 if fp["profile"] == "circle" else max(fp["w"], fp["d"])
        if not (fp_min <= size <= fp_max):
            return
        results.append(LeafColumn(matrix=matrix, local_center=fp["center"], w=fp["w"], d=fp["d"],
                                   r=fp["r"], profile=fp["profile"], root_idx=root_idx,
                                   handle=e.dxf.handle, path=path, layer=e.dxf.layer,
                                   source_mode="block"))

    _traverse(doc, cfg, on_insert=on_insert)
    return results


def _seg_len(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _cluster_columns(geoms, cfg):
    """Raw-geometry detector (flat paradigm): CIRCLE / closed LWPOLYLINE stand
    alone; open LINE/LWPOLYLINE segments cluster by endpoint-snap union-find.
    Any single segment longer than fp_max kills its cluster (grid-line guard)."""
    fp_min = cfg.get("column_footprint_min_mm", 200)
    fp_max = cfg.get("column_footprint_max_mm", 2000)
    snap = 80
    results = []
    segments = []

    for g in geoms:
        if g["type"] == "CIRCLE":
            r = g["r"]
            if fp_min <= r * 2 <= fp_max:
                results.append(LeafColumn(matrix=Matrix44(), local_center=g["center"], w=r * 2,
                                           d=r * 2, r=r, profile="circle", root_idx=g["root_idx"],
                                           handle=g["handle"], layer=g["layer"], source_mode="raw"))
        elif g["type"] == "LWPOLYLINE" and g["closed"]:
            xs = [p[0] for p in g["pts"]]
            ys = [p[1] for p in g["pts"]]
            w, d = max(xs) - min(xs), max(ys) - min(ys)
            if fp_min <= max(w, d) <= fp_max:
                center = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
                results.append(LeafColumn(matrix=Matrix44(), local_center=center, w=w, d=d, r=None,
                                           profile="rect", root_idx=g["root_idx"], handle=g["handle"],
                                           layer=g["layer"], source_mode="raw"))
        else:
            pts = g["pts"]
            for a, b in zip(pts, pts[1:]):
                segments.append({"a": a, "b": b, "root_idx": g["root_idx"],
                                  "handle": g["handle"], "layer": g["layer"]})

    def key(pt):
        return (round(pt[0] / snap), round(pt[1] / snap))

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    tagged = []
    for s in segments:
        ka, kb = key(s["a"]), key(s["b"])
        tagged.append((ka, s))
        union(ka, kb)

    groups = {}
    for ka, s in tagged:
        groups.setdefault(find(ka), []).append(s)

    for segs in groups.values():
        if any(_seg_len(s["a"], s["b"]) > fp_max for s in segs):
            continue
        xs = [p for s in segs for p in (s["a"][0], s["b"][0])]
        ys = [p for s in segs for p in (s["a"][1], s["b"][1])]
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        if not (fp_min <= max(w, d) <= fp_max):
            continue
        center = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
        results.append(LeafColumn(matrix=Matrix44(), local_center=center, w=w, d=d, r=None,
                                   profile="rect", root_idx=segs[0]["root_idx"],
                                   handle=segs[0]["handle"], layer=segs[0]["layer"], source_mode="raw"))
    return results


def _plan_signature(members, tol):
    centers = [c.world_center() for c in members]
    minx = min(p[0] for p in centers)
    miny = min(p[1] for p in centers)
    return frozenset(
        (round((p[0] - minx) / tol), round((p[1] - miny) / tol), round(c.w / 10) * 10, round(c.d / 10) * 10)
        for p, c in zip(centers, members)
    )


def _collapse_duplicate_plans(candidates, cfg):
    """Same nested plan instanced multiple times (root_idx differs, layout
    identical) -> keep one copy per unique translation-invariant signature.
    Flat (root_idx=-1) candidates are never merged (no root to dedup by)."""
    tol = cfg.get("dedup_tol_mm", 100)
    by_root = {}
    for c in candidates:
        if c.root_idx == -1:
            continue
        by_root.setdefault(c.root_idx, []).append(c)

    seen_sigs = {}
    kept_roots = set()
    for root_idx in sorted(by_root):
        members = by_root[root_idx]
        sig = _plan_signature(members, tol)
        if sig in seen_sigs:
            continue
        seen_sigs[sig] = root_idx
        kept_roots.add(root_idx)

    warnings = []
    if len(seen_sigs) > 1:
        warnings.append(
            f"단일층 아님 의심: 서로 다른 평면 서명 {len(seen_sigs)}개 (root {sorted(seen_sigs.values())})"
        )

    kept = [c for c in candidates if c.root_idx == -1 or c.root_idx in kept_roots]
    return kept, kept_roots, warnings


def load_columns(doc, cfg):
    source = cfg.get("column_source") or {"mode": "block", "values": cfg.get("column_name_patterns", ["기둥", "col"])}
    matcher = make_matcher(source)

    block_cands = _block_columns(doc, cfg, matcher)
    raw_cands = []
    if source.get("mode") in ("layer", "path"):
        geoms = _collect_geometry(doc, cfg, lambda layer, path: matcher(None, path, layer))
        raw_cands = _cluster_columns(geoms, cfg)

    candidates = block_cands + raw_cands
    kept, kept_roots, warnings = _collapse_duplicate_plans(candidates, cfg)
    return {
        "raw_count": len(candidates),
        "merged_count": len(kept),
        "candidates": kept,
        "kept_roots": kept_roots,
        "warnings": warnings,
        "source": source,
    }
