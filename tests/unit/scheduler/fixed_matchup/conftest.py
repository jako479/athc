"""Solved-schedule fixtures for Scheduler A (fixed-rank)."""

from __future__ import annotations

import pytest

from athc.scheduler.schedulers.types import SCHEDULER_A, SchedulerResult

from ..conftest import solve_and_report


@pytest.fixture(scope="session")
def scheduler_result(league, tmp_path_factory) -> SchedulerResult:
    return solve_and_report(league, SCHEDULER_A, tmp_path_factory)


@pytest.fixture(scope="session")
def schedule(scheduler_result):
    return scheduler_result.schedule


@pytest.fixture(scope="session")
def matchup_plan(scheduler_result):
    return scheduler_result.matchup_plan
