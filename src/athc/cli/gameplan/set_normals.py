"""`athc gameplan set-normals` — set the 64 normal slots of a .pln from a play list."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, named_file, parse_play_list
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from athc.gameplan.config import load_config
from athc.gameplan.writer import (
    InvalidPlay,
    InvalidPlayListError,
    apply_normal_plays,
)

NORMAL_COUNT = GamePlan.NUMBER_NORMAL_PLAYS


@gameplan.command(name="set-normals", context_settings=CONTEXT_SETTINGS)
@click.argument("gameplan_path", metavar="gameplan", type=click.Path(path_type=Path))
@click.argument(
    "play_list_path",
    metavar="play_list",
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.option("-q", "--quiet", is_flag=True, help="Suppress the success message.")
@league_option
@click.pass_context
def set_normals(
    ctx: click.Context,
    gameplan_path: Path,
    play_list_path: Path,
    quiet: bool,
    league: str | None,
) -> None:
    """Replace the 64 normal slots of gameplan from play_list.

    A play_list of `-` reads the list from the console. One play name per line;
    `::` comment lines and ` ::` trailers are ignored. The league's play pool
    resolves names; run `check` to validate the result.
    """
    gameplan_path = named_file(gameplan_path)
    from_console = str(play_list_path) == "-"
    if from_console:
        text = sys.stdin.read()
    else:
        text = named_file(play_list_path).read_text(encoding="utf-8-sig")
    # A list from the console has no file to name.
    source = "" if from_console else f"{play_list_path}: "
    plays = parse_play_list(text)
    if len(plays) > NORMAL_COUNT:
        raise AthcError(
            f"Too many plays ({len(plays)}). The most is {NORMAL_COUNT}.",
            None if from_console else play_list_path,
        )
    config = load_config(league, rule_files=())  # no gameplan rules needed
    pool = build_pool(
        config.play_path, config.playpool_rules, config.categories, config.league_file
    )

    specials = [
        InvalidPlay(
            play.line, f"'{play.name}' is a special teams play. Use set-specials."
        )
        for play in plays
        if (r := pool.find_by_name(play.name)) is not None
        and r.play_file.is_special_teams
    ]
    if specials:
        for invalid in specials:
            console.fail(f"{source}line {invalid.line}: {invalid.reason}")
        ctx.exit(2)

    gp = read_gameplan(gameplan_path)
    try:
        updated = apply_normal_plays(gp, plays, pool)
    except InvalidPlayListError as error:
        for invalid in error.invalid_plays:
            console.fail(f"{source}line {invalid.line}: {invalid.reason}")
        ctx.exit(2)
    write_gameplan(updated, gameplan_path)
    count = sum(1 for p in updated.normal_plays if p is not None)
    if not quiet:
        console.ok(f"{gameplan_path}: {count} normal play(s)")
