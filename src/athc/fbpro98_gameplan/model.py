"""In-memory data model for FbPro98 .pln gameplan files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, CustomPlayRef, StockPlayRef, SpecialSlot, and the top-level GamePlan
dataclass.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import PureWindowsPath
from typing import ClassVar


class ProfileType(IntEnum):
    """Whether a gameplan is for defense (0) or offense (1). Encoded in J95 data."""

    DEFENSE = 0
    OFFENSE = 1


@dataclass(frozen=True, slots=True)
class CustomPlayRef:
    """A user-authored play stored as a filename reference (`stock_flag = 0`).

    See specs/pln.md section 2.3 for the on-disk layout.
    """

    filename: str
    """Filename of the .ply file backing this play, as written on disk (Windows
    path conventions; usually all-uppercase 8.3 form like `MYPLAY.PLY`)."""

    play_category: int
    """Game category byte; bit 0 = side of ball
    (odd = offense/kicking, even = defense/receiving)."""

    special_category: int
    """Special-teams category; 0 = not special teams, 1-12 = the special-teams
    categories (11 Run Clock and 12 Stop Clock are offense-only stock plays)."""

    user_category: int
    """User category byte; bits 5-0 = play category, bits 7-6 vary."""

    @property
    def name(self) -> str:
        """Display name: the filename's stem (without path or extension)."""
        return PureWindowsPath(self.filename).stem


@dataclass(frozen=True, slots=True)
class StockPlayRef:
    """A built-in play referenced from `STOCK98.MAP` (`stock_flag = 1`).

    See specs/pln.md section 2.3 for the on-disk layout.
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
    """Special-teams category; 0 = not special teams, 1-12 = the special-teams
    categories (11 Run Clock and 12 Stop Clock are offense-only stock plays)."""

    user_category: int
    """User category byte; bits 5-0 = play category, bits 7-6 vary."""

    @property
    def name(self) -> str:
        """Display name: the stock play name (same as `play_name`)."""
        return self.play_name


PlayRef = CustomPlayRef | StockPlayRef


@dataclass(frozen=True, slots=True)
class SpecialSlot:
    """One special-teams category's two slots: the coach's `custom` play and the
    game's `stock` play. Categories 11-12 (Run Clock, Stop Clock) have no custom
    slot on disk, so their `custom` is always None."""

    custom: CustomPlayRef | None = None
    stock: StockPlayRef | None = None


@dataclass(frozen=True, slots=True)
class GamePlan:
    """Full in-memory representation of a `.pln` gameplan file.

    See specs/pln.md for the on-disk binary format. Construction validates
    structural invariants (slot counts, side-of-ball consistency, special-
    category alignment, stock-only clock categories) via __post_init__;
    ValueError is raised for any violation.
    """

    NUMBER_NORMAL_PLAYS: ClassVar[int] = 64
    """Number of normal (non-special) play slots."""

    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 12
    """Special-teams categories 1-12; `special_plays` has one slot per category."""

    CUSTOM_SPECIAL_CATEGORIES: ClassVar[range] = range(1, 11)
    """Categories that have a custom slot. 11 (Run Clock) and 12 (Stop Clock)
    are stock-only and exist only in offense gameplans."""

    NUMBER_PLAY_SLOTS: ClassVar[int] = 86
    """Total slot count in the G95 offsets table (64 normal + 22 special)."""

    profile_type: ProfileType
    """Whether this gameplan is for offense or defense. Determines clock-category
    population and file-size parity."""

    normal_plays: tuple[PlayRef | None, ...]
    """The 64 normal play slots. None indicates an unused slot."""

    special_plays: tuple[SpecialSlot, ...]
    """One SpecialSlot per special-teams category; index = category - 1."""

    audible: bytes = b"\x00\x01\x02\x03"
    """Four-byte audible play reference stored in the G95 block."""

    map_filename: str = "STOCK98.MAP"
    """Filename of the stock-play map this gameplan references (stored in the
    S98 block)."""

    def __post_init__(self) -> None:
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
                    f"Normal slot {i} contains a special-teams play "
                    f"(special_category={play.special_category}); "
                    f"only non-special-teams plays allowed in normal slots"
                )

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
                f"Offense gameplans require a stock play in special category {category}"
            )
        if self.is_defense and slot.stock is not None:
            raise ValueError(
                f"Defense gameplans must not have a play in special category {category}"
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
    def custom_special_plays(self) -> tuple[CustomPlayRef | None, ...]:
        """The custom play of each category in `CUSTOM_SPECIAL_CATEGORIES`, in
        category order (ten entries)."""
        return tuple(
            self.special_plays[c - 1].custom for c in self.CUSTOM_SPECIAL_CATEGORIES
        )

    def with_normal_plays(self, plays: Sequence[PlayRef | None]) -> GamePlan:
        """Return a new GamePlan with `plays` placed in the 64 normal slots.

        The original GamePlan is not mutated. Shorter sequences are right-padded
        with None to fill all 64 slots.

        Args:
            plays: Up to 64 plays (or None entries) in slot order.

        Returns:
            A new GamePlan with the updated normal slots; all other fields copied
            from self.

        Raises:
            ValueError: If `plays` contains more than 64 entries, or if the new
                GamePlan would violate any __post_init__ invariant.
        """
        if len(plays) > self.NUMBER_NORMAL_PLAYS:
            raise ValueError(
                f"Expected at most {self.NUMBER_NORMAL_PLAYS} normal plays, "
                f"got {len(plays)}"
            )
        padded = tuple(list(plays) + [None] * (self.NUMBER_NORMAL_PLAYS - len(plays)))
        return replace(self, normal_plays=padded)

    def with_custom_special_plays(
        self, plays: Iterable[CustomPlayRef | None]
    ) -> GamePlan:
        """Return a new GamePlan with `plays` written into the custom slots of
        categories 1-10.

        Each play is placed into the category dictated by its own
        `special_category`. Order doesn't matter. None entries are ignored.
        Categories not covered by any play have their custom slot cleared. Every
        stock slot, the clock categories included, is preserved.

        Args:
            plays: Iterable of CustomPlayRef (or None) values; each play's
                `special_category` selects its destination category.

        Returns:
            A new GamePlan with the updated custom special-teams slots.

        Raises:
            ValueError: If any play's `special_category` is outside
                `CUSTOM_SPECIAL_CATEGORIES`, or if two plays target the same
                category.
        """
        first = self.CUSTOM_SPECIAL_CATEGORIES[0]
        last = self.CUSTOM_SPECIAL_CATEGORIES[-1]
        customs: dict[int, CustomPlayRef] = {}
        for play in plays:
            if play is None:
                continue
            if play.special_category not in self.CUSTOM_SPECIAL_CATEGORIES:
                raise ValueError(
                    f"Play has special_category={play.special_category}, "
                    f"must be {first}..{last}"
                )
            if play.special_category in customs:
                raise ValueError(
                    f"Two custom special plays target "
                    f"special_category={play.special_category}"
                )
            customs[play.special_category] = play
        new_special = tuple(
            replace(slot, custom=customs.get(category))
            if category in self.CUSTOM_SPECIAL_CATEGORIES
            else slot
            for category, slot in enumerate(self.special_plays, start=1)
        )
        return replace(self, special_plays=new_special)
