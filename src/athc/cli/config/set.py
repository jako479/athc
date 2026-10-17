"""`athc config set` -- write one setting, keeping the file's comments:
`league` into athc.toml, the other keys into the league's league.toml."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.config import config, key_callback
from athc.config import LeagueError, league_dir, set_config_value, set_league_value
from athc.console import console

EXAMPLES = """Examples:

\b
  athc config set league PCFL
  athc config set play_path C:\\SIERRA\\FBPRO98\\PNFL
  athc config set team Denver
"""


@config.command(name="set", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument(
    "key",
    callback=key_callback,
    help="Setting to change: league, path, play_path, team or ppp_path.",
)
@click.argument("value", help="New value.")
@league_option
def set_(key: str, value: str, league: str | None) -> None:
    """Set a value in athc.toml or league.toml.

    league goes in athc.toml, the other keys in the league's league.toml.
    """
    if key == "league":
        written = _set_league(value, league)
    else:
        written = set_league_value(league, key, value)
    console.ok(f"{written}: {key} = {value}")


def _set_league(value: str, league: str | None) -> Path:
    """Write `[athc] league`; the folder is checked first, so `get league`
    never meets a name with nothing behind it."""
    if league is not None:
        raise click.UsageError("--league cannot be used with set league.")
    try:
        league_dir(value)
    except LeagueError as error:
        # Click's "Invalid value for 'VALUE': " starts the sentence.
        text = str(error)
        raise click.BadParameter(
            text[:1].lower() + text[1:], param_hint="'VALUE'"
        ) from error
    return set_config_value("league", value)  # an unreadable athc.toml is a FAIL
