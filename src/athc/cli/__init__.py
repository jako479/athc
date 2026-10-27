from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from importlib.metadata import entry_points, version
from typing import Any, NoReturn

import click

# The team layer's names another package may use, re-exported so nothing
# outside athc imports the private module.
from athc.cli._team import TEAM_KEY as TEAM_KEY
from athc.cli._team import resolve_team as resolve_team
from athc.cli._team import team_not_set as team_not_set
from athc.console import console
from athc.errors import AthcError, error_line
from athc.log import logger, setup_logging

ENTRY_POINT_GROUP = "athc.commands"

# Passed to every command and group, not just the root: Click caches a command's
# help option the first time it runs, so one that ran on its own (no `athc`
# parent to inherit from) would otherwise keep only `--help`.
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _with_period(error: click.UsageError) -> click.UsageError:
    """`error` with its message ending in a period, as every athc line does.
    Click leaves it off a few of its own, like `Got unexpected extra argument
    (x)`; a message that already ends a sentence, or Click's `(Did you mean
    ...?)` hint, is kept as is."""
    message = error.format_message()
    if message.endswith((".", "?", "!", "?)")):
        return error
    return click.UsageError(f"{message}.", error.ctx)


class _OnePlace(click.Command):
    """The one place errors become a line, a log entry and an exit code.

    `main` opens the run log, writes the start line, runs Click in
    non-standalone mode and handles whatever comes out, then writes the end
    line and exits. It sits on the command classes rather than only in the
    `athc` script so a command run under `CliRunner` behaves exactly like the
    real process. Click calls a subcommand's `invoke`, not its `main`, so it
    runs once per process.

    Click's Windows wildcard expansion is off: it would expand every word
    before the command sees it, so a name like `Season [2029]` or a pattern
    meant for one argument could turn into several files. athc expands
    wildcards itself, only in the arguments that take them.
    """

    def main(  # type: ignore[override]
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = False,
        **extra: Any,
    ) -> NoReturn:
        try:
            setup_logging()
        except OSError as error:  # the log folder cannot be written: no run
            console.fail(error_line(error))
            sys.exit(2)
        argv = list(args) if args is not None else sys.argv[1:]
        logger.info("%s", " ".join(["athc", version("athc"), *argv]))
        try:
            returned = super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )
            code = returned if isinstance(returned, int) else 0
        except click.exceptions.NoArgsIsHelpError as error:  # bare `athc`
            error.show()  # the help, on stderr, exit 2; the log gets one line
            logger.error("no command given; help shown")
            code = error.exit_code
        except click.ClickException as error:  # usage: Click's own text, 2
            if isinstance(error, click.UsageError):
                error = _with_period(error)
            error.show()
            logger.error("%s", error.format_message())
            code = error.exit_code
        except click.Abort:  # Ctrl-C (Click turns KeyboardInterrupt into it)
            console.fail("Interrupted.")
            code = 130
        except (AthcError, OSError) as error:  # an expected failure
            console.fail(error_line(error))
            code = 2
        except Exception:  # a bug
            console.unexpected()
            code = 2
        logger.info("exit %d", code)
        sys.exit(code)

    def format_arguments(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Click's "Positional arguments" section, each argument under its bare
        name (`PATH`, not `[PATH]...`): the usage line already says which are
        optional or repeat. The usage line and Click's error hints keep its own
        form."""
        rows = [
            (param.human_readable_name, record[1])
            for param in self.get_params(ctx)
            if isinstance(param, click.Argument)
            and (record := param.get_help_record(ctx)) is not None
        ]
        if rows:
            with formatter.section("Positional arguments"):
                formatter.write_dl(rows)


class AthcCommand(_OnePlace):
    """A command run through the one place; its help is Click's own, but for
    the bare argument names in "Positional arguments"."""


class CommandGroup(_OnePlace, click.Group):
    """A group run through the one place, whose subcommands (and subgroups) are
    built the same way."""

    command_class = AthcCommand
    group_class = type  # subgroups use this same class


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
        metavar="NAME",
        help="League to use (default: the one set with 'athc config set league').",
    )(f)


def team_option(head: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Shared `--team NAME` option, added by each command that finds a team's
    files. `head` says what the team is for on that command; the tail naming
    the default reads the same everywhere."""
    return click.option(
        "--team",
        default=None,
        metavar="NAME",
        help=f"{head} (default: 'team' in league.toml).",
    )


@click.group(cls=AthcGroup, context_settings=CONTEXT_SETTINGS, no_args_is_help=True)
@click.version_option(package_name="athc")
def cli() -> None:
    """Assistant to the Head Coach.

    Tools for Front Page Sports Football Pro '98 coaches and league managers.
    """


def main() -> None:
    """The `athc` console script; `python -m athc` calls it too. Everything
    that follows is `_OnePlace.main` on the root group."""
    cli()
