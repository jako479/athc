"""The scheduler entry rejects a config that does not fit the league before
it solves anything."""

from __future__ import annotations

from dataclasses import replace

import pytest

from athc.scheduler.config import ConfigError, LeagueConfig, RivalriesConfig
from athc.scheduler.schedulers.types import get_scheduler

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES
from .conftest import PCFL_CONFIG


def _generate(config) -> None:
    get_scheduler()(league=PCFL_LEAGUE, seed=0, scheduler_config=config, season=2029)


def test_entry_rejects_weeks_that_do_not_fit_the_league() -> None:
    config = replace(PCFL_CONFIG, league=LeagueConfig(weeks=8))
    with pytest.raises(ConfigError, match="weeks"):
        _generate(config)


def test_entry_rejects_opening_weeks_that_leave_no_room() -> None:
    config = replace(
        PCFL_CONFIG, phase2=replace(PCFL_CONFIG.phase2, opening_nonconference_weeks=4)
    )
    with pytest.raises(ConfigError, match="opening_nonconference_weeks"):
        _generate(config)


def test_entry_rejects_an_unknown_rivalry_team() -> None:
    pairs = (*PCFL_RIVALRIES[:8], ("Penn State", "Nowhere"))
    config = replace(PCFL_CONFIG, rivalries=RivalriesConfig(pairs=pairs))
    with pytest.raises(ConfigError, match="Unknown team"):
        _generate(config)
