"""`athc check-playpool` — check the play pool for misfiled, duplicate and
invalid plays."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli.gameplan._common import build_pool
from athc.config import load_league_config

PROG = "athc check-playpool"
logger = logging.getLogger(__name__)


@click.command(
    name="check-playpool", cls=AthcCommand, context_settings=CONTEXT_SETTINGS
)
@click.argument(
    "play_dir", metavar="[play_dir]", required=False, type=click.Path(path_type=Path)
)
@league_option
@click.pass_context
def check_playpool(
    ctx: click.Context, play_dir: Path | None, league: str | None
) -> None:
    """Check the play pool: plays in the wrong folder, duplicate play names, and
    invalid play files.

    play_dir defaults to the league's play_path; a given play_dir reads no
    league. The messages are the warnings other commands show when they load
    the pool.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if play_dir is None:
        try:
            cfg = load_league_config(league)
        except ValueError as error:  # LeagueError / ConfigFileError
            logger.error("%s: %s", PROG, error)
            ctx.exit(2)
        play_dir = cfg.path("play_path")
        if play_dir is None:
            logger.error(
                "%s: no play_path for the league; set play_path in %s",
                PROG,
                cfg.dir / "league.ini",
            )
            ctx.exit(2)

    # The pool's warnings are this command's findings, printed below on stdout;
    # silence its log so each one doesn't also show on stderr.
    pool_logger = logging.getLogger("athc.playpool")
    level = pool_logger.level
    pool_logger.setLevel(logging.ERROR)
    try:
        pool = build_pool(play_dir, None, prog=PROG, logger=logger)
    finally:
        pool_logger.setLevel(level)
    if pool is None:
        ctx.exit(2)

    for message in pool.issues:
        click.echo(message)
    if pool.issues:
        click.echo()
    plays = (
        len(pool.offensive_plays)
        + len(pool.defensive_plays)
        + len(pool.special_teams_plays)
    )
    click.echo(f"{plays} play(s) checked in '{play_dir}', {len(pool.issues)} issue(s).")
    ctx.exit(1 if pool.issues else 0)
