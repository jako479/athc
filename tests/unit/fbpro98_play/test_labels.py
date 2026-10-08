"""Unit tests for CategoryLabels: a league's offense/defense category labels."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_play import (
    CategoryLabels,
    DefensiveCategory,
    OffensiveCategory,
    SpecialOffensiveCategory,
)

OFFENSE = {"Run Right": "RR", "Pass Short Right": "PSR"}
DEFENSE = {"Run Right": "RunRight", "Pass Short": "PassShort"}


def test_from_tables_maps_game_names_to_members() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.offense == {
        OffensiveCategory.RUN_RIGHT: "RR",
        OffensiveCategory.PASS_SHORT_RIGHT: "PSR",
    }
    assert labels.defense == {
        DefensiveCategory.RUN_RIGHT: "RunRight",
        DefensiveCategory.PASS_SHORT: "PassShort",
    }


def test_label_is_league_label_else_game_name() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.label(OffensiveCategory.RUN_RIGHT) == "RR"
    assert labels.label(OffensiveCategory.PASS_LONG_LEFT) == "Pass Long Left"
    assert labels.label(DefensiveCategory.RUN_RIGHT) == "RunRight"
    assert labels.label(DefensiveCategory.PASS_LONG) == "Pass Long"
    assert labels.label(SpecialOffensiveCategory.PUNT) == "Punt"


def test_no_labels_uses_game_names_everywhere() -> None:
    labels = CategoryLabels()
    assert labels.label(OffensiveCategory.RUN_RIGHT) == "Run Right"
    assert labels.offense_by_label("Run Right") is None
    assert labels.offense_by_label("RR") is None


def test_by_label_resolves_within_its_side() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.offense_by_label("PSR") is OffensiveCategory.PASS_SHORT_RIGHT
    assert labels.defense_by_label("PassShort") is DefensiveCategory.PASS_SHORT
    assert labels.offense_by_label("PassShort") is None
    assert labels.defense_by_label("PSR") is None
    # A game name is not a label.
    assert labels.offense_by_label("Pass Short Right") is None


def test_same_label_on_both_sides_is_allowed() -> None:
    labels = CategoryLabels.from_tables({"Run Right": "RR"}, {"Run Right": "RR"})
    assert labels.offense_by_label("RR") is OffensiveCategory.RUN_RIGHT
    assert labels.defense_by_label("RR") is DefensiveCategory.RUN_RIGHT


def test_label_may_equal_the_other_sides_game_name() -> None:
    labels = CategoryLabels.from_tables({}, {"Run Right": "Pass Short Right"})
    assert labels.defense_by_label("Pass Short Right") is DefensiveCategory.RUN_RIGHT


@pytest.mark.parametrize(
    ("offense", "defense", "message"),
    [
        (
            {"Run Rite": "RR"},
            {},
            "[categories.offense] 'Run Rite': not a game category name for offense",
        ),
        (
            {},
            {"Pass Short Right": "PSR"},
            "[categories.defense] 'Pass Short Right': not a game category name "
            "for defense",
        ),
        ({"Run Right": 1}, {}, "'Run Right': label must be a non-empty string"),
        ({"Run Right": ""}, {}, "'Run Right': label must be a non-empty string"),
        ({"Run Right": " "}, {}, "'Run Right': label must be a non-empty string"),
        (
            {"Run Right": "Run Left"},
            {},
            "'Run Right': label 'Run Left' is a game category name for offense",
        ),
        (
            {},
            {"Run Right": "Pass Long"},
            "'Run Right': label 'Pass Long' is a game category name for defense",
        ),
        (
            {"Run Right": "X", "Run Left": "X"},
            {},
            "'Run Left': label 'X' already used by 'Run Right'",
        ),
    ],
)
def test_from_tables_rejects(
    offense: dict[str, object], defense: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        CategoryLabels.from_tables(offense, defense)
