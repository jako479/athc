"""Phase-2 ScheduleBuilder: inventory-guard error paths and seed determinism."""

from __future__ import annotations

import pytest

from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.domain.league import Division, Team
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_matchup_builder import FixedMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import make_matchup

from .conftest import (
    HISTORY_PATH,
    LEAGUE_5_SLOTS,
    SLOW_SOLVE_TIME_LIMIT,
)


def test_unknown_pair_in_inventory_raises() -> None:
    teams = LEAGUE_5_SLOTS.teams
    foreign = Team(metro="Nowhere", division=Division.AFC_EAST)
    builder = ScheduleBuilder(teams, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([make_matchup(foreign, teams[0])], seed=0, time_limit=5)


def test_empty_inventory_is_infeasible() -> None:
    teams = LEAGUE_5_SLOTS.teams
    builder = ScheduleBuilder(teams, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([], seed=0, time_limit=30)


@pytest.mark.slow
def test_schedule_is_deterministic_for_a_seed() -> None:
    league = LEAGUE_5_SLOTS
    inventory = (
        FixedMatchupBuilder(
            teams=league.teams,
            rankings=league.rankings,
            history=NonConfHistory.load(HISTORY_PATH),
        )
        .build_matchup_plan()
        .matchups
    )

    def solve() -> set[tuple[int, str, str]]:
        # Phase-2 placement here takes ~2-4 min and varies run to run, so use the
        # standard slow-solve cap: both runs must complete to compare equal.
        schedule = ScheduleBuilder(league.teams, SchedulerError).build_schedule(
            inventory, seed=42, time_limit=SLOW_SOLVE_TIME_LIMIT
        )
        return {(g.week, g.home.metro, g.away.metro) for g in schedule.games}

    assert solve() == solve()
