"""In-memory data model for FbPro98 .ply play files.

Defines the types the reader produces (PlayerHeader, PlayerLogic with its
LogicBox and Command, PlayFile) and the play categories: four per-side enums
(offense, defense, special-offense, special-defense), each member carrying its
on-disk code and the long game name (league labels live in `labels.py`).
`resolve_category` names a category from raw bytes. `PlayFile` also tells the
play attributes its players' logic implies: QB run, timed pass, rollout, and
the defensive front (`DefensiveFront`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from athc.fbpro98_play.schema import (
    COMMAND_CHECK_RECEIVERS,
    COMMAND_MOVE_TO,
    COMMAND_RUN,
    COMMAND_TIMED_PASS,
    POSITION_C,
    POSITION_DE,
    POSITION_DT,
    POSITION_G,
    POSITION_QB,
    POSITION_T,
)


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
    """Kicking-side special categories, keyed by `special_category`.
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
    """Receiving-side special categories, keyed by `special_category`."""

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


class DefensiveFront(Enum):
    """A defensive play's front, from its count of down linemen (DT + DE)."""

    THREE_FOUR = "3-4"
    FOUR_THREE = "4-3"
    TWO_DL = "2-DL"  # two down linemen (the Run-and-Shoot front)


# 3-4 and 4-3 name base run defenses; 2-DL names a pass defense.
_RUN_FRONTS = {3: DefensiveFront.THREE_FOUR, 4: DefensiveFront.FOUR_THREE}
_RUN_FRONT_CATEGORIES = frozenset(
    {
        DefensiveCategory.RUN_LEFT,
        DefensiveCategory.RUN_MIDDLE,
        DefensiveCategory.RUN_RIGHT,
    }
)
_DOWN_LINEMEN = frozenset({POSITION_DT, POSITION_DE})
_OFFENSIVE_LINEMEN = frozenset({POSITION_C, POSITION_G, POSITION_T})
_PASSES = frozenset({COMMAND_TIMED_PASS, COMMAND_CHECK_RECEIVERS})


def resolve_category(
    play_category: int, special_category: int, user_category: int
) -> PlayCategory:
    """Resolve a play's category from its raw bytes; `UNKNOWN_CATEGORY` for an
    unrecognized code.

    The byte-level namer: used by `PlayFile.category` and by callers holding
    category bytes without a `PlayFile` (e.g. a gameplan or profile play). Side
    comes from `play_category` parity; special plays use `special_category`;
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

    Parsed from the leading bytes of each player record. See docs/formats/ply.md
    section 2.1 for the on-disk layout.
    """

    offset: int
    """Record offset relative to 0x08 (end of the P95 header)."""

    rank: int
    """Depth-chart rank (u8 at +0x00)."""

    player_type: int
    """Role bits (u8 at +0x01): 0x01 snaps (defense: Preferred Player), 0x02
    takes the snap, 0x04 kicks;
    docs/formats/ply.md section 4.2."""

    position: int
    """Position code (u16 at +0x02), e.g. 0x20 QB, 0x42 HB, 0x0200 LB;
    docs/formats/ply.md section 4.1."""


@dataclass(frozen=True, slots=True)
class Command:
    """One command in a logic box. See docs/formats/ply.md section 2.4."""

    code: int
    """Command code (u8), e.g. 0x02 Move to, 0x06 Timed pass;
    docs/formats/ply.md section 2.5."""

    arguments: tuple[int, ...]
    """Arguments (i16 each), in order; a spot is x, y."""


@dataclass(frozen=True, slots=True)
class LogicBox:
    """One logic box: where the player stands when its commands start, then the
    commands in order. See docs/formats/ply.md section 2.3."""

    x: int
    """Sideways spot, positive to the offense's right; 90 units = 1 yard."""

    y: int
    """Downfield spot, positive toward the defense."""

    commands: tuple[Command, ...]


@dataclass(frozen=True, slots=True)
class PlayerLogic:
    """One player's logic boxes, before the snap and from the snap on.
    See docs/formats/ply.md section 2.2."""

    pre_snap: tuple[LogicBox, ...] = ()
    """Starts with the player's starting spot."""

    after_snap: tuple[LogicBox, ...] = ()
    """Starts with the player's spot at the snap."""


@dataclass(frozen=True, slots=True)
class PlayFile:
    """Parsed FbPro98 .ply play file.

    See docs/formats/ply.md for the on-disk binary format these attributes
    correspond to.
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
    """Special category at 0x1F; 0 = not a special play."""

    user_category: int
    """User category byte at 0x20; bits 5-0 = play category, bits 7-6 vary."""

    player_offsets: tuple[int, ...]
    """u16 player-record offsets from 0x08, in slot order:
    QB, C, LT, LG, RG, RT, TE, RWR, LWR, LHB, RHB."""

    player_headers: tuple[PlayerHeader, ...]
    """One PlayerHeader per slot, same order as player_offsets."""

    player_logic: tuple[PlayerLogic, ...] = ()
    """One PlayerLogic per slot, same order as player_headers."""

    @property
    def is_offensive(self) -> bool:
        """True if this is an offensive (or kicking-side) play."""
        return self.play_category % 2 == 1

    @property
    def is_defensive(self) -> bool:
        """True if this is a defensive (or receiving-side) play."""
        return self.play_category % 2 == 0

    @property
    def is_special(self) -> bool:
        """True if this is a special play (any non-zero special_category)."""
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

    @property
    def is_timed_pass(self) -> bool:
        """True for an offensive play whose QB throws a Timed pass after the snap."""
        return self._qb_has(COMMAND_TIMED_PASS)

    @property
    def is_qb_run(self) -> bool:
        """True for an offensive play whose QB runs the ball (a Run command) after
        the snap."""
        return self._qb_has(COMMAND_RUN)

    def is_rollout(self, margin: int) -> bool:
        """True for an offensive play whose QB, from the snap up to his Timed
        pass or Check receivers, gets beyond `margin` units (90 = 1 yard)
        outside the outermost offensive lineman (C, G or T) on either side, at
        that lineman's spot at the snap: exactly `margin` outside is not a
        rollout. How far counts is the caller's choice."""
        if not self._is_normal_offense:
            return False
        line = [
            logic.after_snap[0].x
            for logic in self._logic_at(*_OFFENSIVE_LINEMEN)
            if logic.after_snap
        ]
        if not line:
            return False
        left, right = min(line), max(line)
        for qb in self._logic_at(POSITION_QB):
            spots = _spots_before_pass(qb)
            if spots and (min(spots) < left - margin or max(spots) > right + margin):
                return True
        return False

    @property
    def defensive_front(self) -> DefensiveFront | None:
        """A defensive play's front from its down linemen (DT + DE): on a Run
        Left, Run Middle or Run Right play 3 is a 3-4 and 4 a 4-3; on a pass
        play 2 is a 2-DL. None for any other play or count."""
        if not self.is_defensive or self.is_special:
            return None
        count = sum(1 for h in self.player_headers if h.position in _DOWN_LINEMEN)
        category = self.category
        if category in _RUN_FRONT_CATEGORIES:
            return _RUN_FRONTS.get(count)
        if category.is_pass and count == 2:
            return DefensiveFront.TWO_DL
        return None

    @property
    def _is_normal_offense(self) -> bool:
        return self.is_offensive and not self.is_special

    def _logic_at(self, *positions: int) -> list[PlayerLogic]:
        """The logic of every player at one of `positions`, in slot order."""
        # A PlayFile built without logic (player_logic=()) has none to give.
        pairs = zip(self.player_headers, self.player_logic, strict=False)
        return [logic for header, logic in pairs if header.position in positions]

    def _qb_has(self, code: int) -> bool:
        """True for an offensive play whose QB has a command with `code` from
        the snap on."""
        return self._is_normal_offense and any(
            command.code == code
            for logic in self._logic_at(POSITION_QB)
            for box in logic.after_snap
            for command in box.commands
        )


def _spots_before_pass(logic: PlayerLogic) -> list[int] | None:
    """A QB's sideways spots from the snap up to his first Timed pass or Check
    receivers: each box's spot and each Move to. None when he never passes."""
    spots: list[int] = []
    for box in logic.after_snap:
        spots.append(box.x)
        for command in box.commands:
            if command.code in _PASSES:
                return spots
            if command.code == COMMAND_MOVE_TO and command.arguments:
                spots.append(command.arguments[0])
    return None
