"""`athc config reveal` -- reveal athc.ini in the file manager."""

from __future__ import annotations

import click

from athc.cli.config import config
from athc.config import config_dir, config_file


@config.command(name="reveal")
def reveal() -> None:
    """Reveal athc.ini in the file manager, or open its folder if it's absent."""
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    settings = config_file()
    if settings.exists():
        click.launch(str(settings), locate=True)  # select the file in Explorer
    else:
        click.launch(str(directory))
