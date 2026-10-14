"""Tests for the scheduler method: league standings by playoff round,
record, strength of schedule (every game), division finish and point
differential; conference standings in league order; division standings by
the game's steps."""

from __future__ import annotations

from athc.fbpro98_standings import Standings
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# The 2048 standings file's overall order (git dade898^,
# config/release/leagues/PNFL/standings/2048.league.ini), in the 2047 file's
# names: Baltimore became Los Angeles for 2048.
OVERALL_2047 = (
    "Miami",
    "Minnesota",
    "Baltimore",
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

# The 2047 standings file's overall order (git dade898^, 2047.league.ini) in
# the 2046 file's names. That file's overall section was written with New
# York A as Baltimore and Indianapolis as Cincinnati; Houston became Miami
# and New York N became New York.
OVERALL_2046 = (
    "Pittsburgh",
    "Washington",
    "Minnesota",
    "New York A",
    "Houston",
    "Buffalo",
    "Seattle",
    "San Francisco",
    "Indianapolis",
    "Las Vegas",
    "Philadelphia",
    "Chicago",
    "Green Bay",
    "Denver",
    "Jacksonville",
    "Atlanta",
    "New York N",
    "New England",
)


def test_scheduler_league_matches_the_2048_standings_file():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    assert names(Standings(lge, method="scheduler", seed=0).league()) == OVERALL_2047


def test_scheduler_league_breaks_a_division_tie_on_division_finish():
    # Chicago and Green Bay: both 6-10, out of the playoffs, equal strength of
    # schedule, one division; Chicago finished above Green Bay in it.
    lge = real_lge("PNFL-2046-after-super-bowl.lge")
    assert names(Standings(lge, method="scheduler", seed=0).league()) == OVERALL_2046


def test_scheduler_division_finish_skipped_across_divisions():
    # A and C (1-0) and B and D (0-1) are level through strength of schedule
    # in different divisions: point differential decides.
    lge = build_league(
        [[["A", "B"], ["C", "D"]]],
        [win("A", "B", by=20), win("C", "D", by=5)],
    )
    assert names(Standings(lge, method="scheduler").league()) == ("A", "C", "D", "B")


def test_scheduler_division_finish_overrides_point_differential():
    # A, B and C are 1-1 in one division with equal strength of schedule. The
    # division's order is B, C, A (B on division net points, then C over A
    # head-to-head); point differential alone would give B, A, C.
    lge = build_league(
        [[["A", "B", "C"]]],
        [win("A", "B", by=1), win("B", "C", by=30), win("C", "A", by=1)],
    )
    assert names(Standings(lge, method="scheduler").league()) == ("B", "C", "A")


def test_scheduler_conference_standings_follow_the_league_order():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    standings = Standings(lge, method="scheduler", seed=0)
    for conference in lge.conferences:
        members = {
            team.name for division in conference.divisions for team in division.teams
        }
        expected = tuple(name for name in OVERALL_2047 if name in members)
        assert names(standings.conference(conference)) == expected
