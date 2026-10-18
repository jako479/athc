"""`athc standings` — show a league's standings."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.config import LEAGUE_FILE, LEAGUE_PATH_KEY, load_league_config, not_set_line
from athc.console import console
from athc.errors import ConfigFileError
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Method, Standings
from athc.standings import VIEWS, View, render

# The default first, the order the usage line lists them in.
_METHODS: tuple[Method, ...] = ("scheduler", "game", "nfl")
# One fixed coin toss, so the same league file always shows the same order.
_SEED = 0


EXAMPLES = """Examples:

\b
  athc standings
  athc standings --view division --method nfl
"""


@click.command(
    name="standings",
    cls=AthcCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=EXAMPLES,
)
@click.option(
    "--view",
    type=click.Choice(VIEWS),
    default="game",
    help="Which standings to show (default: game).",
)
@click.option(
    "--method",
    type=click.Choice(_METHODS),
    default="scheduler",
    help=(
        "Tie-breakers: the scheduler's, the game's or the NFL's (default: scheduler)."
    ),
)
@league_option
def standings(view: View, method: Method, league: str | None) -> None:
    """Show the league's standings as played so far.

    Reads the league's .lge from the folder 'path' names in league.toml.
    """
    config = load_league_config(league)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(not_set_line("path"), config.dir / LEAGUE_FILE)
    lge = read_lge(config.name, folder)
    ranked = Standings(lge, method=method, seed=_SEED)
    for line in render(view, lge, ranked, config.name):
        console.print(line)
