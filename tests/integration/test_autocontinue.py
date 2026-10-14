"""Tests for `athc autocontinue`: config loading, change detection, the CLI and
the watch loop.

Config is resolved from `config_dir()/athc.ini` (isolated per-test via the autouse
`config_dir` fixture, which sets `ATHC_CONFIG_DIR`). There is no `--config` flag.
The CLI is exercised with `auto_continue` stubbed, and the loop on a stand-in
desktop (`Desktop`), so nothing touches the screen or the mouse.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy
import pytest

from athc.autocontinue import config
from athc.cli.autocontinue import autocontinue
from athc.errors import FILE_NOT_FOUND, AthcError, ConfigFileError

WriteConfig = Callable[..., Path]

_BUTTON = numpy.zeros((2, 2), dtype=numpy.uint8)  # stands in for the loaded image

# The shipped defaults, spelled out: what a missing file, section or key means.
DEFAULTS = config.Config(
    mouse_move_duration=0.0, delay_before_continue=1.0, hot_corner=True
)

# The loop's status lines.
START = "Watching for the Continue button. Press Ctrl+C to stop."
HOT_CORNER_ON = "Hot corner on: move the mouse to the top-left corner to stop."
HOT_CORNER_OFF = "Hot corner off: press Ctrl+C to stop."
DRY_RUN = "Dry run: the Continue button is reported, never clicked."
WINDOW = {True: "Game window active.", False: "Waiting for the game window."}

# Where the stand-in screen shows the Continue button.
BUTTON_AT = (812, 640)
# The game window checks of a pass that clicks: before the scan, after the
# match and after the delay.
CLICKING_PASS = (True, True, True)


@pytest.fixture
def valid(write_config: WriteConfig) -> Callable[..., Path]:
    """Write a valid [autocontinue] athc.ini; override mouse/delay per test."""

    def _valid(mouse: str = "0.5", delay: str = "2.5") -> Path:
        return write_config(
            f"[autocontinue]\nmouse_move_duration = {mouse}\ndelay_before_continue = {delay}\n",
        )

    return _valid


class _CtrlC(KeyboardInterrupt):
    """The coach pressing Ctrl+C, which ends a run on the stand-in desktop."""


class Desktop:
    """The coach's desktop as the watch loop sees it in one run.

    `focus` answers each check for the game window in turn, and the coach
    presses Ctrl+C when it runs out; `buttons` answers each scan for the
    Continue button (None, or nothing left: not on screen). pyautogui's mouse
    calls are recorded, not made: `moves` (x, y, duration) and `clicks`
    (x, y). Each sleep is recorded in `slept` instead of slept, after
    `on_sleep` sees it, so a test can change things mid-run.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from athc.autocontinue import main

        self.focus: Sequence[bool] = ()
        self.buttons: Sequence[tuple[int, int] | None] = ()
        self.on_sleep: Callable[[float], None] = lambda seconds: None
        self.slept: list[float] = []
        self.moves: list[tuple[int, int, float]] = []
        self.clicks: list[tuple[int | None, int | None]] = []
        self.said: list[str] = []
        self.warned: list[str] = []
        self.reported: list[str] = []
        self._main = main
        self._checks = 0
        self._scans = 0
        monkeypatch.setattr(main, "_get_screen_size", lambda: (1920, 1080))
        monkeypatch.setattr(main, "_game_has_focus", self._has_focus)
        monkeypatch.setattr(main, "time", SimpleNamespace(sleep=self._sleep))
        monkeypatch.setattr(main.pyautogui, "locateCenterOnScreen", self._locate)
        monkeypatch.setattr(main.pyautogui, "moveTo", self._move_to)
        monkeypatch.setattr(main.pyautogui, "leftClick", self._left_click)
        # The loop sets the hot corner; pyautogui gets its own back afterward.
        monkeypatch.setattr(main.pyautogui, "FAILSAFE", main.pyautogui.FAILSAFE)

    def run(
        self,
        *,
        hot_corner: bool | None = None,
        delay: float | None = None,
        dry_run: bool = False,
    ) -> None:
        """The loop with these options, until the coach presses Ctrl+C."""
        with contextlib.suppress(_CtrlC):
            self._main.auto_continue(
                hot_corner,
                delay,
                dry_run,
                progress=self.said.append,
                warn=self.warned.append,
                report=self.reported.append,
            )

    def _has_focus(self) -> bool:
        if self._checks == len(self.focus):
            raise _CtrlC
        self._checks += 1
        return self.focus[self._checks - 1]

    def _locate(self, image: object, **options: object) -> object:
        where = self.buttons[self._scans] if self._scans < len(self.buttons) else None
        self._scans += 1
        return None if where is None else self._main.pyautogui.Point(*where)

    def _sleep(self, seconds: float) -> None:
        self.on_sleep(seconds)
        self.slept.append(seconds)

    def _move_to(self, x: int, y: int, duration: float) -> None:
        self.moves.append((x, y, duration))

    def _left_click(self, x: int | None = None, y: int | None = None) -> None:
        self.clicks.append((x, y))


@pytest.fixture
def desktop(monkeypatch: pytest.MonkeyPatch) -> Desktop:
    return Desktop(monkeypatch)


# ── load_config: every setting optional ───────────────────────────────────────


def test_load_config_reads_valid_section(valid: Callable[..., Path]) -> None:
    valid()
    cfg = config.load_config()
    assert cfg.mouse_move_duration == 0.5 and cfg.delay_before_continue == 2.5


def test_load_config_defaults_when_no_config() -> None:
    assert config.load_config() == DEFAULTS  # autouse config_dir gives an empty dir


def test_load_config_defaults_when_section_missing(write_config: WriteConfig) -> None:
    write_config("[other]\nfoo = 1\n")
    assert config.load_config() == DEFAULTS


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("mouse_move_duration = 0.5", replace(DEFAULTS, mouse_move_duration=0.5)),
        ("delay_before_continue = 2.5", replace(DEFAULTS, delay_before_continue=2.5)),
        ("hot_corner = false", replace(DEFAULTS, hot_corner=False)),
    ],
)
def test_load_config_fills_missing_settings(
    write_config: WriteConfig, line: str, expected: config.Config
) -> None:
    write_config(f"[autocontinue]\n{line}\n")
    assert config.load_config() == expected


def test_load_config_errors_on_invalid_value(valid: Callable[..., Path]) -> None:
    ini = valid(mouse="fast")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{ini}: [autocontinue] mouse_move_duration: Must be a number, 0 or more, "
        "got 'fast'."
    )


# ── the timings: one validator for both keys, 0 or more ───────────────────────


def test_timing_accepts_zero(write_config: WriteConfig) -> None:
    write_config("[autocontinue]\ndelay_before_continue = 0\n")
    assert config.load_config().delay_before_continue == 0.0


@pytest.mark.parametrize("raw", ["-0.1", "nan", "inf"])
def test_timing_rejects_a_value_below_zero_or_not_finite(
    write_config: WriteConfig, raw: str
) -> None:
    ini = write_config(f"[autocontinue]\ndelay_before_continue = {raw}\n")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{ini}: [autocontinue] delay_before_continue: Must be a number, 0 or more, "
        f"got '{raw}'."
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


def test_cli_help_shows_the_options(runner) -> None:
    result = runner.invoke(autocontinue, ["--help"])
    assert result.exit_code == 0
    assert "--delay SECONDS" in result.stdout and "-n, --dry-run" in result.stdout
    assert "[x>=0]" not in result.stdout


def test_cli_rejects_an_argument(runner) -> None:
    result = runner.invoke(autocontinue, ["x"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (x).\n")


def test_cli_runs_on_the_defaults_with_no_config(runner, desktop: Desktop) -> None:
    desktop.focus = [False]
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == (
        f"{START}\n"
        "mouse_move_duration = 0.0\n"
        "delay_before_continue = 1.0\n"
        f"{HOT_CORNER_ON}\n"
        f"{WINDOW[False]}\n"
    )
    assert result.stdout == "Stopped.\n"


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


@pytest.mark.parametrize(
    ("args", "expected"),
    [([], None), (["--delay", "0"], 0.0), (["--delay", "2.5"], 2.5)],
)
def test_cli_forwards_the_delay(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    expected: float | None,
) -> None:
    """0 is the lowest delay; absent, None lets the config value win."""
    calls: list[float | None] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda delay=None, **options: calls.append(delay),
    )
    result = runner.invoke(autocontinue, args)
    assert result.exit_code == 0 and calls == [expected]


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("-0.1", "must be 0 or more, got -0.1."),
        ("nan", "must be 0 or more, got nan."),
        ("inf", "must be 0 or more, got inf."),
        ("fast", "'fast' is not a valid float."),
    ],
)
def test_cli_rejects_a_bad_delay(runner, value: str, reason: str) -> None:
    result = runner.invoke(autocontinue, ["--delay", value])
    assert result.exit_code == 2
    assert result.stderr.endswith(f"Error: Invalid value for '--delay': {reason}\n")


@pytest.mark.parametrize(
    ("args", "expected"), [([], False), (["--dry-run"], True), (["-n"], True)]
)
def test_cli_forwards_dry_run(
    runner, monkeypatch: pytest.MonkeyPatch, args: list[str], expected: bool
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda dry_run=False, **options: calls.append(dry_run),
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
    assert result.stdout == "Stopped.\n"


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

    def fake(hot_corner=None, delay=None, dry_run=False, *, progress, warn, report):
        progress(START)
        warn("Config reload failed; keeping previous settings. x")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == (
        f"{START}\nWARN Config reload failed; keeping previous settings. x\n"
    )
    assert result.stdout == "Stopped.\n"


def test_dry_run_sightings_go_to_stdout(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(hot_corner=None, delay=None, dry_run=False, *, progress, warn, report):
        report("Continue button found at 812, 640.")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, ["--dry-run"])
    assert result.exit_code == 0
    assert result.stdout == "Continue button found at 812, 640.\nStopped.\n"


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
    main._say_config_changes(None, first, None, said.append)
    main._say_config_changes(
        first, replace(first, delay_before_continue=1.0), None, said.append
    )
    assert said == [
        "mouse_move_duration = 0.5",
        "delay_before_continue = 2.5",
        "delay_before_continue = 1.0",
    ]


# ── the watch loop, on the stand-in desktop ───────────────────────────────────


@pytest.mark.parametrize(
    ("options", "lines"),
    [
        ({}, [HOT_CORNER_ON]),
        ({"hot_corner": False}, [HOT_CORNER_OFF]),
        ({"dry_run": True}, [HOT_CORNER_OFF, DRY_RUN]),
        ({"dry_run": True, "hot_corner": True}, [HOT_CORNER_OFF, DRY_RUN]),
    ],
    ids=["watch", "no hot corner", "dry run", "dry run with hot corner"],
)
def test_loop_start_lines_in_order(
    desktop: Desktop, options: dict[str, bool], lines: list[str]
) -> None:
    """The start line, the settings, the hot corner, a dry run's line, then the
    first check's window line; a dry run's hot corner is off."""
    desktop.focus = [False]
    desktop.run(**options)
    assert desktop.said == [
        START,
        "mouse_move_duration = 0.0",
        "delay_before_continue = 1.0",
        *lines,
        WINDOW[False],
    ]


@pytest.mark.parametrize("active", [True, False], ids=["active", "not active"])
def test_loop_says_the_game_window_at_the_first_check_and_each_change(
    desktop: Desktop, active: bool
) -> None:
    """One line at the first check, then one per change, not one per pass; the
    loop scans every second while the game is active, else checks every 2 s."""
    # With no button on screen a pass checks once: two passes per state.
    answers = [active, active, not active, not active, active]
    desktop.focus = answers
    desktop.run()
    assert [line for line in desktop.said if line in WINDOW.values()] == [
        WINDOW[active],
        WINDOW[not active],
        WINDOW[active],
    ]
    pause = {True: 1.0, False: 2.0}
    assert desktop.slept == [pause[answer] for answer in answers]


def test_loop_delay_option_wins_and_holds_across_a_reload(
    desktop: Desktop, valid: Callable[..., Path]
) -> None:
    """--delay beats delay_before_continue in athc.ini, and a reload that
    changes the key neither applies nor says it."""
    valid(mouse="0.0", delay="2.5")

    def edit(seconds: float) -> None:
        if seconds == 4.0:  # after a click, the coach changes the key
            valid(mouse="0.0", delay="30.0")

    desktop.on_sleep = edit
    desktop.focus = CLICKING_PASS * 2
    desktop.buttons = [BUTTON_AT, BUTTON_AT]
    desktop.run(delay=0.5)
    assert desktop.slept == [0.5, 4.0, 0.5, 4.0]
    assert desktop.said == [
        START,
        "mouse_move_duration = 0.0",
        "delay_before_continue = 0.5 (--delay)",
        HOT_CORNER_ON,
        WINDOW[True],
    ]


def test_loop_a_deleted_athc_ini_means_the_defaults(
    desktop: Desktop, valid: Callable[..., Path]
) -> None:
    """The defaults apply and the settings lines say what changed; no WARN."""
    ini = valid()  # 0.5 s move, 2.5 s delay
    desktop.on_sleep = lambda seconds: ini.unlink(missing_ok=True)
    desktop.focus = [True, *CLICKING_PASS]  # a pass with no button, then a click
    desktop.buttons = [None, BUTTON_AT]
    desktop.run()
    assert desktop.said == [
        START,
        "mouse_move_duration = 0.5",
        "delay_before_continue = 2.5",
        HOT_CORNER_ON,
        WINDOW[True],
        "mouse_move_duration = 0.0",
        "delay_before_continue = 1.0",
    ]
    assert desktop.warned == []
    assert desktop.moves == [(*BUTTON_AT, 0.0)]  # the default move
    assert desktop.slept == [1.0, 1.0, 4.0]  # the click waited the default delay


def test_loop_clicks_on_the_button_itself(desktop: Desktop) -> None:
    """The click names the button's position, so it lands there even when the
    mouse moved off it during the delay."""
    desktop.focus = CLICKING_PASS
    desktop.buttons = [BUTTON_AT]
    desktop.run()
    assert desktop.clicks == [BUTTON_AT]


def test_loop_a_fail_safe_from_the_click_stops_the_watcher(
    desktop: Desktop, monkeypatch: pytest.MonkeyPatch
) -> None:
    from athc.autocontinue import main

    def fail_safe(*args: object, **kwargs: object) -> None:
        raise main.pyautogui.FailSafeException

    monkeypatch.setattr(main.pyautogui, "leftClick", fail_safe)
    desktop.focus = CLICKING_PASS
    desktop.buttons = [BUTTON_AT]
    with pytest.raises(KeyboardInterrupt) as exc:
        desktop.run()
    assert isinstance(exc.value.__cause__, main.pyautogui.FailSafeException)


def test_dry_run_reports_the_button_and_never_moves_or_clicks(
    desktop: Desktop,
) -> None:
    """The sighting goes to `report`, then an 8 s wait; --delay has no effect."""
    desktop.focus = [True, True]  # before the scan and after the match
    desktop.buttons = [BUTTON_AT]
    desktop.run(dry_run=True, delay=3.0)
    assert desktop.reported == ["Continue button found at 812, 640."]
    assert desktop.slept == [8.0]
    assert desktop.moves == [] and desktop.clicks == []
