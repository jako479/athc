"""`athc autocontinue` — auto-click the FbPro '98 'Continue' button between plays."""

from __future__ import annotations

import logging

import click

from athc.autocontinue.config import ConfigError

PROG = "athc autocontinue"
logger = logging.getLogger(__name__)


@click.command(
    name="autocontinue",
    help="Watch the screen for the FbPro '98 'Continue' button and click it.",
)
@click.pass_context
def autocontinue(ctx: click.Context) -> None:
    """Watch the screen for the FbPro '98 'Continue' button and click it.

    Press CTRL-C to stop; move the mouse to a screen corner for PyAutoGUI's fail-safe.
    Reads `[autocontinue]` (mouse_move_duration, delay_before_continue) from athc.ini,
    re-reading whenever the file changes so edits apply while it runs.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        # Lazy import: pulls in pyautogui only when the watcher actually runs.
        from athc.autocontinue.main import auto_continue, shutdown
    except ImportError:
        logger.error(
            "%s: requires pyautogui. Install it with: pip install athc[autocontinue]",
            PROG,
        )
        ctx.exit(2)

    try:
        auto_continue()
    except (ConfigError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    except KeyboardInterrupt:
        shutdown()
