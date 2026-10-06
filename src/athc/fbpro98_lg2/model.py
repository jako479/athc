"""In-memory data model for FbPro98 .lg2 league files.

Each team's eight coaching files, nested by half, then side. A location is a
Windows path relative to the game folder, kept as a string like the gameplan
library's play filenames; split it with `PureWindowsPath`.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    """Full in-memory representation of a custom league's `.lg2` file."""

    teams: tuple[TeamFiles, ...]
    """One entry per team, in file order: the league's `.lge` team order (see specs/lg2.md)."""
