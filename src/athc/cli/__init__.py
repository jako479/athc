from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

import click

ENTRY_POINT_GROUP = "athc.commands"

# Passed to every command and group, not just the root: Click caches a command's
# help option the first time it runs, so one that ran on its own (no `athc`
# parent to inherit from) would otherwise keep only `--help`.
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _option_usage(option: click.Option, ctx: click.Context) -> str:
    """One option as the usage line shows it: `[-r]`, `[--sort slot|name]`,
    `--season year` (required, so no brackets), `[--hot-corner | --no-hot-corner]`."""
    if option.secondary_opts:  # an on/off flag pair
        return f"[{option.opts[0]} | {option.secondary_opts[0]}]"
    name = next((o for o in option.opts if not o.startswith("--")), option.opts[0])
    if option.is_flag:
        text = name
    elif isinstance(option.type, click.Choice):
        text = f"{name} {'|'.join(str(c) for c in option.type.choices)}"
    else:
        text = f"{name} {option.make_metavar(ctx)}"
    return text if option.required else f"[{text}]"


def _usage_pieces(command: click.Command, ctx: click.Context) -> list[str]:
    """Each option, help first, then the arguments: the POSIX synopsis style that
    Python's argparse also uses, instead of Click's single `[OPTIONS]`."""
    params = command.get_params(ctx)
    options = [p for p in params if isinstance(p, click.Option) and not p.hidden]
    help_option = command.get_help_option(ctx)
    if help_option in options:
        options.remove(help_option)
        options.insert(0, help_option)
    pieces = [_option_usage(option, ctx) for option in options]
    for param in params:
        if isinstance(param, click.Argument):
            pieces.extend(param.get_usage_pieces(ctx))
    return pieces


def _write_usage(formatter: click.HelpFormatter, prog: str, pieces: list[str]) -> None:
    """Like Click's `write_usage`, but a long line wraps between options, never
    inside one, so `[-d2 pln_file]` stays together."""
    first = f"Usage: {prog}"
    indent = " " * (len(first) + 1)
    lines: list[str] = []
    line = first
    for piece in pieces:
        if line != first and len(line) + 1 + len(piece) > formatter.width:
            lines.append(line)
            line = indent + piece
        else:
            line = f"{line} {piece}"
    lines.append(line)
    formatter.write("\n".join(lines) + "\n")


class AthcCommand(click.Command):
    """A command whose usage line lists each option."""

    def collect_usage_pieces(self, ctx: click.Context) -> list[str]:
        return _usage_pieces(self, ctx)

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        _write_usage(formatter, ctx.command_path, self.collect_usage_pieces(ctx))


class CommandGroup(click.Group):
    """A group whose usage line lists each option, and whose subcommands (and
    subgroups) are built the same way."""

    command_class = AthcCommand
    group_class = type  # subgroups use this same class

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("subcommand_metavar", "command [args]...")
        super().__init__(*args, **kwargs)

    def collect_usage_pieces(self, ctx: click.Context) -> list[str]:
        return [*_usage_pieces(self, ctx), self.subcommand_metavar]

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        _write_usage(formatter, ctx.command_path, self.collect_usage_pieces(ctx))


class AthcGroup(CommandGroup):
    """Root group that lazy-loads subcommands registered via entry points."""

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
    """Shared `--league` option, added by each command that reads league data.

    It sits on the commands rather than the root group because Click only takes a
    group's options before the subcommand name; on the command it can go anywhere
    after it, like `aws s3 ls --profile x`.
    """
    return click.option(
        "--league",
        default=None,
        metavar="name",
        help="League name (a folder under leagues\\ in the config dir).",
    )(f)


@click.group(cls=AthcGroup, context_settings=CONTEXT_SETTINGS, no_args_is_help=True)
@click.version_option(package_name="athc")
def cli() -> None:
    """Assistant to the Head Coach.

    Tools for Front Page Sports Football Pro '98 coaches and league managers.
    """


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
