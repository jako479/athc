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
# C and D are the ONLY names for the schedulers, used everywhere a user or
# reader sees one: the `--scheduler` value, output filenames, the report
# header, and the docs. Both fix two non-conference games per team by division
# standings (5ths play each other), then one CP-SAT solve picks the rest
# (phase 2 — week placement — is shared):
#   C (fixed-place+CP-SAT) - the line (c_spread) targets the whole
#                            non-conference slate. The default.
#   D (fixed-place+CP-SAT, free-only) - the line (d_spread) targets only the
#                            picked games.
# Algorithms: docs/scheduler/phase-1-matchups-fixed-cpsat.md (C),
# -fixed-cpsat-free.md (D).
SCHEDULER_C = "C"
SCHEDULER_D = "D"
DEFAULT_SCHEDULER = SCHEDULER_C

_SCHEDULER_NAMES = (SCHEDULER_C, SCHEDULER_D)

# Human-facing labels (e.g. for the report header).
_SCHEDULER_DISPLAY_NAMES = {
    SCHEDULER_C: "Scheduler C (fixed-place + CP-SAT)",
    SCHEDULER_D: "Scheduler D (fixed-place + CP-SAT, free-only)",
}

# C tilts the whole slate (c_spread); D tilts only its picked games (d_spread).
_SCHEDULERS_USING_DIFFICULTY_LINE = frozenset({SCHEDULER_C})
_SCHEDULERS_USING_FREE_DIFFICULTY_LINE = frozenset({SCHEDULER_D})


def available_schedulers() -> tuple[str, ...]:
    """Return the registered scheduler keys (`C`, `D`)."""
    return _SCHEDULER_NAMES


def scheduler_display_name(name: str) -> str:
    """Human-facing label for a scheduler key (falls back to the key)."""
    return _SCHEDULER_DISPLAY_NAMES.get(name, name)


def scheduler_uses_difficulty_line(name: str) -> bool:
    """Whether `name` shapes difficulty with the whole-slate line (C)."""
    return name in _SCHEDULERS_USING_DIFFICULTY_LINE


def scheduler_uses_free_difficulty_line(name: str) -> bool:
    """Whether `name` shapes difficulty with the picked-games line (D)."""
    return name in _SCHEDULERS_USING_FREE_DIFFICULTY_LINE


def get_scheduler(name: str) -> SchedulerFunc:
    """Return the scheduler function for `name`. Raises ValueError if unknown.

    Implementations are imported lazily here so this module stays a leaf —
    schedulers depend on `SchedulerResult` defined above, so an eager import
    at module level would form a cycle.
    """
    if name == SCHEDULER_C:
        from athc.scheduler.schedulers.fixed_cpsat_scheduler import generate_schedule

        return generate_schedule
    if name == SCHEDULER_D:
        from athc.scheduler.schedulers.fixed_cpsat_free_scheduler import (
            generate_schedule,
        )

        return generate_schedule
    choices = ", ".join(_SCHEDULER_NAMES)
    raise ValueError(f"Unknown scheduler '{name}'. Available schedulers: {choices}")
