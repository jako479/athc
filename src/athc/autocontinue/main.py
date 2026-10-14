"""Watch for the 'Continue' button in Front Page Sports Football Pro '98 and
click it.

Re-reads the INI when the config file changes on disk, so mouse_move_duration
and delay_before_continue can be tuned while the watcher is running.
"""

from __future__ import annotations

import ctypes
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import pyautogui
from cv2.typing import MatLike

from athc.autocontinue.config import (
    Config,
    config_signature,
    get_runtime_path,
    load_config,
)
from athc.errors import AthcError, ConfigFileError, missing_reason

Say = Callable[[str], None]

CONTINUE_BUTTON_IMAGE = get_runtime_path("continue_button.png")

_LOCATE_CONFIDENCE = 0.8
_SCAN_INTERVAL = 1.0
_POST_CLICK_COOLDOWN = 4.0
_NO_CLICK_COOLDOWN = 8.0
_LOCKED_SCREEN_BACKOFF = 60.0
_UNFOCUSED_POLL = 2.0

# The game auto-pauses when it loses focus, so only scan while it's the active
# window — matched as a case-insensitive substring of the foreground title.
_GAME_WINDOW_TITLE = "Front Page Sports Football Pro '98"

# The hot corner is the top-left one (PyAutoGUI fail-safe); the other three stay
# free for normal mouse use. `FAILSAFE` (toggled below) controls whether it's live.
pyautogui.FAILSAFE_POINTS = [(0, 0)]


def auto_continue(
    hot_corner: bool | None = None,
    delay: float | None = None,
    dry_run: bool = False,
    *,
    progress: Say | None = None,
    warn: Say | None = None,
    report: Say | None = None,
) -> None:
    """Run the watch-and-click loop until interrupted (Ctrl+C or the hot corner).

    Reads `[autocontinue]` from `config_dir()/athc.ini`, every key optional. The
    INI is re-read only when the file changes on disk, so edits apply while the
    watcher runs; a reload that fails validation goes to `warn` and the previous
    settings are kept. A wrong value at start raises ConfigFileError to the
    caller.

    `hot_corner` and `delay` are the CLI overrides: None uses the config value,
    a value forces it and ignores config changes to the setting. `dry_run` finds
    the button as usual and tells `report` where, never moving the mouse or
    clicking. `progress` hears the loop's status lines and `warn` its retries;
    nothing is printed or logged here.
    """
    say = progress or (lambda _: None)
    complain = warn or (lambda _: None)
    tell = report or (lambda _: None)
    if dry_run:
        # pyautogui checks the hot corner only inside the mouse calls a dry run
        # never makes, so it is off whatever the flag or the setting says.
        hot_corner = False
    last_signature = config_signature()
    config = load_config()
    button = _load_button_image(CONTINUE_BUTTON_IMAGE)

    say("Watching for the Continue button. Press Ctrl+C to stop.")
    _say_config_changes(None, config, delay, say)
    corner = _resolve_hot_corner(config, hot_corner)
    _apply_hot_corner(None, corner, say)
    if dry_run:
        say("Dry run: the Continue button is reported, never clicked.")
    width, height = _get_screen_size()
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
                _say_config_changes(config, new_config, delay, say)
                new_corner = _resolve_hot_corner(new_config, hot_corner)
                _apply_hot_corner(corner, new_corner, say)
                corner = new_corner
                config = new_config

        if not window.check():
            time.sleep(_UNFOCUSED_POLL)
            continue

        location = _find_continue_button(button, 0, 0, width, height, complain)
        # Re-check focus: the commish may have switched away (pausing the game)
        # since the top of the loop.
        if location is None or not window.check():
            time.sleep(_SCAN_INTERVAL)
            continue
        if dry_run:
            tell(f"Continue button found at {location.x}, {location.y}.")
            time.sleep(_NO_CLICK_COOLDOWN)
            continue
        try:
            pyautogui.moveTo(location.x, location.y, config.mouse_move_duration)
            time.sleep(_resolve_delay(config, delay))
            if not window.check():
                continue  # lost focus during the pre-click delay
            # On the button itself: the mouse may have moved during the delay.
            pyautogui.leftClick(location.x, location.y)
            time.sleep(_POST_CLICK_COOLDOWN)
        except pyautogui.FailSafeException as exc:
            # Top-left corner is the stop gesture; funnel it through the same
            # path as Ctrl+C.
            raise KeyboardInterrupt from exc


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


def _get_screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


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


def _load_button_image(path: Path) -> MatLike:
    """The Continue button as the matcher compares it (grayscale, as pyscreeze
    reads a file for `grayscale=True`), loaded once: a missing or unreadable
    image is a broken install, so it fails the run instead of retrying."""
    if not path.exists():
        raise AthcError(f"{missing_reason(path)} Reinstall athc.", path)
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:  # OpenCV says only that it could not read it
        raise AthcError("Cannot read the image. Reinstall athc.", path)
    return image


def _find_continue_button(
    button: MatLike, top: int, left: int, width: int, height: int, warn: Say
):
    try:
        # Single screenshot+match per call; the loop paces scans with _SCAN_INTERVAL.
        # (pyscreeze's minSearchTime busy-loops with no sleep, so we don't use it.)
        return pyautogui.locateCenterOnScreen(
            button,
            region=(top, left, width, height),
            grayscale=True,
            confidence=_LOCATE_CONFIDENCE,
        )
    except pyautogui.ImageNotFoundException:
        return None
    except OSError:
        # ImageGrab raises OSError when Windows hides the screen. The button is
        # already loaded, so this is the screen: say why and back off so we
        # don't flood; any other error propagates so real bugs surface.
        warn(
            "The screen is locked, a screensaver is on, or Remote Desktop is "
            f"disconnected. Retrying in {_LOCKED_SCREEN_BACKOFF:.0f} seconds."
        )
        time.sleep(_LOCKED_SCREEN_BACKOFF)
        return None


def _reload_failed(error: ConfigFileError) -> str:
    """The warning for a config file that no longer reads: the error, which
    names the file, then what happens next."""
    return f"{error} Keeping the previous settings."


def _resolve_hot_corner(config: Config, override: bool | None) -> bool:
    """CLI override wins; None falls back to the config value."""
    return config.hot_corner if override is None else override


def _resolve_delay(config: Config, override: float | None) -> float:
    """--delay wins; None falls back to the config value."""
    return config.delay_before_continue if override is None else override


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
    prev: Config | None, current: Config, delay: float | None, say: Say
) -> None:
    """Say each setting at start (no `prev`) and each one a reload changed, by
    its athc.ini key; a delay held by --delay is said once, at start."""
    if prev is None or prev.mouse_move_duration != current.mouse_move_duration:
        say(f"mouse_move_duration = {current.mouse_move_duration}")
    if delay is not None:
        if prev is None:
            say(f"delay_before_continue = {delay} (--delay)")
    elif prev is None or prev.delay_before_continue != current.delay_before_continue:
        say(f"delay_before_continue = {current.delay_before_continue}")
