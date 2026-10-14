"""Tests for athc.fbpro98_standings.standings: the ranking engine, the coin
toss, and the caller's mistakes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import pytest

from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Team
from athc.fbpro98_standings import Method, Standings
from athc.fbpro98_standings.methods import METHODS, MethodRules, Rules
from athc.fbpro98_standings.season import season_of
from athc.fbpro98_standings.standings import _Ranker
from athc.fbpro98_standings.steps import Context, Values
from tests.unit.fbpro98_standings.leagues import (
    NO_GAMES,
    build_league,
    names,
    real_lge,
)

SIX = [[["A", "B", "C", "D", "E", "F"]]]
THREE = [[["A", "B", "C"]]]
A, B, C = range(3)
# A pair is separated by its place here: A over B, C over B, A over C.
PAIR_ORDER = (A, C, B)


def _pairs(group: Sequence[int], context: Context) -> Values:
    """Separates only a pair: the one earlier in PAIR_ORDER."""
    if len(group) != 2:
        return dict.fromkeys(group, 0)
    return {team: -PAIR_ORDER.index(team) for team in group}


def _a_and_b_over_c(group: Sequence[int], context: Context) -> Values:
    return {team: int(team != C) for team in group}


def _ranker(rules: Rules) -> _Ranker:
    season = season_of(build_league(THREE))
    return _Ranker(season, MethodRules(rules, None, rules), seed=0)


def test_regroup_ranks_the_placed_teams_and_the_rest_again():
    # Three level teams: the second step places A and B over C; A and B start
    # over at the first step, which puts A first.
    rules = Rules(sort=(), breakers=(_pairs, _a_and_b_over_c))
    assert _ranker(rules)._order([A, B, C], rules) == (A, B, C)


def test_a_seed_repeats_the_coin_toss():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    first = Standings(lge, method="game", seed=7).division(division)
    second = Standings(lge, method="game", seed=7).division(division)
    assert names(first) == names(second)
    assert sorted(names(first)) == ["A", "B", "C", "D", "E", "F"]


def test_the_coin_toss_does_not_depend_on_what_was_asked_before():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    one = Standings(lge, method="game", seed=7)
    two = Standings(lge, method="game", seed=7)
    league_first = one.league()
    division_second = one.division(division)
    division_first = two.division(division)
    league_second = two.league()
    assert (league_first, division_second) == (league_second, division_first)


def test_without_a_seed_the_same_question_gets_the_same_answer():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    standings = Standings(lge, method="game")
    assert standings.division(division) == standings.division(division)
    assert standings.league() == standings.league()


def test_unknown_method_rejected():
    with pytest.raises(ValueError, match="Unknown method: 'xfl'"):
        Standings(build_league(SIX), method=cast(Method, "xfl"))


def test_team_moves_need_the_previous_file():
    with pytest.raises(ValueError, match="team_moves needs the previous season's"):
        Standings(build_league(SIX), team_moves={"A": "B"}, method="game")


def test_a_division_of_another_file_rejected():
    other = build_league(SIX).conferences[0].divisions[0]
    with pytest.raises(ValueError, match="Not a division of the current file: 'D1'"):
        Standings(build_league(SIX), method="game").division(other)


def test_a_conference_of_another_file_rejected():
    other = build_league(SIX).conferences[0]
    with pytest.raises(ValueError, match="Not a conference of the current file: 'C1'"):
        Standings(build_league(SIX), method="game").conference(other)


def test_an_empty_division_has_no_standings():
    lge = build_league([[["A", "B"], []]])
    conference = lge.conferences[0]
    standings = Standings(lge, method="game", seed=0)
    assert standings.division(conference.divisions[1]) == ()
    assert sorted(names(standings.conference(conference))) == ["A", "B"]


def test_teams_that_look_alike_stay_apart():
    # Two teams equal in every field: told apart by position, never by value.
    first = Team(name="A", nickname="", record=NO_GAMES)
    second = Team(name="A", nickname="", record=NO_GAMES)
    division = Division(name="D1", teams=(first, second), standings=(first, second))
    lge = LgeFile(
        conferences=(
            Conference(name="C1", divisions=(division,), standings=(first, second)),
        ),
        weeks=((Game(second, 20, first, 10),),),
    )
    ranked = Standings(lge, method="game").division(division)
    assert ranked[0] is second
    assert ranked[1] is first


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("filename", ["PNFL-before-week1.lge", "PNFL-after-week16.lge"])
def test_every_method_on_a_season_not_finished(method, filename):
    # Before week 1 every team is level; after week 16 no playoff game is
    # played. Every request still lists each team once.
    lge = real_lge(filename)
    standings = Standings(lge, method=method, seed=0)
    assert sorted(names(standings.league())) == sorted(names(lge.teams))
    for conference in lge.conferences:
        teams = [team for division in conference.divisions for team in division.teams]
        assert sorted(names(standings.conference(conference))) == sorted(names(teams))
        for division in conference.divisions:
            assert sorted(names(standings.division(division))) == sorted(
                names(division.teams)
            )


# Two conferences, three divisions of three; no games, so the coin decides.
LEVEL = [[["A", "B", "C"], ["D", "E", "F"]], [["G", "H", "I"]]]


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("seed", range(10))
def test_conference_standings_agree_with_division_standings(method, seed):
    # Division-mates come out of the conference in their division's order,
    # even when the coin decides both.
    lge = build_league(LEVEL)
    standings = Standings(lge, method=method, seed=seed)
    for conference in lge.conferences:
        ranked = names(standings.conference(conference))
        for division in conference.divisions:
            members = set(names(division.teams))
            assert tuple(name for name in ranked if name in members) == names(
                standings.division(division)
            )
