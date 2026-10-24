"""Tests for Standings with the previous season's file: last season's
results for the current season's divisions and teams."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_standings import Standings, StandingsError
from tests.unit.fbpro98_standings.leagues import names, real_lge

# The 2048 standings file (git dade898^,
# config/release/leagues/PNFL/standings/2048.league.ini): the overall order,
# then each division's finish, in the 2048 file's division order.
OVERALL_2048 = (
    "Miami",
    "Minnesota",
    "Los Angeles",
    "Chicago",
    "Denver",
    "Washington",
    "Atlanta",
    "Las Vegas",
    "New England",
    "Green Bay",
    "Cincinnati",
    "New York",
    "San Francisco",
    "Jacksonville",
    "Philadelphia",
    "Pittsburgh",
    "Seattle",
    "Buffalo",
)
DIVISIONS_2048 = (
    ("Miami", "New England", "Jacksonville", "Buffalo"),
    ("Los Angeles", "Denver", "Las Vegas", "Cincinnati", "Pittsburgh"),
    ("Washington", "Atlanta", "New York", "Philadelphia"),
    ("Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"),
)
# The 2047 order by the scheduler method with seed 0; level teams fall to the
# seed's coin toss.
OVERALL_2047 = (
    "Pittsburgh",
    "Washington",
    "Minnesota",
    "Cincinnati",
    "Miami",
    "Buffalo",
    "Seattle",
    "San Francisco",
    "Baltimore",
    "Las Vegas",
    "Philadelphia",
    "Chicago",
    "Green Bay",
    "Denver",
    "Jacksonville",
    "Atlanta",
    "New York",
    "New England",
)
DIVISIONS_2047 = (
    ("Miami", "Buffalo", "Jacksonville", "New England"),
    ("Pittsburgh", "Cincinnati", "Baltimore", "Las Vegas", "Denver"),
    ("Washington", "Philadelphia", "Atlanta", "New York"),
    ("Minnesota", "Seattle", "San Francisco", "Chicago", "Green Bay"),
)
MOVES_2048 = {"Baltimore": "Los Angeles"}
MOVES_2047 = {
    "Houston": "Miami",
    "New York A": "Cincinnati",
    "Indianapolis": "Baltimore",
    "New York N": "New York",
}


def test_2047_to_2048_matches_the_2048_standings_file():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    standings = Standings(current, previous, MOVES_2048, method="scheduler", seed=0)
    assert names(standings.league()) == OVERALL_2048
    assert (
        tuple(
            names(standings.division(division))
            for conference in current.conferences
            for division in conference.divisions
        )
        == DIVISIONS_2048
    )


def test_answers_are_the_current_files_teams():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    standings = Standings(current, previous, MOVES_2048, method="scheduler", seed=0)
    assert all(
        any(team is known for known in current.teams) for team in standings.league()
    )
    assert sorted(map(id, standings.league())) == sorted(map(id, current.teams))


def test_a_team_that_changed_division_brings_its_record():
    # 2047 AFC East: Miami (11-5 as Houston) and Jacksonville (5-11) came from
    # the West; Buffalo (10-6) and New England (3-13) stayed.
    previous = real_lge("PNFL-2046-after-super-bowl.lge")
    current = real_lge("PNFL-2047-after-week1.lge")
    standings = Standings(current, previous, MOVES_2047, method="scheduler", seed=0)
    east = next(
        division
        for conference in current.conferences
        for division in conference.divisions
        if "Miami" in names(division.teams)
    )
    assert names(standings.division(east)) == (
        "Miami",
        "Buffalo",
        "Jacksonville",
        "New England",
    )
    assert names(standings.league()) == OVERALL_2047
    assert (
        tuple(
            names(standings.division(division))
            for conference in current.conferences
            for division in conference.divisions
        )
        == DIVISIONS_2047
    )


def test_a_missing_team_move_is_an_error():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    with pytest.raises(
        StandingsError,
        match=re.escape("Team(s) not in the current file: Baltimore."),
    ):
        Standings(current, previous, method="scheduler")
