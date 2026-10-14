"""`athc config edit` -- open athc.ini or league.toml in its default app."""

from __future__ import annotations

import os

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.config import FILE_HELP, config, file_callback, settings_file
from athc.config import config_file
from athc.errors import FILE_NOT_FOUND, ConfigFileError

EXAMPLES = """Examples:

\b
  athc config edit
  athc config edit league.toml
  athc config edit --league PCFL
"""


@config.command(name="edit", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument("file", required=False, callback=file_callback, help=FILE_HELP)
@league_option
def edit(file: str | None, league: str | None) -> None:
    """Open athc.ini or league.toml in its default app.

    A missing athc.ini is created empty first.
    """
    path = settings_file(file, league)
    if not path.exists():
        if path != config_file():
            # A league.toml comes with its league; athc does not repair one.
            raise ConfigFileError(FILE_NOT_FOUND, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    # Called directly: click.launch swallows the error, so a file Windows
    # cannot open would look done. Its OSError reaches main as a FAIL line.
    os.startfile(str(path))
