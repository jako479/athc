"""`athc config path` -- print the path of athc.ini or league.toml."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.config import FILE_HELP, config, file_callback, settings_file
from athc.console import console

EXAMPLES = """Examples:

\b
  athc config path
  athc config path league.toml
"""


@config.command(name="path", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument("file", required=False, callback=file_callback, help=FILE_HELP)
@league_option
def path(file: str | None, league: str | None) -> None:
    """Print the path of athc.ini or league.toml.

    The file need not exist yet.
    """
    console.print(str(settings_file(file, league)))
