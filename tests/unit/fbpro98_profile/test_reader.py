"""Reader tests pinned against real game-produced fixtures.

Every expected value is the fixture's bytes decoded at the offsets in
docs/formats/prf.md: the fixtures are the ground truth, never the reader.
Error cases mutate those bytes at the spec's offsets.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from athc.errors import AthcError
from athc.fbpro98_profile import (
    CategoryWeights,
    InvalidProfileError,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
    UnsupportedProfileError,
    parse_profile,
    read_profile,
)

DATA = Path(__file__).resolve().parent / "data"
OFF1 = DATA / "TST-OFF1.prf"
OFF2 = DATA / "TST-OFF2.prf"
DEF1 = DATA / "TST-DEF1.prf"
DEF2 = DATA / "TST-DEF2.prf"
OFF1_AUD = DATA / "TST-OFF1-AUD.prf"
DEF1_AUD = DATA / "TST-DEF1-AUD.prf"
OFF1_PL = DATA / "TST-OFF1-PL.prf"
DEF1_PL = DATA / "TST-DEF1-PL.prf"
STOCK = DATA / "stock_profiles"

# File offsets from docs/formats/prf.md; the F95 data starts at 0x08.
SUBSTITUTIONS_OFFSET = 0x08
SITUATIONS_OFFSET = 0x28
FIELD_GOAL_RANGE_OFFSET = 0x3B38
PAT_SITUATIONS_OFFSET = 0x3B39
F95_USE_AUDIBLES_OFFSET = 0x3CA1
I95_OFFSET = 0x3CA5
I95_DATA_OFFSET = 0x3CAD
TRAILER_OFFSET = 0x3CB7
EMBEDDED_BLOCK_IDS = [b"G95:", b"J95:", b"S98:"]


def _stem(path: Path) -> str:
    return path.stem


def _pair(out_percent: int, in_percent: int) -> SubstitutionPair:
    return SubstitutionPair(out_percent=out_percent, in_percent=in_percent)


def _weights(
    play_category1: int,
    weight1: int,
    play_category2: int,
    weight2: int,
    play_category3: int,
    weight3: int,
) -> CategoryWeights:
    return CategoryWeights(
        play_category1=play_category1,
        weight1=weight1,
        play_category2=play_category2,
        weight2=weight2,
        play_category3=play_category3,
        weight3=weight3,
    )


DEFAULT_PAIR = _pair(80, 90)
OFFENSE_SUBSTITUTIONS = SubstitutionSettings(
    offensive_linemen=_pair(95, 98),
    quarterbacks=_pair(75, 80),
    running_backs=_pair(95, 98),
    receivers=_pair(95, 98),
    defensive_linemen=DEFAULT_PAIR,
    linebackers=DEFAULT_PAIR,
    defensive_backs=DEFAULT_PAIR,
    kickers=DEFAULT_PAIR,
)
DEFENSE_SUBSTITUTIONS = SubstitutionSettings(
    offensive_linemen=DEFAULT_PAIR,
    quarterbacks=DEFAULT_PAIR,
    running_backs=DEFAULT_PAIR,
    receivers=DEFAULT_PAIR,
    defensive_linemen=_pair(96, 98),
    linebackers=_pair(96, 98),
    defensive_backs=_pair(96, 98),
    kickers=DEFAULT_PAIR,
)
# PAT records 1 and 60 of every fixture: Field Goal / PAT at weight 1.
PAT_FIELD_GOAL = _weights(16, 1, 0, 0, 0, 0)


@dataclass(frozen=True)
class Record:
    """A situation record as the spec decodes it (stop clock is bit 7 of weight 1)."""

    weights: CategoryWeights
    stop_clock: bool = False


@dataclass(frozen=True)
class FixtureExpectation:
    path: Path
    profile_type: ProfileType
    field_goal_range: int
    substitutions: SubstitutionSettings
    first_situation: Record
    last_situation: Record
    stop_clock_count: int
    stop_clock_ends: tuple[tuple[int, Record], ...]
    """The first and last flagged situations with their numbers; empty when none."""


EXPECTATIONS = [
    FixtureExpectation(
        path=OFF1,
        profile_type=ProfileType.OFFENSE,
        field_goal_range=36,
        substitutions=OFFENSE_SUBSTITUTIONS,
        first_situation=Record(_weights(10, 1, 9, 10, 12, 1)),
        last_situation=Record(_weights(19, 10, 19, 10, 19, 1)),
        stop_clock_count=522,
        stop_clock_ends=(
            (1023, Record(_weights(11, 5, 9, 6, 12, 5), stop_clock=True)),
            (2387, Record(_weights(6, 10, 9, 10, 3, 1), stop_clock=True)),
        ),
    ),
    FixtureExpectation(
        path=OFF2,
        profile_type=ProfileType.OFFENSE,
        field_goal_range=36,
        substitutions=OFFENSE_SUBSTITUTIONS,
        first_situation=Record(_weights(9, 10, 11, 1, 12, 1)),
        last_situation=Record(_weights(9, 9, 12, 9, 11, 1), stop_clock=True),
        stop_clock_count=617,
        stop_clock_ends=(
            (888, Record(_weights(3, 10, 2, 10, 15, 2), stop_clock=True)),
            (2520, Record(_weights(9, 9, 12, 9, 11, 1), stop_clock=True)),
        ),
    ),
    FixtureExpectation(
        path=DEF1,
        profile_type=ProfileType.DEFENSE,
        field_goal_range=36,
        substitutions=DEFENSE_SUBSTITUTIONS,
        first_situation=Record(_weights(1, 10, 3, 10, 4, 1)),
        last_situation=Record(_weights(19, 10, 19, 10, 10, 0)),
        stop_clock_count=0,
        stop_clock_ends=(),
    ),
    FixtureExpectation(
        path=DEF2,
        profile_type=ProfileType.DEFENSE,
        field_goal_range=36,
        substitutions=DEFENSE_SUBSTITUTIONS,
        first_situation=Record(_weights(2, 10, 3, 9, 1, 1)),
        last_situation=Record(_weights(19, 10, 19, 10, 19, 1)),
        stop_clock_count=322,
        stop_clock_ends=(
            (372, Record(_weights(10, 2, 7, 10, 6, 1), stop_clock=True)),
            (2394, Record(_weights(10, 10, 7, 10, 13, 1), stop_clock=True)),
        ),
    ),
]


def _expectation_id(expected: FixtureExpectation) -> str:
    return expected.path.stem


def _as_record(situation: Situation) -> Record:
    return Record(situation.category_weights, situation.stop_clock)


# ---------- pinned values ----------


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_profile_type(expected: FixtureExpectation) -> None:
    assert read_profile(expected.path).profile_type is expected.profile_type


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_field_goal_range(expected: FixtureExpectation) -> None:
    assert read_profile(expected.path).field_goal_range == expected.field_goal_range


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (OFF1, False),
        (OFF2, False),
        (DEF1, False),
        (DEF2, False),
        (OFF1_AUD, True),
        (DEF1_AUD, True),
    ],
    ids=["OFF1", "OFF2", "DEF1", "DEF2", "OFF1-AUD", "DEF1-AUD"],
)
def test_use_audibles(path: Path, expected: bool) -> None:
    assert read_profile(path).use_audibles is expected


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_substitutions(expected: FixtureExpectation) -> None:
    assert read_profile(expected.path).substitutions == expected.substitutions


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_first_and_last_situation(expected: FixtureExpectation) -> None:
    profile = read_profile(expected.path)
    first, last = profile.situations[0], profile.situations[-1]
    assert (first.situation_number, _as_record(first)) == (1, expected.first_situation)
    assert (last.situation_number, _as_record(last)) == (2520, expected.last_situation)


@pytest.mark.parametrize(
    ("situation_number", "expected"),
    [
        (888, Record(_weights(3, 10, 2, 10, 15, 2), stop_clock=True)),
        (430, Record(_weights(19, 5, 19, 2, 0x1A, 3))),
    ],
    ids=["weight 10 with stop clock", "play category 0x1A"],
)
def test_situation_record_at_the_limits(
    situation_number: int, expected: Record
) -> None:
    profile = read_profile(OFF2)
    assert _as_record(profile.situations[situation_number - 1]) == expected


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_first_and_last_pat_situation(expected: FixtureExpectation) -> None:
    profile = read_profile(expected.path)
    first, last = profile.pat_situations[0], profile.pat_situations[-1]
    assert (first.situation_number, first.category_weights) == (1, PAT_FIELD_GOAL)
    assert (last.situation_number, last.category_weights) == (60, PAT_FIELD_GOAL)


@pytest.mark.parametrize("expected", EXPECTATIONS, ids=_expectation_id)
def test_stop_clock_situations(expected: FixtureExpectation) -> None:
    flagged = read_profile(expected.path).stop_clock_situations
    assert len(flagged) == expected.stop_clock_count
    ends = tuple((n, _as_record(s)) for n, s in flagged[:1] + flagged[-1:])
    assert ends == expected.stop_clock_ends


# ---------- public API surface ----------


def test_parse_profile_from_buffer_matches_read_profile() -> None:
    assert parse_profile(OFF1.read_bytes()) == read_profile(OFF1)


@pytest.mark.parametrize("error", [InvalidProfileError, UnsupportedProfileError])
def test_profile_errors_are_athc_errors(error: type[Exception]) -> None:
    assert issubclass(error, AthcError)


def test_error_names_the_path_first(tmp_path: Path) -> None:
    profile_path = tmp_path / "tiny.prf"
    profile_path.write_bytes(b"")
    with pytest.raises(InvalidProfileError) as exc:
        read_profile(profile_path)
    assert str(exc.value) == f"{profile_path}: File too small to contain F95 block."
    assert exc.value.path == profile_path


def test_nonexistent_path_raises_oserror(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        read_profile(tmp_path / "nonexistent.prf")


# ---------- structural validation: mutated bytes → InvalidProfileError ----------


def _bytes_of(path: Path) -> bytearray:
    return bytearray(path.read_bytes())


def test_file_too_small_for_f95_rejected() -> None:
    with pytest.raises(InvalidProfileError, match="too small to contain F95"):
        parse_profile(b"F95:" + b"\x00" * 4)


def test_file_too_small_for_i95_rejected() -> None:
    data = _bytes_of(OFF1)[: I95_OFFSET + 5]
    with pytest.raises(InvalidProfileError, match="too small to contain I95"):
        parse_profile(bytes(data))


def test_invalid_f95_header_rejected() -> None:
    data = _bytes_of(OFF1)
    data[0:4] = b"BAD!"
    with pytest.raises(InvalidProfileError, match=r"Invalid header 'BAD!' at 0x0\."):
        parse_profile(bytes(data))


def test_wrong_f95_data_size_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<I", data, 4, 99)
    with pytest.raises(InvalidProfileError, match="F95 data size"):
        parse_profile(bytes(data))


def test_invalid_substitution_pair_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<HH", data, SUBSTITUTIONS_OFFSET + 4, 99, 50)
    with pytest.raises(InvalidProfileError, match="substitution pair for quarterbacks"):
        parse_profile(bytes(data))


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (SITUATIONS_OFFSET, 0xFF),
        (SITUATIONS_OFFSET + 1, 0x8B),
        (SITUATIONS_OFFSET + 3, 11),
    ],
    ids=["play category 0xFF", "weight 11 under the stop-clock bit", "weight 11"],
)
def test_invalid_situation_record_rejected(offset: int, value: int) -> None:
    data = _bytes_of(OFF1)
    data[offset] = value
    with pytest.raises(
        InvalidProfileError, match="Invalid situation record at index 0"
    ):
        parse_profile(bytes(data))


@pytest.mark.parametrize(
    "value", [0x81, 0x0B], ids=["weight 1 with the stop-clock bit", "weight 11"]
)
def test_invalid_pat_situation_record_rejected(value: int) -> None:
    data = _bytes_of(OFF1)
    data[PAT_SITUATIONS_OFFSET + 1] = value
    with pytest.raises(
        InvalidProfileError, match="Invalid PAT situation record at index 0"
    ):
        parse_profile(bytes(data))


def _with_field_goal_range(value: int) -> bytes:
    data = _bytes_of(OFF1)
    data[FIELD_GOAL_RANGE_OFFSET] = value
    data[I95_DATA_OFFSET + 3] = value
    return bytes(data)


@pytest.mark.parametrize("value", [5, 50])
def test_field_goal_range_at_the_limits_accepted(value: int) -> None:
    assert parse_profile(_with_field_goal_range(value)).field_goal_range == value


@pytest.mark.parametrize("value", [4, 51])
def test_f95_field_goal_range_past_the_limits_rejected(value: int) -> None:
    with pytest.raises(
        InvalidProfileError, match=rf"F95 field_goal_range {value} outside \[5, 50\]"
    ):
        parse_profile(_with_field_goal_range(value))


@pytest.mark.parametrize("value", [4, 51])
def test_i95_field_goal_range_past_the_limits_rejected(value: int) -> None:
    data = _bytes_of(OFF1)
    data[I95_DATA_OFFSET + 3] = value
    with pytest.raises(
        InvalidProfileError, match=rf"I95 field_goal_range {value} outside \[5, 50\]"
    ):
        parse_profile(bytes(data))


def test_f95_use_audibles_out_of_range_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<I", data, F95_USE_AUDIBLES_OFFSET, 2)
    with pytest.raises(InvalidProfileError, match="F95 use_audibles 2"):
        parse_profile(bytes(data))


def test_i95_use_audibles_out_of_range_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<I", data, I95_DATA_OFFSET + 6, 2)
    with pytest.raises(InvalidProfileError, match="I95 use_audibles 2"):
        parse_profile(bytes(data))


def test_invalid_i95_header_rejected() -> None:
    data = _bytes_of(OFF1)
    data[I95_OFFSET : I95_OFFSET + 4] = b"BAD!"
    with pytest.raises(InvalidProfileError, match="Invalid header 'BAD!' at 0x3ca5"):
        parse_profile(bytes(data))


def test_wrong_i95_data_size_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<I", data, I95_OFFSET + 4, 99)
    with pytest.raises(InvalidProfileError, match="I95 data size"):
        parse_profile(bytes(data))


def test_invalid_profile_type_rejected() -> None:
    data = _bytes_of(OFF1)
    data[I95_DATA_OFFSET] = 5
    with pytest.raises(InvalidProfileError, match="profile_type 5"):
        parse_profile(bytes(data))


def test_nonzero_reserved_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<H", data, I95_DATA_OFFSET + 1, 1)
    with pytest.raises(InvalidProfileError, match="reserved"):
        parse_profile(bytes(data))


def test_f95_i95_field_goal_range_mismatch_rejected() -> None:
    data = _bytes_of(OFF1)
    data[I95_DATA_OFFSET + 3] = 37
    with pytest.raises(
        InvalidProfileError, match=r"F95 field_goal_range \(36\) != I95 .*\(37\)"
    ):
        parse_profile(bytes(data))


def test_f95_i95_use_audibles_mismatch_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<I", data, F95_USE_AUDIBLES_OFFSET, 1)
    with pytest.raises(
        InvalidProfileError, match=r"F95 use_audibles \(1\) != I95 .*\(0\)"
    ):
        parse_profile(bytes(data))


@pytest.mark.parametrize("byte", [0xAB, 0x69], ids=["arbitrary", "stock 0x69"])
def test_invalid_trailer_byte_rejected(byte: int) -> None:
    data = _bytes_of(OFF1)
    data[-1] = byte
    with pytest.raises(InvalidProfileError, match="Trailer byte"):
        parse_profile(bytes(data))


@pytest.mark.parametrize("path", [OFF1, DEF1], ids=_stem)
@pytest.mark.parametrize(
    "resize",
    [lambda data: data + b"\x00", lambda data: data[:-1]],
    ids=["one byte too long", "one byte too short"],
)
def test_wrong_trailer_length_rejected(
    path: Path, resize: Callable[[bytes], bytes]
) -> None:
    with pytest.raises(InvalidProfileError, match="Trailer length"):
        parse_profile(resize(path.read_bytes()))


# ---------- unsupported variants → UnsupportedProfileError ----------


@pytest.mark.parametrize("name", ["OFF1.PRF", "DEF1.PRF"])
def test_real_stock_profile_rejected(name: str) -> None:
    with pytest.raises(UnsupportedProfileError, match="Stock layout"):
        read_profile(STOCK / name)


@pytest.mark.parametrize("path", [OFF1_PL, DEF1_PL], ids=_stem)
def test_real_embedded_game_plan_profile_rejected(path: Path) -> None:
    """The game writes the game plan blocks between F95 and I95."""
    with pytest.raises(UnsupportedProfileError, match="'G95:' before I95"):
        read_profile(path)


@pytest.mark.parametrize("block_id", EMBEDDED_BLOCK_IDS)
def test_embedded_block_before_i95_rejected(block_id: bytes) -> None:
    data = _bytes_of(OFF1)
    data[I95_OFFSET : I95_OFFSET + 4] = block_id
    with pytest.raises(UnsupportedProfileError, match="before I95"):
        parse_profile(bytes(data))


def test_embedded_game_plan_count_rejected() -> None:
    data = _bytes_of(OFF1)
    struct.pack_into("<H", data, I95_DATA_OFFSET + 4, 1)
    with pytest.raises(UnsupportedProfileError, match=r"blocks \(1\) not supported"):
        parse_profile(bytes(data))


@pytest.mark.parametrize("block_id", EMBEDDED_BLOCK_IDS)
def test_embedded_block_after_i95_rejected(block_id: bytes) -> None:
    data = _bytes_of(OFF1)[:TRAILER_OFFSET] + block_id + b"\x00" * 4
    with pytest.raises(UnsupportedProfileError, match="after I95"):
        parse_profile(bytes(data))
