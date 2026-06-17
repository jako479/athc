"""Watch the screen for the FbPro '98 'Continue' button and click it.

Re-reads the INI when the config file changes on disk, so MouseMoveDuration /
DelayBeforeContinue can be tuned while the watcher is running.
"""

from __future__ import annotations

import ctypes
import logging
import sys
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

_LOCATE_MIN_SEARCH_TIME = 10.0
_LOCATE_CONFIDENCE = 0.8
_POST_CLICK_COOLDOWN = 4.0
_NO_CLICK_COOLDOWN = 8.0
_LOCKED_SCREEN_BACKOFF = 60.0


def auto_continue() -> None:
    """Run the watch-and-click loop until interrupted (Ctrl-C).

    Reads `[autocontinue]` from `config_dir()/athc.ini`. The INI is re-read only when
    the file changes on disk, so edits apply while the watcher runs; a reload that
    fails validation is logged and the previous settings kept. The initial load is
    required; a ConfigError there propagates to the caller.
    """
    last_signature = config_signature()
    config = load_config()

    logger.info("AutoContinue is RUNNING. Press CTRL-C to exit.")
    logger.info("(Move mouse to corner of screen to invoke fail-safe.)")
    _log_config_changes(None, config)
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
                config = new_config

        location = _find_continue_button(0, 0, width, height)
        if location is None:
            continue
        pyautogui.moveTo(location.x, location.y, config.mouse_move_duration)
        if config.delay_before_continue >= 0:
            time.sleep(config.delay_before_continue)
            pyautogui.leftClick()
            time.sleep(_POST_CLICK_COOLDOWN)
        else:
            time.sleep(_NO_CLICK_COOLDOWN)


def shutdown() -> None:
    sys.stdout.write("\r\nShutting down AutoContinue")
    for dot in "....\n":
        time.sleep(0.5)
        sys.stdout.write(dot)
        sys.stdout.flush()


def _get_screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _find_continue_button(top: int, left: int, width: int, height: int):
    try:
        return pyautogui.locateCenterOnScreen(
            str(CONTINUE_BUTTON_IMAGE),
            region=(top, left, width, height),
            minSearchTime=_LOCATE_MIN_SEARCH_TIME,
            grayscale=True,
            confidence=_LOCATE_CONFIDENCE,
        )
    except pyautogui.ImageNotFoundException:
        return None
    except Exception:
        # Screen grab fails when the OS is locked. Back off so we don't flood logs.
        time.sleep(_LOCKED_SCREEN_BACKOFF)
        return None


def _log_config_changes(prev: Config | None, current: Config) -> None:
    if prev is None or prev.mouse_move_duration != current.mouse_move_duration:
        logger.info("MouseMoveDuration set to %s", current.mouse_move_duration)
    if prev is None or prev.delay_before_continue != current.delay_before_continue:
        logger.info("DelayBeforeContinue set to %s", current.delay_before_continue)
