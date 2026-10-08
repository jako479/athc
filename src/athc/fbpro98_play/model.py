"""In-memory data model for FbPro98 .ply play files.

Defines the types the reader produces (PlayerHeader, PlayFile) and the play
categories: four per-side enums (offense, defense, special-offense,
special-defense), each member carrying its on-disk code and the long game name
(league labels live in `labels.py`). `resolve_category` names a category from
raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PlayCategory:
    """A play category: on-disk `code` and the `long` game name. Subclassed by
    the four per-side category enums."""

    code: int
    long: str

    def __init__(self, code: int, long: str) -> None:
        self.code = code
        self.long = long

    @property
    def is_run(self) -> bool:
        return "Run" in self.long

    @property
    def is_pass(self) -> bool:
        return "Pass" in self.long


class OffensiveCategory(PlayCategory, Enum):
    """Offensive play categories, keyed by `user_category`."""

    RUN_RIGHT = (0x01, "Run Right")
    PASS_SHORT_RIGHT = (0x03, "Pass Short Right")
    RUN_LEFT = (0x05, "Run Left")
    PASS_SHORT_LEFT = (0x07, "Pass Short Left")
    RUN_MIDDLE = (0x09, "Run Middle")
    PASS_SHORT_MIDDLE = (0x0B, "Pass Short Middle")
    RAZZLE_DAZZLE_RUN = (0x0D, "Razzle Dazzle Run")
    RAZZLE_DAZZLE_PASS = (0x0F, "Razzle Dazzle Pass")
    PASS_MEDIUM_RIGHT = (0x13, "Pass Medium Right")
    PASS_MEDIUM_LEFT = (0x17, "Pass Medium Left")
    PASS_MEDIUM_MIDDLE = (0x1B, "Pass Medium Middle")
    PASS_LONG_RIGHT = (0x23, "Pass Long Right")
    PASS_LONG_LEFT = (0x27, "Pass Long Left")
    PASS_LONG_MIDDLE = (0x2B, "Pass Long Middle")
    GOAL_LINE_RUN = (0x31, "Goal Line Run")
    GOAL_LINE_PASS = (0x33, "Goal Line Pass")
    USER_SPECIFIC = (0xFF, "User Specific")


class DefensiveCategory(PlayCategory, Enum):
    """Defensive play categories, keyed by `user_category`."""

    RUN_RIGHT = (0x00, "Run Right")
    PASS_SHORT = (0x02, "Pass Short")
    RUN_LEFT = (0x04, "Run Left")
    RUN_MIDDLE = (0x08, "Run Middle")
    RUN_DAZZLE = (0x0C, "Run Dazzle")
    PASS_DAZZLE = (0x0E, "Pass Dazzle")
    PASS_MEDIUM = (0x12, "Pass Medium")
    PASS_LONG = (0x22, "Pass Long")
    GOAL_LINE_RUN = (0x30, "Goal Line Run")
    GOAL_LINE_PASS = (0x32, "Goal Line Pass")
    USER_SPECIFIC = (0xFE, "User Specific")


class SpecialOffensiveCategory(PlayCategory, Enum):
    """Kicking-side special-teams categories, keyed by `special_category`.
    11 and 12 are the clock plays, which exist only on offense."""

    FIELD_GOAL_PAT = (0x01, "Field Goal/PAT")
    KICKOFF = (0x02, "Kickoff")
    PUNT = (0x03, "Punt")
    ONSIDE_KICK = (0x04, "Onside Kick")
    FAKE_FG_RUN = (0x05, "Fake FG Run")
    FAKE_FG_PASS = (0x06, "Fake FG Pass")
    FAKE_PUNT_RUN = (0x07, "Fake Punt Run")
    FAKE_PUNT_PASS = (0x08, "Fake Punt Pass")
    FREE_KICK = (0x09, "Free Kick")
    SQUIB_KICK = (0x0A, "Squib Kick")
    RUN_CLOCK = (0x0B, "Run Clock")
    STOP_CLOCK = (0x0C, "Stop Clock")


class SpecialDefensiveCategory(PlayCategory, Enum):
    """Receiving-side special-teams categories, keyed by `special_category`."""

    FIELD_GOAL_PAT_DEFENSE = (0x01, "Field Goal/PAT Defense")
    KICK_RETURN = (0x02, "Kick Return")
    PUNT_RETURN = (0x03, "Punt Return")
    ONSIDE_RETURN = (0x04, "Onside Return")
    FAKE_FG_RUN_DEFENSE = (0x05, "Fake FG Run Defense")
    FAKE_FG_PASS_DEFENSE = (0x06, "Fake FG Pass Defense")
    FAKE_PUNT_RUN_DEFENSE = (0x07, "Fake Punt Run Defense")
    FAKE_PUNT_PASS_DEFENSE = (0x08, "Fake Punt Pass Defense")
    FREE_KICK_RETURN = (0x09, "Free Kick Return")
    SQUIB_RETURN = (0x0A, "Squib Return")


_OFFENSE_BY_CODE = {c.code: c for c in OffensiveCategory}
_DEFENSE_BY_CODE = {c.code: c for c in DefensiveCategory}
_SPECIAL_OFFENSE_BY_CODE = {c.code: c for c in SpecialOffensiveCategory}
_SPECIAL_DEFENSE_BY_CODE = {c.code: c for c in SpecialDefensiveCategory}

UNKNOWN_CATEGORY = PlayCategory(-1, "Unknown")
"""Returned for a play whose category code isn't recognized."""


def resolve_category(
    play_category: int, special_category: int, user_category: int
) -> PlayCategory:
    """Resolve a play's category from its raw bytes; `UNKNOWN_CATEGORY` for an
    unrecognized code.

    The byte-level namer: used by `PlayFile.category` and by callers holding
    category bytes without a `PlayFile` (e.g. a gameplan or profile play). Side
    comes from `play_category` parity; special teams use `special_category`;
    normal plays look up `user_category`, falling back to `user_category & 0x3F`
    (the top two bits vary within a category).
    """
    offense = play_category % 2 == 1
    if special_category != 0:
        table = _SPECIAL_OFFENSE_BY_CODE if offense else _SPECIAL_DEFENSE_BY_CODE
        return table.get(special_category) or UNKNOWN_CATEGORY
    table = _OFFENSE_BY_CODE if offense else _DEFENSE_BY_CODE
    return (
        table.get(user_category) or table.get(user_category & 0x3F) or UNKNOWN_CATEGORY
    )


@dataclass(frozen=True, slots=True)
class PlayerHeader:
    """One player's header within a .ply play file.

    Parsed from the leading bytes of each player record. See specs/ply.md
    section 2.4 for the on-disk layout.
    """

    offset: int
    """Record offset relative to 0x08 (end of the P95 header)."""

    rank: int
    """Depth-chart rank (u8 at +0x00)."""

    player_type: int
    """Record type (u8 at +0x01). Observed: 0x01 pre-snap, 0x02 after-snap,
    0x04 kicking."""

    position: int
    """Position code (u16 at +0x02). Observed: 0x20 QB, 0x12 C, 0x11 T,
    0x10 G, 0x81 TE, 0x80 WR, 0x42 HB."""


@dataclass(frozen=True, slots=True)
class PlayFile:
    """Parsed FbPro98 .ply play file.

    See specs/ply.md for the on-disk binary format these attributes correspond to.
    """

    file_path: Path
    """Path the play was read from; Path("<buffer>") when parsed from raw
    bytes with no path."""

    stream_length: int
    """P95 data-stream size in bytes (file size minus the 8-byte header)."""

    play_category: int
    """Category byte at 0x1E; bit 0 = side of ball
    (odd = offense/kicking, even = defense/receiving)."""

    special_category: int
    """Special-teams category at 0x1F; 0 = not special teams."""

    user_category: int
    """User category byte at 0x20; bits 5-0 = play category, bits 7-6 vary."""

    player_offsets: tuple[int, ...]
    """u16 player-record offsets from 0x08, in slot order:
    QB, C, LT, LG, RG, RT, TE, RWR, LWR, LHB, RHB."""

    player_headers: tuple[PlayerHeader, ...]
    """One PlayerHeader per slot, same order as player_offsets."""

    @property
    def is_offensive(self) -> bool:
        """True if this is an offensive (or kicking-side) play."""
        return self.play_category % 2 == 1

    @property
    def is_defensive(self) -> bool:
        """True if this is a defensive (or receiving-side) play."""
        return self.play_category % 2 == 0

    @property
    def is_special_teams(self) -> bool:
        """True if this is a special-teams play (any non-zero special_category)."""
        return self.special_category != 0

    @property
    def category(self) -> PlayCategory:
        """This play's category; `UNKNOWN_CATEGORY` if the code is unrecognized."""
        return resolve_category(
            self.play_category, self.special_category, self.user_category
        )

    @property
    def category_name(self) -> str:
        """The long game-category name ('Unknown' if the code is unrecognized)."""
        return self.category.long
