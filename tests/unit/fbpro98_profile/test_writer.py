"""Writer tests pinned against real game-produced fixtures.

A byte-identical round trip through every fixture is the writer's main check;
the rest writes what no fixture holds: a profile built from scratch, and an
edit to each field of a profile.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
    build_profile,
    read_profile,
    write_profile,
)

DATA = Path(__file__).resolve().parent / "data"
OFF1 = DATA / "TST-OFF1.prf"
ALL_FIXTURES = [
    OFF1,
    DATA / "TST-OFF2.prf",
    DATA / "TST-DEF1.prf",
    DATA / "TST-DEF2.prf",
    DATA / "TST-OFF1-AUD.prf",
    DATA / "TST-DEF1-AUD.prf",
]

TRAILER_OFFSET = 0x3CB7  # docs/formats/prf.md section 5


def _stem(path: Path) -> str:
    return path.stem


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


def _profile_from_scratch(profile_type: ProfileType) -> Profile:
    return Profile(
        profile_type=profile_type,
        substitutions=SubstitutionSettings.default(),
        situations=[
            Situation(stop_clock=False, category_weights=_weights(0, 0, 0, 0, 0, 0))
            for _ in range(Profile.NUMBER_SITUATIONS)
        ],
        pat_situations=[
            PatSituation(category_weights=_weights(0, 0, 0, 0, 0, 0))
            for _ in range(Profile.NUMBER_PAT_SITUATIONS)
        ],
        field_goal_range=30,
        use_audibles=False,
    )


# ---------- byte-identical round trip ----------


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=_stem)
def test_round_trip_byte_identity(tmp_path: Path, fixture_path: Path) -> None:
    prf_path = tmp_path / fixture_path.name
    shutil.copy2(fixture_path, prf_path)
    write_profile(read_profile(prf_path), prf_path)
    assert prf_path.read_bytes() == fixture_path.read_bytes()


def test_build_profile_reproduces_the_file() -> None:
    assert build_profile(read_profile(OFF1)) == OFF1.read_bytes()


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    folder = tmp_path / "out"
    folder.mkdir()
    prf_path = folder / OFF1.name
    shutil.copy2(OFF1, prf_path)
    write_profile(read_profile(prf_path), prf_path)
    assert [p.name for p in folder.iterdir()] == [OFF1.name]


# ---------- validation before packing ----------


def test_build_refuses_an_invalid_profile() -> None:
    profile = read_profile(OFF1)
    profile.field_goal_range = 51
    with pytest.raises(ValueError, match=r"field_goal_range must be in \[5, 50\]"):
        build_profile(profile)


def test_write_refuses_an_invalid_profile_and_writes_nothing(tmp_path: Path) -> None:
    profile = read_profile(OFF1)
    profile.situations[0].category_weights.weight1 = 11
    target = tmp_path / "bad.prf"
    with pytest.raises(ValueError):
        write_profile(profile, target)
    assert not target.exists()


# ---------- a profile the fixtures do not hold ----------


@pytest.mark.parametrize(
    ("profile_type", "trailer"),
    [(ProfileType.OFFENSE, b"\x00"), (ProfileType.DEFENSE, b"\x00\x00")],
    ids=["offense", "defense"],
)
def test_write_new_profile_from_scratch(
    tmp_path: Path, profile_type: ProfileType, trailer: bytes
) -> None:
    profile = _profile_from_scratch(profile_type)
    out_path = tmp_path / "new.prf"
    write_profile(profile, out_path)
    assert read_profile(out_path) == profile
    assert out_path.read_bytes()[TRAILER_OFFSET:] == trailer


def _edit_field_goal_range(profile: Profile) -> None:
    profile.field_goal_range = 45


def _edit_use_audibles(profile: Profile) -> None:
    profile.use_audibles = True


def _edit_substitutions(profile: Profile) -> None:
    profile.substitutions.quarterbacks = SubstitutionPair(out_percent=60, in_percent=70)


def _edit_situation(profile: Profile) -> None:
    profile.situations[0] = Situation(
        stop_clock=True, category_weights=_weights(0x16, 10, 0x1A, 3, 0x00, 0)
    )


def _edit_pat_situation(profile: Profile) -> None:
    profile.pat_situations[-1] = PatSituation(
        category_weights=_weights(0x11, 4, 0x12, 2, 0x10, 1)
    )


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(_edit_field_goal_range, id="field_goal_range"),
        pytest.param(_edit_use_audibles, id="use_audibles"),
        pytest.param(_edit_substitutions, id="substitutions"),
        pytest.param(_edit_situation, id="situations"),
        pytest.param(_edit_pat_situation, id="pat_situations"),
    ],
)
def test_write_edited_profile(tmp_path: Path, edit: Callable[[Profile], None]) -> None:
    edited = read_profile(OFF1)
    edit(edited)
    assert edited != read_profile(OFF1)
    out_path = tmp_path / "edited.prf"
    write_profile(edited, out_path)
    assert read_profile(out_path) == edited
