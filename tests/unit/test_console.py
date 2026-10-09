"""The one console: streams, labels, prefix-only color, NO_COLOR / FORCE_COLOR,
verbatim text, and the log line each status line writes."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from athc.console import AthcConsole
from athc.log import logger


@pytest.fixture
def plain(monkeypatch: pytest.MonkeyPatch) -> AthcConsole:
    """A console with no color forcing either way."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    return AthcConsole()


@pytest.fixture
def records() -> Iterator[list[logging.LogRecord]]:
    """Every record the athc logger emits while the test runs."""
    seen: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = seen.append  # type: ignore[method-assign]
    logger.addHandler(handler)
    try:
        yield seen
    finally:
        logger.removeHandler(handler)


def test_results_go_to_stdout_unlogged(
    plain: AthcConsole, capsys: pytest.CaptureFixture[str], records
) -> None:
    plain.print("x.pln: 2 violation(s)")
    plain.print()
    out, err = capsys.readouterr()
    assert out == "x.pln: 2 violation(s)\n\n" and err == ""
    assert records == []


@pytest.mark.parametrize(
    ("call", "message", "stream", "line", "level"),
    [
        ("ok", "x.pln: updated", "out", "OK   x.pln: updated", logging.INFO),
        ("skip", "x.pln: defense", "out", "SKIP x.pln: defense", logging.INFO),
        ("result", "3 file(s) checked", "out", "3 file(s) checked", logging.INFO),
        ("progress", "Phase 1", "err", "Phase 1", logging.INFO),
        (
            "warn",
            "plays: no .pln files",
            "err",
            "WARN plays: no .pln files",
            logging.WARNING,
        ),
        ("fail", "x.pln: not found", "err", "FAIL x.pln: not found", logging.ERROR),
    ],
)
def test_status_lines_stream_label_and_log(
    plain: AthcConsole,
    capsys: pytest.CaptureFixture[str],
    records: list[logging.LogRecord],
    call: str,
    message: str,
    stream: str,
    line: str,
    level: int,
) -> None:
    getattr(plain, call)(message)
    out, err = capsys.readouterr()
    assert (out if stream == "out" else err) == line + "\n"
    assert (err if stream == "out" else out) == ""
    assert [(r.levelno, r.getMessage()) for r in records] == [(level, line)]


def test_text_prints_verbatim(
    plain: AthcConsole, capsys: pytest.CaptureFixture[str]
) -> None:
    # Brackets are not markup, `:x:` is not an emoji, nothing is restyled.
    plain.print("  [Run Left] :: 'OR45RL01' [1-3] :smile:")
    assert capsys.readouterr().out == "  [Run Left] :: 'OR45RL01' [1-3] :smile:\n"


def test_long_line_is_not_wrapped(
    plain: AthcConsole, capsys: pytest.CaptureFixture[str]
) -> None:
    line = "x" * 300
    plain.print(line)
    assert capsys.readouterr().out == line + "\n"


def test_warn_prints_once_without_a_handler(
    plain: AthcConsole, capsys: pytest.CaptureFixture[str]
) -> None:
    # No run log set up (a command under CliRunner): logging's last-resort
    # handler must not print the line a second time.
    plain.warn("only once")
    assert capsys.readouterr().err == "WARN only once\n"


def test_color_only_on_the_label(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    AthcConsole(force_terminal=True).ok("x.pln: updated")
    out = capsys.readouterr().out
    assert out.startswith("\x1b[") and out.endswith("   x.pln: updated\n")
    label, _, rest = out.partition("OK")
    assert "\x1b[" in label
    assert "\x1b[" not in rest.split("m", 1)[1]  # the reset code ends the color


@pytest.mark.parametrize(("value", "colored"), [("1", False), ("", True)])
def test_no_color(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    value: str,
    colored: bool,
) -> None:
    monkeypatch.setenv("NO_COLOR", value)
    AthcConsole(force_terminal=True).fail("x")
    assert ("\x1b[" in capsys.readouterr().err) is colored


def test_force_color(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    AthcConsole().ok("x")
    assert "\x1b[" in capsys.readouterr().out


def test_piped_output_has_no_color(
    plain: AthcConsole, capsys: pytest.CaptureFixture[str]
) -> None:
    plain.ok("x")
    assert capsys.readouterr().out == "OK   x\n"


def test_unexpected_names_the_log_and_logs_the_traceback(
    plain: AthcConsole,
    capsys: pytest.CaptureFixture[str],
    records: list[logging.LogRecord],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    try:
        raise RuntimeError("kaboom")
    except RuntimeError:
        plain.unexpected("x.pln")
    err = capsys.readouterr().err
    assert err == f"FAIL x.pln: unexpected error (see log: {tmp_path / 'athc.log'})\n"
    assert records[0].levelno == logging.ERROR and records[0].exc_info is not None


def test_unexpected_without_a_subject(
    plain: AthcConsole,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    try:
        raise RuntimeError("kaboom")
    except RuntimeError:
        plain.unexpected()
    err = capsys.readouterr().err
    assert err == f"FAIL unexpected error (see log: {tmp_path / 'athc.log'})\n"
