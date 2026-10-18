"""`athc config get` -- print one setting: the league in use, or a value from
the league's league.toml."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.config import config, key_callback
from athc.config import LEAGUE_FILE, load_league_config, not_set_line, resolve_league
from athc.console import console
from athc.errors import ConfigFileError

# ppp_path is optional, so its absence is noted, never a failure, and the line
# does not ask the coach to set it.
PPP_PATH_NOT_SET = (
    "Game plan and profile folder is not set. "
    "The folders the league file names are used."
)

EXAMPLES = """Examples:

\b
  athc config get league
  athc config get play_path
"""


@config.command(name="get", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument(
    "key",
    callback=key_callback,
    help="Setting to print: 'league', 'path', 'play_path', 'team' or 'ppp_path'.",
)
@league_option
def get(key: str, league: str | None) -> None:
    """Print a setting.

    'league' comes from athc.toml, the other keys from the league's league.toml.
    """
    if key == "league":
        console.print(resolve_league(league))
        return
    cfg = load_league_config(league)
    value = cfg.string(key) if key == "team" else cfg.path(key)
    if value is not None:
        console.print(str(value))
    elif key == "ppp_path":
        console.warn(f"{cfg.dir / LEAGUE_FILE}: {PPP_PATH_NOT_SET}")
    else:
        raise ConfigFileError(not_set_line(key), cfg.dir / LEAGUE_FILE)
