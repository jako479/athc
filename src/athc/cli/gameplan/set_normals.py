"""`athc gameplan set-normals` — set the 64 normal slots of a .pln from a play list."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from athc.cli import league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, make_backup, parse_play_list
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


@gameplan.command(name="set-normals")
@click.argument("gameplan_path", type=click.Path(path_type=Path))
@click.argument("input_path", required=False, type=click.Path(path_type=Path))
@click.option(
    "--stdin", "use_stdin", is_flag=True, help="Read the play list from stdin."
)
@click.option(
    "--no-backup", is_flag=True, help="Do not create a .bak copy before writing."
)
@click.option("-q", "--quiet", is_flag=True, help="Suppress the success message.")
@click.option(
    "--play-path",
    "play_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Play pool directory (overrides the league's PlayPath).",
)
@click.option(
    "--playpool-rules",
    "playpool_rules",
    type=click.Path(path_type=Path),
    default=None,
    help="Playpool rules TOML (overrides the league's PlayPoolRules).",
)
@league_option
@click.pass_context
def set_normals(
    ctx: click.Context,
    gameplan_path: Path,
    input_path: Path | None,
    use_stdin: bool,
    no_backup: bool,
    quiet: bool,
    play_path: Path | None,
    playpool_rules: Path | None,
    league: str | None,
) -> None:
    """Replace the 64 normal slots of GAMEPLAN_PATH from a play list (file or --stdin).

    One play name per line; `::` comment lines and ` ::` trailers are ignored. A
    timestamped .bak is written next to the target first (unless --no-backup). The
    play pool resolves names; run `check` to validate the result.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if use_stdin and input_path is not None:
        raise click.UsageError("provide either INPUT_PATH or --stdin, not both")
    if not use_stdin and input_path is None:
        raise click.UsageError("INPUT_PATH is required (or pass --stdin)")

    try:
        if use_stdin:
            text = sys.stdin.read()
        else:
            assert input_path is not None
            text = input_path.read_text(encoding="utf-8")
        lines = parse_play_list(text)
        if len(lines) > NORMAL_COUNT:
            logger.error(
                "%s: input has %d play(s), max is %d", PROG, len(lines), NORMAL_COUNT
            )
            ctx.exit(1)
        config = load_config(
            league,
            play_path=play_path,
            playpool_rules=playpool_rules,
        )
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

    backup = None if no_backup else make_backup(gameplan_path)
    write_gameplan(updated, gameplan_path)
    count = sum(1 for p in updated.normal_plays if p is not None)
    tail = "" if backup is None else f" Backup: {backup}"
    if not quiet:
        click.echo(f"Updated {gameplan_path}: {count} normal play(s).{tail}")
