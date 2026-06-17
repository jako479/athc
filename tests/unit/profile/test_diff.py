"""Unit tests for diff_profiles — the structural profile diff."""

from __future__ import annotations

from dataclasses import replace

import pytest

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    ProfileType,
    SubstitutionPair,
    YardsToGo,
)
from athc.profile import ScalarChange, SlotChange, diff_profiles, situation_label
from athc.profile.rules import (
    FIELD_GOAL_PAT,
    PASS_MEDIUM_LEFT,
    PASS_SHORT_LEFT,
    PASS_SHORT_RIGHT,
    RUN_MIDDLE,
)
from tests.unit.profile.conftest import make_profile, replace_situation, weights

# Situation 8 = >5 / 1st / 0-1 / DEF5-35; baseline = (RM 4, PSL 3, PML 3).
N = 8


def _offense():
    return make_profile(ProfileType.OFFENSE)


def test_identical_profiles_have_empty_diff() -> None:
    a = _offense()
    d = diff_profiles(a, a)
    assert d.is_empty
    assert d.profile == () and d.situations == () and d.pat == ()


def test_profile_type_recorded() -> None:
    assert diff_profiles(_offense(), _offense()).profile_type == ProfileType.OFFENSE


def test_field_goal_range_change() -> None:
    a = _offense()
    b = replace(a, field_goal_range=40)
    assert diff_profiles(a, b).profile == (
        ScalarChange("field_goal_range", "20", "40"),
    )


def test_audibles_change() -> None:
    a = _offense()
    b = replace(a, use_audibles=True)
    assert diff_profiles(a, b).profile == (ScalarChange("audibles", "Off", "On"),)


def test_substitution_change() -> None:
    a = _offense()  # default subs: QB 80/90
    b = replace(
        a, substitutions=replace(a.substitutions, quarterbacks=SubstitutionPair(70, 85))
    )
    assert diff_profiles(a, b).profile == (ScalarChange("sub.QB", "80/90", "70/85"),)


def test_situation_stop_clock_change() -> None:
    a = _offense()
    b = replace_situation(a, N, stop_clock=True)
    d = diff_profiles(a, b)
    assert len(d.situations) == 1
    c = d.situations[0]
    assert c.number == N
    assert c.label == situation_label(a.situations[N - 1])
    assert c.stop == ScalarChange("stop", "No", "Yes")
    assert c.slots == ()


def test_situation_weight_only_change() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 6, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3
        ),
    )
    c = diff_profiles(a, b).situations[0]
    assert c.stop is None
    assert c.slots == (SlotChange(1, (RUN_MIDDLE, 4), (RUN_MIDDLE, 6)),)


def test_situation_category_change() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 4, PASS_SHORT_RIGHT, 3, PASS_MEDIUM_LEFT, 3
        ),
    )
    c = diff_profiles(a, b).situations[0]
    assert c.slots == (SlotChange(2, (PASS_SHORT_LEFT, 3), (PASS_SHORT_RIGHT, 3)),)


def test_situation_multiple_slot_changes() -> None:
    a = _offense()
    b = replace_situation(
        a,
        N,
        category_weights=weights(
            RUN_MIDDLE, 7, PASS_SHORT_LEFT, 3, PASS_SHORT_RIGHT, 3
        ),
    )
    c = diff_profiles(a, b).situations[0]
    assert c.slots == (
        SlotChange(1, (RUN_MIDDLE, 4), (RUN_MIDDLE, 7)),
        SlotChange(3, (PASS_MEDIUM_LEFT, 3), (PASS_SHORT_RIGHT, 3)),
    )


def test_unchanged_situations_excluded() -> None:
    a = _offense()
    b = replace_situation(a, N, stop_clock=True)
    d = diff_profiles(a, b)
    assert [c.number for c in d.situations] == [N]
    assert d.pat == () and d.profile == ()


def test_pat_change() -> None:
    a = _offense()
    idx = 6  # PAT situation 7
    new_pat = replace(
        a.pat_situations[idx],
        category_weights=weights(FIELD_GOAL_PAT, 8, 0x11, 0, 0x12, 0),
    )
    b = replace(
        a,
        pat_situations=(*a.pat_situations[:idx], new_pat, *a.pat_situations[idx + 1 :]),
    )
    d = diff_profiles(a, b)
    assert d.situations == () and len(d.pat) == 1
    c = d.pat[0]
    assert c.number == 7 and c.stop is None
    assert c.slots == (SlotChange(1, (FIELD_GOAL_PAT, 10), (FIELD_GOAL_PAT, 8)),)


def test_combined_changes_counts() -> None:
    a = _offense()
    b = replace(replace_situation(a, N, stop_clock=True), field_goal_range=40)
    d = diff_profiles(a, b)
    assert not d.is_empty
    assert len(d.profile) == 1 and len(d.situations) == 1 and d.pat == ()


def test_type_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="cannot diff"):
        diff_profiles(
            make_profile(ProfileType.OFFENSE), make_profile(ProfileType.DEFENSE)
        )


def test_situation_n_game_state_and_baseline() -> None:
    """Guard N: it must be a 1st-and-0-1 cell with the assumed baseline."""
    s = _offense().situations[N - 1]
    assert s.down == Down.FIRST
    assert s.yards_to_go == YardsToGo.ZERO_TO_ONE
    assert s.field_position == FieldPosition.DEF_5_TO_DEF_35
    cw = s.category_weights
    assert (cw.play_category1, cw.weight1) == (RUN_MIDDLE, 4)
