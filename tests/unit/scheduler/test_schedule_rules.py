"""Every rule, checked on a solved schedule for every league case (conftest).

The validator in `tests/integration/schedule_validation.py` applies the rules
that fit the league and its config; the hosting tests pin which rival hosts.
Slow: each case is a full solve; run with `pytest -m slow`.
"""

from __future__ import annotations

from collections import Counter

from athc.scheduler.config import resolve_rivalries
from athc.scheduler.schedulers.types import make_matchup
from tests.integration.schedule_validation import validate_schedule

from .conftest import Solved


def _final_week_games(solved: Solved):
    weeks = solved.config.league.weeks
    return [g for g in solved.schedule.games if g.week == weeks]


def _rivalries(solved: Solved):
    return resolve_rivalries(solved.league, solved.config.rivalries)


def test_solved_schedule_obeys_every_rule(solved: Solved) -> None:
    validate_schedule(
        solved.schedule, solved.league, solved.config, season=solved.case.season
    )


def test_solved_schedule_realizes_the_phase_one_inventory(solved: Solved) -> None:
    counts = Counter(make_matchup(g.home, g.away) for g in solved.schedule.games)
    assert counts == Counter(solved.result.matchup_plan.matchups)


def test_even_season_first_listed_rival_hosts(solved_even_season: Solved) -> None:
    hosts = {g.home for g in _final_week_games(solved_even_season)}
    assert hosts == {first for first, _ in _rivalries(solved_even_season)}


def test_odd_season_second_listed_rival_hosts(solved_odd_season: Solved) -> None:
    hosts = {g.home for g in _final_week_games(solved_odd_season)}
    assert hosts == {second for _, second in _rivalries(solved_odd_season)}


def test_rotation_off_still_plays_rivalries_in_the_final_week(
    solved_no_rotation: Solved,
) -> None:
    final = {
        make_matchup(g.home, g.away) for g in _final_week_games(solved_no_rotation)
    }
    assert final == {make_matchup(a, b) for a, b in _rivalries(solved_no_rotation)}
