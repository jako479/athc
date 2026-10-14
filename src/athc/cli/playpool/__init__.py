"""`athc playpool` command group."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, CommandGroup


@click.group(cls=CommandGroup, context_settings=CONTEXT_SETTINGS)
def playpool() -> None:
    """Check the play pool (.ply)."""


from athc.cli.playpool import check as check  # noqa: E402  (registers the leaf command)
