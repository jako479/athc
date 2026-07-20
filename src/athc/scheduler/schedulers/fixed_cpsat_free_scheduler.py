"""Scheduler D (fixed-place + CP-SAT, free-only): Scheduler C, but the
difficulty line targets only the picked games.

Phase 1 fixes two non-conference games per team by division place (from
`[DivisionStandings]`; 5th places play each other), then one CP-SAT solve
picks the rest, tilting each team's average picked-opponent conference rank
by the configurable `d_spread`. The fixed games do not count toward the line.

Phase 2 uses CP-SAT to place that full inventory into the calendar, sharing
the same week/home-away sequencing constraints as Scheduler C.
"""

from __future__ import annotations

import logging

from athc.scheduler.config import SchedulerConfig
from athc.scheduler.domain.league import League
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_cpsat_free_builder import (
    FixedCpsatFreeMatchupBuilder,
)
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import SchedulerResult

logger = logging.getLogger(__name__)


def generate_schedule(
    league: League,
    seed: int = 0,
    scheduler_config: SchedulerConfig | None = None,
) -> SchedulerResult:
    """Build matchups, then build the final schedule."""
    config = scheduler_config or SchedulerConfig()
    logger.info("Phase 1: selecting matchups")
    matchup_plan = FixedCpsatFreeMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
        d_spread=config.difficulty.d_spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        seed=seed,
    ).build_matchup_plan()

    logger.info(
        "Phase 2: placing games into weeks. This usually takes several "
        "minutes and can take 30 minutes or more.",
    )
    schedule_builder = ScheduleBuilder(
        teams=league.teams, error_cls=SchedulerError, amounts=config.phase2
    )
    schedule = schedule_builder.build_schedule(
        matchups=matchup_plan.matchups,
        seed=seed,
        time_limit=config.solver.time_limit,
    )
    return SchedulerResult(schedule=schedule, matchup_plan=matchup_plan)
