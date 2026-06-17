"""`athc config edit` -- open the athc settings file in an editor."""

from __future__ import annotations

import os

import click

from athc.cli.config import config
from athc.config import config_file


@config.command(name="edit")
def edit() -> None:
    """Open athc.ini in an editor, creating it if missing.

    Uses $VISUAL/$EDITOR when set, else the file's associated app (Notepad by default).
    """
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    if os.environ.get("VISUAL") or os.environ.get("EDITOR"):
        click.edit(filename=str(path))
    else:
        click.launch(str(path))
