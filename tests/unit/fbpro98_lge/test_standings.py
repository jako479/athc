"""Tests for athc.fbpro98_lge.standings: the game's tie-breakers on built
seasons (team numbers and results, no file)."""

from __future__ import annotations

from fractions import Fraction

import pytest

from athc.fbpro98_lge.standings import percentage, rank, season_from_games

# Conference 1: division 1 is teams 1-3, division 2 is teams 4-5; conference
# 2: division 3 is team 6.
DIVISION = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3}
CONFERENCE = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 2}

Game = tuple[int, int, int, int]  # home, home score, away, away score


def _season(*games: Game):
    return season_from_games(games, DIVISION, CONFERENCE)


def _win(winner: int, loser: int, by: int = 10) -> Game:
    return (winner, 10 + by, loser, 10)


def test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero():
    season = _season(_win(1, 2), (1, 10, 4, 10))
    assert percentage(season[1]) == Fraction(3, 4)
    assert percentage(season[6]) == 0


def test_rank_by_percentage_first():
    # 1 is 1-0, 2 is 0-1-1, 4 is 0-0-1.
    season = _season(_win(1, 2), (2, 10, 4, 10))
    assert rank([2, 4, 1], season) == (1, 4, 2)


@pytest.mark.parametrize("numbers", [[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]])
def test_level_teams_keep_the_given_order(numbers):
    assert rank(numbers, _season()) == tuple(numbers)


def test_head_to_head_breaks_a_tie():
    # 1 and 2 are both 1-1; 2 beat 1.
    season = _season(_win(2, 1), _win(1, 4), _win(4, 2))
    assert rank([1, 2], season) == (2, 1)


def test_division_record_breaks_a_split_series():
    # Both 2-1 after a split; 1's third win is a division game, 2's is not.
    season = _season(_win(1, 2), _win(2, 1), _win(1, 3), _win(2, 4))
    assert rank([2, 1], season) == (1, 2)


def test_conference_record_breaks_equal_division_records():
    # Both 2-1 after a split; 1's third win is in the conference, 2's is not.
    season = _season(_win(1, 2), _win(2, 1), _win(1, 4), _win(2, 6))
    assert rank([2, 1], season) == (1, 2)


def test_net_points_in_division_games_breaks_equal_records():
    # Split series, 2 won its game by more.
    season = _season(_win(1, 2, by=10), _win(2, 1, by=20))
    assert rank([1, 2], season) == (2, 1)


def test_net_points_in_all_games_breaks_equal_division_net_points():
    # Split by the same margin; 1 won its other game by more.
    season = _season(_win(1, 2), _win(2, 1), _win(1, 4, by=20), _win(2, 5, by=5))
    assert rank([2, 1], season) == (1, 2)


def test_strength_of_schedule_counts_each_opponent_once():
    # 1 and 2 are level through net points: 1 beat division rival 3 twice and
    # 4 once, 2 beat 3, 4 and 5 once each. Each opponent once, 1's opponents
    # went 3-5 (3 is 0-3, 4 is 3-2) and 2's 3-6 (5 is 0-1), so 1 ranks first;
    # counting 3's 0-3 twice for 1 would rank 2 first.
    season = _season(
        _win(1, 3, by=5),
        _win(1, 3, by=5),
        _win(1, 4),
        _win(2, 3),
        _win(2, 4, by=5),
        _win(2, 5, by=5),
        _win(4, 6),
        _win(4, 6),
        _win(4, 6),
    )
    assert rank([2, 1], season) == (1, 2)


def test_a_step_that_places_one_team_restarts_for_the_rest():
    # 1, 2 and 3 are 2-1 with a head-to-head cycle (1 beat 2, 2 beat 3, 3 beat
    # 1), equal division and conference records and division net points. Net
    # points in all games place 1 first; then 2 and 3 start over at
    # head-to-head, where 2 beat 3, although strength of schedule (step 6)
    # would favor 3.
    season = _season(
        _win(1, 2),
        _win(2, 3),
        _win(3, 1),
        _win(1, 4, by=20),
        _win(2, 5, by=5),
        _win(3, 4, by=5),
        _win(4, 6),
        _win(4, 6),
        _win(4, 6),
    )
    assert rank([3, 2, 1], season) == (1, 2, 3)
