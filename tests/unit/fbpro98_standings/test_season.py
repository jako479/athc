"""Tests for athc.fbpro98_standings.season: a league file's season as
numbers."""

from __future__ import annotations

from athc.fbpro98_standings.season import Result, season_of
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# Conference 1: division 1 is A and B, division 2 is C; conference 2 is D.
SHAPE = [[["A", "B"], ["C"]], [["D"]]]


def test_teams_numbered_in_file_order_with_their_division_and_conference():
    season = season_of(build_league(SHAPE))
    assert names(season.teams) == ("A", "B", "C", "D")
    assert season.division_of == (0, 0, 1, 2)
    assert season.conference_of == (0, 0, 0, 1)
    assert season.division_members(0) == (0, 1)


def test_a_game_counts_for_both_teams():
    season = season_of(build_league(SHAPE, [("A", 20, "B", 10)]))
    assert season.results[0] == (
        Result(opponent=1, scored=20, allowed=10, division=True, conference=True),
    )
    assert season.results[1] == (
        Result(opponent=0, scored=10, allowed=20, division=True, conference=True),
    )


def test_games_marked_division_and_conference():
    season = season_of(build_league(SHAPE, [("A", 20, "C", 10), ("A", 20, "D", 10)]))
    against_c, against_d = season.results[0]
    assert (against_c.division, against_c.conference) == (False, True)
    assert (against_d.division, against_d.conference) == (False, False)


def test_won_and_lost():
    season = season_of(build_league(SHAPE, [("A", 20, "B", 10), ("A", 10, "C", 10)]))
    won, tied = season.results[0]
    assert (won.won, won.lost) == (True, False)
    assert (tied.won, tied.lost) == (False, False)
    assert season.results[1][0].lost


def test_playoff_round_reached_and_the_final():
    # Round 1: A over B, D over C; final: D over A.
    lge = build_league(
        SHAPE, playoffs=[[win("A", "B"), win("D", "C")], [win("D", "A")]]
    )
    season = season_of(lge)
    assert season.playoff_round == (2, 1, 1, 3)
    assert (season.champion, season.runner_up) == (3, 0)


def test_a_bye_counts_by_the_later_round():
    # B sat out round 1 and won the final.
    lge = build_league(SHAPE, playoffs=[[win("A", "C")], [win("B", "A")]])
    season = season_of(lge)
    assert season.playoff_round == (2, 3, 1, 0)
    assert (season.champion, season.runner_up) == (1, 0)


def test_no_champion_before_the_final_is_played():
    lge = build_league(SHAPE, playoffs=[[win("A", "B")], []])
    season = season_of(lge)
    assert season.playoff_round == (2, 1, 0, 0)
    assert (season.champion, season.runner_up) == (None, None)


def test_real_season():
    season = season_of(real_lge("PNFL-2047-after-super-bowl.lge"))
    assert len(season.teams) == 18
    assert all(len(games) == 16 for games in season.results)
    champion, runner_up = season.champion, season.runner_up
    assert champion is not None
    assert runner_up is not None
    assert (season.teams[champion].name, season.teams[runner_up].name) == (
        "Miami",
        "Minnesota",
    )
