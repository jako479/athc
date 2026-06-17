"""`athc profile` command group."""

from __future__ import annotations

import click


@click.group()
def profile() -> None:
    """Validate and edit FbPro98 coaching profiles (.prf)."""


from athc.cli.profile import check as check  # noqa: E402  (registers the leaf command)
from athc.cli.profile import copy as copy  # noqa: E402  (registers the leaf command)
from athc.cli.profile import diff as diff  # noqa: E402  (registers the leaf command)
