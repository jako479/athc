"""`athc autocontinue` — auto-click the Front Page Sports Football Pro '98
'Continue' button between plays."""

from __future__ import annotations

import math

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand
from athc.console import console
from athc.errors import AthcError

# The \b line keeps Click from joining the examples into one line.
EXAMPLES = """Examples:

\b
  athc autocontinue
  athc autocontinue --delay 3
  athc autocontinue --dry-run
"""


def _zero_or_more(
    ctx: click.Context, param: click.Parameter, value: float | None
) -> float | None:
    # NaN and infinity are not delays: time.sleep refuses them.
    if value is not None and not 0 <= value < math.inf:
        raise click.BadParameter(f"must be 0 or more, got {value}.", ctx, param)
    return value


@click.command(
    name="autocontinue",
    cls=AthcCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=EXAMPLES,
)
@click.option(
    "--delay",
    type=float,
    default=None,
    metavar="SECONDS",
    callback=_zero_or_more,
    help=(
        "Seconds to wait before each click. Overrides delay_before_continue in "
        "athc.ini (1.0 by default)."
    ),
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Report the button each time it is found; never move the mouse or click.",
)
@click.option(
    "--hot-corner/--no-hot-corner",
    default=None,
    help=(
        "Stop when the mouse hits the top-left corner. "
        "Overrides hot_corner in athc.ini (on by default)."
    ),
)
def autocontinue(delay: float | None, dry_run: bool, hot_corner: bool | None) -> None:
    """Click the game's Continue button between plays.

    Watches the primary monitor while the game is the active window and clicks
    Continue each time it appears, after a short delay. Runs until you press
    Ctrl+C or move the mouse to the top-left corner of the screen.
    """
    try:
        # Lazy import: pulls in pyautogui only when the watcher actually runs.
        from athc.autocontinue.main import auto_continue
    except ImportError as error:
        raise AthcError(
            f"Missing {error.name or 'pyautogui'}. Reinstall athc."
        ) from error

    try:
        auto_continue(
            hot_corner=hot_corner,
            delay=delay,
            dry_run=dry_run,
            progress=console.progress,
            warn=console.warn,
            report=console.result,
        )
    except KeyboardInterrupt:
        # Ctrl+C and the top-left hot corner both land here: the normal stop.
        console.result("Stopped.")
