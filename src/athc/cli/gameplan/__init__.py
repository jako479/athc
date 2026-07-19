"""`athc gameplan` command group."""

from __future__ import annotations

import click


@click.group()
def gameplan() -> None:
    """Validate and edit Front Page Sports Football Pro '98 gameplans (.pln)."""


from athc.cli.gameplan import check as check  # noqa: E402  (registers the leaf command)
from athc.cli.gameplan import find_play as find_play  # noqa: E402
from athc.cli.gameplan import list_normals as list_normals  # noqa: E402
from athc.cli.gameplan import list_specials as list_specials  # noqa: E402
from athc.cli.gameplan import replace_play as replace_play  # noqa: E402
from athc.cli.gameplan import set_normals as set_normals  # noqa: E402
from athc.cli.gameplan import set_specials as set_specials  # noqa: E402
