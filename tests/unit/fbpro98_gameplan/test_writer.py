from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    SpecialSlot,
    StockPlayRef,
    build_gameplan,
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


def _with_normals(original: GamePlan, plays: list[PlayRef | None]) -> GamePlan:
    """A copy of `original` with `plays` in the first normal slots and the rest
    empty."""
    edited = copy.deepcopy(original)
    edited.normal_plays = plays + [None] * (GamePlan.NUMBER_NORMAL_PLAYS - len(plays))
    return edited


def _j95_counts(data: bytes) -> tuple[int, int, int, int]:
    """The J95 data: profile type, then the custom, stock and special counts."""
    return J95_PLAN_DATA.unpack_from(data, g95_end(data) + J95_HEADER.size)


def _offsets(data: bytes) -> tuple[int, ...]:
    return G95_OFFSETS_TABLE.unpack_from(data, G95_HEADER.size + G95_AUDIBLE.size)


# ---------- round trips ----------


@both_sides
def test_build_gameplan_reproduces_the_file(pln_path: Path) -> None:
    assert build_gameplan(read_gameplan(pln_path)) == pln_path.read_bytes()


@both_sides
def test_write_gameplan_round_trips_byte_identical(
    pln_path: Path, tmp_path: Path
) -> None:
    copy_path = _copy_fixture(pln_path, tmp_path)
    write_gameplan(read_gameplan(copy_path), copy_path)
    assert copy_path.read_bytes() == pln_path.read_bytes()


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    folder = tmp_path / "out"
    folder.mkdir()
    copy_path = _copy_fixture(OFFENSE_PATH, folder)
    write_gameplan(read_gameplan(copy_path), copy_path)
    assert [p.name for p in folder.iterdir()] == [copy_path.name]


def test_special_plays_survive_a_normal_plays_write(tmp_path: Path) -> None:
    copy_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(copy_path)
    edited = _with_normals(original, [_make_play("TEST01")])
    write_gameplan(edited, copy_path)
    assert read_gameplan(copy_path) == edited
    assert read_gameplan(copy_path).special_plays == original.special_plays


# ---------- validation before packing ----------


def test_build_refuses_an_invalid_plan() -> None:
    plan = read_gameplan(OFFENSE_PATH)
    plan.normal_plays[0] = _make_special(1)
    with pytest.raises(ValueError, match="Normal slot 0 contains a special play"):
        build_gameplan(plan)


def test_write_refuses_an_invalid_plan_and_writes_nothing(tmp_path: Path) -> None:
    plan = read_gameplan(OFFENSE_PATH)
    plan.normal_plays[0] = _make_special(1)
    target = tmp_path / "bad.pln"
    with pytest.raises(ValueError):
        write_gameplan(plan, target)
    assert not target.exists()


# ---------- normal slots ----------


def test_empty_slots_produce_zero_offsets() -> None:
    original = read_gameplan(OFFENSE_PATH)
    edited = _with_normals(original, [None, _make_play("TEST01"), None])
    data = build_gameplan(edited)
    # Offsets count from the table's start, so the first record follows the table.
    assert _offsets(data)[:3] == (0, G95_OFFSETS_TABLE.size, 0)
    assert parse_gameplan(data) == edited


def test_fewer_than_64_pads_remaining_empty() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries: list[PlayRef | None] = [_make_play(f"PLAY{i:02d}") for i in range(3)]
    edited = _with_normals(original, entries)
    assert parse_gameplan(build_gameplan(edited)) == edited


def test_all_64_slots_filled() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries: list[PlayRef | None] = [_make_play(f"PLAY{i:02d}") for i in range(64)]
    edited = _with_normals(original, entries)
    assert parse_gameplan(build_gameplan(edited)) == edited


# ---------- J95 counts ----------


def test_j95_counts_follow_the_normal_plays() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries: list[PlayRef | None] = [_make_play(f"PLAY{i:02d}") for i in range(10)]
    edited = _with_normals(original, entries)
    data = build_gameplan(edited)
    assert _j95_counts(data) == (1, 10, 0, 6)  # offense; 6 custom specials kept
    assert parse_gameplan(data) == edited


def test_stock_play_in_a_normal_slot_counts_as_stock() -> None:
    original = read_gameplan(OFFENSE_PATH)
    edited = _with_normals(original, [STOCK_NORMAL])
    data = build_gameplan(edited)
    assert _j95_counts(data) == (1, 0, 1, 6)
    assert parse_gameplan(data) == edited


def test_custom_special_plays_set_the_j95_special_count() -> None:
    original = read_gameplan(OFFENSE_PATH)
    play = _make_special(5)
    edited = copy.deepcopy(original)
    for category in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
        edited.special_plays[category - 1].custom = play if category == 5 else None
    data = build_gameplan(edited)
    assert _j95_counts(data) == (1, 60, 0, 1)
    specials = [
        SpecialSlot(custom=play if category == 5 else None, stock=slot.stock)
        for category, slot in enumerate(original.special_plays, start=1)
    ]
    assert parse_gameplan(data).special_plays == specials
    assert parse_gameplan(data) == edited


# ---------- file size parity ----------


@pytest.mark.parametrize(
    "pln_path, parity",
    [(OFFENSE_PATH, 0), (DEFENSE_PATH, 1)],
    ids=["offense even", "defense odd"],
)
def test_build_pads_to_the_side_parity(pln_path: Path, parity: int) -> None:
    # Emptying the normal slots changes the length; the pad restores the parity.
    plan = _with_normals(read_gameplan(pln_path), [])
    data = build_gameplan(plan)
    assert len(data) % 2 == parity
    assert parse_gameplan(data) == plan
