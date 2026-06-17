"""Unit tests for profile display labels."""

from __future__ import annotations

from athc.fbpro98_profile import PatSituation, ProfileType, Situation
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
from tests.unit.profile.conftest import make_profile, weights

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
    s = Situation.from_situation_number(
        8, stop_clock=False, category_weights=weights(RUN_MIDDLE, 4, 0x0D, 3, 0x0A, 3)
    )
    assert situation_label(s) == ">5 1st 0-1 DEF5-35 Ahd8+"


def test_pat_label_format() -> None:
    p = PatSituation.from_situation_number(
        7, category_weights=weights(0x10, 10, 0x11, 0, 0x12, 0)
    )
    assert pat_label(p) == ">5 Ahd1"


def test_sub_label() -> None:
    assert sub_label("quarterbacks") == "QB"
    assert sub_label("defensive_backs") == "DB"


def test_every_situation_and_pat_labels_without_keyerror() -> None:
    profile = make_profile(OFFENSE)
    assert all(len(situation_label(s).split()) == 5 for s in profile.situations)
    assert all(len(pat_label(p).split()) == 2 for p in profile.pat_situations)
