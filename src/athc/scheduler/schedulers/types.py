"""Shared scheduler types and the registry of available scheduler implementations."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from athc.scheduler.domain.league import Team
from athc.scheduler.domain.schedule import Schedule

Matchup = tuple[Team, Team]
Matchups = Sequence[Matchup]


def make_matchup(team_a: Team, team_b: Team) -> Matchup:
    a, b = sorted((team_a, team_b), key=lambda t: t.metro)
    return (a, b)


@dataclass(frozen=True)
class MatchupPlan:
    matchups: Matchups
    fixed_nonconference_pairs: frozenset[Matchup] = frozenset()


@dataclass(frozen=True)
class SchedulerResult:
    schedule: Schedule
    matchup_plan: MatchupPlan
    workers: int  # solver threads both phases ran ("auto" resolved)


SchedulerFunc = Callable[..., SchedulerResult]

# --- The scheduler -----------------------------------------------------------
# There is one scheduler: two-phase CP-SAT. Phase 1 fixes the same-place pairs
# and any cross-conference rivalry, then one CP-SAT solve picks the rest along
# the difficulty line (spread); phase 2 (week placement) follows. Algorithm:
# docs/scheduler/phase-1-matchups.md.
SCHEDULER_DESCRIPTION = "two-phase CP-SAT"


def get_scheduler() -> SchedulerFunc:
    """Return the scheduler's `generate_schedule`.

    Imported lazily so this module stays a leaf — the scheduler depends on
    `SchedulerResult` defined above, so an eager module-level import would
    form a cycle.
    """
    from athc.scheduler.schedulers.scheduler import generate_schedule

    return generate_schedule
