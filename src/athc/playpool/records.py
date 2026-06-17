"""Typed play records and the category vocabulary they classify into.

Offensive and defensive plays carry fixed, real attributes (set by the pool's
folder/filename classification): offense — `screen`, `rollout`, `qb_draw`,
`pass_logic`; defense — `defensive_front`. Special-teams plays add nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

from athc.fbpro98_play import PlayFile

RUN_CATEGORIES: Final[frozenset[str]] = frozenset({"GLR", "RL", "RM", "RR"})
PASS_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"GLP", "PLR", "PML", "PMM", "PMR", "PRD", "PSL", "PSM", "PSR"}
)
DEFENSE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "GLpass",
        "GLrun",
        "PassDazzle",
        "PassLong",
        "PassMedium",
        "PassShort",
        "RunDazzle",
        "RunLeft",
        "RunMiddle",
        "RunRight",
    }
)


def play_type(category_name: str | None) -> str | None:
    """'run' | 'pass' | None from a game category name — a game fact, not a rule."""
    if category_name is None:
        return None
    if "Run" in category_name:
        return "run"
    if "Pass" in category_name:
        return "pass"
    return None


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
class PlayRecord:
    """A play: its name plus the parsed .ply file behind it."""

    name: str
    play_file: PlayFile

    @property
    def file_path(self) -> Path:
        return self.play_file.file_path

    @property
    def category(self) -> str | None:
        """Game category name from the play's user_category (offense/defense table)."""
        return self.play_file.category_name

    @property
    def play_type(self) -> str | None:
        """'run' | 'pass' | None, derived from the game category."""
        return play_type(self.play_file.category_name)

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
            "category": self.category,
            "play_category": self.play_category,
            "special_category": self.special_category,
            "user_category": self.user_category,
        }

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        return self._base_dict(relative_to=relative_to)


@dataclass(frozen=True)
class OffensivePlayRecord(PlayRecord):
    """An offensive play, classified from its pool directory and name."""

    pool_category: str = ""
    screen: bool = False
    rollout: bool = False
    qb_draw: bool = False
    pass_logic: PassLogic | None = None

    @property
    def is_run(self) -> bool:
        return self.pool_category in RUN_CATEGORIES

    @property
    def is_pass(self) -> bool:
        return self.pool_category in PASS_CATEGORIES

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        result = self._base_dict(relative_to=relative_to)
        result["pool_category"] = self.pool_category
        result["screen"] = self.screen
        result["rollout"] = self.rollout
        result["qb_draw"] = self.qb_draw
        result["pass_logic"] = self.pass_logic.value if self.pass_logic else None
        return result


@dataclass(frozen=True)
class DefensivePlayRecord(PlayRecord):
    """A defensive play, classified from its pool directory."""

    pool_category: str = ""
    defensive_front: DefensiveFront | None = None

    def to_dict(self, *, relative_to: Path | None = None) -> dict[str, object]:
        result = self._base_dict(relative_to=relative_to)
        result["pool_category"] = self.pool_category
        result["defensive_front"] = (
            self.defensive_front.value if self.defensive_front else None
        )
        return result


@dataclass(frozen=True)
class SpecialTeamsPlayRecord(PlayRecord):
    """A special-teams play; adds no fields beyond the base."""


__all__ = [
    "DEFENSE_CATEGORIES",
    "PASS_CATEGORIES",
    "RUN_CATEGORIES",
    "DefensiveFront",
    "DefensivePlayRecord",
    "OffensivePlayRecord",
    "PassLogic",
    "PlayRecord",
    "SpecialTeamsPlayRecord",
]
