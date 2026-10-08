"""`athc gameplan list-normals` — dump the 64 normal plays from a .pln."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import emit_play_list, normal_play_lines
from athc.config import ConfigFileError, LeagueError, load_league_config
from athc.fbpro98_gameplan import InvalidGamePlanError, read_gameplan

PROG = "athc gameplan list-normals"
logger = logging.getLogger(__name__)


@gameplan.command(name="list-normals", context_settings=CONTEXT_SETTINGS)
@click.argument("gameplan_path", metavar="gameplan", type=click.Path(path_type=Path))
@click.argument(
    "output_path",
    metavar="[output_file]",
    required=False,
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.option(
    "--sort",
    type=click.Choice(["slot", "name", "category"]),
    default="slot",
    show_default=True,
    help="Order of the listed plays.",
)
@league_option
@click.pass_context
def list_normals(
    ctx: click.Context,
    gameplan_path: Path,
    output_path: Path | None,
    sort: str,
    league: str | None,
) -> None:
    """List the 64 normal plays from gameplan.

    Writes them, under a `:: <source>` header line, to output_file, or by default
    to <name>.normals.txt next to gameplan; an existing file is replaced. An
    output_file of `-` prints them instead. `--sort slot` keeps slot positions
    (empty slots blank); `name` drops blanks; `category` drops blanks and groups
    the plays by category, each group under a `::` header with the league's
    category name (RL, RunLeft, ...; the game's name where the league has none).
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        labels = load_league_config(league).categories
    except (LeagueError, ConfigFileError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    try:
        gp = read_gameplan(str(gameplan_path))
    except (OSError, InvalidGamePlanError, ValueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    lines = normal_play_lines(gp, sort=sort, labels=labels)
    if output_path is None:
        output_path = gameplan_path.with_name(f"{gameplan_path.stem}.normals.txt")
    ctx.exit(
        emit_play_list(
            lines,
            None if str(output_path) == "-" else output_path,
            gameplan_path,
            prog=PROG,
            logger=logger,
            noun="normal",
        )
    )
