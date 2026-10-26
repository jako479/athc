"""In-memory data model for FbPro98 .pyr player files.

Every player the league knows, by id: names, position and group, years,
injury, height and weight, and both rating sets; plus the header fields and
the coding table a writer needs to put the file back. The model is mutable:
edit a field in place, then `PyrFile.validate()` checks every rule the spec
states.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import IntEnum

from athc.fbpro98_pyr.schema import FIRST_ID, NAME_SIZE, UNKNOWN_SIZE

RATING_MAX = 99

GROUPS = frozenset({0, 10, 13, 14, 15, 16, 17, 18, 19})
"""The position groups the spec's table lists (docs/formats/pyr.md section 5).
A player's group is not checked against their position: a few PNFL and PCFL
players have a group that does not match, all of them players no roster or
free-agent pool holds any more (obsolete records), so the data is read as it
is."""

_U8_MAX = 0xFF
_U16_MAX = 0xFFFF


class Position(IntEnum):
    """A player's position, by the file's code (docs/formats/pyr.md section 5)."""

    QB = 0
    FB = 1
    HB = 2
    TE = 3
    WR = 4
    C = 5
    G = 6
    T = 7
    DE = 8
    DT = 9
    LB = 10
    CB = 11
    S = 12
    K = 13
    P = 14


@dataclass(slots=True)
class Ratings:
    """One set of the eight ratings, 0-99, in file order."""

    acceleration: int
    agility: int
    discipline: int
    endurance: int
    hands: int
    intelligence: int
    speed: int
    strength: int


@dataclass(slots=True)
class Injury:
    """A player's injury (docs/formats/pyr.md section 6). The injury and week
    stay after the player heals."""

    level: int
    """Injury level; 0 is healthy."""

    injury: int
    """Injury name index into `injury.dat`."""

    week: int
    """Week injured - 1, as stored."""


@dataclass(slots=True)
class Player:
    """One player record, decoded."""

    id: int
    first_name: str
    last_name: str
    position: Position
    group: int
    """Position group; see `GROUPS`."""

    years: int
    """Years in the league."""

    injury: Injury
    height: int
    """Inches; 0 except for the newest draft class."""

    weight: int
    """Pounds; 0 except for the newest draft class."""

    potential: Ratings
    """Not shown in the game."""

    actual: Ratings
    """The ratings the game shows."""

    unknown: bytes
    """The six bytes at 0x36, as read."""


@dataclass(slots=True)
class PyrFile:
    """Full in-memory representation of a `.pyr` player file."""

    key: int
    """Header key; picks the coding table."""

    name: str
    """Header name: `SYNERGISTIC1` in stock files, empty in the PNFL's."""

    unknown: bytes
    """The header's last six bytes, as read: the same spot as a record's
    unknown bytes."""

    coding_table: dict[int, int] = field(default_factory=dict)
    """Plain byte value -> the byte written to disk; the entries the file's ids
    reveal (all 256 with 256 or more players)."""

    players: dict[int, Player] = field(default_factory=dict)
    """By player id, in id order: record i is player 100 + i."""

    def validate(self) -> None:
        """Check every rule the spec states, so the file can be written back.

        Raises:
            ValueError: On the first rule broken, in file order; the message
                is a sentence without its period.
        """
        _check_range("key", self.key, _U16_MAX)
        _check_length("name", self.name)
        _check_unknown("unknown", self.unknown)
        self._check_coding_table()
        expected = range(FIRST_ID, FIRST_ID + len(self.players))
        for index, key in enumerate(self.players):
            if key != expected[index]:
                raise ValueError(
                    f"players must be keyed {FIRST_ID}, {FIRST_ID + 1}, ... in "
                    f"order, got {key} at index {index}"
                )
        for key, player in self.players.items():
            if player.id != key:
                raise ValueError(f"players[{key}] holds player {player.id}")
            _check_player(player)

    def _check_coding_table(self) -> None:
        written_as: dict[int, int] = {}
        for plain, disk in self.coding_table.items():
            _check_range("coding_table plain value", plain, _U8_MAX)
            _check_range("coding_table disk value", disk, _U8_MAX)
            if written_as.setdefault(disk, plain) != plain:
                raise ValueError(
                    f"coding_table writes plain {written_as[disk]:#04x} and "
                    f"{plain:#04x} both as {disk:#04x}"
                )


_RATING_NAMES = tuple(f.name for f in fields(Ratings))
_INJURY_LIMITS = (("level", _U16_MAX), ("injury", _U8_MAX), ("week", _U8_MAX))


def _check_player(player: Player) -> None:
    label = f"player {player.id}"
    _check_length(f"{label} first_name", player.first_name)
    _check_length(f"{label} last_name", player.last_name)
    try:
        Position(player.position)
    except ValueError:
        raise ValueError(
            f"{label} position must be 0-{max(Position)}, got {player.position}"
        ) from None
    if player.group not in GROUPS:
        groups = ", ".join(str(group) for group in sorted(GROUPS))
        raise ValueError(f"{label} group must be one of {groups}, got {player.group}")
    for name in ("potential", "actual"):
        ratings: Ratings = getattr(player, name)
        for rating in _RATING_NAMES:
            _check_range(
                f"{label} {name}.{rating}", getattr(ratings, rating), RATING_MAX
            )
    _check_range(f"{label} years", player.years, _U8_MAX)
    _check_range(f"{label} height", player.height, _U8_MAX)
    _check_range(f"{label} weight", player.weight, _U16_MAX)
    for name, limit in _INJURY_LIMITS:
        _check_range(f"{label} injury.{name}", getattr(player.injury, name), limit)
    _check_unknown(f"{label} unknown", player.unknown)


def _check_unknown(what: str, value: bytes) -> None:
    if len(value) != UNKNOWN_SIZE:
        raise ValueError(f"{what} must be {UNKNOWN_SIZE} bytes, got {len(value)}")


def _check_range(what: str, value: int, limit: int) -> None:
    if not 0 <= value <= limit:
        raise ValueError(f"{what} must be 0-{limit}, got {value}")


def _check_length(what: str, text: str) -> None:
    if len(text) > NAME_SIZE:
        raise ValueError(
            f"{what} must be at most {NAME_SIZE} characters, got {len(text)}"
        )
