"""Tests for `athc autocontinue` — config loading, change detection, and the CLI.

Config is resolved from `config_dir()/athc.ini` (isolated per-test via the autouse
`config_dir` fixture, which sets `ATHC_CONFIG_DIR`). There is no `--config` flag.
The watch loop (pyautogui) is manual-only; the CLI is exercised with `auto_continue`
stubbed so nothing touches the screen.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy
import pytest

from athc.autocontinue import config
from athc.cli.autocontinue import autocontinue
from athc.errors import FILE_NOT_FOUND, AthcError, ConfigFileError

WriteConfig = Callable[..., Path]

_BUTTON = numpy.zeros((2, 2), dtype=numpy.uint8)  # stands in for the loaded image


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
    with pytest.raises(ConfigFileError):  # autouse config_dir gives an empty dir
        config.load_config()


def test_load_config_errors_when_section_missing(write_config: WriteConfig) -> None:
    write_config("[other]\nfoo = 1\n")
    with pytest.raises(ConfigFileError):
        config.load_config()


def test_load_config_errors_on_missing_setting(write_config: WriteConfig) -> None:
    ini = write_config("[autocontinue]\nmouse_move_duration = 0.5\n")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{ini}: Missing required setting 'delay_before_continue' in [autocontinue]."
    )


def test_load_config_errors_on_invalid_value(valid: Callable[..., Path]) -> None:
    ini = valid(mouse="fast")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{ini}: [autocontinue] mouse_move_duration: Must be a number, got 'fast'."
    )


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
    ini = write_config(
        "[autocontinue]\nmouse_move_duration = 0.0\ndelay_before_continue = 1.0\n"
        "hot_corner = maybe\n"
    )
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{ini}: [autocontinue] hot_corner: Must be true or false, got 'maybe'."
    )


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
    assert result.exit_code == 0 and "Continue" in result.stdout


def test_cli_no_config_exits_2(runner, config_dir: Path) -> None:
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {config_dir / 'athc.ini'}: No [autocontinue] section. "
        "Add one, or set ATHC_CONFIG_DIR.\n"
    )


def test_cli_missing_dependency_exits_2(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate pyautogui missing: the lazy import fails -> exit 2 naming the module.
    monkeypatch.delitem(sys.modules, "athc.autocontinue.main", raising=False)
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 2
    assert result.stderr == "FAIL Missing pyautogui. Reinstall athc.\n"


def test_cli_runs_with_config(
    runner, valid: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid()
    calls: list[bool | None] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda hot_corner=None, **callbacks: calls.append(hot_corner),
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
        lambda hot_corner=None, **callbacks: calls.append(hot_corner),
    )
    result = runner.invoke(autocontinue, args)
    assert result.exit_code == 0 and calls == [expected]


def test_cli_keyboard_interrupt_exits_clean(
    runner, valid: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid()

    def _boom(hot_corner: bool | None = None, **callbacks: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", _boom)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stdout == "Shutting down AutoContinue\n"


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


# ── progress and warnings through the callbacks ───────────────────────────────


def test_loop_status_goes_to_stderr_through_the_callbacks(
    runner, valid: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid()

    def fake(hot_corner=None, *, progress, warn):
        progress("AutoContinue is RUNNING. Press CTRL-C to exit.")
        warn("Config reload failed; keeping previous settings. x")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == (
        "AutoContinue is RUNNING. Press CTRL-C to exit.\n"
        "WARN Config reload failed; keeping previous settings. x\n"
    )
    assert result.stdout == "Shutting down AutoContinue\n"


def test_reload_failure_names_the_file_and_keeps_the_settings() -> None:
    from athc.autocontinue import main

    error = ConfigFileError("Bad value.", Path("athc.ini"))
    assert main._reload_failed(error) == (
        "athc.ini: Bad value. Keeping the previous settings."
    )


def test_screen_grab_failure_warns_and_backs_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from athc.autocontinue import main

    def grab(*args: object, **kwargs: object) -> None:
        raise OSError("screen grab failed")  # PIL's own text, on a locked screen

    slept: list[float] = []
    monkeypatch.setattr(main.pyautogui, "locateCenterOnScreen", grab)
    monkeypatch.setattr(main.time, "sleep", slept.append)
    said: list[str] = []
    assert main._find_continue_button(_BUTTON, 0, 0, 1, 1, said.append) is None
    assert said == [
        "The screen is locked, a screensaver is on, or Remote Desktop is "
        "disconnected. Retrying in 60 seconds."
    ]
    assert slept == [60.0]


def test_the_loaded_button_image_is_what_the_screen_is_searched_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from athc.autocontinue import main

    seen: list[object] = []
    monkeypatch.setattr(
        main.pyautogui,
        "locateCenterOnScreen",
        lambda image, **kwargs: seen.append(image),
    )
    main._find_continue_button(_BUTTON, 0, 0, 1, 1, lambda _: None)
    assert len(seen) == 1 and seen[0] is _BUTTON


def test_the_shipped_button_image_loads_in_grayscale() -> None:
    from athc.autocontinue import main

    image = main._load_button_image(main.CONTINUE_BUTTON_IMAGE)
    assert image.ndim == 2  # one channel: the matcher compares grayscale


def test_a_missing_button_image_fails_and_says_to_reinstall(tmp_path: Path) -> None:
    from athc.autocontinue import main

    image = tmp_path / "continue_button.png"
    with pytest.raises(AthcError) as exc:
        main._load_button_image(image)
    assert str(exc.value) == f"{image}: {FILE_NOT_FOUND} Reinstall athc."


def test_an_unreadable_button_image_fails_and_says_to_reinstall(
    tmp_path: Path,
) -> None:
    from athc.autocontinue import main

    image = tmp_path / "continue_button.png"
    image.write_bytes(b"not an image")
    with pytest.raises(AthcError) as exc:
        main._load_button_image(image)
    assert str(exc.value) == f"{image}: Cannot read the image. Reinstall athc."


def test_cli_missing_button_image_exits_2_before_watching(
    runner,
    valid: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from athc.autocontinue import main

    def watching() -> None:  # the loop would never end, so fail instead
        raise AssertionError("started watching the screen")

    valid()
    image = tmp_path / "continue_button.png"
    monkeypatch.setattr(main, "CONTINUE_BUTTON_IMAGE", image)
    monkeypatch.setattr(main, "_get_screen_size", watching)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {image}: {FILE_NOT_FOUND} Reinstall athc.\n"


def test_config_changes_are_said_through_the_callback() -> None:
    from athc.autocontinue import main

    said: list[str] = []
    first = config.Config(mouse_move_duration=0.5, delay_before_continue=2.5)
    main._say_config_changes(None, first, said.append)
    main._say_config_changes(
        first, replace(first, delay_before_continue=1.0), said.append
    )
    assert said == [
        "MouseMoveDuration set to 0.5",
        "DelayBeforeContinue set to 2.5",
        "DelayBeforeContinue set to 1.0",
    ]
