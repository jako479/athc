"""`athc autocontinue` — auto-click the Front Page Sports Football Pro '98
'Continue' button between plays."""

from __future__ import annotations

import logging
import time

import click

from athc.autocontinue.config import ConfigError

PROG = "athc autocontinue"
logger = logging.getLogger(__name__)


@click.command(name="autocontinue")
@click.option(
    "--hot-corner/--no-hot-corner",
    default=None,
    help="Stop when the mouse hits the top-left corner (overrides config; default on).",
)
@click.pass_context
def autocontinue(ctx: click.Context, hot_corner: bool | None) -> None:
    """Watch for the 'Continue' button between plays and click it.

    Clicks the 'Continue' button in Front Page Sports Football Pro '98. Stop with
    CTRL-C, or by moving the mouse to the top-left screen corner (the "hot corner",
    on by default; disable with --no-hot-corner or the config). Reads
    `[autocontinue]` (mouse_move_duration, delay_before_continue, hot_corner) from
    athc.ini, re-reading whenever the file changes so edits apply while it runs.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        # Lazy import: pulls in pyautogui only when the watcher actually runs.
        from athc.autocontinue.main import auto_continue
    except ImportError as error:
        logger.error(
            "%s: missing dependency %s -- reinstall athc",
            PROG,
            error.name or "pyautogui",
        )
        ctx.exit(1)

    try:
        auto_continue(hot_corner=hot_corner)
    except (ConfigError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    except KeyboardInterrupt:
        # Ctrl-C and the top-left fail-safe both land here; animated goodbye.
        click.echo("\r\nShutting down AutoContinue", nl=False)
        for dot in "....\n":
            time.sleep(0.5)
            click.echo(dot, nl=False)
