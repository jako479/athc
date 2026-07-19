"""Tests for `athc autocontinue` — config loading, change detection, and the CLI.

Config is resolved from `config_dir()/athc.ini` (isolated per-test via the autouse
`config_dir` fixture, which sets `ATHC_CONFIG_DIR`). There is no `--config` flag.
The watch loop (pyautogui) is manual-only; the CLI is exercised with `auto_continue`
stubbed so nothing touches the screen.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.autocontinue import config
from athc.autocontinue.config import ConfigError
from athc.cli.autocontinue import autocontinue

WriteConfig = Callable[..., Path]


@pytest.fixture
def valid(write_config: WriteConfig) -> Callable[..., Path]:
    """Write a valid [autocontinue] athc.ini; override mouse/delay per test."""

    def _valid(mouse: str = "0.5", delay: str = "2.5") -> Path:
        return write_config(
            f"[autocontinue]\nmouse_move_duration = {mouse}\ndelay_before_continue = {delay}\n",
        )

    return _valid


# ── load_config: section + both settings required ─────────────────────────────


def test_load_config_reads_valid_section(valid: Callable[..., Path]) -> None:
    valid()
    cfg = config.load_config()
    assert cfg.mouse_move_duration == 0.5 and cfg.delay_before_continue == 2.5


def test_load_config_errors_when_no_config() -> None:
    with pytest.raises(ConfigError):  # autouse config_dir gives an empty dir
        config.load_config()


def test_load_config_errors_when_section_missing(write_config: WriteConfig) -> None:
    write_config("[other]\nfoo = 1\n")
    with pytest.raises(ConfigError):
        config.load_config()


def test_load_config_errors_on_missing_setting(write_config: WriteConfig) -> None:
    write_config("[autocontinue]\nmouse_move_duration = 0.5\n")
    with pytest.raises(ConfigError):
        config.load_config()


def test_load_config_errors_on_invalid_value(valid: Callable[..., Path]) -> None:
    valid(mouse="fast")
    with pytest.raises(ConfigError):
        config.load_config()


def test_release_example_section_loads(write_config: WriteConfig) -> None:
    """The shipped release/athc.ini [autocontinue] section is valid."""
    example = Path(__file__).resolve().parents[2] / "release" / "athc.ini"
    write_config(example.read_text(encoding="utf-8"))
    cfg = config.load_config()
    assert cfg.mouse_move_duration == 0.0 and cfg.delay_before_continue == 1.0
    assert cfg.hot_corner is True


# ── hot_corner: optional, defaults to enabled ─────────────────────────────────


def test_hot_corner_defaults_enabled_when_missing(valid: Callable[..., Path]) -> None:
    valid()  # no hot_corner key
    assert config.load_config().hot_corner is True


@pytest.mark.parametrize(
    "raw,expected",
    [("true", True), ("false", False), ("yes", True), ("off", False), ("0", False)],
)
def test_hot_corner_parses_boolean(
    write_config: WriteConfig, raw: str, expected: bool
) -> None:
    write_config(
        f"[autocontinue]\nmouse_move_duration = 0.0\ndelay_before_continue = 1.0\n"
        f"hot_corner = {raw}\n"
    )
    assert config.load_config().hot_corner is expected


def test_hot_corner_invalid_value_errors(write_config: WriteConfig) -> None:
    write_config(
        "[autocontinue]\nmouse_move_duration = 0.0\ndelay_before_continue = 1.0\n"
        "hot_corner = maybe\n"
    )
    with pytest.raises(ConfigError):
        config.load_config()


# ── config_signature: change detection ────────────────────────────────────────


def test_signature_none_when_file_missing() -> None:
    assert config.config_signature() is None


def test_signature_returns_tuple_for_existing_file(valid: Callable[..., Path]) -> None:
    ini = valid()
    sig = config.config_signature()
    assert sig is not None and sig[0] == str(ini)


def test_signature_stable_when_unchanged(valid: Callable[..., Path]) -> None:
    valid()
    assert config.config_signature() == config.config_signature()


def test_signature_changes_when_rewritten(valid: Callable[..., Path]) -> None:
    valid(mouse="0.1")
    before = config.config_signature()
    valid(mouse="0.123456")  # different length -> size differs
    assert before != config.config_signature()


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_cli_help_describes_continue(runner) -> None:
    result = runner.invoke(autocontinue, ["--help"])
    assert result.exit_code == 0 and "Continue" in result.output


def test_cli_no_config_exits_1(runner, caplog) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(autocontinue, [])
    assert result.exit_code == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_cli_missing_dependency_exits_1(
    runner, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    # Simulate pyautogui missing: the lazy import fails -> exit 1 naming the module.
    monkeypatch.delitem(sys.modules, "athc.autocontinue.main", raising=False)
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(autocontinue, [])
    assert result.exit_code == 1
    assert any("pyautogui" in r.getMessage() for r in caplog.records)


def test_cli_runs_with_config(
    runner, valid: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid()
    calls: list[bool | None] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda hot_corner=None: calls.append(hot_corner),
    )
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0 and calls == [None]


@pytest.mark.parametrize(
    "args,expected",
    [([], None), (["--hot-corner"], True), (["--no-hot-corner"], False)],
)
def test_cli_forwards_hot_corner_override(
    runner,
    valid: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    expected: bool | None,
) -> None:
    """The flag overrides config; absent, None lets the config value win."""
    valid()
    calls: list[bool | None] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda hot_corner=None: calls.append(hot_corner),
    )
    result = runner.invoke(autocontinue, args)
    assert result.exit_code == 0 and calls == [expected]


def test_cli_keyboard_interrupt_exits_clean(
    runner, valid: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid()

    def _boom(hot_corner: bool | None = None) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", _boom)
    monkeypatch.setattr("athc.cli.autocontinue.time.sleep", lambda _: None)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert "Shutting down AutoContinue" in result.output


# ── focus gating ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Front Page Sports Football Pro '98", True),
        ("front page sports football pro '98 - week 5", True),  # case + substring
        ("Microsoft Outlook", False),
        ("", False),
    ],
)
def test_game_has_focus_matches_title(
    monkeypatch: pytest.MonkeyPatch, title: str, expected: bool
) -> None:
    from athc.autocontinue import main

    monkeypatch.setattr(main, "_foreground_window_title", lambda: title)
    assert main._game_has_focus() is expected
