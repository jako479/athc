"""Watch for the 'Continue' button in Front Page Sports Football Pro '98 and
click it; click Return at halftime, and stop at the end of the game. With
drive_league_pregame on, click through the league play pre-game screens and
start the game.

Re-reads the INI when the config file changes on disk, so the settings can be
tuned while the watcher is running.
"""

from __future__ import annotations

import ctypes
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy
import pyautogui
from cv2.typing import MatLike
from PIL import Image

from athc.autocontinue.config import (
    Config,
    config_signature,
    get_runtime_path,
    load_config,
)
from athc.errors import AthcError, ConfigFileError, missing_reason
from athc.log import log_path

Say = Callable[[str], None]

CONTINUE_BUTTON_IMAGE = get_runtime_path("continue_button.png")
HALFTIME_LABEL_IMAGE = get_runtime_path("halftime_label.png")
RESULTS_LABEL_IMAGE = get_runtime_path("results_label.png")
RETURN_BUTTON_IMAGE = get_runtime_path("return_button.png")
# Return as the game lights it up once the mouse moves onto it.
RETURN_HIGHLIGHT_IMAGE = get_runtime_path("return_highlight_button.png")
LEAGUE_PLAY_LABEL_IMAGE = get_runtime_path("league_play_label.png")
PLANS_PROFILES_BUTTON_IMAGE = get_runtime_path("plans_profiles_button.png")
VISITOR_BUTTON_IMAGE = get_runtime_path("visitor_button.png")
CONDITIONS_BUTTON_IMAGE = get_runtime_path("conditions_button.png")
VENUES_BUTTON_IMAGE = get_runtime_path("venues_button.png")
GAME_BUTTON_IMAGE = get_runtime_path("game_button.png")
GAME_HIGHLIGHT_IMAGE = get_runtime_path("game_highlight_button.png")

_HALFTIME = "Halftime"
_RESULTS = "Results"

# The pre-game settings, said by their athc.ini keys.
_PREGAME_KEYS = (
    "drive_league_pregame",
    "plans_profiles_pause",
    "conditions_pause",
    "venues_pause",
)

_LOCATE_CONFIDENCE = 0.8
# Return and Game, under the hand pointer the game draws itself: it sits on
# Return through the halftime pause, and on Game where Accept was clicked.
# Measured on real screens: 0.77 and 0.72 with it, against nothing else on
# their screens above 0.50.
_UNDER_POINTER_CONFIDENCE = 0.6
# Venues, under the game's pointer: 0.77 on a real screen, against 0.56 for
# the best other spot on the Conditions page it is searched on (Random
# Weather, which comes first in the search). The other pre-game buttons stay
# over 0.8 under it.
_VENUES_CONFIDENCE = 0.7
_SCAN_INTERVAL = 1.0
_POST_CLICK_COOLDOWN = 4.0
_NO_CLICK_COOLDOWN = 8.0
_LOCKED_SCREEN_BACKOFF = 60.0
_UNFOCUSED_POLL = 2.0
_ERROR_BACKOFF = 5.0

# The game auto-pauses when it loses focus, so only scan while it's the active
# window — matched as a case-insensitive substring of the foreground title.
_GAME_WINDOW_TITLE = "Front Page Sports Football Pro '98"

# The hot corner is the top-left one (PyAutoGUI fail-safe); the other three stay
# free for normal mouse use. `FAILSAFE` (toggled below) controls whether it's live.
pyautogui.FAILSAFE_POINTS = [(0, 0)]


class HotCornerStop(KeyboardInterrupt):
    """The mouse hit the hot corner: a stop like Ctrl+C."""


def auto_continue(
    hot_corner: bool | None = None,
    continue_pause: float | None = None,
    dry_run: bool = False,
    *,
    progress: Say | None = None,
    warn: Say | None = None,
    warn_traced: Say | None = None,
    report: Say | None = None,
) -> None:
    """Run the watch-and-click loop until interrupted (Ctrl+C or the hot corner),
    or return at the end of the game.

    At halftime it clicks Return after `halftime_pause` seconds; at the end of
    the game it moves the mouse to Return and returns, without a click. With
    `drive_league_pregame` on, the league play pre-game screen is clicked
    through to Game.

    Reads `[autocontinue]` from `config_dir()/athc.ini`, every key optional. The
    INI is re-read only when the file changes on disk, so edits apply while the
    watcher runs; a reload that fails validation goes to `warn` and the previous
    settings are kept. A wrong value at start raises ConfigFileError to the
    caller.

    `hot_corner` and `continue_pause` are the CLI overrides: None uses the
    config value, a value forces it and ignores config changes to the setting.
    `dry_run` scans as usual and tells `report` what it finds and where, never
    moving the mouse or clicking; it too returns at the end of the game.
    `progress` hears the loop's status lines and `warn` its retries;
    `warn_traced` hears the first failure of each kind, inside the `except`,
    so its caller can log the traceback; nothing is printed or logged here.
    """
    say = progress or (lambda _: None)
    complain = warn or (lambda _: None)
    complain_traced = warn_traced or complain
    tell = report or (lambda _: None)
    seen: set[tuple[str, str]] = set()  # failures already traced
    if dry_run:
        # pyautogui checks the hot corner only inside the mouse calls a dry run
        # never makes, so it is off whatever the flag or the setting says.
        hot_corner = False
    last_signature = config_signature()
    config = load_config()
    images = _Images.load()

    say("Watching for the Continue button. Press Ctrl+C to stop.")
    _say_config_changes(None, config, continue_pause, say)
    corner = _resolve_hot_corner(config, hot_corner)
    _apply_hot_corner(None, corner, say)
    if dry_run:
        say("Dry run: what it finds is reported, never clicked.")
    window = _GameWindow(say)

    while True:
        signature = config_signature()
        if signature != last_signature:
            last_signature = signature
            try:
                new_config = load_config()
            except ConfigFileError as error:
                complain(_reload_failed(error))
            else:
                _say_config_changes(config, new_config, continue_pause, say)
                new_corner = _resolve_hot_corner(new_config, hot_corner)
                _apply_hot_corner(corner, new_corner, say)
                corner = new_corner
                config = new_config

        try:
            if _watch_once(
                images, window, config, continue_pause, dry_run, say, complain, tell
            ):
                return
        except pyautogui.FailSafeException as exc:
            # Top-left corner is the stop gesture; funnel it through the same
            # path as Ctrl+C, told apart so the run can say which it was.
            raise HotCornerStop from exc
        except Exception as error:
            # A failure, like a driver hiccup mid-game, is said and retried
            # for good: the run is unattended, so a crash would leave the game
            # sitting at the next Continue. The first of each kind names the
            # run log, where its traceback goes; a repeat is one line, so a
            # failure that persists never floods the log. Ctrl+C is not an
            # Exception.
            kind = (type(error).__name__, str(error).rstrip("."))
            what = f"Unexpected {kind[0]}: {kind[1]}."
            retry = f"Retrying in {_ERROR_BACKOFF:.0f} seconds."
            if kind in seen:
                complain(f"{what} {retry}")
            else:
                seen.add(kind)
                complain_traced(f"{what} See {log_path()} for details. {retry}")
            time.sleep(_ERROR_BACKOFF)


def _watch_once(
    images: _Images,
    window: _GameWindow,
    config: Config,
    continue_pause: float | None,
    dry_run: bool,
    say: Say,
    complain: Say,
    tell: Say,
) -> bool:
    """One pass of the loop: scan, then act on what it finds. True at the end
    of the game."""
    if not window.check():
        time.sleep(_UNFOCUSED_POLL)
        return False

    sighting = _scan(images, complain, pregame=config.drive_league_pregame)
    # Re-check focus: the commish may have switched away (pausing the game)
    # since the top of the loop.
    if sighting is None or not window.check():
        time.sleep(_SCAN_INTERVAL)
        return False
    if isinstance(sighting, _Pregame):
        _drive_pregame(sighting, images, window, config, dry_run, say, complain, tell)
        return False
    if dry_run:
        for line in _sighting_lines(sighting):
            tell(line)
        if sighting.label is not None and sighting.label.name == _RESULTS:
            return True
        time.sleep(_NO_CLICK_COOLDOWN)
        return False
    x, y = sighting.button
    if sighting.label is None:
        pyautogui.moveTo(x, y, config.mouse_move_duration)
        time.sleep(_resolve_continue_pause(config, continue_pause))
    else:
        for line in _sighting_lines(sighting):
            say(line)
        # Instant, so the mouse is off the halftime stats at once.
        pyautogui.moveTo(x, y, 0.0)
        if sighting.label.name == _RESULTS:
            return True
        say(_waiting(config.halftime_pause))
        time.sleep(config.halftime_pause)
    if not window.check():
        return False  # lost focus during the wait
    # Re-check just before the click: the coach may have clicked it himself,
    # or dragged the window, during the wait.
    screen = _grab_screen(complain)
    if screen is None:
        return False  # the warning has said why
    gone = _gone(sighting, images, screen)
    if gone is not None:
        say(gone)
        return False
    if not window.check():
        return False  # lost focus while the button was checked
    # On the button itself: the mouse may have moved during the wait.
    pyautogui.leftClick(x, y)
    if sighting.label is not None:
        # Every click is said but Continue, which comes 100 or more times a
        # game.
        say("Return button clicked.")
    time.sleep(_POST_CLICK_COOLDOWN)
    return False


def _drive_pregame(
    sighting: _Pregame,
    images: _Images,
    window: _GameWindow,
    config: Config,
    dry_run: bool,
    say: Say,
    complain: Say,
    tell: Say,
) -> None:
    """Click through the league play pre-game screen, then Game. Each click
    is checked first: the game still the active window, and a fresh screenshot
    still showing the screen and the button. A dry run reports the buttons on
    the scan's screenshot instead."""
    steps = _pregame_steps(images, config)
    label = _found("League play label", sighting.at)
    if dry_run:
        tell(label)
        for step in steps:
            box = _locate_any(step.images, sighting.screen, step.confidence)
            if box is None:
                tell(f"{step.name} not found.")
            else:
                tell(_found(step.name, pyautogui.Point(*pyautogui.center(box))))
        time.sleep(_NO_CLICK_COOLDOWN)
        return
    say(label)
    for step in steps:
        if not window.check():
            return  # lost focus during the pause
        screen = _grab_screen(complain)
        if screen is None:
            return  # the warning has said why
        if _locate(images.league_play_label, screen) is None:
            # The coach clicked Game himself during the pause.
            say(f"League play label gone; {step.name} not clicked.")
            return
        box = _locate_any(step.images, screen, step.confidence)
        if box is None:
            say(f"{step.name} not found; not clicked.")
            # The label stays, so the next scan starts over: not every second.
            time.sleep(_NO_CLICK_COOLDOWN)
            return
        if not window.check():
            return  # lost focus while the button was found
        x, y = pyautogui.center(box)
        pyautogui.leftClick(x, y)
        say(f"{step.name} clicked.")
        time.sleep(step.pause)


@dataclass(frozen=True, slots=True)
class _Step:
    """One pre-game click: the button, as its lines name it, the pause after
    the click, and how close a match counts."""

    name: str
    images: tuple[MatLike, ...]
    pause: float
    confidence: float = _LOCATE_CONFIDENCE


def _pregame_steps(images: _Images, config: Config) -> list[_Step]:
    """The pre-game clicks in order; a pause of 0 skips its click, and the
    Plans/Profiles pause skips Visitor too. Plans/Profiles is clicked even
    though league play opens on it."""
    steps: list[_Step] = []
    if config.plans_profiles_pause:
        steps += [
            _Step(
                "Plans/profiles button",
                (images.plans_profiles_button,),
                config.plans_profiles_pause,
            ),
            _Step(
                "Visitor button", (images.visitor_button,), config.plans_profiles_pause
            ),
        ]
    if config.conditions_pause:
        steps.append(
            _Step(
                "Conditions button",
                (images.conditions_button,),
                config.conditions_pause,
            )
        )
    if config.venues_pause:
        steps.append(
            _Step(
                "Venues button",
                (images.venues_button,),
                config.venues_pause,
                _VENUES_CONFIDENCE,
            )
        )
    steps.append(
        _Step(
            "Game button",
            images.games,
            _POST_CLICK_COOLDOWN,
            _UNDER_POINTER_CONFIDENCE,
        )
    )
    return steps


@dataclass(slots=True)
class _GameWindow:
    """Whether the game is the active window, said on the first check (the
    state starts unknown) and on each change."""

    say: Say
    active: bool | None = None

    def check(self) -> bool:
        active = _game_has_focus()
        if active != self.active:
            self.active = active
            self.say(
                "Game window active." if active else "Waiting for the game window."
            )
        return active


def _game_has_focus() -> bool:
    """True when the foreground window is the game (works windowed or fullscreen,
    since the window keeps its title even with the title bar hidden)."""
    return _GAME_WINDOW_TITLE.casefold() in _foreground_window_title().casefold()


def _foreground_window_title() -> str:
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _load_image(path: Path) -> MatLike:
    """An image as the matcher compares it (grayscale, as pyscreeze reads a
    file for `grayscale=True`), loaded once: a missing or unreadable image is
    a broken install, so it fails the run instead of retrying."""
    if not path.exists():
        raise AthcError(f"{missing_reason(path)} Reinstall athc.", path)
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:  # OpenCV says only that it could not read it
        raise AthcError("Cannot read the image. Reinstall athc.", path)
    return image


@dataclass(frozen=True, slots=True)
class _Images:
    """The images the screen is searched for, loaded once at start."""

    continue_button: MatLike
    halftime_label: MatLike
    results_label: MatLike
    return_button: MatLike
    return_highlight: MatLike
    league_play_label: MatLike
    plans_profiles_button: MatLike
    visitor_button: MatLike
    conditions_button: MatLike
    venues_button: MatLike
    game_button: MatLike
    game_highlight: MatLike

    @classmethod
    def load(cls) -> _Images:
        return cls(
            continue_button=_load_image(CONTINUE_BUTTON_IMAGE),
            halftime_label=_load_image(HALFTIME_LABEL_IMAGE),
            results_label=_load_image(RESULTS_LABEL_IMAGE),
            return_button=_load_image(RETURN_BUTTON_IMAGE),
            return_highlight=_load_image(RETURN_HIGHLIGHT_IMAGE),
            league_play_label=_load_image(LEAGUE_PLAY_LABEL_IMAGE),
            plans_profiles_button=_load_image(PLANS_PROFILES_BUTTON_IMAGE),
            visitor_button=_load_image(VISITOR_BUTTON_IMAGE),
            conditions_button=_load_image(CONDITIONS_BUTTON_IMAGE),
            venues_button=_load_image(VENUES_BUTTON_IMAGE),
            game_button=_load_image(GAME_BUTTON_IMAGE),
            game_highlight=_load_image(GAME_HIGHLIGHT_IMAGE),
        )

    @property
    def returns(self) -> tuple[MatLike, MatLike]:
        """Return as drawn, then lit up by the mouse; either one counts."""
        return self.return_button, self.return_highlight

    @property
    def games(self) -> tuple[MatLike, MatLike]:
        """Game as drawn, then lit up by the mouse; either one counts."""
        return self.game_button, self.game_highlight


@dataclass(frozen=True, slots=True)
class _Label:
    name: str  # _HALFTIME or _RESULTS
    at: pyautogui.Point


@dataclass(frozen=True, slots=True)
class _Sighting:
    """One scan's find: the Continue button alone, or a label with the Return
    button."""

    button: pyautogui.Point
    label: _Label | None = None


@dataclass(frozen=True, slots=True)
class _Pregame:
    """One scan's find of the league play pre-game screen: where its label
    is, on the screenshot it was found on."""

    at: pyautogui.Point
    screen: MatLike


def _scan(
    images: _Images, warn: Say, *, pregame: bool = False
) -> _Sighting | _Pregame | None:
    """One screenshot, checked for the Results label, then the Halftime label,
    then (with `pregame`) the League play label, then the Continue button. A
    Results or Halftime label counts only with Return on screen too, and the
    League play label only with Game, since it also shows on other league
    screens, like the schedule."""
    screen = _grab_screen(warn)
    if screen is None:
        return None
    labels = ((_RESULTS, images.results_label), (_HALFTIME, images.halftime_label))
    for name, image in labels:
        at = _locate(image, screen)
        if at is not None:
            box = _locate_any(images.returns, screen, _UNDER_POINTER_CONFIDENCE)
            if box is None:
                return None
            return _Sighting(pyautogui.Point(*pyautogui.center(box)), _Label(name, at))
    if pregame:
        at = _locate(images.league_play_label, screen)
        if at is not None:
            if _locate_any(images.games, screen, _UNDER_POINTER_CONFIDENCE) is None:
                return None
            return _Pregame(at, screen)
    button = _locate(images.continue_button, screen)
    return None if button is None else _Sighting(button)


def _gone(sighting: _Sighting, images: _Images, screen: MatLike) -> str | None:
    """The line for a sighting that cannot be clicked any more, or None. At
    halftime the label must still be on screen; the button must still be
    under the spot the scan found, or the click would miss it."""
    if sighting.label is None:
        name, box = "Continue button", _locate_box(images.continue_button, screen)
    else:
        if _locate(images.halftime_label, screen) is None:
            return "Halftime label gone; Return not clicked."
        # The mouse is on it after the pause: lit up, under the pointer.
        name = "Return button"
        box = _locate_any(images.returns, screen, _UNDER_POINTER_CONFIDENCE)
    if box is None:
        return f"{name} gone; not clicked."
    left, top, width, height = box
    x, y = sighting.button
    if not (left <= x < left + width and top <= y < top + height):
        return f"{name} moved; not clicked."
    return None


def _grab_screen(warn: Say) -> MatLike | None:
    """The screen in gray, as the images are; None while Windows hides it."""
    try:
        shot = pyautogui.screenshot()
    except OSError:
        # ImageGrab raises OSError when Windows hides the screen. The images
        # are already loaded, so this is the screen: say why and back off so
        # we don't flood; any other error propagates so real bugs surface.
        warn(
            "The screen is locked, a screensaver is on, or Remote Desktop is "
            f"disconnected. Retrying in {_LOCKED_SCREEN_BACKOFF:.0f} seconds."
        )
        time.sleep(_LOCKED_SCREEN_BACKOFF)
        return None
    return _gray(shot)


def _gray(shot: Image.Image) -> MatLike:
    """A screenshot in gray, the way pyscreeze turns one gray. Done once per
    screenshot: pyscreeze searches a gray picture as it is, where it would
    turn a color one gray again for every search."""
    return cv2.cvtColor(numpy.asarray(shot.convert("RGB")), cv2.COLOR_RGB2GRAY)


def _locate(image: MatLike, screen: MatLike) -> pyautogui.Point | None:
    """Where `image`'s middle is on the screenshot, or None."""
    box = _locate_box(image, screen)
    return None if box is None else pyautogui.Point(*pyautogui.center(box))


def _locate_box(
    image: MatLike, screen: MatLike, confidence: float = _LOCATE_CONFIDENCE
) -> tuple[int, int, int, int] | None:
    """`image`'s (left, top, width, height) on the whole screenshot, or None.
    No region: the screenshot is the primary screen as it is now, whatever its
    size."""
    try:
        box = pyautogui.locate(image, screen, grayscale=True, confidence=confidence)
    except pyautogui.ImageNotFoundException:
        return None
    if box is None:  # pyscreeze returns None instead when set not to raise
        return None
    left, top, width, height = box
    return left, top, width, height


def _locate_any(
    images: tuple[MatLike, ...],
    screen: MatLike,
    confidence: float = _LOCATE_CONFIDENCE,
) -> tuple[int, int, int, int] | None:
    """The box of the first of `images` found on the screenshot, or None."""
    for image in images:
        box = _locate_box(image, screen, confidence)
        if box is not None:
            return box
    return None


def _sighting_lines(sighting: _Sighting) -> list[str]:
    """What a sighting says: the label and Return, or the Continue button."""
    if sighting.label is None:
        return [_found("Continue button", sighting.button)]
    return [
        _found(f"{sighting.label.name} label", sighting.label.at),
        _found("Return button", sighting.button),
    ]


def _found(what: str, at: pyautogui.Point) -> str:
    return f"{what} found at {at.x}, {at.y}."


def _waiting(seconds: float) -> str:
    """`Waiting 10 seconds.`: a whole number without its .0; 1 second."""
    shown = int(seconds) if seconds.is_integer() else seconds
    return f"Waiting {shown} second{'' if seconds == 1 else 's'}."


def _reload_failed(error: ConfigFileError) -> str:
    """The warning for a config file that no longer reads: the error, which
    names the file, then what happens next."""
    return f"{error} Keeping the previous settings."


def _resolve_hot_corner(config: Config, override: bool | None) -> bool:
    """CLI override wins; None falls back to the config value."""
    return config.hot_corner if override is None else override


def _resolve_continue_pause(config: Config, override: float | None) -> float:
    """--continue-pause wins; None falls back to the config value."""
    return config.continue_pause if override is None else override


def _apply_hot_corner(prev: bool | None, enabled: bool, say: Say) -> None:
    """Toggle the PyAutoGUI fail-safe and say the state on change. On: the
    top-left corner stops the watcher at its next move or click. Off: Ctrl+C
    only."""
    pyautogui.FAILSAFE = enabled
    if prev == enabled:
        return
    if enabled:
        say("Hot corner on: move the mouse to the top-left corner to stop.")
    else:
        say("Hot corner off: press Ctrl+C to stop.")


def _say_config_changes(
    prev: Config | None, current: Config, continue_pause: float | None, say: Say
) -> None:
    """Say each setting at start (no `prev`) and each one a reload changed, by
    its athc.ini key; a pause held by --continue-pause is said once, at
    start."""
    if prev is None or prev.mouse_move_duration != current.mouse_move_duration:
        say(f"mouse_move_duration = {current.mouse_move_duration}")
    if continue_pause is not None:
        if prev is None:
            say(f"continue_pause = {continue_pause} (--continue-pause)")
    elif prev is None or prev.continue_pause != current.continue_pause:
        say(f"continue_pause = {current.continue_pause}")
    if prev is None or prev.halftime_pause != current.halftime_pause:
        say(f"halftime_pause = {current.halftime_pause}")
    for key in _PREGAME_KEYS:
        value = getattr(current, key)
        if prev is None or getattr(prev, key) != value:
            # As athc.ini spells it: true, not Python's True.
            shown = str(value).lower() if isinstance(value, bool) else value
            say(f"{key} = {shown}")
