"""`athc config` command group, and what its verbs share: the KEY and FILE
matching and the file `path`, `edit` and `reveal` act on."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, CommandGroup
from athc.config import config_file, league_file, resolve_league

# The settings `get` prints and `set` writes, in their canonical spelling.
KEYS = ("league", "path", "play_path", "team", "ppp_path")
# The files `path`, `edit` and `reveal` take.
FILE_NAMES = ("athc.toml", "league.toml")
FILE_HELP = (
    "athc.toml or league.toml (default: athc.toml, or league.toml when --league "
    "is given)."
)

# The \b line keeps Click from joining the examples into one line.
EXAMPLES = """Examples:

\b
  athc config set league PCFL
  athc config edit league.toml
"""


@click.group(cls=CommandGroup, context_settings=CONTEXT_SETTINGS, epilog=EXAMPLES)
def config() -> None:
    """Show or change athc settings (athc.toml, league.toml).

    Both live in your settings folder, %LOCALAPPDATA%\\athc.
    """


def _match(word: str, names: tuple[str, ...]) -> str | None:
    """The name `word` spells, without case, or None."""
    return next((name for name in names if name.casefold() == word.casefold()), None)


def _not_one_of(word: str, names: tuple[str, ...]) -> str:
    """Click's own `Choice` wording for a word that is none of `names`."""
    return click.Choice(names).get_invalid_choice_message(word, None)


def key_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """KEY matched without case; the canonical spelling is what `set` writes.

    A plain argument rather than a `Choice`, whose placeholder would list the
    keys in the usage line. Click adds the argument's own hint, `'KEY'`.
    """
    key = _match(value, KEYS)
    if key is None:
        raise click.BadParameter(_not_one_of(value, KEYS))
    return key


def file_callback(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> str | None:
    """FILE matched without case; None when it was left out."""
    if value is None:
        return None
    name = _match(value, FILE_NAMES)
    if name is None:
        # Click's own hint for an optional argument would read '[FILE]'.
        raise click.BadParameter(_not_one_of(value, FILE_NAMES), param_hint="'FILE'")
    return name


def settings_file(file: str | None, league: str | None) -> Path:
    """The file `path`, `edit` and `reveal` act on: FILE, else `league.toml`
    when `--league` names a league, else `athc.toml`. A named league must exist
    even with `athc.toml`; a blank `--league` counts as not given, as in
    `resolve_league`."""
    named = bool((league or "").strip())
    if file is None:
        file = "league.toml" if named else "athc.toml"
    if file == "league.toml":
        return league_file(league)
    if named:
        resolve_league(league)  # checked only: athc.toml has nothing per league
    return config_file()


from athc.cli.config import edit as edit  # noqa: E402  (registers the leaf command)
from athc.cli.config import get as get  # noqa: E402
from athc.cli.config import path as path  # noqa: E402
from athc.cli.config import reveal as reveal  # noqa: E402
from athc.cli.config import set as set  # noqa: E402
