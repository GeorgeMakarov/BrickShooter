"""Logging setup for the game server.

One logger per concern:
  - `brickshooter.game` — gameplay events (JOIN / LEAVE / IN / OUT / SNAPSHOT)
  - uvicorn/FastAPI default loggers remain untouched

Config via env vars:
  BRICKSHOOTER_LOG_LEVEL  (default INFO; DEBUG also dumps full field state)
  BRICKSHOOTER_LOG_FILE   (optional path; if set, add a rotating file handler)

Call `setup_logging()` once at process start (done in backend/__main__.py).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

GAME_LOGGER = "brickshooter.game"


def setup_logging() -> None:
    level_name = os.environ.get("BRICKSHOOTER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger(GAME_LOGGER)
    root.setLevel(level)
    # Don't duplicate to root logger — uvicorn already has its own handler.
    root.propagate = True

    fmt = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d %(levelname)-5s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # If stderr isn't already handling this logger, attach a stream handler.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)

    log_file = os.environ.get("BRICKSHOOTER_LOG_FILE")
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    root.debug("logging configured level=%s file=%s", level_name, log_file or "-")
