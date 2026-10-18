"""`athc gameplan list-specials` — dump the custom special plays from a .pln."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli._files import resolve_output
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    emit_play_list,
    epilog,
    one_game_plan,
    require_a_key,
    special_play_lines,
)
from athc.config import resolve_league
from athc.fbpro98_gameplan import read_gameplan


@gameplan.command(
    name="list-specials",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan list-specials def1 -",
        "athc gameplan list-specials DEN-DGP1.pln spec.txt",
    ),
)
@click.argument("game_plan", help="A .pln file or a game plan key.")
@click.argument(
    "output",
    required=False,
    help=(
        "File or folder for the list (default: GAME_PLAN with .specials.txt, "
        "beside it; - prints it)."
    ),
)
@team_option(TEAM_HELP)
@league_option
def list_specials(
    game_plan: str,
    output: str | None,
    team: str | None,
    league: str | None,
) -> None:
    """List the special plays in a game plan.

    Lists them in game plan order; an existing output file is replaced.
    """
    require_a_key(team, [game_plan])
    if league is not None:
        resolve_league(league)  # nothing is read from it for a path
    source = one_game_plan(game_plan, team, league)
    gp = read_gameplan(source)
    lines = special_play_lines(gp)
    default = source.with_name(f"{source.stem}.specials.txt")
    emit_play_list(
        lines,
        None if output == "-" else resolve_output(output, default, ".txt"),
        source,
        noun="special",
    )
