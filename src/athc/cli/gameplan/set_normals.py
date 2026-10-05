"""`athc gameplan set-normals` — set the 64 normal slots of a .pln from a play list."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, parse_play_list
from athc.fbpro98_gameplan import (
    GamePlan,
    InvalidGamePlanError,
    read_gameplan,
    write_gameplan,
)
from athc.gameplan.config import ConfigFileError, load_config
from athc.gameplan.writer import InvalidPlayInputError, apply_normal_plays

PROG = "athc gameplan set-normals"
logger = logging.getLogger(__name__)
NORMAL_COUNT = GamePlan.NUMBER_NORMAL_PLAYS


@gameplan.command(name="set-normals", context_settings=CONTEXT_SETTINGS)
@click.argument("gameplan_path", metavar="gameplan", type=click.Path(path_type=Path))
@click.argument(
    "input_path",
    metavar="input_file",
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.option("-q", "--quiet", is_flag=True, help="Suppress the success message.")
@league_option
@click.pass_context
def set_normals(
    ctx: click.Context,
    gameplan_path: Path,
    input_path: Path,
    quiet: bool,
    league: str | None,
) -> None:
    """Replace the 64 normal slots of gameplan from the play list in input_file.

    An input_file of `-` reads the list from the console. One play name per line;
    `::` comment lines and ` ::` trailers are ignored. The league's play pool
    resolves names; run `check` to validate the result.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if str(input_path) == "-":
            text = sys.stdin.read()
        else:
            text = input_path.read_text(encoding="utf-8")
        lines = parse_play_list(text)
        if len(lines) > NORMAL_COUNT:
            logger.error(
                "%s: input has %d play(s), max is %d", PROG, len(lines), NORMAL_COUNT
            )
            ctx.exit(1)
        config = load_config(league, rule_files=())  # no gameplan rules needed
    except (ConfigFileError, ValueError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)

    pool = build_pool(config.play_path, config.playpool_rules, prog=PROG, logger=logger)
    if pool is None:
        ctx.exit(1)

    specials = [
        f"line {i}: '{name}' is a special teams play; use set-specials"
        for i, name in enumerate(lines, start=1)
        if (r := pool.find_by_name(name)) is not None and r.play_file.is_special_teams
    ]
    if specials:
        for err in specials:
            logger.error("%s: %s", PROG, err)
        ctx.exit(1)

    try:
        gp = read_gameplan(str(gameplan_path))
        updated = apply_normal_plays(gp, lines, pool)
    except InvalidPlayInputError as error:
        for violation in error.violations:
            logger.error("%s", violation)
        logger.error(
            "%s: %d invalid input line(s). Gameplan NOT updated.",
            PROG,
            len(error.violations),
        )
        ctx.exit(1)
    except (OSError, InvalidGamePlanError, ValueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)

    write_gameplan(updated, gameplan_path)
    count = sum(1 for p in updated.normal_plays if p is not None)
    if not quiet:
        click.echo(f"Updated {gameplan_path}: {count} normal play(s).")
