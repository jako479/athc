"""`athc config set` -- write one setting into athc.ini, keeping its comments."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.config import config
from athc.config import ConfigFileError, LeagueError, league_dir, set_config_value

KNOWN_KEYS = ("league",)


@config.command(name="set", context_settings=CONTEXT_SETTINGS)
@click.argument("key", metavar="key")
@click.argument("value", metavar="value")
def set_(key: str, value: str) -> None:
    """Set key to value in athc.ini (comments are kept).

    Keys: league -- the league used when --league is not given (value must be a
    folder under leagues\\ in the config dir).
    """
    if key not in KNOWN_KEYS:
        raise click.BadParameter(
            f"unknown key '{key}'; known keys: {', '.join(KNOWN_KEYS)}",
            param_hint="key",
        )
    if key == "league":
        try:
            league_dir(value)
        except LeagueError as error:
            raise click.BadParameter(str(error), param_hint="value") from error
    try:
        set_config_value(key, value)
    except ConfigFileError as error:
        raise click.UsageError(str(error)) from error
    click.echo(f"Set {key} = {value}")
