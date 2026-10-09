"""The run log: the `athc` logger, where its file lives, and `setup_logging()`.

The console writes every status line here itself; nothing else in athc logs.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from platformdirs import user_log_path

LOGGER_NAME = "athc"
LOG_FILE = "athc.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5
_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(LOGGER_NAME)
# File only: nothing from `logging` reaches the console, and a run without
# `setup_logging()` (a command under CliRunner) never falls back to
# `logging.lastResort`, which would print the line a second time.
logger.propagate = False
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)


def log_dir() -> Path:
    """`%LOCALAPPDATA%\\athc\\Logs`, or `ATHC_LOG_DIR` when set (tests, dev)."""
    if override := os.environ.get("ATHC_LOG_DIR"):
        return Path(override)
    return user_log_path("athc", appauthor=False)


def log_path() -> Path:
    return log_dir() / LOG_FILE


class _RunLogHandler(RotatingFileHandler):
    """A rotating handler that logs on when the rotation fails.

    Windows refuses to rename a file another process holds open, and an
    `autocontinue` left running holds the log for hours. The stdlib handler
    would then print a traceback to stderr for every line; this one keeps
    writing to the current file and stops trying to rotate for the rest of
    the process.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._rotation_failed = False

    def shouldRollover(self, record: logging.LogRecord) -> int:
        if self._rotation_failed:
            return 0
        return super().shouldRollover(record)

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except OSError:
            self._rotation_failed = True
            if self.stream is None:
                self.stream = self._open()


def setup_logging() -> Path:
    """Open the rotating run log and return its path; `main()` calls this once
    per run. A previous file handler is closed and replaced, so a test may call
    it again without stacking handlers."""
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    handler = _RunLogHandler(
        path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    logger.addHandler(handler)
    return path
