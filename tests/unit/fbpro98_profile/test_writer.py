"""Writer tests pinned against real game-produced fixtures.

A byte-identical round trip through every fixture is the writer's main check;
the rest writes what no fixture holds: a profile built from scratch, and an
edit to each field of a profile.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import replace
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
    zero_weights = _weights(0, 0, 0, 0, 0, 0)
    return Profile(
        profile_type=profile_type,
        substitutions=SubstitutionSettings.default(),
        situations=tuple(
            Situation(stop_clock=False, category_weights=zero_weights)
            for _ in range(Profile.NUMBER_SITUATIONS)
        ),
        pat_situations=tuple(
            PatSituation(category_weights=zero_weights)
            for _ in range(Profile.NUMBER_PAT_SITUATIONS)
        ),
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


def _edit_substitutions(profile: Profile) -> Profile:
    quarterbacks = SubstitutionPair(out_percent=60, in_percent=70)
    substitutions = replace(profile.substitutions, quarterbacks=quarterbacks)
    return replace(profile, substitutions=substitutions)


def _edit_situation(profile: Profile) -> Profile:
    situations = list(profile.situations)
    situations[0] = Situation(
        stop_clock=True, category_weights=_weights(0x16, 10, 0x1A, 3, 0x00, 0)
    )
    return replace(profile, situations=tuple(situations))


def _edit_pat_situation(profile: Profile) -> Profile:
    pat_situations = list(profile.pat_situations)
    pat_situations[-1] = PatSituation(
        category_weights=_weights(0x11, 4, 0x12, 2, 0x10, 1)
    )
    return replace(profile, pat_situations=tuple(pat_situations))


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda p: replace(p, field_goal_range=45), id="field_goal_range"),
        pytest.param(lambda p: replace(p, use_audibles=True), id="use_audibles"),
        pytest.param(_edit_substitutions, id="substitutions"),
        pytest.param(_edit_situation, id="situations"),
        pytest.param(_edit_pat_situation, id="pat_situations"),
    ],
)
def test_write_edited_profile(
    tmp_path: Path, edit: Callable[[Profile], Profile]
) -> None:
    edited = edit(read_profile(OFF1))
    out_path = tmp_path / "edited.prf"
    write_profile(edited, out_path)
    assert read_profile(out_path) == edited
