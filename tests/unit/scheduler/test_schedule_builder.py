"""Phase-2 ScheduleBuilder: inventory-guard error paths and soft-objective wiring.

Seed determinism and schedule correctness are covered end-to-end by the golden
regression test in tests/integration/test_generate_schedule.py.
"""

from __future__ import annotations

import pytest

from athc.scheduler.domain.league import Division, Team
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import make_matchup

from .conftest import LEAGUE_5_SLOTS


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


def test_soft_objective_is_added_to_the_model() -> None:
    # Building the model (no solve) wires the soft objective: 8 metrics, each
    # with an over- and under-slack term -> 16 objective terms.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS.teams, SchedulerError)
    builder._populate_model(matchups=[])
    assert len(builder.model.proto.objective.vars) == 16


def test_solver_is_configured_for_reproducible_parallel_search() -> None:
    # The worker count must reach the solver as a fixed interleave width (both
    # num_search_workers and interleave_batch_size), stopping on deterministic
    # time -- this is what keeps a seed reproducible across machines.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS.teams, SchedulerError)
    params = builder._make_solver(seed=3, time_limit=42.0, workers=5).parameters
    assert params.random_seed == 3
    assert params.num_search_workers == 5
    assert params.interleave_search is True
    assert params.interleave_batch_size == 5
    assert params.max_deterministic_time == 42.0
