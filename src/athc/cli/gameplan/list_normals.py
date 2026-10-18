"""`athc gameplan list-normals` — dump the 64 normal plays from a .pln."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli._files import resolve_output
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    emit_play_list,
    epilog,
    normal_play_lines,
    one_game_plan,
    require_a_key,
)
from athc.config import load_league_config, resolve_league
from athc.fbpro98_gameplan import read_gameplan


@gameplan.command(
    name="list-normals",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan list-normals off1",
        "athc gameplan list-normals DEN-OGP1.pln plays.txt --sort category",
    ),
)
@click.argument("game_plan", help="A .pln file or a game plan key.")
@click.argument(
    "output",
    required=False,
    help=(
        "File or folder for the list (default: <name>.normals.txt next to "
        "GAME_PLAN; use '-' for stdout)."
    ),
)
@click.option(
    "--sort",
    type=click.Choice(["slot", "name", "category"]),
    default="slot",
    help="Sort the list (default: slot).",
)
@team_option(TEAM_HELP)
@league_option
def list_normals(
    game_plan: str,
    output: str | None,
    sort: str,
    team: str | None,
    league: str | None,
) -> None:
    """List the 64 normal plays in a game plan.

    An existing output file is replaced.
    """
    require_a_key(team, [game_plan])
    if league is not None:
        resolve_league(league)  # a league that does not exist fails first
    source = one_game_plan(game_plan, team, league)
    labels = load_league_config(league).categories
    gp = read_gameplan(source)
    lines = normal_play_lines(gp, sort=sort, labels=labels)
    default = source.with_name(f"{source.stem}.normals.txt")
    emit_play_list(
        lines,
        None if output == "-" else resolve_output(output, default, ".txt"),
        source,
        noun="normal",
    )
