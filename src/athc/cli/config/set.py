"""`athc config set` -- write one setting into athc.ini, keeping its comments."""

from __future__ import annotations

import click

from athc.cli.config import config
from athc.config import ConfigFileError, LeagueError, league_dir, set_config_value

KNOWN_KEYS = ("league",)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def set_(key: str, value: str) -> None:
    """Set KEY to VALUE in athc.ini (comments are kept).

    Keys: league -- the league used when --league / ATHC_LEAGUE is not given
    (VALUE must be a folder under leagues\\ in the config dir).
    """
    if key not in KNOWN_KEYS:
        raise click.BadParameter(
            f"unknown key '{key}'; known keys: {', '.join(KNOWN_KEYS)}",
            param_hint="KEY",
        )
    if key == "league":
        try:
            league_dir(value)
        except LeagueError as error:
            raise click.BadParameter(str(error), param_hint="VALUE") from error
    try:
        set_config_value(key, value)
    except ConfigFileError as error:
        raise click.UsageError(str(error)) from error
    click.echo(f"Set {key} = {value}")
