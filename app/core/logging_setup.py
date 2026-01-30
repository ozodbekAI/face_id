import logging
import os
from logging.handlers import RotatingFileHandler

from .config import settings


def setup_logging() -> None:
    log_dir = settings.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)

    root = logging.getLogger()
    if getattr(root, "_faceid_configured", False):
        return

    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    root._faceid_configured = True
