"""Unit tests for profile display labels."""

from __future__ import annotations

from athc.fbpro98_profile import Profile, ProfileType
from athc.profile import category_label, pat_label, situation_label
from athc.profile.display import sub_label
from athc.profile.rules import (
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_LEFT,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    PUNT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_MIDDLE,
)
from tests.unit.profile.conftest import make_profile

OFFENSE = ProfileType.OFFENSE
DEFENSE = ProfileType.DEFENSE


def test_offense_category_labels_are_caps() -> None:
    assert category_label(RUN_MIDDLE, OFFENSE) == "RM"
    assert category_label(PASS_SHORT_LEFT, OFFENSE) == "PSL"
    assert category_label(RAZZLE_DAZZLE_PASS, OFFENSE) == "PRD"
    assert category_label(GOAL_LINE_RUN, OFFENSE) == "GLR"


def test_defense_labels_words_and_collapse_directions() -> None:
    assert category_label(RUN_MIDDLE, DEFENSE) == "RunMiddle"
    assert category_label(GOAL_LINE_PASS, DEFENSE) == "GLpass"
    directions = {
        category_label(c, DEFENSE)
        for c in (PASS_SHORT_LEFT, PASS_SHORT_MIDDLE, PASS_SHORT_RIGHT)
    }
    assert directions == {"PassShort"}


def test_codes_outside_side_set_fall_back_to_hex() -> None:
    assert (
        category_label(RAZZLE_DAZZLE_RUN, OFFENSE) == "0x01"
    )  # offense has no razzle-run pick
    assert category_label(PASS_LONG_LEFT, OFFENSE) == "0x07"  # offense allows only PLR
    assert category_label(PUNT, DEFENSE) == "0x13"


def test_situation_label_format() -> None:
    assert situation_label(Profile.game_state(8)) == ">5 1st 0-1 DEF5-35 Ahd8+"


def test_pat_label_format() -> None:
    assert pat_label(Profile.pat_game_state(7)) == ">5 Ahd1"


def test_sub_label() -> None:
    assert sub_label("quarterbacks") == "QB"
    assert sub_label("defensive_backs") == "DB"


def test_every_situation_and_pat_labels_without_keyerror() -> None:
    profile = make_profile(OFFENSE)
    assert all(
        len(situation_label(state).split()) == 5
        for _, state, _ in profile.iter_situations()
    )
    assert all(
        len(pat_label(state).split()) == 2
        for _, state, _ in profile.iter_pat_situations()
    )
