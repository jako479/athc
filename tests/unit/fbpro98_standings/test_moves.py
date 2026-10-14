"""Tests for athc.fbpro98_standings.moves: matching the previous season's
teams to the current season's."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_standings import StandingsError
from athc.fbpro98_standings.moves import match
from tests.unit.fbpro98_standings.leagues import Shape, build_league

# Previous season: division 1 is A and B, division 2 is C.
PREVIOUS = [[["A", "B"], ["C"]]]


def _match(
    current: Shape,
    team_moves: dict[str, str] | None = None,
    previous: Shape = PREVIOUS,
) -> tuple[int, ...]:
    return match(build_league(previous), build_league(current), team_moves or {})


def test_teams_match_by_name_wherever_they_moved():
    # C moved into A's division, B into C's old one.
    assert _match([[["A", "C"], ["B"]]]) == (0, 2, 1)


def test_a_team_move_matches_a_renamed_team():
    assert _match([[["A", "B"], ["X"]]], {"C": "X"}) == (0, 1, 2)


def test_team_moves_may_swap_names():
    assert _match([[["B", "A"], ["C"]]], {"A": "B", "B": "A"}) == (0, 1, 2)


@pytest.mark.parametrize(
    ("previous", "current", "team_moves", "message"),
    [
        (
            [[["A", "A"]]],
            [[["A", "B"]]],
            {},
            "Team name repeats in the previous file: A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "A"]]],
            {},
            "Team name repeats in the current file: A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B"]]],
            {"Z": "B"},
            "Team move Z: Not a team in the previous file.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B"]]],
            {"A": "Z"},
            "Team move A: Z is not a team in the current file.",
        ),
        (
            [[["A", "B"]]],
            [[["B", "C"]]],
            {"A": "B"},
            "Team move A: Another team in the previous file is named B.",
        ),
        (
            [[["A", "B", "C"]]],
            [[["X", "C"]]],
            {"A": "X", "B": "X"},
            "Team move B: X is also the new name of A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "C"]]],
            {},
            "Team(s) not in the current file: B. "
            "List each team whose name changed in the team moves.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B", "C"]]],
            {},
            "Team(s) not in the previous file: C.",
        ),
    ],
)
def test_mismatch_rejected(previous, current, team_moves, message):
    with pytest.raises(StandingsError, match=re.escape(message)):
        _match(current, team_moves, previous)
