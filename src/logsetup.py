import logging
import os


def setup_logging(cfg, name="dxf_to_ifc"):
    level_name = (cfg or {}).get("log_level", "DEBUG")
    level = getattr(logging, level_name, logging.DEBUG)
    out_dir = (cfg or {}).get("out_dir", "out")
    os.makedirs(out_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(os.path.join(out_dir, "debug.log"), mode="w", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
