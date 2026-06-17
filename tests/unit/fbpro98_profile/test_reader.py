"""Reader tests pinned against real game-produced fixtures.

The expected values below were captured by running the reader against the
`TST-*.prf` fixtures and recording the actual output. Treat them as
ground-truth: if a value here disagrees with the reader, the reader is
wrong, not the fixture.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    InvalidProfileError,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    UnsupportedProfileError,
    parse_profile,
    read_profile,
)
from athc.fbpro98_profile.schema import (
    F95_DATA_SIZE,
    F95_HEADER,
    I95_HEADER,
)

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
OFF1_PATH = TEST_DATA_DIR / "TST-OFF1.prf"
OFF2_PATH = TEST_DATA_DIR / "TST-OFF2.prf"
DEF1_PATH = TEST_DATA_DIR / "TST-DEF1.prf"
DEF2_PATH = TEST_DATA_DIR / "TST-DEF2.prf"
OFF1_AUD_PATH = TEST_DATA_DIR / "TST-OFF1-AUD.prf"
DEF1_AUD_PATH = TEST_DATA_DIR / "TST-DEF1-AUD.prf"
OFF1_PL_PATH = TEST_DATA_DIR / "TST-OFF1-PL.prf"
DEF1_PL_PATH = TEST_DATA_DIR / "TST-DEF1-PL.prf"

I95_OFFSET = F95_HEADER.size + F95_DATA_SIZE  # 0x3CA5
I95_DATA_OFFSET = I95_OFFSET + I95_HEADER.size  # 0x3CAD


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real profile fixture: {path}")
    return path


def _load_fixture_bytes(path: Path) -> bytearray:
    return bytearray(_require_fixture(path).read_bytes())


# ---------- TST-OFF1.prf: pinned values ----------


def test_off1_profile_type() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert profile.profile_type is ProfileType.OFFENSE
    assert profile.is_offense is True


def test_off1_field_goal_range() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert profile.field_goal_range == 36


def test_off1_use_audibles() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert profile.use_audibles is False


def test_off1_situation_counts() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert len(profile.situations) == 2520
    assert len(profile.pat_situations) == 60


def test_off1_substitutions() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    s = profile.substitutions
    assert (s.offensive_linemen.out_percent, s.offensive_linemen.in_percent) == (95, 98)
    assert (s.quarterbacks.out_percent, s.quarterbacks.in_percent) == (75, 80)
    assert (s.running_backs.out_percent, s.running_backs.in_percent) == (95, 98)
    assert (s.receivers.out_percent, s.receivers.in_percent) == (95, 98)
    assert (s.defensive_linemen.out_percent, s.defensive_linemen.in_percent) == (80, 90)
    assert (s.linebackers.out_percent, s.linebackers.in_percent) == (80, 90)
    assert (s.defensive_backs.out_percent, s.defensive_backs.in_percent) == (80, 90)
    assert (s.kickers.out_percent, s.kickers.in_percent) == (80, 90)


def test_off1_first_situation() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    situation = profile.situations[0]
    assert situation.situation_number == 1
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=10,
        weight1=1,
        play_category2=9,
        weight2=10,
        play_category3=12,
        weight3=1,
    )


def test_off1_last_situation() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    situation = profile.situations[-1]
    assert situation.situation_number == 2520
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=19,
        weight1=10,
        play_category2=19,
        weight2=10,
        play_category3=19,
        weight3=1,
    )


def test_off1_first_pat_situation() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    pat = profile.pat_situations[0]
    assert pat.situation_number == 1
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_off1_last_pat_situation() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    pat = profile.pat_situations[-1]
    assert pat.situation_number == 60
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_off1_stop_clock_situations_count() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert len(profile.stop_clock_situations) == 522


def test_off1_first_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    first_situation_number, first_situation = profile.stop_clock_situations[0]
    assert first_situation_number == 1023
    assert first_situation.stop_clock is True
    assert first_situation.category_weights.play_category1 == 11
    assert first_situation.category_weights.weight1 == 5


def test_off1_last_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    last_situation_number, last_situation = profile.stop_clock_situations[-1]
    assert last_situation_number == 2387
    assert last_situation.stop_clock is True


# ---------- TST-OFF2.prf: pinned values ----------


def test_off2_profile_type() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    assert profile.profile_type is ProfileType.OFFENSE


def test_off2_field_goal_range() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    assert profile.field_goal_range == 36


def test_off2_substitutions() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    s = profile.substitutions
    assert (s.offensive_linemen.out_percent, s.offensive_linemen.in_percent) == (95, 98)
    assert (s.quarterbacks.out_percent, s.quarterbacks.in_percent) == (75, 80)
    assert (s.running_backs.out_percent, s.running_backs.in_percent) == (95, 98)
    assert (s.receivers.out_percent, s.receivers.in_percent) == (95, 98)


def test_off2_first_situation() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    situation = profile.situations[0]
    assert situation.situation_number == 1
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=9,
        weight1=10,
        play_category2=11,
        weight2=1,
        play_category3=12,
        weight3=1,
    )


def test_off2_last_situation() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    situation = profile.situations[-1]
    assert situation.situation_number == 2520
    assert situation.stop_clock is True
    assert situation.category_weights == CategoryWeights(
        play_category1=9,
        weight1=9,
        play_category2=12,
        weight2=9,
        play_category3=11,
        weight3=1,
    )


def test_off2_first_pat_situation() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    pat = profile.pat_situations[0]
    assert pat.situation_number == 1
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_off2_last_pat_situation() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    pat = profile.pat_situations[-1]
    assert pat.situation_number == 60
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_off2_stop_clock_situations_count() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    assert len(profile.stop_clock_situations) == 617


def test_off2_first_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    first_situation_number, _ = profile.stop_clock_situations[0]
    assert first_situation_number == 888


def test_off2_last_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(OFF2_PATH))
    last_situation_number, _ = profile.stop_clock_situations[-1]
    assert last_situation_number == 2520


# ---------- TST-DEF1.prf: pinned values ----------


def test_def1_profile_type() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    assert profile.profile_type is ProfileType.DEFENSE
    assert profile.is_defense is True


def test_def1_field_goal_range() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    assert profile.field_goal_range == 36


def test_def1_use_audibles() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    assert profile.use_audibles is False


def test_def1_substitutions() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    s = profile.substitutions
    assert (s.defensive_linemen.out_percent, s.defensive_linemen.in_percent) == (96, 98)
    assert (s.linebackers.out_percent, s.linebackers.in_percent) == (96, 98)
    assert (s.defensive_backs.out_percent, s.defensive_backs.in_percent) == (96, 98)
    assert (s.offensive_linemen.out_percent, s.offensive_linemen.in_percent) == (80, 90)
    assert (s.quarterbacks.out_percent, s.quarterbacks.in_percent) == (80, 90)
    assert (s.running_backs.out_percent, s.running_backs.in_percent) == (80, 90)
    assert (s.receivers.out_percent, s.receivers.in_percent) == (80, 90)
    assert (s.kickers.out_percent, s.kickers.in_percent) == (80, 90)


def test_def1_first_situation() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    situation = profile.situations[0]
    assert situation.situation_number == 1
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=1,
        weight1=10,
        play_category2=3,
        weight2=10,
        play_category3=4,
        weight3=1,
    )


def test_def1_last_situation() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    situation = profile.situations[-1]
    assert situation.situation_number == 2520
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=19,
        weight1=10,
        play_category2=19,
        weight2=10,
        play_category3=10,
        weight3=0,
    )


def test_def1_first_pat_situation() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    pat = profile.pat_situations[0]
    assert pat.situation_number == 1
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_def1_last_pat_situation() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    pat = profile.pat_situations[-1]
    assert pat.situation_number == 60
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_def1_stop_clock_situations_empty() -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    assert profile.stop_clock_situations == ()


# ---------- TST-DEF2.prf: pinned values ----------


def test_def2_profile_type() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    assert profile.profile_type is ProfileType.DEFENSE


def test_def2_field_goal_range() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    assert profile.field_goal_range == 36


def test_def2_substitutions() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    s = profile.substitutions
    assert (s.defensive_linemen.out_percent, s.defensive_linemen.in_percent) == (96, 98)
    assert (s.linebackers.out_percent, s.linebackers.in_percent) == (96, 98)
    assert (s.defensive_backs.out_percent, s.defensive_backs.in_percent) == (96, 98)


def test_def2_first_situation() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    situation = profile.situations[0]
    assert situation.situation_number == 1
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=2,
        weight1=10,
        play_category2=3,
        weight2=9,
        play_category3=1,
        weight3=1,
    )


def test_def2_last_situation() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    situation = profile.situations[-1]
    assert situation.situation_number == 2520
    assert situation.stop_clock is False
    assert situation.category_weights == CategoryWeights(
        play_category1=19,
        weight1=10,
        play_category2=19,
        weight2=10,
        play_category3=19,
        weight3=1,
    )


def test_def2_first_pat_situation() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    pat = profile.pat_situations[0]
    assert pat.situation_number == 1
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_def2_last_pat_situation() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    pat = profile.pat_situations[-1]
    assert pat.situation_number == 60
    assert pat.category_weights == CategoryWeights(
        play_category1=16,
        weight1=1,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )


def test_def2_stop_clock_situations_count() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    assert len(profile.stop_clock_situations) == 322


def test_def2_first_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    first_situation_number, first_situation = profile.stop_clock_situations[0]
    assert first_situation_number == 372
    assert first_situation.stop_clock is True
    assert first_situation.category_weights.play_category1 == 10
    assert first_situation.category_weights.weight1 == 2


def test_def2_last_stop_clock_situation_number() -> None:
    profile = read_profile(_require_fixture(DEF2_PATH))
    last_situation_number, _ = profile.stop_clock_situations[-1]
    assert last_situation_number == 2394


# ---------- TST-OFF1-AUD.prf / TST-DEF1-AUD.prf: use_audibles=True ----------


def test_off1_aud_use_audibles_true() -> None:
    profile = read_profile(_require_fixture(OFF1_AUD_PATH))
    assert profile.use_audibles is True


def test_def1_aud_use_audibles_true() -> None:
    profile = read_profile(_require_fixture(DEF1_AUD_PATH))
    assert profile.use_audibles is True


# ---------- gameplan-included PL profiles: UnsupportedProfileError ----------


def test_off1_pl_profile_raises_unsupported() -> None:
    with pytest.raises(UnsupportedProfileError, match=r"[Ee]mbedded game plan"):
        read_profile(_require_fixture(OFF1_PL_PATH))


def test_def1_pl_profile_raises_unsupported() -> None:
    with pytest.raises(UnsupportedProfileError, match=r"[Ee]mbedded game plan"):
        read_profile(_require_fixture(DEF1_PL_PATH))


# ---------- public API surface ----------


def test_read_profile_returns_profile_instance() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert isinstance(profile, Profile)


def test_situations_are_situation_instances() -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    assert isinstance(profile.situations[0], Situation)
    assert isinstance(profile.pat_situations[0], PatSituation)


def test_parse_profile_from_buffer_matches_read_profile() -> None:
    buffer = _require_fixture(OFF1_PATH).read_bytes()
    from_buffer = parse_profile(buffer)
    from_file = read_profile(OFF1_PATH)
    assert from_buffer.profile_type == from_file.profile_type
    assert from_buffer.field_goal_range == from_file.field_goal_range
    assert from_buffer.use_audibles == from_file.use_audibles
    assert from_buffer.substitutions == from_file.substitutions
    assert from_buffer.situations == from_file.situations
    assert from_buffer.pat_situations == from_file.pat_situations


def test_invalid_profile_error_is_value_error_subclass() -> None:
    assert issubclass(InvalidProfileError, ValueError)


def test_unsupported_profile_error_is_value_error_subclass() -> None:
    assert issubclass(UnsupportedProfileError, ValueError)


# ---------- structural validation: error paths ----------


def test_file_too_small_raises(tmp_path):
    profile_path = tmp_path / "tiny.prf"
    profile_path.write_bytes(b"F95:" + b"\x00" * 4)
    with pytest.raises(InvalidProfileError, match="too small"):
        read_profile(profile_path)


def test_invalid_f95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[0:4] = b"BAD!"
    profile_path = tmp_path / "bad_f95.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match=r"Invalid header.*at 0x0"):
        read_profile(profile_path)


def test_wrong_f95_data_size_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<I", data, 4, 99)
    profile_path = tmp_path / "bad_f95_size.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="F95 data size"):
        read_profile(profile_path)


@pytest.mark.parametrize("stock_size", [0x3F69, 0x4509])
def test_stock_layout_raises_unsupported(tmp_path, stock_size):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<I", data, 4, stock_size)
    profile_path = tmp_path / f"stock_{stock_size:X}.prf"
    profile_path.write_bytes(data)
    with pytest.raises(UnsupportedProfileError, match="Stock layout"):
        read_profile(profile_path)


def test_invalid_substitution_pair_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<HH", data, 0x08 + 4, 99, 50)
    profile_path = tmp_path / "bad_subs.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="substitution pair for quarterbacks"):
        read_profile(profile_path)


def test_invalid_situation_play_category_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[0x28] = 0xFF
    profile_path = tmp_path / "bad_situation.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="situation record"):
        read_profile(profile_path)


def test_invalid_situation_weight_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[0x28 + 3] = 11
    profile_path = tmp_path / "bad_weight.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="situation record"):
        read_profile(profile_path)


def test_f95_field_goal_range_out_of_bounds_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[0x3B38] = 4
    profile_path = tmp_path / "bad_fg.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="F95 field_goal_range"):
        read_profile(profile_path)


def test_f95_use_audibles_out_of_range_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<I", data, 0x3CA1, 2)
    profile_path = tmp_path / "bad_audibles.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="F95 use_audibles"):
        read_profile(profile_path)


def test_invalid_i95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[I95_OFFSET : I95_OFFSET + 4] = b"BAD!"
    profile_path = tmp_path / "bad_i95.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="Invalid header"):
        read_profile(profile_path)


def test_wrong_i95_data_size_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<I", data, I95_OFFSET + 4, 99)
    profile_path = tmp_path / "bad_i95_size.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="I95 data size"):
        read_profile(profile_path)


def test_invalid_profile_type_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[I95_DATA_OFFSET] = 5
    profile_path = tmp_path / "bad_profile_type.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="profile_type"):
        read_profile(profile_path)


def test_nonzero_reserved_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<H", data, I95_DATA_OFFSET + 1, 1)
    profile_path = tmp_path / "bad_reserved.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="reserved"):
        read_profile(profile_path)


def test_f95_i95_field_goal_range_mismatch_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[I95_DATA_OFFSET + 3] = (data[I95_DATA_OFFSET + 3] + 1) & 0xFF
    profile_path = tmp_path / "fg_mismatch.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="field_goal_range"):
        read_profile(profile_path)


def test_f95_i95_use_audibles_mismatch_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<I", data, 0x3CA1, 1)
    profile_path = tmp_path / "audibles_mismatch.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="use_audibles"):
        read_profile(profile_path)


def test_embedded_game_plan_count_raises_unsupported(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    struct.pack_into("<H", data, I95_DATA_OFFSET + 4, 1)
    profile_path = tmp_path / "embedded_count.prf"
    profile_path.write_bytes(data)
    with pytest.raises(UnsupportedProfileError, match=r"[Ee]mbedded game plan"):
        read_profile(profile_path)


def test_embedded_g95_after_i95_raises_unsupported(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    body_end = I95_OFFSET + I95_HEADER.size + 0x0A
    data = data[:body_end] + b"G95:" + b"\x00" * 4
    profile_path = tmp_path / "embedded_g95.prf"
    profile_path.write_bytes(data)
    with pytest.raises(UnsupportedProfileError, match=r"[Ee]mbedded game plan"):
        read_profile(profile_path)


def test_invalid_trailer_byte_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[-1] = 0xAB
    profile_path = tmp_path / "bad_trailer.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="Trailer byte"):
        read_profile(profile_path)


def test_stock_trailer_byte_rejected(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data[-1] = 0x69
    profile_path = tmp_path / "stock_trailer.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="Trailer byte"):
        read_profile(profile_path)


@pytest.mark.parametrize("stock_name", ["OFF1.PRF", "DEF1.PRF"])
def test_real_stock_profile_rejected(stock_name: str) -> None:
    stock_path = TEST_DATA_DIR / "stock_profiles" / stock_name
    if not stock_path.is_file():
        pytest.skip(f"Missing real stock fixture: {stock_path}")
    with pytest.raises(UnsupportedProfileError, match="Stock layout"):
        read_profile(stock_path)


def test_wrong_trailer_length_raises(tmp_path):
    data = _load_fixture_bytes(OFF1_PATH)
    data.append(0)
    profile_path = tmp_path / "wrong_trailer_len.prf"
    profile_path.write_bytes(data)
    with pytest.raises(InvalidProfileError, match="Trailer length"):
        read_profile(profile_path)


def test_nonexistent_path_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        read_profile(tmp_path / "nonexistent.prf")
