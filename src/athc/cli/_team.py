"""A team's coaching files: the league's two files, the team a name picks,
where each of its files is, and the lines and checks every command that
looks for them shares.

The `.lg2` lists each team's eight files, the `.lge` its names; team N is the
Nth team of both. A file is found in one of three places, in this order: a
folder the command was given, `ppp_path` in `league.toml` (your team only),
or its league location, `path` joined with the folder the `.lg2` gives it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath
from typing import Literal

import click

from athc.config import LEAGUE_PATH_KEY, LEAGUE_SECTION
from athc.errors import (
    DIRECTORY_INVALID,
    PATH_NOT_FOUND,
    AthcError,
    ConfigFileError,
    StrPath,
)
from athc.fbpro98_lg2 import LeagueType, Lg2File, TeamFiles, read_lg2
from athc.fbpro98_lge import LgeFile, Team, read_lge

__all__ = [
    "LEAGUE_PATH_KEY",
    "PPP_PATH_HINT",
    "PPP_PATH_KEY",
    "TEAM_FILE_NAMES",
    "TEAM_KEY",
    "LeagueFiles",
    "Located",
    "Source",
    "folder_reason",
    "folders",
    "is_key",
    "is_yours",
    "league_file_names",
    "load_league_files",
    "locate",
    "location_hint",
    "option_team",
    "path_not_set",
    "ppp_folder",
    "resolve_team",
    "setting_team",
    "team_files",
    "team_label",
    "team_not_set",
]

# Your team's four files of a kind, in `.lg2` order: 1st-half offense,
# 1st-half defense, 2nd-half offense, 2nd-half defense.
TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")
TEAM_KEY = "team"  # [league] team: your team's name or nickname
PPP_PATH_KEY = "ppp_path"  # [league] ppp_path: where you keep your team's files
PPP_PATH_HINT = "Run 'athc config set ppp_path FOLDER'."


@dataclass(frozen=True, slots=True)
class LeagueFiles:
    """The league's `.lg2` (each team's files) and `.lge` (each team's names),
    with the same teams in the same order: team N is `lg2.teams[N - 1]` and
    `lge.teams[N - 1]`."""

    lg2: Lg2File
    lge: LgeFile


class Source(Enum):
    """Where `locate` looked for a file."""

    FOLDER = "folder"
    """By name, without case, in a folder: `ppp_path` or one the command was
    given."""

    LEAGUE = "league"
    """At its league location: `path` joined with the `.lg2` folder."""


@dataclass(frozen=True, slots=True)
class Located:
    """One team file and whether it is there."""

    path: Path
    """As the folder spells it when it is there, else as the `.lg2` does."""

    exists: bool
    source: Source


def load_league_files(league: str, league_dir: StrPath) -> LeagueFiles:
    """The `<league>.lg2` and `<league>.lge` in `league_dir`, read in that
    order. A stock `.lg2` is an AthcError, checked before the `.lge` is read;
    so are files that list different team counts. A file that cannot be read
    raises its own error."""
    lg2_path = Path(league_dir) / f"{league}.lg2"
    lg2 = read_lg2(league, league_dir)
    if lg2.league_type is not LeagueType.CUSTOM:
        raise AthcError("Stock league not supported.", lg2_path)
    lge = read_lge(league, league_dir)
    if len(lg2.teams) != len(lge.teams):
        raise AthcError(
            f"Lists {len(lg2.teams)} team(s), but {league}.lge has {len(lge.teams)}.",
            lg2_path,
        )
    return LeagueFiles(lg2, lge)


def resolve_team(name: str, lge: LgeFile) -> int:
    """The number (1..N) of the one team `name` names: its team name, its
    nickname or both (`Denver`, `Broncos`, `Denver Broncos`), matched without
    case. AthcError, with no path, when no team or more than one matches; the
    caller puts it where the name came from."""
    wanted = " ".join(name.split()).casefold()
    matches = [
        number
        for number, team in enumerate(lge.teams, 1)
        if wanted and wanted in _names(team)
    ]
    if len(matches) == 1:
        return matches[0]
    shown = name.strip()
    if not matches:
        teams = ", ".join(team.official_name for team in lge.teams)
        raise AthcError(f"No team named '{shown}'. Teams: {teams}.")
    both = _and([lge.teams[number - 1].official_name for number in matches])
    raise AthcError(
        f"'{shown}' matches {both}. Use the nickname, or both names in quotes."
    )


def team_files(
    team: TeamFiles, kind: Literal["profile", "gameplan"]
) -> list[tuple[str, str]]:
    """The team's four files of `kind` as `(name, .lg2 location)` pairs, named
    as `TEAM_FILE_NAMES` and in that order. A file two slots share is listed
    for each, so a caller with fixed slots knows which slot each one fills."""
    pairs = (
        team.first_half.offense,
        team.first_half.defense,
        team.second_half.offense,
        team.second_half.defense,
    )
    return [
        (name, pair.profile if kind == "profile" else pair.gameplan)
        for name, pair in zip(TEAM_FILE_NAMES, pairs, strict=True)
    ]


def locate(file: str, ppp_path: Path | None, league_path: Path) -> Located:
    """Where the `.lg2` location `file` is: by its name, without case, in the
    folder `ppp_path` (`ppp_path`, or a folder the command was given), else at
    its league location under `league_path`. Whether it is there is decided
    here, before anything reads it; a folder that cannot be listed holds no
    files."""
    location = PureWindowsPath(file)
    if ppp_path is not None:
        folder, source = ppp_path, Source.FOLDER
    else:
        folder, source = league_path.joinpath(*location.parent.parts), Source.LEAGUE
    name = _on_disk(folder, location.name)
    if name is None:
        return Located(folder / location.name, False, source)
    return Located(folder / name, True, source)


def is_key(raw: str) -> bool:
    """Whether the operand `raw` names one of your team's four files (`off1`,
    `def1`, `off2`, `def2`, any case): one of the four names with nothing of
    that name in the current folder, which would be that path. A key never
    has an extension or a folder separator."""
    return raw.casefold() in TEAM_FILE_NAMES and not Path(raw).exists()


def team_not_set(way: str) -> str:
    """The line for `team` not set, ending with the command's own way out
    (`--team`, `--team or a .prf file`)."""
    return f"Team is not set. Run 'athc config set team NAME' or pass {way}."


def path_not_set(way: str) -> str:
    """The line for `path` not set, ending with the command's own way out."""
    return (
        f"League files folder is not set. Run 'athc config set path FOLDER' or "
        f"pass {way}."
    )


def location_hint(way: str) -> str:
    """The hint for your team's file missing at its league location, ending
    with the command's own way out."""
    return f"Run 'athc config set ppp_path FOLDER' or pass {way}."


def option_team(name: str, files: LeagueFiles) -> int:
    """The team `--team` names; a usage error when it names none or two."""
    try:
        return resolve_team(name, files.lge)
    except AthcError as error:
        # Click's "Invalid value for '--team': " starts the sentence.
        reason = error.reason[:1].lower() + error.reason[1:]
        raise click.BadParameter(
            reason, ctx=click.get_current_context(), param_hint="'--team'"
        ) from error


def setting_team(name: str, files: LeagueFiles, league_file: Path) -> int:
    """The team `team` in league.toml names; ConfigFileError when it names
    none or two."""
    try:
        return resolve_team(name, files.lge)
    except AthcError as error:
        raise ConfigFileError(
            f"[{LEAGUE_SECTION}] {TEAM_KEY}: {error.reason}", league_file
        ) from error


def is_yours(setting: str | None, files: LeagueFiles, number: int) -> bool:
    """Whether team `number` is the one `team` in league.toml (`setting`)
    names, however `--team` named it: `ppp_path` and its hints are for that
    team alone. A `setting` that names none or two is no team."""
    if setting is None:
        return False
    try:
        return resolve_team(setting, files.lge) == number
    except AthcError:
        return False


def team_label(files: LeagueFiles, number: int) -> str:
    """The team's `.lge` team name, as the lines name a team."""
    team = files.lge.teams[number - 1]
    return team.name or team.official_name


def ppp_folder(path: Path) -> Path:
    """`ppp_path` when it is a folder; else ConfigFileError in Windows' words,
    as `play_path`'s, with the command that sets it."""
    if not path.is_dir():
        reason = DIRECTORY_INVALID if path.exists() else PATH_NOT_FOUND
        raise ConfigFileError(f"{reason} {PPP_PATH_HINT}", path)
    return path


def folder_reason(folder: Path, label: str, noun: str) -> str:
    """Why a team's league folder holds none of its files (`noun`: `files`,
    `game plans`)."""
    if folder.is_dir():
        return f"No {label} {noun}."
    return DIRECTORY_INVALID if folder.exists() else PATH_NOT_FOUND


def folders(top: Path, *, recursive: bool) -> Iterator[Path]:
    """`top`, or with `recursive` every folder in its tree: top first, then
    subfolders by name. A folder that can't be read is skipped, as `os.walk`
    does. Each folder stands alone, since weeks and seasons reuse the same
    file names."""
    for folder, subfolders, _ in top.walk():
        subfolders.sort(key=str.casefold)  # in place: walk descends in this order
        if not recursive:
            subfolders.clear()
        yield folder


def league_file_names(locations: Iterable[str]) -> str:
    """The file names of `.lg2` locations, each once, as the league file first
    spells it, joined for a line: `A.pln, B.pln`."""
    names: dict[str, str] = {}
    for location in locations:
        name = location.rsplit("\\", 1)[-1]
        names.setdefault(name.casefold(), name)
    return ", ".join(names.values())


def _on_disk(folder: Path, name: str) -> str | None:
    """`name` as `folder` spells it, matched without case, when a file of that
    name is there."""
    wanted = name.casefold()
    try:
        # scandir's entries know whether they are files without another call.
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.casefold() == wanted and entry.is_file():
                    return entry.name
    except OSError:
        return None
    return None


def _names(team: Team) -> set[str]:
    return {
        part.casefold()
        for part in (team.name, team.nickname, team.official_name)
        if part
    }


def _and(names: Sequence[str]) -> str:
    """`A and B`, or `A, B and C`."""
    return f"{', '.join(names[:-1])} and {names[-1]}"
