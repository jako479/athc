"""Writer tests pinned against real game-produced fixtures.

The `TST-*.prf` fixtures are the authoritative byte-level ground truth.
Writer correctness is established primarily by byte-identical round-trip
(`read_profile` → `write_profile` → compare to original bytes) across all
fixtures.
"""

from __future__ import annotations

import dataclasses
import shutil
from pathlib import Path

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionSettings,
    build_profile_bytes,
    parse_profile,
    read_profile,
    write_profile,
)
from athc.fbpro98_profile.schema import (
    F95_DATA_SIZE,
    F95_HEADER,
    F95_SUBSTITUTIONS,
    I95_DATA_SIZE,
    I95_HEADER,
    STOP_CLOCK_BIT,
)

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
OFF1_PATH = TEST_DATA_DIR / "TST-OFF1.prf"
OFF2_PATH = TEST_DATA_DIR / "TST-OFF2.prf"
DEF1_PATH = TEST_DATA_DIR / "TST-DEF1.prf"
DEF2_PATH = TEST_DATA_DIR / "TST-DEF2.prf"
OFF1_AUD_PATH = TEST_DATA_DIR / "TST-OFF1-AUD.prf"
DEF1_AUD_PATH = TEST_DATA_DIR / "TST-DEF1-AUD.prf"
ALL_FIXTURES = [OFF1_PATH, OFF2_PATH, DEF1_PATH, DEF2_PATH, OFF1_AUD_PATH, DEF1_AUD_PATH]

F95_SITUATIONS_OFFSET = F95_HEADER.size + F95_SUBSTITUTIONS.size  # 0x28
PAT_REGION_OFFSET = F95_SITUATIONS_OFFSET + Profile.NUMBER_SITUATIONS * 6 + 1  # +FG range byte


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real profile fixture: {path}")
    return path


def _copy_fixture(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copy2(_require_fixture(src), dest)
    return dest


def _minimal_profile(profile_type: ProfileType) -> Profile:
    """Construct a fully synthetic Profile with zero category weights and defaults."""
    zero_weights = CategoryWeights(
        play_category1=0,
        weight1=0,
        play_category2=0,
        weight2=0,
        play_category3=0,
        weight3=0,
    )
    situations = tuple(
        Situation.from_situation_number(n, stop_clock=False, category_weights=zero_weights)
        for n in range(1, Profile.NUMBER_SITUATIONS + 1)
    )
    pat_situations = tuple(
        PatSituation.from_situation_number(n, category_weights=zero_weights)
        for n in range(1, Profile.NUMBER_PAT_SITUATIONS + 1)
    )
    return Profile(
        profile_type=profile_type,
        substitutions=SubstitutionSettings.default(),
        situations=situations,
        pat_situations=pat_situations,
        field_goal_range=30,
        use_audibles=False,
    )


# ---------- byte-identity round-trip ----------


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_round_trip_byte_identity(tmp_path: Path, fixture_path: Path) -> None:
    prf_path = _copy_fixture(fixture_path, tmp_path)
    original_bytes = prf_path.read_bytes()

    profile = read_profile(prf_path)
    write_profile(profile, prf_path)

    assert prf_path.read_bytes() == original_bytes


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_build_profile_bytes_matches_file(fixture_path: Path) -> None:
    source_bytes = _require_fixture(fixture_path).read_bytes()
    profile = parse_profile(source_bytes, fixture_path)
    assert build_profile_bytes(profile) == source_bytes


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_write_profile_round_trips_through_model(tmp_path: Path, fixture_path: Path) -> None:
    original = read_profile(_require_fixture(fixture_path))
    out_path = tmp_path / "out.prf"
    write_profile(original, out_path)
    assert read_profile(out_path) == original


# ---------- block sizes and trailer ----------


def test_f95_block_size(tmp_path: Path) -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    _, data_size = F95_HEADER.unpack_from(buf, 0)
    assert data_size == F95_DATA_SIZE


def test_i95_block_size(tmp_path: Path) -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    i95_start = F95_HEADER.size + F95_DATA_SIZE
    _, data_size = I95_HEADER.unpack_from(buf, i95_start)
    assert data_size == I95_DATA_SIZE


def test_offense_trailer_single_nul(tmp_path: Path) -> None:
    profile = read_profile(_require_fixture(OFF1_PATH))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    assert len(buf) % 2 == 0
    assert buf[-1] == 0x00


def test_defense_trailer_two_nuls(tmp_path: Path) -> None:
    profile = read_profile(_require_fixture(DEF1_PATH))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    assert len(buf) % 2 == 1
    assert buf[-2:] == b"\x00\x00"


# ---------- Stop-Clock bit packing ----------


def test_stop_clock_bit_set_on_situation_372_weight1(tmp_path: Path) -> None:
    """TST-DEF2 has stop_clock=True at situation 372 (weight1=2); the bit must pack into the weight1 byte."""
    EXPECTED_SITUATION_NUMBER = 372
    EXPECTED_WEIGHT1 = 2
    profile = read_profile(_require_fixture(DEF2_PATH))
    situation = profile.situations[EXPECTED_SITUATION_NUMBER - 1]
    assert situation.stop_clock is True
    assert situation.category_weights.weight1 == EXPECTED_WEIGHT1
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    weight1_offset = F95_SITUATIONS_OFFSET + (EXPECTED_SITUATION_NUMBER - 1) * 6 + 1
    weight1_byte = buf[weight1_offset]
    assert (weight1_byte & STOP_CLOCK_BIT) != 0
    assert (weight1_byte & 0x7F) == EXPECTED_WEIGHT1


def test_pat_weight1_no_stop_clock_bit_set(tmp_path: Path) -> None:
    """PAT records have no Stop-Clock bit; weight1's bit 7 must be clear."""
    profile = read_profile(_require_fixture(OFF1_PATH))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    buf = out_path.read_bytes()
    for i in range(Profile.NUMBER_PAT_SITUATIONS):
        weight1_offset = PAT_REGION_OFFSET + i * 6 + 1
        assert (buf[weight1_offset] & STOP_CLOCK_BIT) == 0, f"PAT record {i} weight1 has bit 7 set"


@pytest.mark.parametrize("fixture_path", [OFF1_PATH, OFF1_AUD_PATH], ids=lambda p: p.stem)
def test_i95_mirrors_f95_field_goal_range_and_use_audibles(tmp_path: Path, fixture_path: Path) -> None:
    profile = read_profile(_require_fixture(fixture_path))
    out_path = tmp_path / "out.prf"
    write_profile(profile, out_path)
    reparsed = read_profile(out_path)
    # If F95 and I95 disagreed, read_profile would have raised InvalidProfileError.
    assert reparsed.field_goal_range == profile.field_goal_range
    assert reparsed.use_audibles == profile.use_audibles


# ---------- mutation round-trips ----------


def test_round_trip_modified_field_goal_range(tmp_path: Path) -> None:
    original = read_profile(_require_fixture(OFF1_PATH))
    modified = dataclasses.replace(original, field_goal_range=45)
    out_path = tmp_path / "out.prf"
    write_profile(modified, out_path)
    reloaded = read_profile(out_path)
    assert reloaded.field_goal_range == 45


def test_round_trip_modified_use_audibles(tmp_path: Path) -> None:
    original = read_profile(_require_fixture(OFF1_PATH))
    toggled = dataclasses.replace(original, use_audibles=not original.use_audibles)
    out_path = tmp_path / "out.prf"
    write_profile(toggled, out_path)
    reloaded = read_profile(out_path)
    assert reloaded.use_audibles is not original.use_audibles


# ---------- use_audibles round-trips on real audible-enabled fixtures ----------


@pytest.mark.parametrize("fixture_path", [OFF1_AUD_PATH, DEF1_AUD_PATH], ids=lambda p: p.stem)
def test_use_audibles_preserved_on_round_trip(tmp_path: Path, fixture_path: Path) -> None:
    """Reading and writing a use_audibles=True fixture must not silently clear the flag."""
    original = read_profile(_require_fixture(fixture_path))
    assert original.use_audibles is True
    out_path = tmp_path / "out.prf"
    write_profile(original, out_path)
    reloaded = read_profile(out_path)
    assert reloaded.use_audibles is True


# ---------- workflow tests: update existing / write new ----------


def test_update_existing_offense_in_place(tmp_path: Path) -> None:
    copy_path = _copy_fixture(OFF1_PATH, tmp_path)
    profile = read_profile(copy_path)
    modified = dataclasses.replace(profile, field_goal_range=45)
    write_profile(modified, copy_path)
    reloaded = read_profile(copy_path)
    assert reloaded.field_goal_range == 45
    assert reloaded.profile_type == ProfileType.OFFENSE


def test_update_existing_defense_in_place(tmp_path: Path) -> None:
    copy_path = _copy_fixture(DEF1_PATH, tmp_path)
    profile = read_profile(copy_path)
    modified = dataclasses.replace(profile, use_audibles=not profile.use_audibles)
    write_profile(modified, copy_path)
    reloaded = read_profile(copy_path)
    assert reloaded.use_audibles is not profile.use_audibles
    assert reloaded.profile_type == ProfileType.DEFENSE


def test_write_new_offense_from_scratch(tmp_path: Path) -> None:
    profile = _minimal_profile(ProfileType.OFFENSE)
    out_path = tmp_path / "new_offense.prf"
    write_profile(profile, out_path)
    reloaded = read_profile(out_path)
    assert reloaded == profile
    buf = out_path.read_bytes()
    assert len(buf) % 2 == 0
    assert buf[-1] == 0x00


def test_write_new_defense_from_scratch(tmp_path: Path) -> None:
    profile = _minimal_profile(ProfileType.DEFENSE)
    out_path = tmp_path / "new_defense.prf"
    write_profile(profile, out_path)
    reloaded = read_profile(out_path)
    assert reloaded == profile
    buf = out_path.read_bytes()
    assert len(buf) % 2 == 1
    assert buf[-2:] == b"\x00\x00"


@pytest.mark.parametrize("fixture_path", [OFF1_PATH, OFF2_PATH, OFF1_AUD_PATH], ids=lambda p: p.stem)
def test_reconstructed_offense_matches_fixture_bytes(tmp_path: Path, fixture_path: Path) -> None:
    original = read_profile(_require_fixture(fixture_path))
    reconstructed = Profile(
        profile_type=original.profile_type,
        substitutions=original.substitutions,
        situations=original.situations,
        pat_situations=original.pat_situations,
        field_goal_range=original.field_goal_range,
        use_audibles=original.use_audibles,
    )
    out_path = tmp_path / "out.prf"
    write_profile(reconstructed, out_path)
    assert out_path.read_bytes() == fixture_path.read_bytes()


@pytest.mark.parametrize("fixture_path", [DEF1_PATH, DEF2_PATH, DEF1_AUD_PATH], ids=lambda p: p.stem)
def test_reconstructed_defense_matches_fixture_bytes(tmp_path: Path, fixture_path: Path) -> None:
    original = read_profile(_require_fixture(fixture_path))
    reconstructed = Profile(
        profile_type=original.profile_type,
        substitutions=original.substitutions,
        situations=original.situations,
        pat_situations=original.pat_situations,
        field_goal_range=original.field_goal_range,
        use_audibles=original.use_audibles,
    )
    out_path = tmp_path / "out.prf"
    write_profile(reconstructed, out_path)
    assert out_path.read_bytes() == fixture_path.read_bytes()
