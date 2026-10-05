"""`athc config edit` -- open the athc settings file in its default app."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.config import config
from athc.config import config_file


@config.command(name="edit", context_settings=CONTEXT_SETTINGS)
def edit() -> None:
    """Open athc.ini in its default app, creating it if missing."""
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    click.launch(str(path))
