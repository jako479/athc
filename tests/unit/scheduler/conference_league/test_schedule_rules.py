"""Every PCFL rule, checked on solved schedules (see conftest for the configs).

Marked `slow`: each of the three solves takes about 30 s; run with `-m slow`.
"""

from __future__ import annotations

from collections import Counter

import pytest

from athc.scheduler.config import RivalriesConfig, resolve_rivalries
from athc.scheduler.domain.schedule import Schedule
from athc.scheduler.schedulers.types import make_matchup
from athc.scheduler.writers.report import build_schedule_report

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

pytestmark = pytest.mark.slow

WEEKS = 12
RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))
TEAMS = PCFL_LEAGUE.teams


def _games(schedule: Schedule, team):
    return sorted(schedule.games_for(team), key=lambda g: g.week)


def _is_conference(game) -> bool:
    return game.home.conference == game.away.conference


def test_structure(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    assert len(schedule.games) == WEEKS * 9
    for week in range(1, WEEKS + 1):
        assert sum(1 for g in schedule.games if g.week == week) == 9, week
    for team in TEAMS:
        games = _games(schedule, team)
        assert [g.week for g in games] == list(range(1, WEEKS + 1)), team.metro
        assert len(schedule.home_games_for(team)) == 6, team.metro


def test_matches_phase_one_inventory(pcfl_result) -> None:
    counts = Counter(make_matchup(g.home, g.away) for g in pcfl_result.schedule.games)
    assert counts == Counter(pcfl_result.matchup_plan.matchups)


def test_conference_round_robin_four_home_four_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        conference = [g for g in _games(schedule, team) if _is_conference(g)]
        opponents = {g.away if g.home == team else g.home for g in conference}
        assert opponents == set(PCFL_LEAGUE.conference_opponents(team)), team.metro
        assert sum(1 for g in conference if g.home == team) == 4, team.metro


def test_nonconference_two_home_two_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        nonconference = [g for g in _games(schedule, team) if not _is_conference(g)]
        assert len(nonconference) == 4, team.metro
        assert sum(1 for g in nonconference if g.home == team) == 2, team.metro


def test_opening_weeks_are_all_nonconference(pcfl_result) -> None:
    for game in pcfl_result.schedule.games:
        if game.week <= 3:
            assert not _is_conference(game), game


def test_later_weeks_hold_exactly_one_cross_conference_game(pcfl_result) -> None:
    for week in range(4, WEEKS + 1):
        cross = [
            g
            for g in pcfl_result.schedule.games
            if g.week == week and not _is_conference(g)
        ]
        assert len(cross) == 1, week


def test_max_three_consecutive_home_or_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        home = [g.home == team for g in _games(schedule, team)]
        for start in range(WEEKS - 3):
            assert 1 <= sum(home[start : start + 4]) <= 3, (team.metro, start + 1)


def test_max_two_consecutive_conference_home_or_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        venues = [g.home == team for g in _games(schedule, team) if _is_conference(g)]
        assert len(venues) == 8, team.metro
        for start in range(len(venues) - 2):
            assert len(set(venues[start : start + 3])) == 2, (team.metro, start)


def test_final_week_is_rivalry_week(pcfl_result) -> None:
    final = {
        make_matchup(g.home, g.away)
        for g in pcfl_result.schedule.games
        if g.week == WEEKS
    }
    assert final == {make_matchup(a, b) for a, b in RIVALRIES}


def test_even_season_first_listed_hosts(pcfl_even) -> None:
    hosts = {g.home for g in pcfl_even.schedule.games if g.week == WEEKS}
    assert hosts == {first for first, _ in RIVALRIES}


def test_odd_season_second_listed_hosts(pcfl_odd) -> None:
    hosts = {g.home for g in pcfl_odd.schedule.games if g.week == WEEKS}
    assert hosts == {second for _, second in RIVALRIES}


def test_rotation_off_still_plays_rivalries_in_the_final_week(pcfl_free) -> None:
    final = {
        make_matchup(g.home, g.away)
        for g in pcfl_free.schedule.games
        if g.week == WEEKS
    }
    assert final == {make_matchup(a, b) for a, b in RIVALRIES}


def test_report_builds_for_a_league_without_divisions(pcfl_even) -> None:
    report = build_schedule_report(
        schedule=pcfl_even.schedule,
        matchup_plan=pcfl_even.matchup_plan,
        league=PCFL_LEAGUE,
        seed=7,
        config_path="test",
        elapsed_time_seconds=0.0,
        difficulty_spread=0.0,
    )
    assert len(report.teams) == 18
    assert all(len(row.nonconference_opponents) == 4 for row in report.teams)
