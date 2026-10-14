"""Tests for athc.fbpro98_standings.steps: each tie-break step on its own,
on small leagues built in code."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from athc.fbpro98_standings import steps
from athc.fbpro98_standings.season import Season, season_of
from tests.unit.fbpro98_standings.leagues import Played, Shape, build_league, win

# Conference 1: division 1 is A, B, C; division 2 is D, E. Conference 2: F.
SHAPE = [[["A", "B", "C"], ["D", "E"]], [["F"]]]
A, B, C, D, E, F = range(6)


@dataclass
class _Context:
    season: Season
    orders: dict[int, tuple[int, ...]] = field(default_factory=dict)

    def division_order(self, division: int) -> tuple[int, ...]:
        return self.orders[division]


def _context(
    *games: Played,
    shape: Shape = SHAPE,
    playoffs: list[list[Played]] | None = None,
) -> _Context:
    return _Context(season_of(build_league(shape, games, playoffs or [])))


def test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero():
    context = _context(win("A", "B"), ("A", 10, "D", 10))
    assert steps.percentage(context.season.results[A]) == Fraction(3, 4)
    assert steps.percentage(context.season.results[F]) == 0


def test_win_percentage_counts_every_game():
    context = _context(win("A", "B"), win("A", "F"), win("B", "F"))
    assert steps.win_percentage([A, B, F], context) == {
        A: 1,
        B: Fraction(1, 2),
        F: 0,
    }


def test_head_to_head_counts_only_games_among_the_level_teams():
    # B beat A; A's win over D does not count.
    context = _context(win("B", "A"), win("A", "D"), win("D", "B"))
    assert steps.head_to_head([A, B], context) == {A: 0, B: 1}


def test_sweep_with_two_teams_is_head_to_head():
    context = _context(win("B", "A"))
    assert steps.head_to_head_sweep([A, B], context) == {A: 0, B: 1}


def test_sweep_places_a_team_that_beat_every_other_first():
    context = _context(win("A", "B"), win("A", "C"), win("B", "C"))
    assert steps.head_to_head_sweep([A, B, C], context) == {A: 1, B: 0, C: 0}


def test_sweep_places_a_team_that_lost_to_every_other_last():
    context = _context(win("A", "C"), win("B", "C"), ("A", 10, "B", 10))
    assert steps.head_to_head_sweep([A, B, C], context) == {A: 0, B: 0, C: -1}


def test_no_sweep_in_a_cycle():
    context = _context(win("A", "B"), win("B", "C"), win("C", "A"))
    assert steps.head_to_head_sweep([A, B, C], context) is None


def test_no_sweep_without_a_game_against_every_other():
    # A beat B but never played C; C lost to B only.
    context = _context(win("A", "B"), win("B", "C"))
    assert steps.head_to_head_sweep([A, B, C], context) is None


def test_division_and_conference_percentage():
    # A: 2-1 in the division (B, B, C). B: 1-1 in the division (A, A), 2-1 in
    # the conference with its win over D; its win over F is outside it.
    context = _context(
        win("A", "B"), win("B", "A"), win("A", "C"), win("B", "D"), win("B", "F")
    )
    assert steps.division_percentage([A, B], context) == {
        A: Fraction(2, 3),
        B: Fraction(1, 2),
    }
    assert steps.conference_percentage([A, B], context) == {
        A: Fraction(2, 3),
        B: Fraction(2, 3),
    }


def test_net_points_by_kind_of_game():
    context = _context(
        win("A", "B", by=10),
        win("B", "A", by=20),
        win("A", "D", by=5),
        win("B", "F", by=7),
    )
    group = [A, B]
    assert steps.division_net_points(group, context) == {A: -10, B: 10}
    assert steps.conference_net_points(group, context) == {A: -5, B: 10}
    assert steps.net_points(group, context) == {A: -5, B: 17}


# One division: A and B against W, X, Y and Z.
COMMON = [[["A", "B", "W", "X", "Y", "Z"]]]


def test_common_games_at_the_minimum_apply():
    # Both played W, X, Y and Z: A won all four, B three.
    context = _context(
        *(win("A", other) for other in "WXYZ"),
        *(win("B", other) for other in "WXY"),
        win("Z", "B"),
        shape=COMMON,
    )
    assert steps.common_games(4)([0, 1], context) == {0: 1, 1: Fraction(3, 4)}


def test_common_games_one_short_of_the_minimum_skipped():
    context = _context(
        *(win("A", other) for other in "WXY"),
        *(win("B", other) for other in "WXY"),
        shape=COMMON,
    )
    assert steps.common_games(4)([0, 1], context) is None


def test_common_net_points():
    context = _context(
        *(win("A", other) for other in "WXYZ"),
        *(win("B", other) for other in "WXY"),
        win("Z", "B"),
        shape=COMMON,
    )
    assert steps.common_net_points([0, 1], context) == {0: 40, 1: 20}


# A beat X twice and Y once; B beat Y; X beat Y. X is 1-2, Y 0-3.
VICTORY = [[["A", "B", "X", "Y"]]]
VICTORY_GAMES = (
    win("A", "X"),
    win("A", "X"),
    win("A", "Y"),
    win("B", "Y"),
    win("X", "Y"),
)


def test_strength_of_victory_counts_every_win():
    context = _context(*VICTORY_GAMES, shape=VICTORY)
    # A: X's three games twice and Y's three: 2 wins in 9.
    assert steps.strength_of_victory([0, 1], context) == {0: Fraction(2, 9), 1: 0}


def test_strength_of_schedule_each_opponent_once_or_every_game():
    context = _context(*VICTORY_GAMES, shape=VICTORY)
    once = steps.strength_of_schedule(each_opponent_once=True)
    every = steps.strength_of_schedule(each_opponent_once=False)
    assert once([0, 1], context) == {0: Fraction(1, 6), 1: 0}
    assert every([0, 1], context) == {0: Fraction(2, 9), 1: 0}


def test_combined_ranking_within_the_conference_or_the_league():
    # Points for / against: A 30/0, B 20/20, C 30/80, D 60/40.
    context = _context(
        ("A", 30, "D", 0),
        ("B", 20, "C", 20),
        ("D", 60, "C", 10),
        shape=[[["A", "B", "C"]], [["D"]]],
    )
    group = [0, 1, 2]
    # Conference (A, B, C): A and C share first in points scored.
    assert steps.combined_ranking("conference")(group, context) == {
        0: 0,
        1: -3,
        2: -2,
    }
    # League: D outscored everyone.
    assert steps.combined_ranking("league")(group, context) == {
        0: -1,
        1: -4,
        2: -4,
    }


def test_division_finish_for_teams_of_one_division():
    context = _context()
    context.orders[0] = (B, A, C)
    assert steps.division_finish([A, B], context) == {A: -1, B: 0}


def test_division_finish_skipped_for_teams_of_different_divisions():
    assert steps.division_finish([A, D], _context()) is None


def test_playoff_round_and_champion_then_runner_up():
    # Round 1: A over B, D over C; final: D over A.
    context = _context(playoffs=[[win("A", "B"), win("D", "C")], [win("D", "A")]])
    group = [A, B, C, D, E]
    assert steps.playoff_round(group, context) == {A: 2, B: 1, C: 1, D: 3, E: 0}
    assert steps.champion_then_runner_up(group, context) == {
        A: 1,
        B: 0,
        C: 0,
        D: 2,
        E: 0,
    }
