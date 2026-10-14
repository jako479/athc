"""`athc standings` — show a league's standings."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.config import LEAGUE_FILE, LEAGUE_PATH_KEY, load_league_config
from athc.console import console
from athc.errors import ConfigFileError
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Method, Standings
from athc.standings import VIEWS, View, render

# The default first, the order the usage line lists them in.
_METHODS: tuple[Method, ...] = ("scheduler", "game", "nfl")
# One fixed coin toss, so the same league file always shows the same order.
_SEED = 0


@click.command(name="standings", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.option(
    "--view",
    type=click.Choice(VIEWS),
    default="game",
    show_default=True,
    help="The game's standings screen, or an ESPN standings tab.",
)
@click.option(
    "--method",
    type=click.Choice(_METHODS),
    default="scheduler",
    show_default=True,
    help="Tie-breakers: the scheduler's, the game's or the NFL's.",
)
@league_option
def standings(view: View, method: Method, league: str | None) -> None:
    """Show the league's standings as played so far.

    Reads the league's <league>.lge from the folder `path` names in its
    league.toml.

    \b
      --view game         the game's standings screen
      --view league       every team, numbered (ESPN's League tab)
      --view conference   each conference, numbered (ESPN's Conference tab)
      --view division     each division (ESPN's Division tab)
    """
    config = load_league_config(league)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(
            f"No {LEAGUE_PATH_KEY} for the league. Set {LEAGUE_PATH_KEY} in this file.",
            config.dir / LEAGUE_FILE,
        )
    lge = read_lge(config.name, folder)
    ranked = Standings(lge, method=method, seed=_SEED)
    for line in render(view, lge, ranked, config.name):
        console.print(line)
