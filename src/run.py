import argparse
import time

import ezdxf
import yaml

from . import logsetup
from .columns import extract_columns
from .ifc_writer import write_ifc
from .ir import build_ir, save_ir
from .levels import build_levels
from .load import load_columns
from .report import validate_and_summarize


def run_pipeline(cfg, stream_queue=None):
    t0 = time.time()
    logger = logsetup.setup_logging(cfg)
    logger.info(f"입력: {cfg.get('input_dxf')}")

    doc = ezdxf.readfile(cfg["input_dxf"])

    columns = []
    if cfg.get("build_elements", {}).get("column", True):
        result = load_columns(doc, cfg)
        for w in result["warnings"]:
            logger.warning(w)
        columns = extract_columns(result["candidates"], cfg)
        logger.info(f"기둥: raw={result['raw_count']} merged={result['merged_count']} dedup후={len(columns)}")
    else:
        logger.info("기둥 비활성, 스킵")

    walls = []
    if cfg.get("build_elements", {}).get("wall", False):
        logger.warning("벽 인식 미구현 — 스킵 (Phase2 예정)")

    levels = build_levels(cfg)
    ir = build_ir(cfg, columns, levels, walls)
    ir_path = save_ir(ir, cfg)
    logger.info(f"IR 저장: {ir_path}")

    ifc_meta = write_ifc(ir, cfg)
    logger.info(f"IFC 저장: {ifc_meta['path']}")

    report = validate_and_summarize(ifc_meta["path"], ir, ifc_meta, t0)
    return {"ir": ir, "ifc_meta": ifc_meta, "report": report}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
