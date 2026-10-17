"""Tests for `athc autocontinue`: config loading, change detection, the CLI and
the watch loop.

Config is resolved from `config_dir()/athc.toml` (isolated per-test via the autouse
`config_dir` fixture, which sets `ATHC_CONFIG_DIR`). There is no `--config` flag.
The CLI is exercised with `auto_continue` stubbed, and the loop on a stand-in
desktop (`Desktop`), so nothing touches the screen or the mouse.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy
import pytest
from click.testing import Result
from PIL import Image

from athc.autocontinue import config
from athc.cli.autocontinue import autocontinue
from athc.errors import FILE_NOT_FOUND, AthcError, ConfigFileError

WriteConfig = Callable[..., Path]
# One screenshot on the stand-in desktop: where each image's middle shows, by
# file name; a real screenshot's file name in SCREENS; or what the grab does.
Screen = Mapping[str, tuple[int, int]] | str | Exception | None

# Screenshots of the real game, cropped to the game window: the Windows
# Sandbox ones 641x506, the posted ones 642x507.
SCREENS = Path(__file__).parent / "data" / "autocontinue_screens"
# How far a found middle may be from where the game draws it: the matcher
# takes the first spot over its confidence, not always the best one.
NEAR = 3

# The defaults, spelled out: what a missing file, section or key means. The
# shipped athc.toml has them all but drive_league_pregame, which it turns on.
DEFAULTS = config.Config(
    mouse_move_duration=0.0,
    continue_pause=1.0,
    halftime_pause=8.0,
    hot_corner=True,
    drive_league_pregame=False,
    plans_profiles_pause=1.5,
    conditions_pause=2.5,
    venues_pause=1.5,
)
# The settings lines at start, on the defaults, after halftime_pause.
PREGAME_SETTINGS = [
    "drive_league_pregame = false",
    "plans_profiles_pause = 1.5",
    "conditions_pause = 2.5",
    "venues_pause = 1.5",
]

# The loop's status lines.
START = "Watching for the Continue button. Press Ctrl+C to stop."
HOT_CORNER_ON = "Hot corner on: move the mouse to the top-left corner to stop."
HOT_CORNER_OFF = "Hot corner off: press Ctrl+C to stop."
DRY_RUN = "Dry run: what it finds is reported, never clicked."
WINDOW = {True: "Game window active.", False: "Waiting for the game window."}
CTRL_C = "Ctrl+C pressed."
HOT_CORNER_HIT = "Hot corner hit."

# Where the stand-in screens show each image's middle, by file name.
BUTTON_AT = (812, 640)
LABEL_AT = (400, 120)
RETURN_AT = (960, 700)
CONTINUE = {"continue_button.png": BUTTON_AT}
HALFTIME = {"halftime_label.png": LABEL_AT, "return_button.png": RETURN_AT}
RESULTS = {"results_label.png": LABEL_AT, "return_button.png": RETURN_AT}
# The game window checks of a pass that clicks: before the scan, after the
# match, after the delay and just before the click.
CLICKING_PASS = (True, True, True, True)

# What the halftime and end-of-game screens say.
FOUND = ["Halftime label found at 400, 120.", "Return button found at 960, 700."]
END = ["Results label found at 400, 120.", "Return button found at 960, 700."]

# The league play pre-game screen, where the game shows each one.
LEAGUE_PLAY_AT = (571, 38)
PLANS_PROFILES_AT = (154, 496)
VISITOR_AT = (457, 198)
CONDITIONS_AT = (59, 499)
VENUES_AT = (370, 496)
GAME_AT = (579, 466)
LEAGUE_PLAY = {
    "league_play_label.png": LEAGUE_PLAY_AT,
    "plans_profiles_button.png": PLANS_PROFILES_AT,
    "visitor_button.png": VISITOR_AT,
    "conditions_button.png": CONDITIONS_AT,
    "venues_button.png": VENUES_AT,
    "game_button.png": GAME_AT,
}
PREGAME_ON = "[autocontinue]\ndrive_league_pregame = true\n"
# The game window checks of a pre-game pass: before the scan and after the
# match, then before the screenshot and just before the click of each button.
PREGAME_START = (True, True)
PREGAME_CLICK = (True, True)
PREGAME_CLICKED = {
    "Plans/profiles button": PLANS_PROFILES_AT,
    "Visitor button": VISITOR_AT,
    "Conditions button": CONDITIONS_AT,
    "Venues button": VENUES_AT,
    "Game button": GAME_AT,
}


@pytest.fixture
def valid(write_config: WriteConfig) -> Callable[..., Path]:
    """Write a valid [autocontinue] athc.toml; override mouse/pause per test."""

    def _valid(mouse: str = "0.5", pause: str = "2.5") -> Path:
        return write_config(
            f"[autocontinue]\nmouse_move_duration = {mouse}\ncontinue_pause = {pause}\n",
        )

    return _valid


class _CtrlC(KeyboardInterrupt):
    """The coach pressing Ctrl+C, which ends a run on the stand-in desktop."""


class Desktop:
    """The coach's desktop as the watch loop sees it in one run.

    `focus` answers each check for the game window in turn, and the coach
    presses Ctrl+C when it runs out; `screens` answers each screenshot in turn
    with where each image's middle shows, by file name (None: Windows hides
    the screen; an exception: raised by the grab; nothing left: an empty
    screen). A pass that clicks takes two:
    the scan and the re-check just before the click. pyautogui's mouse calls
    are recorded, not made: `moves`
    (x, y, duration) and `clicks` (x, y). Each sleep is recorded in `slept`
    instead of slept, after `on_sleep` sees it, so a test can change things
    mid-run.

    With `real`, a screen is the file name of a real game screenshot in
    SCREENS: the shipped images load, the screenshot turns gray and the
    matcher searches it as in a run.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, real: bool = False) -> None:
        from athc.autocontinue import main

        self.focus: Sequence[bool] = ()
        self.screens: Sequence[Screen] = ()
        self.on_sleep: Callable[[float], None] = lambda seconds: None
        self.slept: list[float] = []
        self.moves: list[tuple[int, int, float]] = []
        self.clicks: list[tuple[int | None, int | None]] = []
        self.said: list[str] = []
        self.warned: list[str] = []
        self.traced: list[str] = []
        self.reported: list[str] = []
        self._main = main
        self._checks = 0
        self._scans = 0
        monkeypatch.setattr(main, "_game_has_focus", self._has_focus)
        monkeypatch.setattr(main, "time", SimpleNamespace(sleep=self._sleep))
        monkeypatch.setattr(main.pyautogui, "screenshot", self._screenshot)
        if not real:
            # Each image stands in as its file name, which the screens are
            # keyed by.
            monkeypatch.setattr(main, "_load_image", lambda path: path.name)
            # Each screen stands in as a mapping, which has no colors to drop.
            monkeypatch.setattr(main, "_gray", lambda shot: shot)
            monkeypatch.setattr(main.pyautogui, "locate", self._locate)
        monkeypatch.setattr(main.pyautogui, "moveTo", self._move_to)
        monkeypatch.setattr(main.pyautogui, "leftClick", self._left_click)
        # The loop sets the hot corner; pyautogui gets its own back afterward.
        monkeypatch.setattr(main.pyautogui, "FAILSAFE", main.pyautogui.FAILSAFE)

    def run(
        self,
        *,
        hot_corner: bool | None = None,
        continue_pause: float | None = None,
        dry_run: bool = False,
    ) -> bool:
        """The loop with these options: True when it stops on its own, False
        when the coach presses Ctrl+C."""
        try:
            self._main.auto_continue(
                hot_corner,
                continue_pause,
                dry_run,
                progress=self.said.append,
                warn=self.warned.append,
                warn_traced=self.traced.append,
                report=self.reported.append,
            )
        except _CtrlC:
            return False
        return True

    def _has_focus(self) -> bool:
        if self._checks == len(self.focus):
            raise _CtrlC
        self._checks += 1
        return self.focus[self._checks - 1]

    def _screenshot(self) -> Mapping[str, tuple[int, int]] | Image.Image:
        screen = self.screens[self._scans] if self._scans < len(self.screens) else {}
        self._scans += 1
        if screen is None:
            raise OSError("screen grab failed")  # PIL's own text, on a locked screen
        if isinstance(screen, Exception):
            raise screen
        if isinstance(screen, str):
            return Image.open(SCREENS / screen)
        return screen

    def _locate(
        self, image: str, screen: Mapping[str, tuple[int, int]], **options: object
    ) -> tuple[int, int, int, int]:
        if image not in screen:
            raise self._main.pyautogui.ImageNotFoundException
        x, y = screen[image]
        return (x - 5, y - 5, 10, 10)  # a 10-pixel box whose middle is the point

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


@pytest.fixture
def real_desktop(monkeypatch: pytest.MonkeyPatch) -> Desktop:
    """The desktop with real game screenshots."""
    return Desktop(monkeypatch, real=True)


@pytest.fixture
def images(desktop: Desktop) -> object:
    """The images, each standing in as its file name."""
    from athc.autocontinue import main

    return main._Images.load()


# ── load_config: every setting optional ───────────────────────────────────────


def test_load_config_defaults_when_no_config() -> None:
    assert config.load_config() == DEFAULTS  # autouse config_dir gives an empty dir


def test_load_config_defaults_when_section_missing(write_config: WriteConfig) -> None:
    write_config("[other]\nfoo = 1\n")
    assert config.load_config() == DEFAULTS


def test_load_config_errors_on_invalid_value(valid: Callable[..., Path]) -> None:
    toml = valid(mouse='"fast"')
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{toml}: [autocontinue] mouse_move_duration: Must be a number, 0 or more, "
        "got 'fast'."
    )


# ── the timings: one validator for every timing key, 0 or more ────────────────


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ('"1.0"', "'1.0'"),
        ("true", "true"),
        ("1979-05-27", "1979-05-27"),
        ("-1.0", "-1.0"),
        ("nan", "nan"),
        ("inf", "inf"),
    ],
)
def test_timing_must_be_a_number_zero_or_more(
    write_config: WriteConfig, raw: str, shown: str
) -> None:
    """A string, a boolean or a date is not a number, even one that reads as
    one; below zero, NaN and infinity are not 0 or more. The value is shown as
    TOML spells it."""
    toml = write_config(f"[autocontinue]\ncontinue_pause = {raw}\n")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{toml}: [autocontinue] continue_pause: Must be a number, 0 or more, "
        f"got {shown}."
    )


def test_integers_are_numbers(write_config: WriteConfig) -> None:
    write_config("[autocontinue]\ncontinue_pause = 2\n")
    pause = config.load_config().continue_pause
    assert pause == 2.0 and isinstance(pause, float)


# ── hot_corner: a TOML boolean ────────────────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [("true", True), ("false", False)])
def test_hot_corner_parses_boolean(
    write_config: WriteConfig, raw: str, expected: bool
) -> None:
    write_config(
        f"[autocontinue]\nmouse_move_duration = 0.0\ncontinue_pause = 1.0\n"
        f"hot_corner = {raw}\n"
    )
    assert config.load_config().hot_corner is expected


@pytest.mark.parametrize(
    ("raw", "shown"), [('"maybe"', "'maybe'"), ("1", "1"), ('"true"', "'true'")]
)
def test_hot_corner_must_be_a_toml_boolean(
    write_config: WriteConfig, raw: str, shown: str
) -> None:
    """TOML's ints and strings are not booleans, even 1 or "true"."""
    toml = write_config(f"[autocontinue]\nhot_corner = {raw}\n")
    with pytest.raises(ConfigFileError) as exc:
        config.load_config()
    assert str(exc.value) == (
        f"{toml}: [autocontinue] hot_corner: Must be true or false, got {shown}."
    )


# ── a test per setting: missing (its default), -1 and 0 ───────────────────────

# Why -1 fails at start, by kind of setting.
TIMING = "Must be a number, 0 or more"
BOOLEAN = "Must be true or false"
# Each setting test's cases: the key missing, -1 and 0 (false for an on/off
# setting, which takes no number).
SETTING_IDS = ["default", "-1", "0"]
SWITCH_IDS = ["default", "-1", "false"]


def _run_with(
    runner, write_config: WriteConfig, key: str, value: str, base: str = ""
) -> tuple[Result, Path]:
    """The command run with athc.toml's `[autocontinue]` holding `base`'s
    lines and `key = value`, or no line for the key when `value` is
    "default". Returns the result and athc.toml."""
    line = "" if value == "default" else f"{key} = {value}\n"
    toml = write_config(f"[autocontinue]\n{base}{line}")
    return runner.invoke(autocontinue, []), toml


def _fails_at_start(
    result: Result, desktop: Desktop, toml: Path, key: str, why: str
) -> None:
    """Exit 2 with the FAIL line naming the key, before any watching."""
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {toml}: [autocontinue] {key}: {why}, got -1.\n"
    assert desktop.slept == [] and desktop.moves == [] and desktop.clicks == []


@pytest.mark.parametrize(
    ("value", "seconds"),
    [("default", 0.0), ("-1", None), ("0", 0.0), ("0.5", 0.5)],
    ids=[*SETTING_IDS, "0.5"],
)
def test_setting_mouse_move_duration(
    runner, desktop: Desktop, write_config: WriteConfig, value: str, seconds
) -> None:
    """The move to Continue takes its seconds: instant by default and at 0;
    0.5 shows the setting is the one used, the other two being 0."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [CONTINUE, CONTINUE]
    result, toml = _run_with(runner, write_config, "mouse_move_duration", value)
    if seconds is None:
        _fails_at_start(result, desktop, toml, "mouse_move_duration", TIMING)
        return
    assert result.exit_code == 0
    assert config.load_config() == replace(DEFAULTS, mouse_move_duration=seconds)
    assert f"mouse_move_duration = {seconds}" in result.stderr.splitlines()
    assert desktop.moves == [(*BUTTON_AT, seconds)]
    assert desktop.clicks == [BUTTON_AT]


@pytest.mark.parametrize(
    ("value", "seconds"),
    [("default", 1.0), ("-1", None), ("0", 0.0)],
    ids=SETTING_IDS,
)
def test_setting_continue_pause(
    runner, desktop: Desktop, write_config: WriteConfig, value: str, seconds
) -> None:
    """The wait before the Continue click: 1 s by default, none at 0."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [CONTINUE, CONTINUE]
    result, toml = _run_with(runner, write_config, "continue_pause", value)
    if seconds is None:
        _fails_at_start(result, desktop, toml, "continue_pause", TIMING)
        return
    assert result.exit_code == 0
    assert config.load_config() == replace(DEFAULTS, continue_pause=seconds)
    assert f"continue_pause = {seconds}" in result.stderr.splitlines()
    assert desktop.slept == [seconds, 4.0]
    assert desktop.clicks == [BUTTON_AT]


@pytest.mark.parametrize(
    ("value", "seconds", "waiting"),
    [
        ("default", 8.0, "Waiting 8 seconds."),
        ("-1", None, None),
        ("0", 0.0, "Waiting 0 seconds."),
    ],
    ids=SETTING_IDS,
)
def test_setting_halftime_pause(
    runner,
    desktop: Desktop,
    write_config: WriteConfig,
    value: str,
    seconds,
    waiting,
) -> None:
    """The wait at halftime before Return is clicked: 8 s by default, none
    at 0."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [HALFTIME, HALFTIME]
    result, toml = _run_with(runner, write_config, "halftime_pause", value)
    if seconds is None:
        _fails_at_start(result, desktop, toml, "halftime_pause", TIMING)
        return
    assert result.exit_code == 0
    assert config.load_config() == replace(DEFAULTS, halftime_pause=seconds)
    lines = result.stderr.splitlines()
    assert f"halftime_pause = {seconds}" in lines
    assert lines[-3:-1] == [waiting, "Return button clicked."]
    assert desktop.slept == [seconds, 4.0] and desktop.clicks == [RETURN_AT]


@pytest.mark.parametrize(
    ("value", "on"),
    [("default", True), ("-1", None), ("false", False)],
    ids=SWITCH_IDS,
)
def test_setting_hot_corner(
    runner, desktop: Desktop, write_config: WriteConfig, value: str, on
) -> None:
    """pyautogui's fail-safe, the hot corner: on by default, off at false."""
    from athc.autocontinue import main

    desktop.focus = [False]
    result, toml = _run_with(runner, write_config, "hot_corner", value)
    if on is None:
        _fails_at_start(result, desktop, toml, "hot_corner", BOOLEAN)
        return
    assert result.exit_code == 0
    assert config.load_config() == replace(DEFAULTS, hot_corner=on)
    assert (HOT_CORNER_ON if on else HOT_CORNER_OFF) in result.stderr.splitlines()
    assert main.pyautogui.FAILSAFE is on


@pytest.mark.parametrize("value", SWITCH_IDS)
def test_setting_drive_league_pregame(
    runner, desktop: Desktop, write_config: WriteConfig, value: str
) -> None:
    """Off by default (the code's default, a missing key) and at false: the league
    play screen is left alone, and the next scan comes a second later."""
    desktop.focus = [True]
    desktop.screens = [LEAGUE_PLAY]
    result, toml = _run_with(runner, write_config, "drive_league_pregame", value)
    if value == "-1":
        _fails_at_start(result, desktop, toml, "drive_league_pregame", BOOLEAN)
        return
    assert result.exit_code == 0
    assert config.load_config() == replace(DEFAULTS, drive_league_pregame=False)
    lines = result.stderr.splitlines()
    assert "drive_league_pregame = false" in lines
    assert lines[-1] == CTRL_C and lines[-2] == WINDOW[True]
    assert desktop.clicks == [] and desktop.slept == [1.0]


# The pauses of a pre-game drive at the defaults, Game last.
DEFAULT_PAUSES = [1.5, 1.5, 2.5, 1.5, 4.0]


def _pregame_pause(
    runner,
    desktop: Desktop,
    write_config: WriteConfig,
    key: str,
    value: str,
    seconds: float | None,
    skipped: list[str],
    slept: list[float],
) -> None:
    """The league play pre-game driven with `key` at `value`: the buttons not
    `skipped` clicked and said in order, then `slept`; -1 fails at start."""
    clicked = {name: at for name, at in PREGAME_CLICKED.items() if name not in skipped}
    desktop.focus = _pregame_focus(len(clicked))
    desktop.screens = [LEAGUE_PLAY] * (1 + len(clicked))
    result, toml = _run_with(
        runner, write_config, key, value, base="drive_league_pregame = true\n"
    )
    if seconds is None:
        _fails_at_start(result, desktop, toml, key, TIMING)
        return
    assert result.exit_code == 0
    expected = replace(DEFAULTS, drive_league_pregame=True, **{key: seconds})
    assert config.load_config() == expected
    lines = result.stderr.splitlines()
    assert f"{key} = {seconds}" in lines
    said = lines[-1 - len(clicked) : -1]
    assert said == [f"{name} clicked." for name in clicked]
    assert desktop.clicks == list(clicked.values())
    assert desktop.slept == slept


@pytest.mark.parametrize(
    ("value", "seconds", "skipped", "slept"),
    [
        ("default", 1.5, [], DEFAULT_PAUSES),
        ("-1", None, [], []),
        ("0", 0.0, ["Plans/profiles button", "Visitor button"], [2.5, 1.5, 4.0]),
    ],
    ids=SETTING_IDS,
)
def test_setting_plans_profiles_pause(
    runner, desktop: Desktop, write_config: WriteConfig, value, seconds, skipped, slept
) -> None:
    """The pause after Plans/Profiles and after Visitor: 1.5 s by default; 0
    skips both clicks."""
    _pregame_pause(
        runner,
        desktop,
        write_config,
        "plans_profiles_pause",
        value,
        seconds,
        skipped,
        slept,
    )


@pytest.mark.parametrize(
    ("value", "seconds", "skipped", "slept"),
    [
        ("default", 2.5, [], DEFAULT_PAUSES),
        ("-1", None, [], []),
        ("0", 0.0, ["Conditions button"], [1.5, 1.5, 1.5, 4.0]),
    ],
    ids=SETTING_IDS,
)
def test_setting_conditions_pause(
    runner, desktop: Desktop, write_config: WriteConfig, value, seconds, skipped, slept
) -> None:
    """The pause after Conditions: 2.5 s by default; 0 skips the click."""
    _pregame_pause(
        runner,
        desktop,
        write_config,
        "conditions_pause",
        value,
        seconds,
        skipped,
        slept,
    )


@pytest.mark.parametrize(
    ("value", "seconds", "skipped", "slept"),
    [
        ("default", 1.5, [], DEFAULT_PAUSES),
        ("-1", None, [], []),
        ("0", 0.0, ["Venues button"], [1.5, 1.5, 2.5, 4.0]),
    ],
    ids=SETTING_IDS,
)
def test_setting_venues_pause(
    runner, desktop: Desktop, write_config: WriteConfig, value, seconds, skipped, slept
) -> None:
    """The pause after Venues: 1.5 s by default; 0 skips the click."""
    _pregame_pause(
        runner,
        desktop,
        write_config,
        "venues_pause",
        value,
        seconds,
        skipped,
        slept,
    )


# ── config_signature: change detection ────────────────────────────────────────


def test_signature_none_when_file_missing() -> None:
    assert config.config_signature() is None


def test_signature_returns_tuple_for_existing_file(valid: Callable[..., Path]) -> None:
    toml = valid()
    sig = config.config_signature()
    assert sig is not None and sig[0] == str(toml)


def test_signature_stable_when_unchanged(valid: Callable[..., Path]) -> None:
    valid()
    assert config.config_signature() == config.config_signature()


def test_signature_changes_when_rewritten(valid: Callable[..., Path]) -> None:
    valid(mouse="0.1")
    before = config.config_signature()
    valid(mouse="0.123456")  # different length -> size differs
    assert before != config.config_signature()


# ── CLI ───────────────────────────────────────────────────────────────────────


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
        "continue_pause = 1.0\n"
        "halftime_pause = 8.0\n"
        + "".join(f"{line}\n" for line in PREGAME_SETTINGS)
        + f"{HOT_CORNER_ON}\n"
        f"{WINDOW[False]}\n"
        f"{CTRL_C}\n"
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
    [
        ([], None),
        (["--continue-pause", "0"], 0.0),
        (["--continue-pause", "2.5"], 2.5),
    ],
)
def test_cli_forwards_the_continue_pause(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    expected: float | None,
) -> None:
    """0 is the lowest pause; absent, None lets the config value win."""
    calls: list[float | None] = []
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue",
        lambda continue_pause=None, **options: calls.append(continue_pause),
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
def test_cli_rejects_a_bad_continue_pause(runner, value: str, reason: str) -> None:
    result = runner.invoke(autocontinue, ["--continue-pause", value])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        f"Error: Invalid value for '--continue-pause': {reason}\n"
    )


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


def test_cli_hot_corner_says_so_and_exits_clean(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    from athc.autocontinue import main

    def _corner(*args: object, **options: object) -> None:
        raise main.HotCornerStop

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", _corner)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == f"{HOT_CORNER_HIT}\n" and result.stdout == "Stopped.\n"


def test_cli_end_of_game_stops_clean(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop returning (the end of the game) is a stop like Ctrl+C, with no
    stop line of its own: the Results lines say why."""
    monkeypatch.setattr(
        "athc.autocontinue.main.auto_continue", lambda *args, **options: None
    )
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0 and result.stdout == "Stopped.\n"
    assert result.stderr == ""


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

    def fake(
        hot_corner=None,
        continue_pause=None,
        dry_run=False,
        *,
        progress,
        warn,
        warn_traced,
        report,
    ):
        progress(START)
        warn("Config reload failed; keeping previous settings. x")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == (
        f"{START}\nWARN Config reload failed; keeping previous settings. x\n{CTRL_C}\n"
    )
    assert result.stdout == "Stopped.\n"


def test_dry_run_sightings_go_to_stdout(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(
        hot_corner=None,
        continue_pause=None,
        dry_run=False,
        *,
        progress,
        warn,
        warn_traced,
        report,
    ):
        report("Continue button found at 812, 640.")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, ["--dry-run"])
    assert result.exit_code == 0
    assert result.stdout == "Continue button found at 812, 640.\nStopped.\n"


def test_the_screen_is_searched_in_gray(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turned gray once per screenshot, as the images are: pure red is 76."""
    from PIL import Image

    from athc.autocontinue import main

    red = Image.new("RGB", (2, 1), (255, 0, 0))
    monkeypatch.setattr(main.pyautogui, "screenshot", lambda: red)
    screen = main._grab_screen(lambda _: None)
    assert screen is not None and screen.tolist() == [[76, 76]]


@pytest.mark.parametrize(
    ("pregame", "order"),
    [
        (False, ["results_label", "halftime_label", "continue_button"]),
        (
            True,
            [
                "results_label",
                "halftime_label",
                "league_play_label",
                "continue_button",
            ],
        ),
    ],
    ids=["pre-game off", "pre-game on"],
)
def test_scan_searches_the_screen_for_each_image_in_order(
    monkeypatch: pytest.MonkeyPatch, pregame: bool, order: list[str]
) -> None:
    """The loaded images, in order, each searched for on the same screen with
    the same settings: the whole screen, in gray, confidence 0.8. The league
    play label only while the pre-game is driven."""
    from athc.autocontinue import main

    shot = object()
    seen: list[tuple[object, object, dict[str, object]]] = []

    def locate(image: object, screen: object, **options: object) -> None:
        seen.append((image, screen, options))
        raise main.pyautogui.ImageNotFoundException

    monkeypatch.setattr(main, "_grab_screen", lambda warn: shot)
    monkeypatch.setattr(main.pyautogui, "locate", locate)
    # One-pixel images, told apart by their value.
    fields = [field.name for field in dataclasses.fields(main._Images)]
    images = main._Images(
        **{
            name: numpy.full((1, 1), value, dtype=numpy.uint8)
            for value, name in enumerate(fields)
        }
    )
    assert main._scan(images, lambda _: None, pregame=pregame) is None
    settings = {"grayscale": True, "confidence": 0.8}  # no region: all of it
    assert seen == [(getattr(images, name), shot, settings) for name in order]


@pytest.mark.parametrize(
    ("screen", "label", "button"),
    [
        ({**CONTINUE, **HALFTIME, **RESULTS}, "Results", RETURN_AT),
        ({**CONTINUE, **HALFTIME}, "Halftime", RETURN_AT),
        (CONTINUE, None, BUTTON_AT),
    ],
    ids=["results first", "halftime before continue", "continue"],
)
def test_scan_order(
    desktop: Desktop, images, screen, label: str | None, button: tuple[int, int]
) -> None:
    from athc.autocontinue import main

    desktop.screens = [screen]
    sighting = main._scan(images, desktop.warned.append)
    assert isinstance(sighting, main._Sighting) and sighting.button == button
    assert (sighting.label.name if sighting.label else None) == label


@pytest.mark.parametrize(
    "screen",
    [
        {},
        {"halftime_label.png": LABEL_AT, **CONTINUE},
        {"results_label.png": LABEL_AT, **CONTINUE},
    ],
    ids=["nothing", "halftime without return", "results without return"],
)
def test_scan_finds_nothing_without_return_under_a_label(
    desktop: Desktop, images, screen
) -> None:
    from athc.autocontinue import main

    desktop.screens = [screen]
    assert main._scan(images, desktop.warned.append) is None


@pytest.mark.parametrize(
    ("screen", "pregame", "searched"),
    [
        (
            {"halftime_label.png": LABEL_AT},
            False,
            [
                ("results_label.png", 0.8),
                ("halftime_label.png", 0.8),
                ("return_button.png", 0.6),
                ("return_highlight_button.png", 0.6),
            ],
        ),
        (
            {"league_play_label.png": LEAGUE_PLAY_AT},
            True,
            [
                ("results_label.png", 0.8),
                ("halftime_label.png", 0.8),
                ("league_play_label.png", 0.8),
                ("game_button.png", 0.6),
                ("game_highlight_button.png", 0.6),
            ],
        ),
    ],
    ids=["return", "game"],
)
def test_scan_finds_return_and_game_at_a_lower_confidence(
    desktop: Desktop,
    images,
    monkeypatch: pytest.MonkeyPatch,
    screen: Mapping[str, tuple[int, int]],
    pregame: bool,
    searched: list[tuple[str, float]],
) -> None:
    """The game draws its own pointer, which sits on Return at halftime and on
    Game after Accept: those two are searched for at 0.6, the rest at 0.8."""
    from athc.autocontinue import main

    seen: list[tuple[str, float]] = []

    def locate(
        image: str, shot: Mapping[str, tuple[int, int]], **options: float
    ) -> tuple[int, int, int, int]:
        seen.append((image, options["confidence"]))
        if image not in shot:
            raise main.pyautogui.ImageNotFoundException
        x, y = shot[image]
        return (x - 5, y - 5, 10, 10)

    desktop.screens = [screen]
    monkeypatch.setattr(main.pyautogui, "locate", locate)
    main._scan(images, desktop.warned.append, pregame=pregame)
    assert seen == searched


def test_scan_finds_no_pregame_without_game(desktop: Desktop, images) -> None:
    """The League play label also shows on other league screens, like the
    schedule; it counts only with Game on screen too."""
    from athc.autocontinue import main

    desktop.screens = [{"league_play_label.png": LEAGUE_PLAY_AT, **CONTINUE}]
    assert main._scan(images, desktop.warned.append, pregame=True) is None


@pytest.mark.parametrize("label", ["halftime_label.png", "results_label.png"])
def test_scan_finds_return_highlighted(desktop: Desktop, images, label: str) -> None:
    """The mouse moved onto Return lights it up; that counts as Return too."""
    from athc.autocontinue import main

    desktop.screens = [{label: LABEL_AT, "return_highlight_button.png": RETURN_AT}]
    sighting = main._scan(images, desktop.warned.append)
    assert isinstance(sighting, main._Sighting) and sighting.button == RETURN_AT


def test_an_unreadable_image_fails_and_says_to_reinstall(
    tmp_path: Path,
) -> None:
    from athc.autocontinue import main

    image = tmp_path / "continue_button.png"
    image.write_bytes(b"not an image")
    with pytest.raises(AthcError) as exc:
        main._load_image(image)
    assert str(exc.value) == f"{image}: Cannot read the image. Reinstall athc."


def test_cli_a_missing_image_exits_2_before_watching(
    runner,
    valid: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """One image missing; the real-screen tests load all twelve."""
    from athc.autocontinue import main

    def watching() -> None:  # the loop would never end, so fail instead
        raise AssertionError("started watching the screen")

    valid()
    image = tmp_path / main.CONTINUE_BUTTON_IMAGE.name
    monkeypatch.setattr(main, "CONTINUE_BUTTON_IMAGE", image)
    monkeypatch.setattr(main, "_game_has_focus", watching)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {image}: {FILE_NOT_FOUND} Reinstall athc.\n"


def test_config_changes_are_said_through_the_callback() -> None:
    from athc.autocontinue import main

    said: list[str] = []
    first = config.Config(mouse_move_duration=0.5, continue_pause=2.5)
    main._say_config_changes(None, first, None, said.append)
    main._say_config_changes(
        first, replace(first, continue_pause=1.0), None, said.append
    )
    main._say_config_changes(
        first, replace(first, halftime_pause=2.5), None, said.append
    )
    main._say_config_changes(
        first,
        replace(first, drive_league_pregame=True, conditions_pause=0.0),
        None,
        said.append,
    )
    assert said == [
        "mouse_move_duration = 0.5",
        "continue_pause = 2.5",
        "halftime_pause = 8.0",
        *PREGAME_SETTINGS,
        "continue_pause = 1.0",
        "halftime_pause = 2.5",
        "drive_league_pregame = true",
        "conditions_pause = 0.0",
    ]


def test_waiting_line_says_1_second() -> None:
    """1 second, not 1 seconds; the halftime tests show 8, 2.5 and 0."""
    from athc.autocontinue import main

    assert main._waiting(1.0) == "Waiting 1 second."


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
        "continue_pause = 1.0",
        "halftime_pause = 8.0",
        *PREGAME_SETTINGS,
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


def test_loop_continue_pause_option_wins_and_holds_across_a_reload(
    desktop: Desktop, valid: Callable[..., Path]
) -> None:
    """--continue-pause beats continue_pause in athc.toml, and a reload that
    changes the key neither applies nor says it."""
    valid(mouse="0.0", pause="2.5")

    def edit(seconds: float) -> None:
        if seconds == 4.0:  # after a click, the coach changes the key
            valid(mouse="0.0", pause="30.0")

    desktop.on_sleep = edit
    desktop.focus = CLICKING_PASS * 2
    desktop.screens = [CONTINUE] * 4
    desktop.run(continue_pause=0.5)
    assert desktop.slept == [0.5, 4.0, 0.5, 4.0]
    assert desktop.said == [
        START,
        "mouse_move_duration = 0.0",
        "continue_pause = 0.5 (--continue-pause)",
        "halftime_pause = 8.0",
        *PREGAME_SETTINGS,
        HOT_CORNER_ON,
        WINDOW[True],
    ]


def test_loop_a_deleted_athc_toml_means_the_defaults(
    desktop: Desktop, valid: Callable[..., Path]
) -> None:
    """The defaults apply and the settings lines say what changed; no WARN."""
    toml = valid()  # 0.5 s move, 2.5 s delay
    desktop.on_sleep = lambda seconds: toml.unlink(missing_ok=True)
    desktop.focus = [True, *CLICKING_PASS]  # a pass with no button, then a click
    desktop.screens = [{}, CONTINUE, CONTINUE]
    desktop.run()
    assert desktop.said == [
        START,
        "mouse_move_duration = 0.5",
        "continue_pause = 2.5",
        "halftime_pause = 8.0",
        *PREGAME_SETTINGS,
        HOT_CORNER_ON,
        WINDOW[True],
        "mouse_move_duration = 0.0",
        "continue_pause = 1.0",
    ]
    assert desktop.warned == []
    assert desktop.moves == [(*BUTTON_AT, 0.0)]  # the default move
    assert desktop.slept == [1.0, 1.0, 4.0]  # the click waited the default delay


def test_loop_a_fail_safe_from_the_click_stops_the_watcher(
    desktop: Desktop, monkeypatch: pytest.MonkeyPatch
) -> None:
    from athc.autocontinue import main

    def fail_safe(*args: object, **kwargs: object) -> None:
        raise main.pyautogui.FailSafeException

    monkeypatch.setattr(main.pyautogui, "leftClick", fail_safe)
    desktop.focus = CLICKING_PASS
    desktop.screens = [CONTINUE, CONTINUE]
    with pytest.raises(main.HotCornerStop) as exc:
        desktop.run()
    assert isinstance(exc.value.__cause__, main.pyautogui.FailSafeException)


def test_dry_run_reports_the_button_and_never_moves_or_clicks(
    desktop: Desktop,
) -> None:
    """The sighting goes to `report`, then an 8 s wait; --continue-pause has no
    effect."""
    desktop.focus = [True, True]  # before the scan and after the match
    desktop.screens = [CONTINUE]
    desktop.run(dry_run=True, continue_pause=3.0)
    assert desktop.reported == ["Continue button found at 812, 640."]
    assert desktop.slept == [8.0]
    assert desktop.moves == [] and desktop.clicks == []


def test_loop_halftime_moves_to_return_waits_then_clicks(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    """An instant move whatever mouse_move_duration says, the pause from
    athc.toml whatever --continue-pause says, then the click on Return, said."""
    write_config("[autocontinue]\nmouse_move_duration = 0.5\nhalftime_pause = 2.5\n")
    desktop.focus = CLICKING_PASS
    desktop.screens = [HALFTIME, HALFTIME]
    assert desktop.run(continue_pause=0.5) is False
    assert desktop.said[-4:] == [
        *FOUND,
        "Waiting 2.5 seconds.",
        "Return button clicked.",
    ]
    assert desktop.moves == [(*RETURN_AT, 0.0)]
    assert desktop.slept == [2.5, 4.0]
    assert desktop.clicks == [RETURN_AT]


def test_loop_halftime_clicks_return_highlighted_by_the_mouse(
    desktop: Desktop,
) -> None:
    """With the mouse on it after the pause, Return is lit up; still Return."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [
        HALFTIME,
        {"halftime_label.png": LABEL_AT, "return_highlight_button.png": RETURN_AT},
    ]
    desktop.run()
    assert desktop.said[-1] == "Return button clicked."
    assert desktop.clicks == [RETURN_AT]


def test_loop_halftime_focus_lost_during_the_pause_means_no_click(
    desktop: Desktop,
) -> None:
    desktop.focus = [True, True, False]
    desktop.screens = [HALFTIME]
    desktop.run()
    assert desktop.slept[0] == 8.0 and desktop.clicks == []


def test_loop_continue_gone_before_the_click_is_not_clicked(desktop: Desktop) -> None:
    """The coach clicked Continue himself during the delay."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [CONTINUE, {}]
    desktop.run()
    assert desktop.said[-1] == "Continue button gone; not clicked."
    assert desktop.moves == [(*BUTTON_AT, 0.0)] and desktop.clicks == []


@pytest.mark.parametrize(
    ("screen", "line"),
    [
        ({}, "Halftime label gone; Return not clicked."),
        ({"halftime_label.png": LABEL_AT}, "Return button gone; not clicked."),
    ],
    ids=["halftime closed", "return gone"],
)
def test_loop_halftime_gone_before_the_click_is_not_clicked(
    desktop: Desktop, screen: Mapping[str, tuple[int, int]], line: str
) -> None:
    """The coach closed halftime himself during the pause."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [HALFTIME, screen]
    desktop.run()
    assert desktop.said[-1] == line and desktop.clicks == []


@pytest.mark.parametrize(
    ("screens", "line"),
    [
        (
            [CONTINUE, {"continue_button.png": (BUTTON_AT[0] + 6, BUTTON_AT[1])}],
            "Continue button moved; not clicked.",
        ),
        (
            [HALFTIME, {**HALFTIME, "return_button.png": (RETURN_AT[0] + 6, 700)}],
            "Return button moved; not clicked.",
        ),
    ],
    ids=["continue", "return"],
)
def test_loop_a_button_moved_before_the_click_is_not_clicked(
    desktop: Desktop, screens: list[Mapping[str, tuple[int, int]]], line: str
) -> None:
    """The window was dragged during the wait: the old spot is no longer on
    the button (6 pixels off a 10-pixel button), so nothing is clicked."""
    desktop.focus = CLICKING_PASS
    desktop.screens = screens
    desktop.run()
    assert desktop.said[-1] == line and desktop.clicks == []


def test_loop_a_button_still_under_the_old_spot_is_clicked(desktop: Desktop) -> None:
    """Moved 5 pixels, the old spot is still on the 10-pixel button: the click
    goes ahead, on the old spot."""
    desktop.focus = CLICKING_PASS
    desktop.screens = [
        CONTINUE,
        {"continue_button.png": (BUTTON_AT[0] + 5, BUTTON_AT[1])},
    ]
    desktop.run()
    assert desktop.clicks == [BUTTON_AT]


def test_loop_focus_lost_just_before_the_click_means_no_click(
    desktop: Desktop,
) -> None:
    """The coach alt-tabs while the button is checked: no click lands in the
    app now in front."""
    desktop.focus = [True, True, True, False]
    desktop.screens = [CONTINUE, CONTINUE]
    desktop.run()
    assert desktop.clicks == [] and desktop.said[-1] == WINDOW[False]


def test_loop_a_reload_that_fails_warns_and_keeps_the_settings(
    desktop: Desktop, config_dir: Path, valid: Callable[..., Path]
) -> None:
    """The coach saves athc.toml as ANSI with an accent mid-run: a WARN, the
    old settings, and the watcher carries on."""
    toml = valid(mouse="0.0", pause="2.5")

    def edit(seconds: float) -> None:
        if seconds == 2.0:  # once, while the game window is away
            toml.write_bytes(b"[autocontinue]\n# caf\xe9\ncontinue_pause = 9\n")

    desktop.on_sleep = edit
    desktop.focus = [False, *CLICKING_PASS]
    desktop.screens = [CONTINUE, CONTINUE]
    desktop.run()
    assert desktop.warned == [
        f"{toml}: Not UTF-8 text. Save it as UTF-8. Keeping the previous settings."
    ]
    assert desktop.slept == [2.0, 2.5, 4.0] and desktop.clicks == [BUTTON_AT]


def test_loop_a_hidden_screen_before_the_click_means_no_click(
    desktop: Desktop,
) -> None:
    """The warning says why, so nothing is said about the button."""
    desktop.focus = [True, True, True]  # before the scan, the match, the grab
    desktop.screens = [CONTINUE, None]
    desktop.run()
    assert desktop.warned == [
        "The screen is locked, a screensaver is on, or Remote Desktop is "
        "disconnected. Retrying in 60 seconds."
    ]
    assert desktop.said[-1] == WINDOW[True]
    assert desktop.clicks == [] and desktop.slept == [1.0, 60.0]


def test_loop_an_unexpected_error_is_traced_once_and_retried(
    desktop: Desktop, log_dir: Path
) -> None:
    """A failure is a WARN and a retry, not the end of the run. The first of a
    kind names the run log, where its traceback goes; a repeat is one line;
    a new kind is traced too."""
    desktop.focus = [True, True, True, *CLICKING_PASS]
    desktop.screens = [
        RuntimeError("driver hiccup"),
        RuntimeError("driver hiccup"),
        ValueError("bad pixels"),
        CONTINUE,
        CONTINUE,
    ]
    desktop.run()
    see = f"See {log_dir / 'athc.log'} for details."
    assert desktop.traced == [
        f"Unexpected RuntimeError: driver hiccup. {see} Retrying in 5 seconds.",
        f"Unexpected ValueError: bad pixels. {see} Retrying in 5 seconds.",
    ]
    assert desktop.warned == [
        "Unexpected RuntimeError: driver hiccup. Retrying in 5 seconds."
    ]
    assert desktop.slept[:3] == [5.0, 5.0, 5.0] and desktop.clicks == [BUTTON_AT]


def test_cli_an_unexpected_error_puts_its_traceback_in_the_run_log(
    runner, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    def fake(*args: object, warn_traced: Callable[[str], None], **options: object):
        try:
            raise RuntimeError("driver hiccup")
        except RuntimeError:
            warn_traced("Unexpected RuntimeError: driver hiccup.")
        raise KeyboardInterrupt

    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, [])
    assert result.stderr == (
        f"WARN Unexpected RuntimeError: driver hiccup.\n{CTRL_C}\n"
    )
    log = (log_dir / "athc.log").read_text(encoding="utf-8").splitlines()
    warning = next(i for i, line in enumerate(log) if "driver hiccup" in line)
    assert log[warning + 1] == "Traceback (most recent call last):"


def test_loop_end_of_game_moves_to_return_and_stops(
    desktop: Desktop, valid: Callable[..., Path]
) -> None:
    valid(mouse="0.5")
    desktop.focus = [True, True, True]  # one more than it needs
    desktop.screens = [RESULTS]
    assert desktop.run() is True
    assert desktop.said[-2:] == END
    assert desktop.moves == [(*RETURN_AT, 0.0)]
    assert desktop.clicks == [] and desktop.slept == []


def test_dry_run_reports_halftime_and_never_moves_or_clicks(desktop: Desktop) -> None:
    desktop.focus = [True, True]
    desktop.screens = [HALFTIME]
    desktop.run(dry_run=True)
    assert desktop.reported == FOUND
    assert desktop.slept == [8.0]
    assert desktop.moves == [] and desktop.clicks == []


def test_dry_run_reports_the_end_of_the_game_and_stops(desktop: Desktop) -> None:
    desktop.focus = [True, True, True]
    desktop.screens = [RESULTS]
    assert desktop.run(dry_run=True) is True
    assert desktop.reported == END
    assert desktop.moves == [] and desktop.clicks == [] and desktop.slept == []


# ── the league play pre-game, on the stand-in desktop ─────────────────────────


def _pregame_focus(clicks: int) -> list[bool]:
    """The game window checks of a pre-game pass that clicks `clicks` buttons."""
    return [*PREGAME_START, *PREGAME_CLICK * clicks]


def test_loop_a_pregame_pause_over_0_clicks(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    """Just over 0, the pause is waited and its button clicked; 0 skips it
    (the setting tests)."""
    write_config(f"{PREGAME_ON}conditions_pause = 0.1\n")
    desktop.focus = _pregame_focus(5)
    desktop.screens = [LEAGUE_PLAY] * 6
    desktop.run()
    assert desktop.said[-5:] == [f"{name} clicked." for name in PREGAME_CLICKED]
    assert desktop.clicks == list(PREGAME_CLICKED.values())
    assert desktop.slept == [1.5, 1.5, 0.1, 1.5, 4.0]


def test_loop_pregame_clicks_game_lit_up_by_the_mouse(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    write_config(
        f"{PREGAME_ON}plans_profiles_pause = 0\nconditions_pause = 0\n"
        "venues_pause = 0\n"
    )
    screen = {
        "league_play_label.png": LEAGUE_PLAY_AT,
        "game_highlight_button.png": GAME_AT,
    }
    desktop.focus = _pregame_focus(1)
    desktop.screens = [screen, screen]
    desktop.run()
    assert desktop.said[-1] == "Game button clicked."
    assert desktop.clicks == [GAME_AT]


def test_loop_pregame_label_gone_means_no_more_clicks(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    """The coach clicked Game himself during a pause."""
    write_config(PREGAME_ON)
    desktop.focus = [*_pregame_focus(1), True]
    desktop.screens = [LEAGUE_PLAY, LEAGUE_PLAY, {}]
    desktop.run()
    assert desktop.said[-1] == "League play label gone; Visitor button not clicked."
    assert desktop.clicks == [PLANS_PROFILES_AT] and desktop.slept == [1.5]


def test_loop_pregame_button_not_found_is_not_clicked(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    """Nothing more is clicked, and the pass waits 8 s before the next scan,
    which drives the pre-game again from the start."""
    write_config(PREGAME_ON)
    no_visitor = {
        name: at for name, at in LEAGUE_PLAY.items() if name != "visitor_button.png"
    }
    desktop.focus = [*_pregame_focus(1), True]
    desktop.screens = [LEAGUE_PLAY, LEAGUE_PLAY, no_visitor]
    desktop.run()
    assert desktop.said[-1] == "Visitor button not found; not clicked."
    assert desktop.clicks == [PLANS_PROFILES_AT] and desktop.slept == [1.5, 8.0]


def test_loop_pregame_focus_lost_just_before_a_click_means_no_click(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    write_config(PREGAME_ON)
    desktop.focus = [*PREGAME_START, True, False]
    desktop.screens = [LEAGUE_PLAY, LEAGUE_PLAY]
    desktop.run()
    assert desktop.clicks == [] and desktop.said[-1] == WINDOW[False]


def test_dry_run_reports_the_pregame_and_never_clicks(
    desktop: Desktop, write_config: WriteConfig
) -> None:
    """The label, then each button it would click, found or not; then an 8 s
    wait."""
    write_config(PREGAME_ON)
    no_venues = {
        name: at for name, at in LEAGUE_PLAY.items() if name != "venues_button.png"
    }
    desktop.focus = [True, True]
    desktop.screens = [no_venues]
    desktop.run(dry_run=True)
    assert desktop.reported == [
        "League play label found at 571, 38.",
        "Plans/profiles button found at 154, 496.",
        "Visitor button found at 457, 198.",
        "Conditions button found at 59, 499.",
        "Venues button not found.",
        "Game button found at 579, 466.",
    ]
    assert desktop.slept == [8.0]
    assert desktop.moves == [] and desktop.clicks == []


# ── the shipped images on real game screens ───────────────────────────────────

# Only the screenshot is stood in for: the images load, the screen turns gray
# and the matcher searches it as in a run, with drive_league_pregame on, as the
# shipped athc.toml has it.


def _scan_real(
    monkeypatch: pytest.MonkeyPatch, screen: str, *, pregame: bool = True
) -> object:
    """One scan, as the watcher makes it, of the real screenshot `screen`."""
    from athc.autocontinue import main

    shot = Image.open(SCREENS / screen)
    monkeypatch.setattr(main.pyautogui, "screenshot", lambda: shot)
    return main._scan(main._Images.load(), lambda _: None, pregame=pregame)


def _near(at: tuple[int, int], expected: tuple[int, int]) -> bool:
    return abs(at[0] - expected[0]) <= NEAR and abs(at[1] - expected[1]) <= NEAR


def _find_button(
    monkeypatch: pytest.MonkeyPatch, screen: str, button: str
) -> tuple[int, int] | None:
    """The middle of `button` where a run finds it on the real screenshot
    `screen`, or None. Continue counts only where the scan sees it alone,
    Return only under its label ("Halftime Return", "Results Return"), and a
    pre-game button only on the pre-game screen, searched as its step is."""
    from athc.autocontinue import main

    sighting = _scan_real(monkeypatch, screen)
    if button in ("Continue", "Halftime Return", "Results Return"):
        if not isinstance(sighting, main._Sighting):
            return None
        seen = "Continue" if sighting.label is None else f"{sighting.label.name} Return"
        if seen != button:
            return None
        return sighting.button.x, sighting.button.y
    if not isinstance(sighting, main._Pregame):
        return None
    images = main._Images.load()
    steps = main._pregame_steps(images, config.Config(drive_league_pregame=True))
    step = next(each for each in steps if each.name == button)
    box = main._locate_any(step.images, sighting.screen, step.confidence)
    if box is None:
        return None
    x, y = main.pyautogui.center(box)
    return x, y


def _cases(pointer: str, *cases: tuple[str, str, tuple[int, int]]) -> list[object]:
    """(screen, button, middle) cases, each named by its button and `pointer`."""
    return [pytest.param(*case, id=f"{case[1]}, {pointer}") for case in cases]


# Every button autocontinue acts on, on the screen it acts on it, and where
# the game draws it there.
BUTTONS = [
    *_cases(
        "pointer elsewhere",
        ("continue.png", "Continue", (382, 170)),
        ("halftime.png", "Halftime Return", (577, 459)),
        ("results.png", "Results Return", (578, 460)),
        ("league_play_pregame_opening.png", "Plans/profiles button", (153, 495)),
        ("league_play_pregame.png", "Visitor button", (457, 198)),
        ("league_play_pregame_visitor_plans.png", "Conditions button", (59, 499)),
        ("league_play_pregame_conditions.png", "Venues button", (369, 495)),
        ("league_play_pregame_venues.png", "Game button", (579, 466)),
    ),
    # Under the pointer a click on the screen before left there: unlit, but
    # Visitor, which the game lights even so. No click leaves it on Return,
    # which a move onto it lights.
    *_cases(
        "pointer on it",
        ("continue_pointer_on_continue.png", "Continue", (382, 182)),
        (
            "league_play_pregame_pointer_on_plans_profiles.png",
            "Plans/profiles button",
            (153, 495),
        ),
        ("league_play_pregame_pointer_on_visitor.png", "Visitor button", (457, 198)),
        (
            "league_play_pregame_pointer_on_conditions.png",
            "Conditions button",
            (58, 498),
        ),
        ("league_play_pregame_pointer_on_venues.png", "Venues button", (369, 495)),
        ("league_play_pregame_pointer_on_game.png", "Game button", (579, 466)),
    ),
    # Continue has no lit look: a move onto it changes only the pointer.
    *_cases(
        "lit",
        ("halftime_return_lit.png", "Halftime Return", (577, 459)),
        ("results_return_lit.png", "Results Return", (577, 459)),
        (
            "league_play_pregame_plans_profiles_lit.png",
            "Plans/profiles button",
            (153, 495),
        ),
        ("league_play_pregame_visitor_lit.png", "Visitor button", (457, 198)),
        ("league_play_pregame_conditions_lit.png", "Conditions button", (58, 498)),
        ("league_play_pregame_venues_lit.png", "Venues button", (369, 495)),
        # The game's hand at Game's corner, not its middle.
        ("league_play_pregame_game_lit.png", "Game button", (579, 466)),
    ),
]


@pytest.mark.parametrize(("screen", "button", "at"), BUTTONS)
def test_real_button_found(
    monkeypatch: pytest.MonkeyPatch, screen: str, button: str, at: tuple[int, int]
) -> None:
    found = _find_button(monkeypatch, screen, button)
    assert found is not None and _near(found, at)


# ── each match cutoff, from either side ───────────────────────────────────────

# The matcher keeps only scores over its confidence. Each cutoff is tested on
# a screen scoring just over it and one scoring just under.
SIDES = pytest.mark.parametrize("over", [True, False], ids=["just over", "just under"])


def _scored(
    needles: Sequence[numpy.ndarray],
    cutoff: float,
    *,
    over: bool,
    above: numpy.ndarray | None = None,
) -> tuple[numpy.ndarray, tuple[int, int]]:
    """A screen on which the best that any of `needles` scores is just over,
    or else just under, `cutoff`: the first needle with noise added, on noise,
    below `above` when given, so a label can sit over its button. Returns the
    screen and the needle's middle on it."""
    import cv2

    rng = numpy.random.default_rng(0)
    needle = needles[0]
    shapes = [each.shape for each in needles]
    # As wide as any image a scan looks for (the Results label, 127).
    width = max([128, *(w for _, w in shapes)])
    background = rng.integers(0, 256, (max(h for h, _ in shapes), width))
    noise = rng.normal(0.0, 1.0, needle.shape)
    top = numpy.zeros((0, width))
    if above is not None:
        top = rng.integers(0, 256, (above.shape[0], width))
        top[:, : above.shape[1]] = above
    low, high = 0.0, 255.0  # how much noise: more scores lower
    for _ in range(60):
        amount = (low + high) / 2
        part = background.copy()
        part[: needle.shape[0], : needle.shape[1]] = needle + amount * noise
        screen = numpy.clip(numpy.vstack([top, part]), 0, 255).astype(numpy.uint8)
        score = max(
            cv2.matchTemplate(screen, each, cv2.TM_CCOEFF_NORMED).max()
            for each in needles
        )
        if (score > cutoff) == over and abs(score - cutoff) < 0.005:
            middle = (needle.shape[1] // 2, len(top) + needle.shape[0] // 2)
            return screen, middle
        if score > cutoff:
            low = amount
        else:
            high = amount
    raise AssertionError(f"no screen scores just {'over' if over else 'under'}")


@SIDES
@pytest.mark.parametrize(
    ("step", "cutoff"),
    [
        ("Plans/profiles button", 0.8),
        ("Visitor button", 0.8),
        ("Conditions button", 0.8),
        # The pointer can rest on Venues, and sits on Game where Accept was.
        ("Venues button", 0.7),
        ("Game button", 0.6),
    ],
)
def test_pregame_step_finds_its_button_over_its_cutoff(
    step: str, cutoff: float, over: bool
) -> None:
    from athc.autocontinue import main

    images = main._Images.load()
    steps = main._pregame_steps(images, config.Config(drive_league_pregame=True))
    found = next(each for each in steps if each.name == step)
    screen, _ = _scored(found.images, cutoff, over=over)
    assert (
        main._locate_any(found.images, screen, found.confidence) is not None
    ) is over


@SIDES
def test_before_the_click_continue_counts_over_0_8(over: bool) -> None:
    from athc.autocontinue import main

    images = main._Images.load()
    screen, at = _scored((images.continue_button,), 0.8, over=over)
    gone = main._gone(main._Sighting(main.pyautogui.Point(*at)), images, screen)
    assert gone == (None if over else "Continue button gone; not clicked.")


@SIDES
def test_before_the_click_return_counts_over_0_6(over: bool) -> None:
    """Under the Halftime label, as the pause leaves it."""
    from athc.autocontinue import main

    images = main._Images.load()
    screen, at = _scored(images.returns, 0.6, over=over, above=images.halftime_label)
    label = main._Label("Halftime", main.pyautogui.Point(0, 0))
    sighting = main._Sighting(main.pyautogui.Point(*at), label)
    gone = main._gone(sighting, images, screen)
    assert gone == (None if over else "Return button gone; not clicked.")


@SIDES
def test_scan_finds_return_under_its_label_over_0_6(
    monkeypatch: pytest.MonkeyPatch, over: bool
) -> None:
    from athc.autocontinue import main

    images = main._Images.load()
    screen, at = _scored(images.returns, 0.6, over=over, above=images.halftime_label)
    monkeypatch.setattr(main, "_grab_screen", lambda warn: screen)
    sighting = main._scan(images, lambda _: None)
    if over:
        assert isinstance(sighting, main._Sighting) and _near(sighting.button, at)
    else:
        assert sighting is None


@SIDES
def test_scan_finds_the_pregame_with_game_over_0_6(
    monkeypatch: pytest.MonkeyPatch, over: bool
) -> None:
    from athc.autocontinue import main

    images = main._Images.load()
    screen, _ = _scored(images.games, 0.6, over=over, above=images.league_play_label)
    monkeypatch.setattr(main, "_grab_screen", lambda warn: screen)
    sighting = main._scan(images, lambda _: None, pregame=True)
    assert isinstance(sighting, main._Pregame) is over


# Where the pre-game buttons show, in the order they are clicked.
REAL_PREGAME_AT = {
    "Plans/profiles button": (153, 495),
    "Visitor button": (457, 198),
    "Conditions button": (58, 498),
    "Venues button": (369, 495),
    "Game button": (579, 466),
}
# The pre-game, each step's screenshot with the pointer on the button it
# clicks; the first is the scan's too.
POINTER_ON_EACH = [
    "league_play_pregame_pointer_on_plans_profiles.png",
    "league_play_pregame_pointer_on_plans_profiles.png",
    "league_play_pregame_pointer_on_visitor.png",
    "league_play_pregame_pointer_on_conditions.png",
    "league_play_pregame_pointer_on_venues.png",
    "league_play_pregame_pointer_on_game.png",
]
EACH_LIT = [
    "league_play_pregame_plans_profiles_lit.png",
    "league_play_pregame_plans_profiles_lit.png",
    "league_play_pregame_visitor_lit.png",
    "league_play_pregame_conditions_lit.png",
    "league_play_pregame_venues_lit.png",
    "league_play_pregame_game_lit.png",
]


@pytest.mark.parametrize("screens", [POINTER_ON_EACH, EACH_LIT], ids=["unlit", "lit"])
def test_real_pregame_driven_to_game(
    real_desktop: Desktop, write_config: WriteConfig, screens: list[str]
) -> None:
    """The pointer on each button the drive clicks: each found and clicked, in
    order, through to Game."""
    write_config(PREGAME_ON)
    real_desktop.focus = _pregame_focus(5)
    real_desktop.screens = screens
    real_desktop.run()
    assert real_desktop.said[-6].startswith("League play label found at ")
    assert real_desktop.said[-5:] == [f"{name} clicked." for name in REAL_PREGAME_AT]
    clicks = real_desktop.clicks
    assert len(clicks) == len(REAL_PREGAME_AT)
    for click, at in zip(clicks, REAL_PREGAME_AT.values(), strict=True):
        assert click[0] is not None and click[1] is not None
        assert _near((click[0], click[1]), at)
    assert real_desktop.slept == [1.5, 1.5, 2.5, 1.5, 4.0]


# Each page of the league play pre-game, the pointer elsewhere.
PREGAME_PAGES = [
    "league_play_pregame_opening.png",
    "league_play_pregame.png",
    "league_play_pregame_visitor_plans.png",
    "league_play_pregame_conditions.png",
    "league_play_pregame_venues.png",
]


def test_real_pregame_left_alone_when_off(real_desktop: Desktop) -> None:
    """drive_league_pregame missing, so off: one pass on each page, nothing
    said, moved or clicked."""
    real_desktop.focus = [True] * len(PREGAME_PAGES)
    real_desktop.screens = PREGAME_PAGES
    real_desktop.run()
    assert real_desktop.said[-1] == WINDOW[True]
    assert real_desktop.moves == [] and real_desktop.clicks == []
    assert real_desktop.slept == [1.0] * len(PREGAME_PAGES)


# Each page of the exhibition pre-game: Game, Plans/Profiles, Visitor,
# Conditions and Venues as in league play, without the League play label.
EXHIBITION_PAGES = [
    "exhibition_pregame_pointer_on_game.png",
    "exhibition_pregame.png",
    "exhibition_pregame_visitor_plans.png",
    "exhibition_pregame_conditions.png",
    "exhibition_pregame_venues.png",
    "exhibition_pregame_difficulty_levels.png",
    "exhibition_pregame_game_controls.png",
]


@pytest.mark.parametrize(
    "settings",
    ["[autocontinue]\ndrive_league_pregame = true\n", "[autocontinue]\n"],
    ids=["on", "off"],
)
def test_real_exhibition_pregame_left_alone(
    real_desktop: Desktop, write_config: WriteConfig, settings: str
) -> None:
    """With drive_league_pregame on or off: one pass on each page, nothing
    said, moved or clicked."""
    write_config(settings)
    real_desktop.focus = [True] * len(EXHIBITION_PAGES)
    real_desktop.screens = EXHIBITION_PAGES
    real_desktop.run()
    assert real_desktop.said[-1] == WINDOW[True]
    assert real_desktop.moves == [] and real_desktop.clicks == []
    assert real_desktop.slept == [1.0] * len(EXHIBITION_PAGES)


@pytest.mark.parametrize(
    ("screen", "pregame"),
    [
        ("coin_toss.png", False),
        ("league_play_schedule.png", True),
        ("controllers.png", True),
        ("controllers_accept_lit.png", True),
    ],
    ids=[
        "coin toss: Receive is not Continue",
        "schedule: League play label, not the pre-game",
        "controllers: Accept, where Game shows next",
        "controllers: Accept lit",
    ],
)
def test_real_screen_with_nothing_to_act_on(
    monkeypatch: pytest.MonkeyPatch, screen: str, pregame: bool
) -> None:
    assert _scan_real(monkeypatch, screen, pregame=pregame) is None
