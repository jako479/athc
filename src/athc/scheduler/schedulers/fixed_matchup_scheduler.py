"""Fixed-Matchup PNFL scheduler.

Phase 1 builds the full opponent inventory for the schedule builder to use
to build out the schedule: divisional home-and-away games, conference games,
three non-conference opponents based on a fixed rank table, one extra AFC East
vs NFC East rank-based pairing for teams in the four-team divisions, and one
final AFC vs NFC pairing. LinearSumAssignment is used to determine that final
non-conference pairing based on conference rankings along with head-to-head
history for the coaches.

Phase 2 uses CP-SAT to place that full inventory into the calendar while keeping the
existing weekly/home-away sequencing constraints.
"""

from __future__ import annotations

from athc.scheduler.config import SchedulerConfig
from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.domain.league import League
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_matchup_builder import FixedMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import SchedulerResult


def generate_schedule(
    league: League,
    history: NonConfHistory,
    season: int,
    seed: int = 0,
    scheduler_config: SchedulerConfig | None = None,
) -> SchedulerResult:
    """Build matchups, then build the final schedule."""
    config = scheduler_config or SchedulerConfig()
    matchup_plan = FixedMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=history,
        season=season,
    ).build_matchup_plan()

    schedule_builder = ScheduleBuilder(
        teams=league.teams, error_cls=SchedulerError, amounts=config.phase2
    )
    schedule = schedule_builder.build_schedule(
        matchups=matchup_plan.matchups,
        seed=seed,
        time_limit=config.solver.time_limit,
    )
    return SchedulerResult(schedule=schedule, matchup_plan=matchup_plan)
