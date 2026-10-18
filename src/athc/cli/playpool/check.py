"""`athc playpool check` — check the play pool for misfiled, duplicate and
invalid plays."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.playpool import playpool
from athc.config import (
    LEAGUE_FILE,
    LeagueConfig,
    LeagueError,
    load_league_config,
    not_set_line,
    play_dir,
)
from athc.console import console
from athc.errors import (
    DIRECTORY_INVALID,
    PATH_NOT_FOUND,
    AthcError,
    ConfigFileError,
)
from athc.fbpro98_play import CategoryLabels
from athc.playpool import read_play_pool

EXAMPLES = """Examples:

\b
  athc playpool check
  athc playpool check newplays
"""


@playpool.command(name="check", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument(
    "folder",
    required=False,
    type=click.Path(path_type=Path),
    help="Play pool folder (default: the league's play_path).",
)
@league_option
@click.pass_context
def check(ctx: click.Context, folder: Path | None, league: str | None) -> None:
    """Check the play pool for problems.

    Finds plays in the wrong folder, duplicate names and invalid play files.
    """
    if folder is None:
        cfg = load_league_config(league)
        labels = cfg.categories
        folder = _league_pool(cfg)
    else:
        labels = _folder_labels(league)
        # A folder the user typed: Windows' plain phrases, no setting to point at.
        if not folder.exists():
            raise AthcError(PATH_NOT_FOUND, folder)
        if not folder.is_dir():
            raise AthcError(DIRECTORY_INVALID, folder)
    pool = read_play_pool(folder, labels=labels)

    # The pool's issues are this command's findings: results, on stdout.
    for message in pool.issues:
        console.print(message)
    if pool.issues:
        console.print()
    plays = (
        len(pool.offensive_plays) + len(pool.defensive_plays) + len(pool.special_plays)
    )
    console.result(f"{folder}: {plays} play(s) checked, {len(pool.issues)} issue(s)")
    ctx.exit(1 if pool.issues else 0)


def _league_pool(cfg: LeagueConfig) -> Path:
    """The league's `play_path`, checked by `play_dir()` so a missing pool gets
    the same line, hint included, as every other pool consumer."""
    play_path = cfg.path("play_path")
    if play_path is None:
        raise ConfigFileError(
            not_set_line("play_path", "the folder"), cfg.dir / LEAGUE_FILE
        )
    return play_dir(play_path)


def _folder_labels(league: str | None) -> CategoryLabels:
    """The category labels a given folder's names go by: the league's when one
    resolves, else none."""
    try:
        return load_league_config(league).categories
    except LeagueError:
        # A given folder needs no league, but a league the user named must exist.
        if league:
            raise
        return CategoryLabels()
