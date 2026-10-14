"""Tests for the NFL method: only one team advances at a time, and teams of
different divisions go on only as each division's best."""

from __future__ import annotations

from collections.abc import Sequence

from athc.fbpro98_standings import Standings
from athc.fbpro98_standings.methods import MethodRules, Rules
from athc.fbpro98_standings.season import season_of
from athc.fbpro98_standings.standings import _Ranker
from athc.fbpro98_standings.steps import Context, Step, Values
from tests.unit.fbpro98_standings.leagues import Shape, build_league, names, real_lge

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


def _prefer(*order: int) -> Step:
    """A step that ranks teams by their place in `order`."""

    def step(group: Sequence[int], context: Context) -> Values:
        return {team: -order.index(team) for team in group}

    return step


def _ranker(shape: Shape, method: MethodRules) -> _Ranker:
    return _Ranker(season_of(build_league(shape)), method, seed=0)


def test_nfl_sends_the_teams_a_step_dropped_back_to_the_first_tie_breaker():
    # The second step drops C; A advances over B on the first. Then B and C
    # start over at the first step, where C beats B.
    rules = Rules(sort=(), breakers=(_pairs, _a_and_b_over_c), one_advances=True)
    ranker = _ranker([[["A", "B", "C"]]], MethodRules(rules, None, rules))
    assert ranker._order([A, B, C], rules) == (A, C, B)


def test_nfl_conference_keeps_only_each_divisions_best():
    # One conference: A1 and A2 in one division, B1 in the other.
    a1, a2, b1 = range(3)
    division = Rules(sort=(), breakers=(_prefer(a1, a2, b1),), one_advances=True)
    conference = Rules(
        sort=(),
        breakers=(_prefer(b1, a2, a1),),
        one_advances=True,
        by_division_first=True,
    )
    league = Rules(sort=(), breakers=())
    ranker = _ranker(
        [[["A1", "A2"], ["B1"]]], MethodRules(division, conference, league)
    )
    # A1 is its division's best; B1 beats it. Then A1 and A2, one division,
    # go by the division rules.
    assert ranker._order([a1, a2, b1], conference) == (b1, a1, a2)


def test_nfl_league_keeps_each_divisions_then_each_conferences_best():
    # Conference 1: A1 and A2, each its own division; conference 2: B1.
    a1, a2, b1 = range(3)
    division = Rules(sort=(), breakers=(), one_advances=True)
    conference = Rules(
        sort=(),
        breakers=(_prefer(a2, a1, b1),),
        one_advances=True,
        by_division_first=True,
    )
    league = Rules(
        sort=(),
        breakers=(_prefer(a1, b1, a2),),
        one_advances=True,
        by_division_first=True,
    )
    ranker = _ranker(
        [[["A1"], ["A2"]], [["B1"]]], MethodRules(division, conference, league)
    )
    # A2 is conference 1's best and B1 beats it for the league. Then A1 and
    # A2, one conference, go by the conference rules.
    assert ranker._order([a1, a2, b1], league) == (b1, a2, a1)


def test_nfl_on_a_real_season():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    standings = Standings(lge, method="nfl", seed=0)
    league = names(standings.league())
    assert league[:2] == ("Miami", "Minnesota")
    assert sorted(league) == sorted(names(lge.teams))
    for conference in lge.conferences:
        teams = [team for division in conference.divisions for team in division.teams]
        assert sorted(names(standings.conference(conference))) == sorted(names(teams))
        for division in conference.divisions:
            assert sorted(names(standings.division(division))) == sorted(
                names(division.teams)
            )
