"""The scheduler (two-phase CP-SAT): NFL-like same-place seeding.

Phase 1 fixes the same-place games (each division place plays the same place in
every other-conference division that has it, from the divisions' finish orders)
and any cross-conference rivalry, then one CP-SAT solve picks the rest: each
team's opponent conference ranks add up close to a target tilted by the
configurable `difficulty_slope`, or with `random_nonconference` the picks are
random from the seed.

Phase 2 uses CP-SAT to place that full inventory into the league's weeks under
the rules in docs/design/scheduler-phase-2-schedule.md (`schedule_builder.py`); the
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
    check_weeks(league, weeks, path=config.source)
    check_opening_weeks(
        league, weeks, config.phase2.opening_nonconference_weeks, path=config.source
    )
    rivalries = resolve_rivalries(league, config.rivalries, path=config.source)
    # "auto" becomes one count up front, so both phases run the same width and
    # the report can show it.
    workers = resolve_workers(config.solver.solver_workers)

    say("Phase 1: selecting matchups")
    matchup_plan = MatchupBuilder(
        league,
        weeks=weeks,
        rivalries=rivalries,
        difficulty_slope=config.phase1.difficulty_slope,
        random_nonconference=config.phase1.random_nonconference,
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
        config_path=config.source,
    )
    schedule = schedule_builder.build_schedule(
        matchups=matchup_plan.matchups,
        seed=seed,
        time_limit=config.solver.phase2_time_limit,
        workers=workers,
    )
    return SchedulerResult(
        schedule=schedule, matchup_plan=matchup_plan, workers=workers
    )
