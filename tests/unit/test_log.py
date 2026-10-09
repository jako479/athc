"""The run log: where it goes, what a line looks like, rotation, and that
`setup_logging` is safe to call again."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from athc.log import log_path, logger, setup_logging


def _file_handlers() -> list[RotatingFileHandler]:
    return [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]


def test_log_dir_defaults_to_the_user_log_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ATHC_LOG_DIR", raising=False)
    path = log_path()
    assert path.name == "athc.log"
    assert path.parent.name == "Logs" and path.parent.parent.name == "athc"


def test_athc_log_dir_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path / "logs"))
    assert log_path() == tmp_path / "logs" / "athc.log"


def test_setup_creates_the_folder_and_writes_time_level_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path / "a" / "b"))
    path = setup_logging()
    logger.info("hello %s", "there")
    assert path == tmp_path / "a" / "b" / "athc.log"
    line = path.read_text(encoding="utf-8").splitlines()[-1]
    date, time, level, *message = line.split()
    assert level == "INFO" and " ".join(message) == "hello there"
    assert len(date) == 10 and len(time) == 8


def test_setup_twice_keeps_one_file_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    setup_logging()
    assert len(_file_handlers()) == 1


def test_rotation_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    handler = _file_handlers()[0]
    assert handler.maxBytes == 1_000_000 and handler.backupCount == 5
    assert handler.encoding == "utf-8"


def test_nothing_reaches_the_root_logger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    seen: list[logging.LogRecord] = []
    root_handler = logging.Handler()
    root_handler.emit = seen.append  # type: ignore[method-assign]
    logging.getLogger().addHandler(root_handler)
    try:
        logger.warning("quiet")
    finally:
        logging.getLogger().removeHandler(root_handler)
    assert seen == []


def test_rotation_blocked_by_another_handle_keeps_logging_quietly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Windows refuses to rename a log another athc holds open (an autocontinue
    left running); the handler then logs on without rotating instead of printing
    a traceback for every line."""
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    monkeypatch.setattr("athc.log.MAX_BYTES", 80)
    path = setup_logging()
    with path.open("rb"):
        for i in range(10):
            logger.info("line %d is long enough to pass the rotation limit", i)
    assert capsys.readouterr().err == ""
    assert "line 9 is long enough" in path.read_text(encoding="utf-8")
    assert not (tmp_path / "athc.log.1").exists()
