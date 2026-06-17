"""`athc config` command group."""

from __future__ import annotations

import click


@click.group()
def config() -> None:
    """Print the path to athc.ini, edit it, or reveal it in the file manager."""


from athc.cli.config import edit as edit  # noqa: E402  (registers the leaf command)
from athc.cli.config import path as path  # noqa: E402
from athc.cli.config import reveal as reveal  # noqa: E402
