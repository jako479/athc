"""Shared helpers for `athc profile`: the files a command was given (paths, or
your team's profiles by profile key), the help both share, and the rules.

A profile key (`off1`, `def1`, `off2`, `def2`) stands for one of your team's
four profiles, found through the shared team layer in `_team.py`. An operand
that exists on disk is a path whatever it is called, so `off1.prf`, `.\\off1`
and a folder named `off1` are paths; only a bare word with nothing of its name
in the current folder is a key.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import click

from athc.cli._files import Collected, collect_files, is_glob, named_file
from athc.cli._team import (
    LEAGUE_PATH_KEY,
    PPP_PATH_KEY,
    TEAM_KEY,
    Located,
    Source,
    is_key,
    is_yours,
    load_league_files,
    locate,
    location_hint,
    option_team,
    path_not_set,
    ppp_folder,
    setting_team,
    team_files,
    team_not_set,
)
from athc.config import LEAGUE_FILE, load_league_config, resolve_league
from athc.errors import (
    AthcError,
    ConfigFileError,
    missing_reason,
)
from athc.profile import ProfileRules, load_rules

__all__ = [
    "Collected",
    "Expanded",
    "TeamProfiles",
    "collect_files",
    "epilog",
    "expand_names",
    "is_glob",
    "is_key",
    "load_rules_or_raise",
    "named_file",
    "one_profile",
    "team_profiles",
]

TEAM_HELP = "Team the profile keys refer to"

TEAM_REQUIRES_KEY = "--team requires a profile key (off1, def1, off2 or def2)."
TEAM_NOT_SET = team_not_set("--team or a .prf file")
PATH_NOT_SET = path_not_set("a .prf file")
LEAGUE_LOCATION_HINT = location_hint("a .prf file")

# The \b lines keep Click from joining each block's lines into one paragraph.
_KEYS = """\b
Profile keys, for your team's profiles:
  off1  1st-half offense    def1  1st-half defense
  off2  2nd-half offense    def2  2nd-half defense
"""


def epilog(*examples: str) -> str:
    """The help's closing blocks: what each profile key means, then the
    examples, one per line."""
    lines = "".join(f"  {example}\n" for example in examples)
    return f"{_KEYS}\nExamples:\n\n\b\n{lines}"


def load_rules_or_raise(rule_files: Iterable[Path]) -> ProfileRules:
    """The league's profile rules. ConfigFileError when none are configured; a
    rules file that cannot be read or parsed raises its own error."""
    files = list(rule_files)
    if not files:
        raise ConfigFileError(
            "No rules configured. Add profile.toml to the league folder."
        )
    return load_rules(files)


@dataclass(frozen=True, slots=True)
class TeamProfiles:
    """Where the team's profiles that a command's keys name are, and whether
    each is there."""

    located: dict[str, Located]
    """By key, lowercase; only the keys the command was given."""

    yours: bool
    """The team `team` names: a profile missing at its league location gets
    the `ppp_path` hint."""

    def find(self, raw: str) -> Located:
        return self.located[raw.casefold()]

    def missing(self, located: Located) -> str:
        """Why a profile that is not there cannot be used, in Windows' words,
        with the hint when it is yours and at its league location."""
        reason = missing_reason(located.path)
        if self.yours and located.source is Source.LEAGUE:
            return f"{reason} {LEAGUE_LOCATION_HINT}"
        return reason


@dataclass(frozen=True, slots=True)
class Expanded:
    """A command's operands with each key replaced by its profile: `paths`
    for `collect_files`, in order, and a `FAIL` line in `errors` for each key
    whose profile is not there."""

    paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def team_profiles(
    operands: Sequence[str], *, team: str | None, league: str | None
) -> TeamProfiles | None:
    """The setup for the keys among all of a command's operands, in the order
    its errors show: `--team` with no key is a usage error; `--league` is
    resolved whenever given; with a key, `team` in league.toml (before
    `path`), `path`, the league files and the team match. None when no
    operand is a key: then nothing past `--league` is read."""
    keys = {raw.casefold() for raw in operands if is_key(raw)}
    if team is not None and not keys:
        raise click.UsageError(TEAM_REQUIRES_KEY)
    if league is not None:
        resolve_league(league)
    if not keys:
        return None
    config = load_league_config(league)
    league_file = config.dir / LEAGUE_FILE
    setting = config.string(TEAM_KEY)
    if team is None and setting is None:
        raise ConfigFileError(TEAM_NOT_SET, league_file)
    league_path = config.path(LEAGUE_PATH_KEY)
    if league_path is None:
        raise ConfigFileError(PATH_NOT_SET, league_file)
    files = load_league_files(config.name, league_path)
    if team is not None:
        number = option_team(team, files)
    else:
        assert setting is not None  # checked above: no --team needs `team`
        number = setting_team(setting, files, league_file)
    yours = is_yours(setting, files, number)
    # `ppp_path` holds your team's files only; another team's are where the
    # league file puts them.
    ppp_path = config.path(PPP_PATH_KEY) if yours else None
    if ppp_path is not None:
        ppp_path = ppp_folder(ppp_path)
    entries = dict(team_files(files.lg2.teams[number - 1], "profile"))
    located = {key: locate(entries[key], ppp_path, league_path) for key in keys}
    return TeamProfiles(located, yours)


def expand_names(operands: Iterable[str], profiles: TeamProfiles | None) -> Expanded:
    """`operands` with each key replaced by its profile's path; a key whose
    profile is not there becomes a `FAIL` line instead, never a path, so
    `collect_files` never sees it. Every other operand passes through."""
    expanded = Expanded()
    for raw in operands:
        if profiles is None or not is_key(raw):
            expanded.paths.append(raw)
            continue
        located = profiles.find(raw)
        if located.exists:
            expanded.paths.append(str(located.path))
        else:
            expanded.errors.append(f"{located.path}: {profiles.missing(located)}")
    return expanded


def one_profile(raw: str, profiles: TeamProfiles | None) -> Path:
    """The one profile the operand `raw` names: `named_file` for a path; for
    a key its profile, AthcError (with the hint, when it applies) when that
    is not there."""
    if profiles is None or not is_key(raw):
        return named_file(raw)
    located = profiles.find(raw)
    if not located.exists:
        raise AthcError(profiles.missing(located), located.path)
    return located.path
