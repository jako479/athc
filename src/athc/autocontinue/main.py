"""Watch for the 'Continue' button in Front Page Sports Football Pro '98 and
click it.

Re-reads the INI when the config file changes on disk, so MouseMoveDuration /
DelayBeforeContinue can be tuned while the watcher is running.
"""

from __future__ import annotations

import ctypes
import logging
import time

import pyautogui

from athc.autocontinue.config import (
    Config,
    ConfigError,
    config_signature,
    get_runtime_path,
    load_config,
)

logger = logging.getLogger(__name__)

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


def auto_continue(hot_corner: bool | None = None) -> None:
    """Run the watch-and-click loop until interrupted (Ctrl-C).

    Reads `[autocontinue]` from `config_dir()/athc.ini`. The INI is re-read only when
    the file changes on disk, so edits apply while the watcher runs; a reload that
    fails validation is logged and the previous settings kept. The initial load is
    required; a ConfigError there propagates to the caller.

    `hot_corner` is the CLI override: None uses the config value, True/False forces it
    and ignores config changes to the setting.
    """
    last_signature = config_signature()
    config = load_config()

    logger.info("AutoContinue is RUNNING. Press CTRL-C to exit.")
    _log_config_changes(None, config)
    corner = _resolve_hot_corner(config, hot_corner)
    _apply_hot_corner(None, corner)
    width, height = _get_screen_size()

    while True:
        signature = config_signature()
        if signature != last_signature:
            last_signature = signature
            try:
                new_config = load_config()
            except ConfigError as error:
                logger.warning(
                    "Config reload failed; keeping previous settings. %s", error
                )
            else:
                _log_config_changes(config, new_config)
                new_corner = _resolve_hot_corner(new_config, hot_corner)
                _apply_hot_corner(corner, new_corner)
                corner = new_corner
                config = new_config

        if not _game_has_focus():
            time.sleep(_UNFOCUSED_POLL)
            continue

        location = _find_continue_button(0, 0, width, height)
        # Re-check focus: the commish may have switched away (pausing the game)
        # since the top of the loop.
        if location is None or not _game_has_focus():
            time.sleep(_SCAN_INTERVAL)
            continue
        try:
            pyautogui.moveTo(location.x, location.y, config.mouse_move_duration)
            if config.delay_before_continue >= 0:
                time.sleep(config.delay_before_continue)
                if not _game_has_focus():
                    continue  # lost focus during the pre-click delay
                pyautogui.leftClick()
                time.sleep(_POST_CLICK_COOLDOWN)
            else:
                time.sleep(_NO_CLICK_COOLDOWN)
        except pyautogui.FailSafeException as exc:
            # Top-left corner is the stop gesture; funnel it through the same
            # path as Ctrl-C.
            raise KeyboardInterrupt from exc


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


def _find_continue_button(top: int, left: int, width: int, height: int):
    try:
        # Single screenshot+match per call; the loop paces scans with _SCAN_INTERVAL.
        # (pyscreeze's minSearchTime busy-loops with no sleep, so we don't use it.)
        return pyautogui.locateCenterOnScreen(
            str(CONTINUE_BUTTON_IMAGE),
            region=(top, left, width, height),
            grayscale=True,
            confidence=_LOCATE_CONFIDENCE,
        )
    except pyautogui.ImageNotFoundException:
        return None
    except OSError as error:
        # ImageGrab raises OSError on a locked screen / screensaver / disconnected
        # RDP. Log it (so it isn't silent) and back off so we don't flood; any
        # other error propagates so real bugs surface instead of being swallowed.
        logger.warning(
            "Screen grab failed (%s); retrying in %.0fs.", error, _LOCKED_SCREEN_BACKOFF
        )
        time.sleep(_LOCKED_SCREEN_BACKOFF)
        return None


def _resolve_hot_corner(config: Config, override: bool | None) -> bool:
    """CLI override wins; None falls back to the config value."""
    return config.hot_corner if override is None else override


def _apply_hot_corner(prev: bool | None, enabled: bool) -> None:
    """Toggle the PyAutoGUI fail-safe and log the state on change. Enabled: the
    top-left corner stops the watcher. Disabled: Ctrl-C only."""
    pyautogui.FAILSAFE = enabled
    if prev == enabled:
        return
    if enabled:
        logger.info("(Move the mouse to the top-left corner to stop.)")
    else:
        logger.info("Hot corner disabled; press CTRL-C to stop.")


def _log_config_changes(prev: Config | None, current: Config) -> None:
    if prev is None or prev.mouse_move_duration != current.mouse_move_duration:
        logger.info("MouseMoveDuration set to %s", current.mouse_move_duration)
    if prev is None or prev.delay_before_continue != current.delay_before_continue:
        logger.info("DelayBeforeContinue set to %s", current.delay_before_continue)
