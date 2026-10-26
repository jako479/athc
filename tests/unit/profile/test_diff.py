"""Unit tests for diff_profiles — the structural profile diff."""

from __future__ import annotations

import pytest

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    Profile,
    ProfileType,
    SubstitutionPair,
    YardsToGo,
)
from athc.profile import (
    ProfileTypeMismatchError,
    ScalarChange,
    SituationChange,
    SlotChange,
    diff_profiles,
)
from athc.profile.rules import (
    FAKE_FIELD_GOAL_PASS,
    FAKE_FIELD_GOAL_RUN,
    FIELD_GOAL_PAT,
    PASS_MEDIUM_LEFT,
    PASS_SHORT_LEFT,
    PASS_SHORT_RIGHT,
    RUN_MIDDLE,
)
from tests.unit.profile.conftest import (
    edited,
    make_profile,
    replace_situation,
    weights,
)

# Situation 8 = >5 / 1st / 0-1 / DEF5-35; baseline = (RM 4, PSL 3, PML 3).
N = 8
N_LABEL = ">5 1st 0-1 DEF5-35 Ahd8+"


def _offense():
    return make_profile(ProfileType.OFFENSE)


def test_identical_profiles_have_empty_diff() -> None:
    a = _offense()
    d = diff_profiles(a, a)
    assert d.is_empty
    assert d.profile == () and d.situations == () and d.pat == ()


@pytest.mark.parametrize("ptype", [ProfileType.OFFENSE, ProfileType.DEFENSE])
def test_profile_type_recorded(ptype: ProfileType) -> None:
    profile = make_profile(ptype)
    assert diff_profiles(profile, profile).profile_type == ptype


def test_field_goal_range_change() -> None:
    a = _offense()
    b = edited(a, field_goal_range=40)
    assert diff_profiles(a, b).profile == (
        ScalarChange("field_goal_range", "20", "40"),
    )


def test_audibles_change() -> None:
    a = _offense()
    b = edited(a, use_audibles=True)
    assert diff_profiles(a, b).profile == (ScalarChange("audibles", "Off", "On"),)


def test_substitution_change() -> None:
    a = _offense()  # default subs: QB 80/90
    b = edited(a)
    b.substitutions.quarterbacks = SubstitutionPair(70, 85)
    assert diff_profiles(a, b).profile == (ScalarChange("sub.QB", "80/90", "70/85"),)


def test_situation_stop_clock_change() -> None:
    a = _offense()
    b = replace_situation(a, N, stop_clock=True)
    assert diff_profiles(a, b).situations == (
        SituationChange(N, N_LABEL, ScalarChange("stop", "No", "Yes"), ()),
    )


def test_situation_weight_only_change() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 6, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3
        ),
    )
    assert diff_profiles(a, b).situations == (
        SituationChange(
            N, N_LABEL, None, (SlotChange(1, (RUN_MIDDLE, 4), (RUN_MIDDLE, 6)),)
        ),
    )


def test_situation_category_change() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 4, PASS_SHORT_RIGHT, 3, PASS_MEDIUM_LEFT, 3
        ),
    )
    slot = SlotChange(2, (PASS_SHORT_LEFT, 3), (PASS_SHORT_RIGHT, 3))
    assert diff_profiles(a, b).situations == (
        SituationChange(N, N_LABEL, None, (slot,)),
    )


def test_situation_multiple_slot_changes() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 7, PASS_SHORT_LEFT, 3, PASS_SHORT_RIGHT, 3
        ),
    )
    slots = (
        SlotChange(1, (RUN_MIDDLE, 4), (RUN_MIDDLE, 7)),
        SlotChange(3, (PASS_MEDIUM_LEFT, 3), (PASS_SHORT_RIGHT, 3)),
    )
    assert diff_profiles(a, b).situations == (SituationChange(N, N_LABEL, None, slots),)


def test_unchanged_situations_excluded() -> None:
    a = _offense()
    b = replace_situation(a, N, stop_clock=True)
    d = diff_profiles(a, b)
    assert [c.number for c in d.situations] == [N]
    assert d.pat == () and d.profile == ()


def test_pat_change() -> None:
    a = _offense()
    idx = 6  # PAT situation 7
    b = edited(a)
    b.pat_situations[idx].category_weights = weights(
        FIELD_GOAL_PAT, 8, FAKE_FIELD_GOAL_RUN, 0, FAKE_FIELD_GOAL_PASS, 0
    )
    d = diff_profiles(a, b)
    slot = SlotChange(1, (FIELD_GOAL_PAT, 10), (FIELD_GOAL_PAT, 8))
    assert d.situations == ()
    assert d.pat == (SituationChange(7, ">5 Ahd1", None, (slot,)),)


def test_combined_changes_counts() -> None:
    a = _offense()
    b = edited(replace_situation(a, N, stop_clock=True), field_goal_range=40)
    d = diff_profiles(a, b)
    assert not d.is_empty
    assert len(d.profile) == 1 and len(d.situations) == 1 and d.pat == ()


# Both paths given name both files; with one or none, neither is named.
@pytest.mark.parametrize(
    ("paths", "message"),
    [
        ({}, "Cannot compare offense with defense."),
        (
            {"a_path": "a.prf", "b_path": "b.prf"},
            "Cannot compare a.prf (offense) with b.prf (defense).",
        ),
        ({"a_path": "a.prf"}, "Cannot compare offense with defense."),
        ({"b_path": "b.prf"}, "Cannot compare offense with defense."),
    ],
    ids=["no_paths", "both_paths", "a_path_only", "b_path_only"],
)
def test_type_mismatch_raises(paths: dict[str, str], message: str) -> None:
    with pytest.raises(ProfileTypeMismatchError) as exc:
        diff_profiles(
            make_profile(ProfileType.OFFENSE),
            make_profile(ProfileType.DEFENSE),
            **paths,
        )
    assert str(exc.value) == message


def test_situation_n_game_state_and_baseline() -> None:
    """Guard N: it must be a 1st-and-0-1 cell with the assumed baseline."""
    state = Profile.game_state(N)
    assert state.down == Down.FIRST
    assert state.yards_to_go == YardsToGo.ZERO_TO_ONE
    assert state.field_position == FieldPosition.DEF_5_TO_DEF_35
    cw = _offense().situations[N - 1].category_weights
    assert (cw.play_category1, cw.weight1) == (RUN_MIDDLE, 4)
