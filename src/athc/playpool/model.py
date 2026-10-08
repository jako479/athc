"""In-memory data model for a play pool.

Typed play records that wrap a parsed .ply file, and the `PlayPool` that holds
them. A record's `category` comes from the play file (`play_file.category`, an
`fbpro98_play` enum member). Folder-derived attributes (offense `screen`; defense
`defensive_front`) and filename-derived ones (`rollout`, `qb_draw`, `pass_logic`)
are set by the reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from athc.fbpro98_play import PlayCategory, PlayFile
from athc.playpool.rules import StrPath


class PassLogic(Enum):
    """How an offensive pass play reads the field."""

    TIMED = "Timed"
    CHECK_RECEIVERS = "Check Receivers"


class DefensiveFront(Enum):
    """Defensive personnel front."""

    THREE_FOUR = "3-4"
    FOUR_THREE = "4-3"
    TWO_DL = "2-DL"  # two down linemen (the Run-and-Shoot front)


@dataclass(frozen=True)
class Play:
    """A play: its name plus the parsed .ply file behind it."""

    name: str
    play_file: PlayFile

    @property
    def file_path(self) -> Path:
        return self.play_file.file_path

    @property
    def category(self) -> PlayCategory:
        """The play's category; `UNKNOWN_CATEGORY` if the code is unrecognized."""
        return self.play_file.category

    @property
    def play_category(self) -> int:
        return self.play_file.play_category

    @property
    def special_category(self) -> int:
        return self.play_file.special_category

    @property
    def user_category(self) -> int:
        return self.play_file.user_category

    def _base_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        file_path = self.file_path
        if relative_to is not None:
            file_path = file_path.relative_to(relative_to)
        return {
            "name": self.name,
            "file_path": file_path.as_posix(),
            "category": self.category.long,
            "play_category": self.play_category,
            "special_category": self.special_category,
            "user_category": self.user_category,
        }

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        return self._base_dict(relative_to=relative_to)


@dataclass(frozen=True)
class OffensivePlay(Play):
    """An offensive play: `screen` from the folder, the rest from filename rules."""

    screen: bool = False
    rollout: bool = False
    qb_draw: bool = False
    pass_logic: PassLogic | None = None

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        result = self._base_dict(relative_to=relative_to)
        result["screen"] = self.screen
        result["rollout"] = self.rollout
        result["qb_draw"] = self.qb_draw
        result["pass_logic"] = self.pass_logic.value if self.pass_logic else None
        return result


@dataclass(frozen=True)
class DefensivePlay(Play):
    """A defensive play: `defensive_front` from the folder when present."""

    defensive_front: DefensiveFront | None = None

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        result = self._base_dict(relative_to=relative_to)
        result["defensive_front"] = (
            self.defensive_front.value if self.defensive_front else None
        )
        return result


@dataclass(frozen=True)
class SpecialTeamsPlay(Play):
    """A special-teams play; adds no fields beyond the base."""


class PlayPool:
    """All plays under a root directory, indexed by name and split by side."""

    def __init__(self, root_dir: StrPath) -> None:
        self.root_dir = Path(root_dir)
        self.offensive_plays: list[OffensivePlay] = []
        self.defensive_plays: list[DefensivePlay] = []
        self.special_teams_plays: list[SpecialTeamsPlay] = []
        # The reader's warnings, kept word for word so a caller like playpool
        # check can print and count them as findings.
        self.issues: list[str] = []
        self._plays_by_name: dict[str, Play] = {}

    def find_by_name(self, name: str) -> Play | None:
        return self._plays_by_name.get(name.upper())

    def add(self, play: OffensivePlay | DefensivePlay | SpecialTeamsPlay) -> None:
        """File `play` under its side and index it by name (case-insensitive); a
        repeated name replaces the earlier entry in the index."""
        if isinstance(play, OffensivePlay):
            self.offensive_plays.append(play)
        elif isinstance(play, DefensivePlay):
            self.defensive_plays.append(play)
        elif isinstance(play, SpecialTeamsPlay):
            self.special_teams_plays.append(play)
        else:
            raise TypeError(
                f"not an offensive, defensive or special-teams play: {play!r}"
            )
        self._plays_by_name[play.name.upper()] = play


__all__ = [
    "DefensiveFront",
    "DefensivePlay",
    "OffensivePlay",
    "PassLogic",
    "Play",
    "PlayPool",
    "SpecialTeamsPlay",
]
