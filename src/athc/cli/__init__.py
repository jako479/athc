from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

import click

ENTRY_POINT_GROUP = "athc.commands"


class AthcGroup(click.Group):
    """Click group that lazy-loads subcommands registered via entry points."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._plugins_loaded = False

    def _load_plugins(self) -> None:
        if self._plugins_loaded:
            return
        for ep in entry_points(group=ENTRY_POINT_GROUP):
            self.add_command(ep.load(), name=ep.name)
        self._plugins_loaded = True

    def list_commands(self, ctx: click.Context) -> list[str]:
        self._load_plugins()
        return super().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        self._load_plugins()
        return super().get_command(ctx, cmd_name)


@click.group(
    cls=AthcGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.version_option(package_name="athc")
def cli() -> None:
    """Assistant to the Head Coach -- tools for FbPro98 coaches and league managers."""


def league_option(f: Callable[..., Any]) -> Callable[..., Any]:
    """Shared `--league` option for tools that operate on league-specific data."""
    return click.option(
        "--league",
        envvar="ATHC_LEAGUE",
        default=None,
        help="League name (matches a section like [league.PNFL] in athc.ini).",
    )(f)


def main() -> None:
    cli()
