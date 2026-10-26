"""Tests for athc.fbpro98_pyr.model: `PyrFile.validate()` on models built in
Python, each rule at its limit and one past it."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_pyr import Injury, Player, Position, PyrFile, Ratings

# The position groups of pyr.md section 5.
SPEC_GROUPS = {0, 10, 13, 14, 15, 16, 17, 18, 19}


def _player(player_id: int, **overrides: object) -> Player:
    # PNFL.pyr's player 100.
    player = Player(
        id=player_id,
        first_name="Kirk",
        last_name="Cousins",
        position=Position.QB,
        group=0,
        years=20,
        injury=Injury(level=0, injury=0, week=0),
        height=0,
        weight=0,
        potential=Ratings(67, 63, 84, 69, 57, 92, 65, 80),
        actual=Ratings(60, 63, 84, 69, 57, 92, 57, 80),
        unknown=bytes(6),
    )
    for name, value in overrides.items():
        setattr(player, name, value)
    return player


def _pyr_file(*players: Player) -> PyrFile:
    return PyrFile(
        key=0xCE5F,
        name="",
        unknown=bytes(6),
        coding_table={plain: plain for plain in range(256)},
        players={player.id: player for player in players},
    )


def _rejects(pyr: PyrFile, message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        pyr.validate()


def test_valid_file_passes():
    _pyr_file(_player(100), _player(101)).validate()


def test_file_without_players_passes():
    PyrFile(key=0, name="", unknown=bytes(6)).validate()


# --- header ---


@pytest.mark.parametrize(
    ("field", "value"),
    [("key", 0), ("key", 0xFFFF), ("unknown", bytes(6)), ("name", "SYNERGISTIC1O")],
)
def test_header_field_at_its_limit_accepted(field: str, value: object):
    pyr = _pyr_file()
    setattr(pyr, field, value)
    pyr.validate()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("key", 0x10000, "key: Must be 0-65535, got 65536"),
        ("key", -1, "key: Must be 0-65535, got -1"),
        ("unknown", bytes(5), "unknown: Must be 6 bytes, got 5"),
        ("unknown", bytes(7), "unknown: Must be 6 bytes, got 7"),
        ("name", "SYNERGISTIC1OX", "name: Must be at most 13 characters, got 14"),
    ],
)
def test_header_field_past_its_limit_rejected(field: str, value: object, message: str):
    pyr = _pyr_file()
    setattr(pyr, field, value)
    _rejects(pyr, message)


# --- coding table ---


def test_partial_coding_table_accepted():
    pyr = _pyr_file()
    pyr.coding_table = {0: 255, 255: 0}
    pyr.validate()


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({256: 0}, "coding_table key: Must be 0-255, got 256"),
        ({-1: 0}, "coding_table key: Must be 0-255, got -1"),
        ({0: 256}, "coding_table[0x00]: Must be 0-255, got 256"),
        ({0: -1}, "coding_table[0x00]: Must be 0-255, got -1"),
        (
            {1: 0x3F, 2: 0x3F},
            "coding_table: Plain 0x01 and 0x02 are both written as 0x3f",
        ),
    ],
)
def test_coding_table_rejected(table: dict[int, int], message: str):
    pyr = _pyr_file()
    pyr.coding_table = table
    _rejects(pyr, message)


# --- players ---


@pytest.mark.parametrize(
    ("ids", "message"),
    [
        ((101,), "players: Must be keyed 100, 101, ... in order, got 101 at index 0"),
        (
            (100, 102),
            "players: Must be keyed 100, 101, ... in order, got 102 at index 1",
        ),
        (
            (101, 100),
            "players: Must be keyed 100, 101, ... in order, got 101 at index 0",
        ),
    ],
)
def test_players_not_keyed_from_100_in_order_rejected(ids: tuple[int, ...], message):
    _rejects(_pyr_file(*(_player(player_id) for player_id in ids)), message)


def test_player_key_not_its_id_rejected():
    pyr = _pyr_file()
    pyr.players = {100: _player(101)}
    _rejects(pyr, "players[100]: Holds player 101")


@pytest.mark.parametrize("field", ["first_name", "last_name"])
def test_name_limits(field: str):
    _pyr_file(_player(100, **{field: "A" * 13})).validate()
    _rejects(
        _pyr_file(_player(100, **{field: "A" * 14})),
        f"player 100: {field}: Must be at most 13 characters, got 14",
    )


@pytest.mark.parametrize(
    ("ratings", "rating"), [("potential", "acceleration"), ("actual", "strength")]
)
@pytest.mark.parametrize("value", [0, 99])
def test_rating_at_its_limit_accepted(ratings: str, rating: str, value: int):
    player = _player(100)
    setattr(getattr(player, ratings), rating, value)
    _pyr_file(player).validate()


@pytest.mark.parametrize(
    ("ratings", "rating"), [("potential", "acceleration"), ("actual", "strength")]
)
@pytest.mark.parametrize("value", [100, -1])
def test_rating_past_its_limit_rejected(ratings: str, rating: str, value: int):
    player = _player(100)
    setattr(getattr(player, ratings), rating, value)
    _rejects(
        _pyr_file(player), f"player 100: {ratings}.{rating}: Must be 0-99, got {value}"
    )


@pytest.mark.parametrize("position", [Position.P, 14, Position.QB, 0])
def test_position_as_member_or_code_accepted(position: object):
    _pyr_file(_player(100, position=position)).validate()


@pytest.mark.parametrize("position", [15, -1])
def test_position_outside_the_codes_rejected(position: int):
    _rejects(
        _pyr_file(_player(100, position=position)),
        f"player 100: position: Must be 0-14, got {position}",
    )


@pytest.mark.parametrize("group", sorted(SPEC_GROUPS))
def test_every_group_of_the_spec_table_accepted(group: int):
    _pyr_file(_player(100, group=group)).validate()


@pytest.mark.parametrize("group", [1, 9, 11, 12, 20, -1])
def test_group_outside_the_spec_table_rejected(group: int):
    _rejects(
        _pyr_file(_player(100, group=group)),
        f"player 100: group: Must be one of 0, 10, 13, 14, 15, 16, 17, 18, 19, got {group}",
    )


@pytest.mark.parametrize(
    ("field", "limit"), [("years", 255), ("height", 255), ("weight", 65535)]
)
def test_numeric_field_limits(field: str, limit: int):
    _pyr_file(_player(100, **{field: limit})).validate()
    _pyr_file(_player(100, **{field: 0})).validate()
    _rejects(
        _pyr_file(_player(100, **{field: limit + 1})),
        f"player 100: {field}: Must be 0-{limit}, got {limit + 1}",
    )
    _rejects(
        _pyr_file(_player(100, **{field: -1})),
        f"player 100: {field}: Must be 0-{limit}, got -1",
    )


@pytest.mark.parametrize(
    ("field", "limit"), [("level", 65535), ("injury", 255), ("week", 255)]
)
def test_injury_field_limits(field: str, limit: int):
    player = _player(100)
    setattr(player.injury, field, limit)
    _pyr_file(player).validate()
    setattr(player.injury, field, limit + 1)
    _rejects(
        _pyr_file(player),
        f"player 100: injury.{field}: Must be 0-{limit}, got {limit + 1}",
    )
    setattr(player.injury, field, -1)
    _rejects(
        _pyr_file(player), f"player 100: injury.{field}: Must be 0-{limit}, got -1"
    )


@pytest.mark.parametrize("size", [5, 7])
def test_unknown_not_six_bytes_rejected(size: int):
    _rejects(
        _pyr_file(_player(100, unknown=bytes(size))),
        f"player 100: unknown: Must be 6 bytes, got {size}",
    )


def test_problem_in_a_later_player_names_that_player():
    _rejects(
        _pyr_file(_player(100), _player(101, years=256)),
        "player 101: years: Must be 0-255, got 256",
    )


def test_first_problem_in_file_order_reported():
    # A bad key and a bad player: the header comes first.
    pyr = _pyr_file(_player(100, years=256))
    pyr.key = -1
    _rejects(pyr, "key: Must be 0-65535, got -1")
