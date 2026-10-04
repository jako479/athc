from __future__ import annotations

import logging
import os
import sys
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


def league_option(f: Callable[..., Any]) -> Callable[..., Any]:
    """Shared `--league` option for tools that operate on league-specific data."""
    return click.option(
        "--league",
        envvar="ATHC_LEAGUE",
        default=None,
        help="League name (a folder under leagues\\ in the config dir).",
    )(f)


@click.group(
    cls=AthcGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.version_option(package_name="athc")
@league_option
@click.pass_context
def cli(ctx: click.Context, league: str | None) -> None:
    """Assistant to the Head Coach.

    Tools for Front Page Sports Football Pro '98 coaches and league managers.
    """
    ctx.ensure_object(dict)["league"] = league


def selected_league(ctx: click.Context) -> str | None:
    """The league named by `athc --league` (or `ATHC_LEAGUE`) on the root group;
    None when the command runs on its own (tests, embedding)."""
    obj = ctx.obj
    return obj.get("league") if isinstance(obj, dict) else None


def main() -> None:
    """CLI entry point. Click handles usage errors and each command handles its
    own failures; this backstop turns any *unexpected* exception into a one-line
    message instead of a traceback. Set `ATHC_DEBUG=1` to re-raise for debugging.
    """
    try:
        cli()
    except Exception as error:
        if os.environ.get("ATHC_DEBUG"):
            raise
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
        logging.getLogger("athc").error(
            "unexpected error: %s (set ATHC_DEBUG=1 for the full traceback)", error
        )
        sys.exit(2)
