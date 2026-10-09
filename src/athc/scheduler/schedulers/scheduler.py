"""The scheduler (two-phase CP-SAT): NFL-like same-place seeding.

Phase 1 fixes the same-place games (each division place plays the same place in
every other-conference division that has it, from `[DivisionStandings]`) and any
cross-conference rivalry, then one CP-SAT solve picks the rest, tilting each
team's average opponent conference rank by the configurable `spread`.

Phase 2 uses CP-SAT to place that full inventory into the league's weeks under
the rules in docs/scheduler/phase-2-schedule.md (`schedule_builder.py`); the
season decides rivalry hosting when it rotates.
"""

from __future__ import annotations

from collections.abc import Callable

from athc.scheduler.config import (
    SchedulerConfig,
    check_opening_weeks,
    check_weeks,
    resolve_rivalries,
)
from athc.scheduler.domain.league import League
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.matchup_builder import MatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import SchedulerResult
from athc.scheduler.schedulers.utils import resolve_workers


def generate_schedule(
    league: League,
    seed: int = 0,
    scheduler_config: SchedulerConfig | None = None,
    *,
    season: int,
    progress: Callable[[str], None] | None = None,
) -> SchedulerResult:
    """Build matchups, then build the final schedule for `season`. `progress`
    hears the start of each phase; nothing is printed or logged here."""
    say = progress or (lambda _: None)
    config = scheduler_config or SchedulerConfig()
    weeks = config.league.weeks
    check_weeks(league, weeks)
    check_opening_weeks(league, weeks, config.phase2.opening_nonconference_weeks)
    rivalries = resolve_rivalries(league, config.rivalries)
    # "auto" becomes one count up front, so both phases run the same width and
    # the report can show it.
    workers = resolve_workers(config.solver.solver_workers)

    say("Phase 1: selecting matchups")
    matchup_plan = MatchupBuilder(
        league,
        weeks=weeks,
        rivalries=rivalries,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        workers=workers,
        seed=seed,
    ).build_matchup_plan()

    say(
        "Phase 2: placing games into weeks. This usually takes several "
        "minutes and can take 30 minutes or more."
    )
    schedule_builder = ScheduleBuilder(
        league,
        error_cls=SchedulerError,
        amounts=config.phase2,
        weeks=weeks,
        rivalries=rivalries,
        rotate_rivalry_home_by_season=config.rivalries.rotate_home_by_season,
        season=season,
    )
    schedule = schedule_builder.build_schedule(
        matchups=matchup_plan.matchups,
        seed=seed,
        time_limit=config.solver.time_limit,
        workers=workers,
    )
    return SchedulerResult(
        schedule=schedule, matchup_plan=matchup_plan, workers=workers
    )
