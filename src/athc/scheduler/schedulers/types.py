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


SchedulerFunc = Callable[..., SchedulerResult]

# --- Scheduler registry -----------------------------------------------------
# C is the only scheduler. Its name shows everywhere a user or reader sees one:
# the output filenames, the report header, and the docs. It fixes two
# non-conference games per team by division standings (5ths play each other),
# then one CP-SAT solve picks the rest along the difficulty line (c_spread);
# phase 2 (week placement) follows. Algorithm:
# docs/scheduler/phase-1-matchups-fixed-cpsat.md.
SCHEDULER_C = "C"
DEFAULT_SCHEDULER = SCHEDULER_C

_SCHEDULER_NAMES = (SCHEDULER_C,)

# Human-facing labels (e.g. for the report header).
_SCHEDULER_DISPLAY_NAMES = {
    SCHEDULER_C: "Scheduler C (fixed-place + CP-SAT)",
}

# C tilts the whole non-conference slate (c_spread).
_SCHEDULERS_USING_DIFFICULTY_LINE = frozenset({SCHEDULER_C})


def available_schedulers() -> tuple[str, ...]:
    """Return the registered scheduler keys (`C`)."""
    return _SCHEDULER_NAMES


def scheduler_display_name(name: str) -> str:
    """Human-facing label for a scheduler key (falls back to the key)."""
    return _SCHEDULER_DISPLAY_NAMES.get(name, name)


def scheduler_uses_difficulty_line(name: str) -> bool:
    """Whether `name` shapes difficulty with the whole-slate line (C)."""
    return name in _SCHEDULERS_USING_DIFFICULTY_LINE


def get_scheduler(name: str) -> SchedulerFunc:
    """Return the scheduler function for `name`. Raises ValueError if unknown.

    Implementations are imported lazily here so this module stays a leaf —
    schedulers depend on `SchedulerResult` defined above, so an eager import
    at module level would form a cycle.
    """
    if name == SCHEDULER_C:
        from athc.scheduler.schedulers.fixed_cpsat_scheduler import generate_schedule

        return generate_schedule
    choices = ", ".join(_SCHEDULER_NAMES)
    raise ValueError(f"Unknown scheduler '{name}'. Available schedulers: {choices}")
