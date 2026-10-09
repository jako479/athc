"""`athc playpool check` — check the play pool for misfiled, duplicate and
invalid plays."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.playpool import playpool
from athc.config import LEAGUE_FILE, LeagueError, load_league_config
from athc.console import console
from athc.errors import AthcError, ConfigFileError
from athc.fbpro98_play import CategoryLabels
from athc.playpool import read_play_pool


@playpool.command(name="check", context_settings=CONTEXT_SETTINGS)
@click.argument(
    "play_dir", metavar="[play_dir]", required=False, type=click.Path(path_type=Path)
)
@league_option
@click.pass_context
def check(ctx: click.Context, play_dir: Path | None, league: str | None) -> None:
    """Check the play pool: plays in the wrong folder, duplicate play names, and
    invalid play files.

    play_dir defaults to the league's play_path. A given play_dir needs no
    league, but a league that resolves still lends its category names to the
    folders; without one no folder name means a category. The messages are the
    warnings other commands show when they load the pool.
    """
    labels = CategoryLabels()
    try:
        cfg = load_league_config(league)
    except LeagueError:
        # A given play_dir needs no league, but a league the user named must exist.
        if play_dir is None or league:
            raise
    else:
        labels = cfg.categories
        if play_dir is None:
            play_dir = cfg.path("play_path")
            if play_dir is None:
                raise ConfigFileError(
                    f"no play_path for the league; set play_path in "
                    f"{cfg.dir / LEAGUE_FILE}"
                )

    if not play_dir.exists():
        raise AthcError("not found", play_dir)
    if not play_dir.is_dir():
        raise AthcError("not a directory", play_dir)
    pool = read_play_pool(play_dir, labels=labels)

    # The pool's issues are this command's findings: results, on stdout.
    for message in pool.issues:
        console.print(message)
    if pool.issues:
        console.print()
    plays = (
        len(pool.offensive_plays)
        + len(pool.defensive_plays)
        + len(pool.special_teams_plays)
    )
    console.result(
        f"{plays} play(s) checked in '{play_dir}', {len(pool.issues)} issue(s)"
    )
    ctx.exit(1 if pool.issues else 0)
