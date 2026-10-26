"""In-memory data model for FbPro98 .pln gameplan files.

Defines the mutable types that the reader produces and the writer consumes:
ProfileType, CustomPlayRef, StockPlayRef, SpecialSlot, and the top-level GamePlan
dataclass. A game plan is edited by assignment; `GamePlan.validate()` checks
everything the file format imposes.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import IntEnum
from pathlib import PureWindowsPath
from typing import ClassVar

from athc.fbpro98_gameplan.schema import (
    DEFAULT_AUDIBLE,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_STOCK_PLAY_BODY,
    S98_EXPECTED_DATA,
)
from athc.fbpro98_play import UNKNOWN_CATEGORY, resolve_category


class ProfileType(IntEnum):
    """Whether a gameplan is for defense (0) or offense (1). Encoded in J95 data."""

    DEFENSE = 0
    OFFENSE = 1


@dataclass(slots=True)
class CustomPlayRef:
    """A user-authored play stored as a filename reference (`stock_flag = 0`).

    See docs/formats/pln.md section 2.3 for the on-disk layout.
    """

    filename: str
    """Filename of the .ply file backing this play, as written on disk (Windows
    path conventions; usually all-uppercase 8.3 form like `MYPLAY.PLY`)."""

    play_category: int
    """Game category byte; bit 0 = side of ball
    (odd = offense/kicking, even = defense/receiving)."""

    special_category: int
    """Special category; 0 = not a special play, 1-12 = the special categories
    (11 Run Clock and 12 Stop Clock are offense-only stock plays)."""

    user_category: int
    """User category byte; bits 5-0 = play category, bits 7-6 vary."""

    @property
    def name(self) -> str:
        """Display name: the filename's stem (without path or extension)."""
        return PureWindowsPath(self.filename).stem


@dataclass(slots=True)
class StockPlayRef:
    """A built-in play referenced from `STOCK98.MAP` (`stock_flag = 1`).

    See docs/formats/pln.md section 2.3 for the on-disk layout.
    """

    play_name: str
    """Eight-character ASCII play name as stored on disk (with trailing
    nulls/spaces stripped)."""

    map_offset: int
    """Byte offset into `STOCK98.MAP` where this play's bytes begin."""

    map_size: int
    """Number of bytes this play occupies inside `STOCK98.MAP`."""

    play_category: int
    """Game category byte; bit 0 = side of ball
    (odd = offense/kicking, even = defense/receiving)."""

    special_category: int
    """Special category; 0 = not a special play, 1-12 = the special categories
    (11 Run Clock and 12 Stop Clock are offense-only stock plays)."""

    user_category: int
    """User category byte; bits 5-0 = play category, bits 7-6 vary."""

    @property
    def name(self) -> str:
        """Display name: the stock play name (same as `play_name`)."""
        return self.play_name


PlayRef = CustomPlayRef | StockPlayRef


@dataclass(slots=True)
class SpecialSlot:
    """One special category's two slots: the coach's `custom` play and the
    game's `stock` play. Categories 11-12 (Run Clock, Stop Clock) have no custom
    slot on disk, so their `custom` is always None."""

    custom: CustomPlayRef | None = None
    stock: StockPlayRef | None = None


# The file's field widths: a category byte, the stock play name, its map
# offset (u32) and size (u16), and a record's offset in the offsets table
# (u16, counted from the table's start).
_BYTE_MAX = 0xFF
_PLAY_NAME_LENGTH = 8
_MAP_OFFSET_MAX = 0xFFFF_FFFF
_MAP_SIZE_MAX = 0xFFFF
_RECORD_OFFSET_MAX = 0xFFFF
_MAP_FILENAME = S98_EXPECTED_DATA.rstrip(b"\x00").decode("ascii")


@dataclass(slots=True)
class GamePlan:
    """Full in-memory representation of a `.pln` gameplan file.

    See docs/formats/pln.md for the on-disk binary format. Edit by assignment;
    `validate()` checks the structural invariants (slot counts, side-of-ball
    consistency, special-category alignment, stock-only clock categories) and
    the field widths, and the writer runs it before packing.
    """

    NUMBER_NORMAL_PLAYS: ClassVar[int] = 64
    """Number of normal (non-special) play slots."""

    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 12
    """Special categories 1-12; `special_plays` has one slot per category."""

    CUSTOM_SPECIAL_CATEGORIES: ClassVar[range] = range(1, 11)
    """Categories that have a custom slot. 11 (Run Clock) and 12 (Stop Clock)
    are stock-only and exist only in offense gameplans."""

    NUMBER_PLAY_SLOTS: ClassVar[int] = 86
    """Total slot count in the G95 offsets table (64 normal + 22 special)."""

    profile_type: ProfileType
    """Whether this gameplan is for offense or defense. Determines clock-category
    population and file-size parity."""

    normal_plays: list[PlayRef | None]
    """The 64 normal play slots. None indicates an unused slot."""

    special_plays: list[SpecialSlot]
    """One SpecialSlot per special category; index = category - 1."""

    audible: bytes = b"\x00\x01\x02\x03"
    """Four-byte audible play reference stored in the G95 block."""

    map_filename: str = "STOCK98.MAP"
    """Filename of the stock-play map this gameplan references (stored in the
    S98 block)."""

    def validate(self) -> None:
        """Check everything the file format imposes; ValueError on the first
        problem, naming the slot or field and the value.

        The profile type; the counts (64 normal slots, 12 special
        categories); each special slot's types, category alignment and the
        stock-only clock categories by side; each play's side parity; no
        special play in a normal slot; then each play's fields: category
        bytes that name a known category, an ASCII filename without NUL, a
        stock play name of at most 8 ASCII characters, its map offset (u32)
        and size (u16); the audible bytes and the map filename the game
        writes; and the play records fitting the offsets table (u16).
        """
        if self.profile_type not in (ProfileType.DEFENSE, ProfileType.OFFENSE):
            raise ValueError(f"profile_type: Must be 0 or 1, got {self.profile_type}")
        if len(self.normal_plays) != self.NUMBER_NORMAL_PLAYS:
            raise ValueError(
                f"normal_plays must have exactly {self.NUMBER_NORMAL_PLAYS} "
                f"entries, got {len(self.normal_plays)}"
            )
        if len(self.special_plays) != self.NUMBER_SPECIAL_CATEGORIES:
            raise ValueError(
                f"special_plays must have exactly {self.NUMBER_SPECIAL_CATEGORIES} "
                f"entries, got {len(self.special_plays)}"
            )

        for category, slot in enumerate(self.special_plays, start=1):
            self._check_slot(category, slot)

        expected_parity = 1 if self.is_offense else 0
        for label, play in self._filled_plays():
            if play.play_category % 2 != expected_parity:
                play_side = "offensive" if play.play_category % 2 == 1 else "defensive"
                gp_side = "OFFENSE" if expected_parity == 1 else "DEFENSE"
                raise ValueError(
                    f"{label}: play has {play_side} "
                    f"play_category=0x{play.play_category:02X}, "
                    f"but profile_type is {gp_side}"
                )

        for i, play in enumerate(self.normal_plays):
            if play is None:
                continue
            if play.special_category != 0:
                raise ValueError(
                    f"Normal slot {i} contains a special play "
                    f"(special_category={play.special_category}); "
                    f"only non-special plays allowed in normal slots"
                )

        for label, play in self._filled_plays():
            _check_play_fields(label, play)
        if self.audible != DEFAULT_AUDIBLE:
            raise ValueError(
                f"audible: Must be {DEFAULT_AUDIBLE.hex(' ')}, "
                f"got {self.audible.hex(' ')}"
            )
        if self.map_filename != _MAP_FILENAME:
            raise ValueError(
                f"map_filename: Must be {_MAP_FILENAME}, got {self.map_filename}"
            )
        self._check_offsets()

    def _check_offsets(self) -> None:
        """Each record's offset in the table, counted from the table's start,
        must fit its u16: the records before it set it."""
        records: list[tuple[str, PlayRef | None]] = [
            (f"Normal slot {i}", play) for i, play in enumerate(self.normal_plays)
        ]
        for category, slot in enumerate(self.special_plays, start=1):
            if category in self.CUSTOM_SPECIAL_CATEGORIES:
                records.append((f"Special category {category} custom", slot.custom))
            records.append((f"Special category {category} stock", slot.stock))
        offset = G95_OFFSETS_TABLE.size
        for label, play in records:
            if play is None:
                continue
            if offset > _RECORD_OFFSET_MAX:
                raise ValueError(
                    f"{label}: Record offset must be at most {_RECORD_OFFSET_MAX}, "
                    f"got {offset}"
                )
            offset += _record_size(play)

    def _check_slot(self, category: int, slot: SpecialSlot) -> None:
        # Runtime type checks stay: callers can smuggle the wrong ref type past
        # the annotations (the tests do), and the writer trusts these fields.
        if slot.custom is not None:
            if not isinstance(slot.custom, CustomPlayRef):
                raise ValueError(
                    f"Special category {category}: custom must be CustomPlayRef "
                    f"or None, got {type(slot.custom).__name__}"
                )
            if slot.custom.special_category != category:
                raise ValueError(
                    f"Special category {category}: custom play has "
                    f"special_category={slot.custom.special_category}"
                )
        if slot.stock is not None:
            if not isinstance(slot.stock, StockPlayRef):
                raise ValueError(
                    f"Special category {category}: stock must be StockPlayRef "
                    f"or None, got {type(slot.stock).__name__}"
                )
            if slot.stock.special_category != category:
                raise ValueError(
                    f"Special category {category}: stock play has "
                    f"special_category={slot.stock.special_category}"
                )
        if category in self.CUSTOM_SPECIAL_CATEGORIES:
            return
        if slot.custom is not None:
            raise ValueError(
                f"Special category {category} is stock-only; custom must be None"
            )
        if self.is_offense and slot.stock is None:
            raise ValueError(
                "Offense game plans require a stock play "
                f"in special category {category}"
            )
        if self.is_defense and slot.stock is not None:
            raise ValueError(
                "Defense game plans must not have a play "
                f"in special category {category}"
            )

    def _filled_plays(self) -> Iterator[tuple[str, PlayRef]]:
        """Every filled play with the label error messages use for it."""
        for i, play in enumerate(self.normal_plays):
            if play is not None:
                yield f"Normal slot {i}", play
        for category, slot in enumerate(self.special_plays, start=1):
            if slot.custom is not None:
                yield f"Special category {category} custom", slot.custom
            if slot.stock is not None:
                yield f"Special category {category} stock", slot.stock

    @property
    def is_offense(self) -> bool:
        """True if this gameplan is for offense."""
        return self.profile_type == ProfileType.OFFENSE

    @property
    def is_defense(self) -> bool:
        """True if this gameplan is for defense."""
        return self.profile_type == ProfileType.DEFENSE

    @property
    def custom_special_plays(self) -> list[CustomPlayRef | None]:
        """The custom play of each category in `CUSTOM_SPECIAL_CATEGORIES`, in
        category order (ten entries)."""
        return [
            self.special_plays[c - 1].custom for c in self.CUSTOM_SPECIAL_CATEGORIES
        ]


def _check_play_fields(label: str, play: PlayRef) -> None:
    """One play's fields: its category bytes, which must name a category, and,
    by kind, its filename or its stock name, map offset and map size."""
    for field_name in ("play_category", "special_category", "user_category"):
        _check_range(label, field_name, getattr(play, field_name), 0, _BYTE_MAX)
    category = resolve_category(
        play.play_category, play.special_category, play.user_category
    )
    if category is UNKNOWN_CATEGORY:
        raise ValueError(
            f"{label}: Unrecognized play category "
            f"(play_category=0x{play.play_category:02X}, "
            f"special_category=0x{play.special_category:02X}, "
            f"user_category=0x{play.user_category:02X})"
        )
    if isinstance(play, CustomPlayRef):
        _check_ascii(f"{label}: filename", play.filename)
        return
    _check_ascii(f"{label}: play_name", play.play_name)
    if len(play.play_name) > _PLAY_NAME_LENGTH:
        raise ValueError(
            f"{label}: play_name: Must be at most {_PLAY_NAME_LENGTH} characters, "
            f"got {len(play.play_name)}"
        )
    _check_range(label, "map_offset", play.map_offset, 0, _MAP_OFFSET_MAX)
    _check_range(label, "map_size", play.map_size, 0, _MAP_SIZE_MAX)


def _record_size(play: PlayRef) -> int:
    """The bytes a play's record takes on disk."""
    if isinstance(play, CustomPlayRef):
        return G95_PLAY_HEADER.size + len(play.filename) + 1
    return G95_PLAY_HEADER.size + G95_STOCK_PLAY_BODY.size


def _check_range(label: str, field_name: str, value: int, low: int, high: int) -> None:
    if not low <= value <= high:
        raise ValueError(f"{label}: {field_name}: Must be {low}-{high}, got {value}")


def _check_ascii(location: str, text: str) -> None:
    """A string written as NUL-terminated or NUL-padded ASCII."""
    if not text.isascii():
        raise ValueError(f"{location}: Must be ASCII")
    if "\x00" in text:
        raise ValueError(f"{location}: Must not contain NUL")
