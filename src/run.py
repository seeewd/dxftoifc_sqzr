import argparse
import logging
import time

import ezdxf
import yaml

from . import logsetup
from .columns import extract_columns
from .ifc_writer import write_ifc
from .ir import build_ir, save_ir
from .levels import build_levels
from .load import load_columns, load_wall_lines
from .report import validate_and_summarize
from .walls import extract_walls


class _QueueLogHandler(logging.Handler):
    """Pushes formatted log lines onto a queue for SSE streaming (backend/app.py)."""

    def __init__(self, q):
        super().__init__()
        self.q = q

    def emit(self, record):
        self.q.put(self.format(record))


def run_pipeline(cfg, stream_queue=None):
    t0 = time.time()
    logger = logsetup.setup_logging(cfg)

    queue_handler = None
    if stream_queue is not None:
        queue_handler = _QueueLogHandler(stream_queue)
        queue_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logger.addHandler(queue_handler)

    try:
        logger.info(f"입력: {cfg.get('input_dxf')}")

        doc = ezdxf.readfile(cfg["input_dxf"])

        columns = []
        kept_roots = None
        if cfg.get("build_elements", {}).get("column", True):
            result = load_columns(doc, cfg)
            for w in result["warnings"]:
                logger.warning(w)
            columns = extract_columns(result["candidates"], cfg)
            kept_roots = result["kept_roots"]
            logger.info(f"기둥: raw={result['raw_count']} merged={result['merged_count']} dedup후={len(columns)}")
        else:
            logger.info("기둥 비활성, 스킵")

        walls = []
        if cfg.get("build_elements", {}).get("wall", False):
            segments = load_wall_lines(doc, cfg, kept_roots)
            walls = extract_walls(segments, cfg)
            logger.info(f"벽: 선분={len(segments)} 최종={len(walls)}")
        else:
            logger.info("벽 비활성, 스킵")

        levels = build_levels(cfg)
        ir = build_ir(cfg, columns, levels, walls)
        ir_path = save_ir(ir, cfg)
        logger.info(f"IR 저장: {ir_path}")

        ifc_meta = write_ifc(ir, cfg)
        logger.info(f"IFC 저장: {ifc_meta['path']}")

        report = validate_and_summarize(ifc_meta["path"], ir, ifc_meta, t0)
        return {"ir": ir, "ifc_meta": ifc_meta, "report": report}
    finally:
        if queue_handler is not None:
            logger.removeHandler(queue_handler)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
