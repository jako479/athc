"""`athc autocontinue` — auto-click the Front Page Sports Football Pro '98
'Continue' button between plays."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand
from athc.console import console
from athc.errors import AthcError


@click.command(name="autocontinue", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.option(
    "--hot-corner/--no-hot-corner",
    default=None,
    help="Stop when the mouse hits the top-left corner (overrides config; default on).",
)
def autocontinue(hot_corner: bool | None) -> None:
    """Watch for the 'Continue' button between plays and click it.

    Clicks the 'Continue' button in Front Page Sports Football Pro '98. Stop with
    CTRL-C, or by moving the mouse to the top-left screen corner (the "hot corner",
    on by default; disable with --no-hot-corner or the config). Reads
    `[autocontinue]` (mouse_move_duration, delay_before_continue, hot_corner) from
    athc.ini, re-reading whenever the file changes so edits apply while it runs.
    """
    try:
        # Lazy import: pulls in pyautogui only when the watcher actually runs.
        from athc.autocontinue.main import auto_continue
    except ImportError as error:
        raise AthcError(
            f"missing {error.name or 'pyautogui'} -- reinstall athc"
        ) from error

    try:
        auto_continue(
            hot_corner=hot_corner, progress=console.progress, warn=console.warn
        )
    except KeyboardInterrupt:
        # Ctrl-C and the top-left fail-safe both land here: the normal stop.
        console.result("Shutting down AutoContinue")
