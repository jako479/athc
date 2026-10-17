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
  athc autocontinue --continue-pause 3
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
    "--continue-pause",
    type=float,
    default=None,
    metavar="SECONDS",
    callback=_zero_or_more,
    help=(
        "Seconds to wait before each Continue click. Overrides "
        "continue_pause in athc.toml (1.0 by default)."
    ),
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Report what it finds each time; never move the mouse or click.",
)
@click.option(
    "--hot-corner/--no-hot-corner",
    default=None,
    help=(
        "Stop when the mouse hits the top-left corner. "
        "Overrides hot_corner in athc.toml (on by default)."
    ),
)
def autocontinue(
    continue_pause: float | None, dry_run: bool, hot_corner: bool | None
) -> None:
    """Click the game's Continue button between plays.

    Clicks Return at halftime and stops at the end of the game.
    """
    try:
        # Lazy import: pulls in pyautogui only when the watcher actually runs.
        from athc.autocontinue.main import HotCornerStop, auto_continue
    except ImportError as error:
        raise AthcError(
            f"Missing {error.name or 'pyautogui'}. Reinstall athc."
        ) from error

    # Ctrl+C and the top-left hot corner raise; the end of the game returns.
    # All three are the normal stop; the first two say which it was, the end
    # of the game has said so already.
    try:
        auto_continue(
            hot_corner=hot_corner,
            continue_pause=continue_pause,
            dry_run=dry_run,
            progress=console.progress,
            warn=console.warn,
            warn_traced=lambda message: console.warn(message, exc_info=True),
            report=console.result,
        )
    except HotCornerStop:
        console.progress("Hot corner hit.")
    except KeyboardInterrupt:
        console.progress("Ctrl+C pressed.")
    console.result("Stopped.")
