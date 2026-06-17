"""`athc gameplan list-normals` — dump the 64 normal plays from a .pln."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import emit_play_list, normal_play_lines
from athc.fbpro98_gameplan import InvalidGamePlanError, read_gameplan

PROG = "athc gameplan list-normals"
logger = logging.getLogger(__name__)


@gameplan.command(name="list-normals")
@click.argument("gameplan_path", type=click.Path(path_type=Path))
@click.argument("output_path", required=False, type=click.Path(path_type=Path))
@click.option(
    "--sort",
    type=click.Choice(["slot", "name"]),
    default="slot",
    show_default=True,
    help="Order of the listed plays.",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite OUTPUT_PATH if it exists.")
@click.pass_context
def list_normals(
    ctx: click.Context,
    gameplan_path: Path,
    output_path: Path | None,
    sort: str,
    force: bool,
) -> None:
    """List the 64 normal plays from GAMEPLAN_PATH.

    Prints to stdout, or writes to OUTPUT_PATH with a `:: <source>` header line.
    `--sort slot` keeps slot positions (empty slots blank); `name` drops blanks.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        gp = read_gameplan(str(gameplan_path))
    except (OSError, InvalidGamePlanError, ValueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    lines = normal_play_lines(gp, sort=sort)
    ctx.exit(
        emit_play_list(
            lines,
            output_path,
            gameplan_path,
            force=force,
            prog=PROG,
            logger=logger,
            noun="normal",
        )
    )
