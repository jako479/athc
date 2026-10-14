"""`athc config reveal` -- show athc.ini or league.toml in File Explorer."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.config import FILE_HELP, config, file_callback, settings_file

EXAMPLES = """Examples:

\b
  athc config reveal
  athc config reveal league.toml
"""


@config.command(name="reveal", context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
@click.argument("file", required=False, callback=file_callback, help=FILE_HELP)
@league_option
def reveal(file: str | None, league: str | None) -> None:
    """Show athc.ini or league.toml in File Explorer.

    Selects the file, or opens its folder when the file is missing.
    """
    path = settings_file(file, league)
    folder = path.parent
    folder.mkdir(parents=True, exist_ok=True)  # the settings folder, on a first run
    if path.exists():
        click.launch(str(path), locate=True)  # select the file in Explorer
    else:
        click.launch(str(folder))
