from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    SpecialSlot,
    StockPlayRef,
    build_gameplan_bytes,
    parse_gameplan,
    read_gameplan,
    write_gameplan,
)
from athc.fbpro98_gameplan.schema import (
    G95_AUDIBLE,
    G95_HEADER,
    G95_OFFSETS_TABLE,
    J95_HEADER,
    J95_PLAN_DATA,
)
from tests.unit.fbpro98_gameplan.conftest import (
    DEFENSE_PATH,
    OFFENSE_PATH,
    both_sides,
    g95_end,
)

# A stock play in a normal slot: offense Run Right, as the game writes stock records.
STOCK_NORMAL = StockPlayRef(
    play_name="RUNRIGHT",
    map_offset=1,
    map_size=2,
    play_category=1,
    special_category=0,
    user_category=1,
)


def _copy_fixture(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copy2(src, dest)
    return dest


def _make_play(name: str) -> CustomPlayRef:
    """An offense play saved as Pass Short Right (0x03), in that folder."""
    return CustomPlayRef(
        filename=f"plays\\Offense\\PSR\\{name}.ply",
        play_category=3,
        special_category=0,
        user_category=3,
    )


def _make_special(category: int) -> CustomPlayRef:
    """An offense custom special play of `category`."""
    return CustomPlayRef(
        filename=f"plays\\Special\\SPEC{category:02d}.ply",
        play_category=1,
        special_category=category,
        user_category=1,
    )


def _j95_counts(data: bytes) -> tuple[int, int, int, int]:
    """The J95 data: profile type, then the custom, stock and special counts."""
    return J95_PLAN_DATA.unpack_from(data, g95_end(data) + J95_HEADER.size)


def _offsets(data: bytes) -> tuple[int, ...]:
    return G95_OFFSETS_TABLE.unpack_from(data, G95_HEADER.size + G95_AUDIBLE.size)


# ---------- round trips ----------


@both_sides
def test_build_gameplan_bytes_reproduces_the_file(pln_path: Path) -> None:
    assert build_gameplan_bytes(read_gameplan(pln_path)) == pln_path.read_bytes()


@both_sides
def test_write_gameplan_round_trips_byte_identical(
    pln_path: Path, tmp_path: Path
) -> None:
    copy = _copy_fixture(pln_path, tmp_path)
    write_gameplan(read_gameplan(copy), copy)
    assert copy.read_bytes() == pln_path.read_bytes()


@both_sides
def test_with_normal_plays_round_trips(pln_path: Path, tmp_path: Path) -> None:
    copy = _copy_fixture(pln_path, tmp_path)
    original = read_gameplan(copy)
    write_gameplan(original.with_normal_plays(list(original.normal_plays)), copy)
    assert read_gameplan(copy) == original


def test_special_plays_survive_a_normal_plays_write(tmp_path: Path) -> None:
    copy = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(copy)
    write_gameplan(original.with_normal_plays([_make_play("TEST01")]), copy)
    assert read_gameplan(copy) == replace(
        original, normal_plays=(_make_play("TEST01"), *(None,) * 63)
    )


# ---------- normal slots ----------


def test_empty_slots_produce_zero_offsets() -> None:
    original = read_gameplan(OFFENSE_PATH)
    data = build_gameplan_bytes(
        original.with_normal_plays([None, _make_play("TEST01"), None])
    )
    # Offsets count from the table's start, so the first record follows the table.
    assert _offsets(data)[:3] == (0, G95_OFFSETS_TABLE.size, 0)
    assert parse_gameplan(data) == replace(
        original, normal_plays=(None, _make_play("TEST01"), *(None,) * 62)
    )


def test_fewer_than_64_pads_remaining_empty() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(3)]
    data = build_gameplan_bytes(original.with_normal_plays(entries))
    assert parse_gameplan(data) == replace(
        original, normal_plays=(*entries, *(None,) * 61)
    )


def test_all_64_slots_filled() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(64)]
    data = build_gameplan_bytes(original.with_normal_plays(entries))
    assert parse_gameplan(data) == replace(original, normal_plays=tuple(entries))


# ---------- J95 counts ----------


def test_j95_counts_follow_the_normal_plays() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(10)]
    data = build_gameplan_bytes(original.with_normal_plays(entries))
    assert _j95_counts(data) == (1, 10, 0, 6)  # offense; 6 custom specials kept
    assert parse_gameplan(data) == replace(
        original, normal_plays=(*entries, *(None,) * 54)
    )


def test_stock_play_in_a_normal_slot_counts_as_stock() -> None:
    original = read_gameplan(OFFENSE_PATH)
    data = build_gameplan_bytes(original.with_normal_plays([STOCK_NORMAL]))
    assert _j95_counts(data) == (1, 0, 1, 6)
    assert parse_gameplan(data) == replace(
        original, normal_plays=(STOCK_NORMAL, *(None,) * 63)
    )


def test_custom_special_plays_set_the_j95_special_count() -> None:
    original = read_gameplan(OFFENSE_PATH)
    play = _make_special(5)
    data = build_gameplan_bytes(original.with_custom_special_plays([play]))
    assert _j95_counts(data) == (1, 60, 0, 1)
    specials = tuple(
        SpecialSlot(custom=play if category == 5 else None, stock=slot.stock)
        for category, slot in enumerate(original.special_plays, start=1)
    )
    assert parse_gameplan(data) == replace(original, special_plays=specials)


# ---------- file size parity ----------


@pytest.mark.parametrize(
    "pln_path, parity",
    [(OFFENSE_PATH, 0), (DEFENSE_PATH, 1)],
    ids=["offense even", "defense odd"],
)
def test_build_pads_to_the_side_parity(pln_path: Path, parity: int) -> None:
    # Emptying the normal slots changes the length; the pad restores the parity.
    plan = read_gameplan(pln_path).with_normal_plays([])
    data = build_gameplan_bytes(plan)
    assert len(data) % 2 == parity
    assert parse_gameplan(data) == plan
