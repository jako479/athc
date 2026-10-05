"""`athc config path` -- print the path to the athc settings file."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.config import config
from athc.config import config_file


@config.command(name="path", context_settings=CONTEXT_SETTINGS)
def path() -> None:
    """Print the full path to athc.ini (it need not exist yet)."""
    click.echo(str(config_file()))
