"""Tests for the game method: the FbPro98 manual's tie-breakers (page 129)
and its draft order (page 136), reversed, for league standings."""

from __future__ import annotations

import pytest

from athc.fbpro98_lge import LgeFile
from athc.fbpro98_standings import Standings
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# Each division's season-end order, as the game showed it (2048) and as the
# manual's steps give it (2043, 2046); the fbpro98_lge tests hold the same.
GAME_DIVISIONS = [
    (
        "PNFL-2048-after-week16.lge",
        (
            ("Miami", "Buffalo", "New England", "Jacksonville"),
            ("Cincinnati", "Pittsburgh", "Las Vegas", "Denver", "Los Angeles"),
            ("Washington", "Atlanta", "New York", "Philadelphia"),
            ("Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"),
        ),
    ),
    (
        "PNFL-2043-after-super-bowl.lge",
        (
            ("New York A", "Indianapolis", "New England", "Jacksonville"),
            ("Kansas City", "Minnesota", "Los Angeles", "Las Vegas", "Pittsburgh"),
            ("Washington", "Detroit", "New York N", "Atlanta"),
            ("Chicago", "San Francisco", "New Orleans", "Seattle", "Anaheim"),
        ),
    ),
    (
        "PNFL-2046-after-super-bowl.lge",
        (
            ("New York A", "Buffalo", "Indianapolis", "New England"),
            ("Pittsburgh", "Houston", "Las Vegas", "Jacksonville", "Denver"),
            ("Washington", "Philadelphia", "Atlanta", "New York N"),
            ("Minnesota", "Seattle", "San Francisco", "Chicago", "Green Bay"),
        ),
    ),
]


def _divisions(standings: Standings, lge: LgeFile) -> tuple[tuple[str, ...], ...]:
    return tuple(
        names(standings.division(division))
        for conference in lge.conferences
        for division in conference.divisions
    )


@pytest.mark.parametrize(("filename", "expected"), GAME_DIVISIONS)
def test_game_division_standings_match_the_game(filename, expected):
    lge = real_lge(filename)
    assert _divisions(Standings(lge, method="game", seed=0), lge) == expected


def test_game_conference_standings_put_division_winners_first():
    # 2047 after week 16. Division winners: Baltimore and Miami; Chicago and
    # Washington. 7-9: New York beat Green Bay; 6-10: Philadelphia beat San
    # Francisco.
    lge = real_lge("PNFL-after-week16.lge")
    standings = Standings(lge, method="game", seed=0)
    afc, nfc = lge.conferences
    assert names(standings.conference(afc)) == (
        "Baltimore",
        "Miami",
        "Denver",
        "Las Vegas",
        "New England",
        "Cincinnati",
        "Jacksonville",
        "Pittsburgh",
        "Buffalo",
    )
    assert names(standings.conference(nfc)) == (
        "Chicago",
        "Washington",
        "Minnesota",
        "Atlanta",
        "New York",
        "Green Bay",
        "Philadelphia",
        "San Francisco",
        "Seattle",
    )


def test_game_ranks_the_placed_teams_and_the_rest_again():
    # T1, T2, T3 split head-to-head in a cycle with equal division and
    # conference records and division net points. Net points in all games
    # place T1 first; T2 and T3 start over at head-to-head, where T2 beat T3,
    # although strength of schedule would favor T3.
    lge = build_league(
        [[["T1", "T2", "T3"], ["T4", "T5"]], [["T6"]]],
        [
            win("T1", "T2"),
            win("T2", "T3"),
            win("T3", "T1"),
            win("T1", "T4", by=20),
            win("T2", "T5", by=5),
            win("T3", "T4", by=5),
            win("T4", "T6"),
            win("T4", "T6"),
            win("T4", "T6"),
        ],
    )
    division = lge.conferences[0].divisions[0]
    assert names(Standings(lge, method="game").division(division)) == (
        "T1",
        "T2",
        "T3",
    )


def test_game_league_puts_the_champion_and_runner_up_first():
    # A is 2-0 but lost in round 1; B is 0-2 and won the final over D.
    lge = build_league(
        [[["A", "B"], ["C", "D"]]],
        [win("A", "B"), win("A", "C"), win("C", "D"), win("D", "B")],
        [[win("D", "A")], [win("B", "D")]],
    )
    assert names(Standings(lge, method="game").league()) == ("B", "D", "A", "C")


def test_game_league_breaks_record_ties_on_strength_of_schedule():
    # C, D and E are 1-1. Their opponents, each once: E's A (2-0) and D
    # (1-1) = 3/4; C's A and B (0-2) = 1/2; D's B and E = 1/4.
    lge = build_league(
        [[["A", "B", "C", "D", "E"]]],
        [win("A", "E"), win("A", "C"), win("C", "B"), win("D", "B"), win("E", "D")],
    )
    assert names(Standings(lge, method="game").league()) == ("A", "E", "C", "D", "B")


def test_game_conference_without_divisions():
    # One division per conference: its winner first, then the rest.
    lge = build_league([[["A", "B"]], [["C", "D"]]], [win("B", "A"), win("D", "C")])
    standings = Standings(lge, method="game")
    first, second = lge.conferences
    assert names(standings.conference(first)) == ("B", "A")
    assert names(standings.conference(second)) == ("D", "C")
