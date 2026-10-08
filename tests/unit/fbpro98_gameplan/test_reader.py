from __future__ import annotations

import struct
from pathlib import Path

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    InvalidGamePlanError,
    PlayRef,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
    parse_gameplan,
    read_gameplan,
)
from athc.fbpro98_gameplan.schema import G95_HEADER, J95_HEADER, J95_PLAN_DATA

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
EXPECTED_DIR = TEST_DATA_DIR / "expected"
OFFENSE_PATH = TEST_DATA_DIR / "offense.pln"
DEFENSE_PATH = TEST_DATA_DIR / "defense.pln"


# ---------- helpers ----------


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real gameplan fixture: {path}")
    return path


def _load_fixture_bytes(path: Path) -> bytearray:
    return bytearray(_require_fixture(path).read_bytes())


def _load_expected(name: str) -> list[str]:
    return (EXPECTED_DIR / name).read_text(encoding="utf-8").splitlines()


def _slot_names(plays: tuple[PlayRef | None, ...]) -> list[str]:
    """Convert a play tuple to a list of names with empty strings for None slots."""
    return [p.name if p is not None else "" for p in plays]


def _filled_names_sorted(plays: tuple[PlayRef | None, ...]) -> list[str]:
    """Names of non-None plays, case-insensitively sorted (matches reader's by-name output)."""
    return sorted((p.name for p in plays if p is not None), key=str.lower)


def _first_used_slot_offset(data: bytes | bytearray) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset != 0:
            return slot, 12 + relative_offset
    raise AssertionError("Fixture does not contain any play records")


def _first_custom_record_offset(data: bytes | bytearray) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset == 0:
            continue
        record_offset = 12 + relative_offset
        if data[record_offset] == 0:
            return slot, record_offset
    pytest.skip("Fixture does not contain a custom play record")


def _record_offset(data: bytes | bytearray, slot: int) -> int:
    """Absolute offset of the play record in `slot`; skips when the slot is empty."""
    offsets = struct.unpack_from("<86H", data, 12)
    if offsets[slot] == 0:
        pytest.skip(f"Fixture slot {slot} is empty")
    return 12 + offsets[slot]


def _g95_end(data: bytes | bytearray) -> int:
    _, g95_size = G95_HEADER.unpack_from(data, 0)
    return G95_HEADER.size + g95_size


def _s98_start(data: bytes | bytearray) -> int:
    return _g95_end(data) + J95_HEADER.size + J95_PLAN_DATA.size


# ---------- offense fixture: full data assertions ----------


def test_offense_profile_type_is_offense() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert plan.profile_type is ProfileType.OFFENSE
    assert plan.is_offense is True
    assert plan.is_defense is False


def test_offense_normal_plays_match_expected_slot_layout() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert _slot_names(plan.normal_plays) == _load_expected(
        "offense_normal_by_slot.txt"
    )


def test_offense_normal_plays_filled_count_matches_expected_by_name() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert _filled_names_sorted(plan.normal_plays) == _load_expected(
        "offense_normal_by_name.txt"
    )


def test_offense_custom_special_plays_match_expected() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert _slot_names(plan.custom_special_plays) == _load_expected(
        "offense_special.txt"
    )


def test_offense_clock_categories_hold_stock_plays() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    run_clock = plan.special_plays[10]
    stop_clock = plan.special_plays[11]
    assert run_clock.custom is None and stop_clock.custom is None
    assert run_clock.stock is not None and run_clock.stock.name == "RUNCLOCK"
    assert stop_clock.stock is not None and stop_clock.stock.name == "STOPCLOK"
    assert run_clock.stock.special_category == 11
    assert stop_clock.stock.special_category == 12


def test_offense_normal_plays_have_special_category_zero() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for play in plan.normal_plays:
        if play is not None:
            assert play.special_category == 0


def test_offense_normal_plays_have_offensive_play_category() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for play in plan.normal_plays:
        if play is not None:
            assert play.play_category % 2 == 1


def test_offense_special_slots_are_typed() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for slot in plan.special_plays:
        assert slot.custom is None or isinstance(slot.custom, CustomPlayRef)
        assert slot.stock is None or isinstance(slot.stock, StockPlayRef)


def test_offense_special_slots_carry_their_category() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for category, slot in enumerate(plan.special_plays, start=1):
        for play in (slot.custom, slot.stock):
            if play is not None:
                assert play.special_category == category


# ---------- defense fixture: full data assertions ----------


def test_defense_profile_type_is_defense() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert plan.profile_type is ProfileType.DEFENSE
    assert plan.is_defense is True
    assert plan.is_offense is False


def test_defense_normal_plays_match_expected_slot_layout() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert _slot_names(plan.normal_plays) == _load_expected(
        "defense_normal_by_slot.txt"
    )


def test_defense_normal_plays_filled_count_matches_expected_by_name() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert _filled_names_sorted(plan.normal_plays) == _load_expected(
        "defense_normal_by_name.txt"
    )


def test_defense_custom_special_plays_match_expected() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert _slot_names(plan.custom_special_plays) == _load_expected(
        "defense_special.txt"
    )


def test_defense_clock_categories_are_empty() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert plan.special_plays[10] == SpecialSlot()
    assert plan.special_plays[11] == SpecialSlot()


def test_defense_normal_plays_have_defensive_play_category() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    for play in plan.normal_plays:
        if play is not None:
            assert play.play_category % 2 == 0


# ---------- public API surface ----------


def test_read_gameplan_returns_gameplan_instance() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert isinstance(plan, GamePlan)


def test_parse_gameplan_from_buffer_matches_read_gameplan() -> None:
    buffer = _require_fixture(OFFENSE_PATH).read_bytes()
    from_buffer = parse_gameplan(buffer)
    from_file = read_gameplan(OFFENSE_PATH)
    assert _slot_names(from_buffer.normal_plays) == _slot_names(from_file.normal_plays)
    assert from_buffer.special_plays == from_file.special_plays
    assert from_buffer.profile_type == from_file.profile_type


def test_gameplan_normal_plays_has_64_entries() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert len(plan.normal_plays) == 64


def test_gameplan_special_plays_has_12_entries() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert len(plan.special_plays) == 12


def test_gameplan_custom_special_plays_view_has_10_entries() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert len(plan.custom_special_plays) == 10
    for play in plan.custom_special_plays:
        assert play is None or isinstance(play, CustomPlayRef)


def test_custom_play_name_strips_directory_and_extension() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for play in plan.normal_plays:
        if isinstance(play, CustomPlayRef):
            assert "\\" not in play.name
            assert "." not in play.name
            return
    pytest.skip("Fixture has no CustomPlayRef in normal_plays")


def test_invalid_gameplan_error_is_value_error_subclass() -> None:
    assert issubclass(InvalidGamePlanError, ValueError)


# ---------- structural validation: error paths ----------


def test_file_too_small_raises(tmp_path):
    gameplan_path = tmp_path / "tiny.pln"
    gameplan_path.write_bytes(b"G95:" + b"\x00" * 4)
    with pytest.raises(InvalidGamePlanError, match="File too small"):
        read_gameplan(gameplan_path)


def test_invalid_g95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data[0:4] = b"BAD!"
    gameplan_path = tmp_path / "bad_g95.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match=r"Invalid header.*at 0x0"):
        read_gameplan(gameplan_path)


def test_g95_block_extends_past_eof_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    struct.pack_into("<I", data, 4, len(data) * 10)
    gameplan_path = tmp_path / "bad_g95_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="G95 block extends past"):
        read_gameplan(gameplan_path)


def test_invalid_audible_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data[8] = 0xFF
    gameplan_path = tmp_path / "bad_audible.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Audible"):
        read_gameplan(gameplan_path)


def test_out_of_range_offset_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    slot, _ = _first_used_slot_offset(data)
    struct.pack_into("<H", data, 12 + (slot * 2), 1)
    gameplan_path = tmp_path / "bad_offset.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="out of range"):
        read_gameplan(gameplan_path)


def test_missing_null_terminator_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    _, record_offset = _first_custom_record_offset(data)
    string_start = record_offset + 4
    string_end = data.index(0, string_start)
    data[string_end] = ord("X")
    gameplan_path = tmp_path / "bad_string.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Missing null terminator"):
        read_gameplan(gameplan_path)


def test_invalid_stock_flag_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    _, record_offset = _first_custom_record_offset(data)
    data[record_offset] = 0x77
    gameplan_path = tmp_path / "bad_stock_flag.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid stock flag"):
        read_gameplan(gameplan_path)


def test_invalid_j95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    data[j95_pos : j95_pos + 4] = b"BAD!"
    gameplan_path = tmp_path / "bad_j95.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_invalid_j95_data_size_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    struct.pack_into("<I", data, j95_pos + 4, 99)
    gameplan_path = tmp_path / "bad_j95_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="J95 data size"):
        read_gameplan(gameplan_path)


def test_invalid_profile_type_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    data[j95_pos + J95_HEADER.size] = 5
    gameplan_path = tmp_path / "bad_profile.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="profile type"):
        read_gameplan(gameplan_path)


def test_j95_count_mismatch_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_data = _g95_end(data) + J95_HEADER.size
    struct.pack_into("<H", data, j95_data + 1, 9999)
    gameplan_path = tmp_path / "bad_j95_count.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="J95 counts"):
        read_gameplan(gameplan_path)


def test_invalid_s98_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    data[s98_pos : s98_pos + 4] = b"BAD!"
    gameplan_path = tmp_path / "bad_s98.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_invalid_s98_data_size_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    struct.pack_into("<I", data, s98_pos + 4, 99)
    gameplan_path = tmp_path / "bad_s98_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="S98 data size"):
        read_gameplan(gameplan_path)


def test_invalid_s98_data_content_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    data[s98_pos + 8] = ord("X")
    gameplan_path = tmp_path / "bad_s98_content.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="S98 data"):
        read_gameplan(gameplan_path)


def test_wrong_parity_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data.append(0)
    gameplan_path = tmp_path / "bad_parity.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="wrong parity"):
        read_gameplan(gameplan_path)


def test_nonexistent_path_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        read_gameplan(tmp_path / "nonexistent.pln")


# ---------- more error branches ----------


def test_file_too_small_for_j95_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    truncated = data[: _g95_end(data) + 2]  # valid G95, no room for the J95 block
    gameplan_path = tmp_path / "no_j95.pln"
    gameplan_path.write_bytes(truncated)
    with pytest.raises(InvalidGamePlanError, match="too small to contain J95"):
        read_gameplan(gameplan_path)


def test_file_too_small_for_s98_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    truncated = data[: _s98_start(data) + 4]  # valid G95+J95, S98 header doesn't fit
    gameplan_path = tmp_path / "no_s98.pln"
    gameplan_path.write_bytes(truncated)
    with pytest.raises(InvalidGamePlanError, match="too small to contain S98"):
        read_gameplan(gameplan_path)


# ---------- play categories ----------


def test_unrecognized_play_category_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    slot, record_offset = _first_used_slot_offset(data)
    # Only a normal slot resolves by user_category; specials ignore that byte.
    assert slot < GamePlan.NUMBER_NORMAL_PLAYS
    data[record_offset + 3] = 0x3F  # user_category no table knows
    gameplan_path = tmp_path / "bad_category.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(
        InvalidGamePlanError, match=f"Unrecognized play category at slot {slot}"
    ):
        read_gameplan(gameplan_path)


def test_custom_play_in_clock_slot_raises(tmp_path):
    """A clock slot holding a custom record is a model violation, not a crash."""
    data = _load_fixture_bytes(OFFENSE_PATH)
    # Turn the Run Clock stock record (slot 84) into a custom record: stock_flag 0.
    # Its body then reads as a filename up to the first NUL inside map_offset, and
    # its special_category stays 11. Bump the J95 special count so the count check
    # passes and the model gets to judge the slot.
    data[_record_offset(data, 84)] = 0
    j95_special = _g95_end(data) + J95_HEADER.size + 5  # after type u8 + 2 x u16
    struct.pack_into(
        "<H", data, j95_special, struct.unpack_from("<H", data, j95_special)[0] + 1
    )
    gameplan_path = tmp_path / "custom_clock.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(
        ValueError, match="Special category 11: stock must be StockPlayRef"
    ):
        read_gameplan(gameplan_path)
