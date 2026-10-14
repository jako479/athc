"""In-memory data model for FbPro98 .lg2 league files.

Each team's eight coaching files, nested by half, then side. A location is a
Windows path relative to the game folder, kept as a string like the gameplan
library's play filenames; split it with `PureWindowsPath`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LeagueType(Enum):
    """Which of the three .lg2 layouts a file has; see docs/formats/lg2.md."""

    CUSTOM = "custom"
    MODERN_STOCK = "modern stock"
    OLD_STOCK = "old stock"


@dataclass(frozen=True, slots=True)
class FilePair:
    """One side's coaching profile and game plan for one half."""

    profile: str
    """`.prf` location, `folder\\filename` (or just `filename`)."""

    gameplan: str
    """`.pln` location, `folder\\filename` (or just `filename`)."""


@dataclass(frozen=True, slots=True)
class HalfFiles:
    """Offense and defense files for one half."""

    offense: FilePair
    defense: FilePair


@dataclass(frozen=True, slots=True)
class TeamFiles:
    """One team's files for both halves."""

    first_half: HalfFiles
    second_half: HalfFiles


@dataclass(frozen=True, slots=True)
class Lg2File:
    """Full in-memory representation of a `.lg2` league file."""

    league_type: LeagueType
    """Custom, modern stock or old stock, judged by the first file entry's
    folder field (see the README)."""

    teams: tuple[TeamFiles, ...]
    """One entry per team, in file order: the league's `.lge` team order (see
    docs/formats/lg2.md)."""
