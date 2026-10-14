"""`athc gameplan set-normals` — set the 64 normal slots of a .pln from a play list."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    build_pool,
    epilog,
    one_game_plan,
    parse_play_list,
    read_play_list,
    require_a_key,
)
from athc.config import resolve_league
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


@gameplan.command(
    name="set-normals",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan set-normals off1 plays.txt",
        "athc gameplan set-normals DEN-OGP1.pln -",
    ),
)
@click.argument("game_plan", help="A .pln file or a game plan key.")
@click.argument(
    "input_file",
    type=click.Path(path_type=Path, allow_dash=True),
    help="Play list, one name per line (- reads the console).",
)
@team_option(TEAM_HELP)
@league_option
@click.pass_context
def set_normals(
    ctx: click.Context,
    game_plan: str,
    input_file: Path,
    team: str | None,
    league: str | None,
) -> None:
    """Set the 64 normal plays from a play list.

    Lines starting with :: are comments; run athc gameplan check afterward.
    """
    require_a_key(team, [game_plan])
    if league is not None:
        resolve_league(league)  # a league that does not exist fails first
    target = one_game_plan(game_plan, team, league)
    from_console = str(input_file) == "-"
    text = sys.stdin.read() if from_console else read_play_list(input_file)
    # A list from the console has no file to name.
    source = "" if from_console else f"{input_file}: "
    plays = parse_play_list(text)
    if len(plays) > NORMAL_COUNT:
        raise AthcError(
            f"Too many plays ({len(plays)}). The most is {NORMAL_COUNT}.",
            None if from_console else input_file,
        )
    config = load_config(league, rule_files=())  # no gameplan rules needed
    pool = build_pool(config.play_path, config.categories)

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

    gp = read_gameplan(target)
    try:
        updated = apply_normal_plays(gp, plays, pool)
    except InvalidPlayListError as error:
        for invalid in error.invalid_plays:
            console.fail(f"{source}line {invalid.line}: {invalid.reason}")
        ctx.exit(2)
    write_gameplan(updated, target)
    count = sum(1 for p in updated.normal_plays if p is not None)
    console.ok(f"{target}: {count} normal play(s)")
