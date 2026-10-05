"""`athc gameplan list-specials` — dump the custom special-teams plays from a .pln."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import emit_play_list, special_play_lines
from athc.fbpro98_gameplan import InvalidGamePlanError, read_gameplan

PROG = "athc gameplan list-specials"
logger = logging.getLogger(__name__)


@gameplan.command(name="list-specials", context_settings=CONTEXT_SETTINGS)
@click.argument("gameplan_path", metavar="gameplan", type=click.Path(path_type=Path))
@click.argument(
    "output_path",
    metavar="[output_file]",
    required=False,
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.pass_context
def list_specials(
    ctx: click.Context,
    gameplan_path: Path,
    output_path: Path | None,
) -> None:
    """List the custom special-teams plays from gameplan, in source order.

    Writes them, under a `:: <source>` header line, to output_file, or by default
    to <name>.specials.txt next to gameplan; an existing file is replaced. An
    output_file of `-` prints them instead. Empty special slots are blank lines.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        gp = read_gameplan(str(gameplan_path))
    except (OSError, InvalidGamePlanError, ValueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    lines = special_play_lines(gp)
    if output_path is None:
        output_path = gameplan_path.with_name(f"{gameplan_path.stem}.specials.txt")
    ctx.exit(
        emit_play_list(
            lines,
            None if str(output_path) == "-" else output_path,
            gameplan_path,
            prog=PROG,
            logger=logger,
            noun="special",
        )
    )
