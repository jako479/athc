"""Solved PCFL schedules: an even season, an odd season, and rotation off.

These solves have no objective, so CP-SAT stops at the first feasible schedule,
but each still takes about 30 s, so the tests using them are marked `slow`
(see the module note in test_schedule_rules.py).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from athc.scheduler.config import (
    DifficultyConfig,
    LeagueConfig,
    Phase2Config,
    RivalriesConfig,
    SchedulerConfig,
)
from athc.scheduler.schedulers.types import SchedulerResult, get_scheduler

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

PCFL_CONFIG = SchedulerConfig(
    league=LeagueConfig(weeks=12),
    difficulty=DifficultyConfig(spread=0.0),
    phase2=Phase2Config(
        max_consecutive_home_or_away=3,
        max_consecutive_conference_home_or_away=2,
        opening_nonconference_weeks=3,
        require_home_balance_per_six_weeks=False,
        require_home_away_streak_caps=False,
        require_mixed_home_away_at_season_ends=False,
    ),
    rivalries=RivalriesConfig(pairs=PCFL_RIVALRIES, rotate_home_by_season=True),
)
NO_ROTATION_CONFIG = replace(
    PCFL_CONFIG, rivalries=replace(PCFL_CONFIG.rivalries, rotate_home_by_season=False)
)


def _solve(season: int, config: SchedulerConfig = PCFL_CONFIG) -> SchedulerResult:
    return get_scheduler()(
        league=PCFL_LEAGUE, seed=7, scheduler_config=config, season=season
    )


@pytest.fixture(scope="session")
def pcfl_even() -> SchedulerResult:
    return _solve(2028)


@pytest.fixture(scope="session")
def pcfl_odd() -> SchedulerResult:
    return _solve(2029)


@pytest.fixture(scope="session")
def pcfl_free() -> SchedulerResult:
    return _solve(2029, NO_ROTATION_CONFIG)


@pytest.fixture(params=["pcfl_even", "pcfl_odd", "pcfl_free"])
def pcfl_result(request) -> SchedulerResult:
    return request.getfixturevalue(request.param)
