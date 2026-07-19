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
    extra_nonconference_pairs: frozenset[Matchup] = frozenset()
    history_nonconference_pairs: frozenset[Matchup] = frozenset()


@dataclass(frozen=True)
class SchedulerResult:
    schedule: Schedule
    matchup_plan: MatchupPlan


SchedulerFunc = Callable[..., SchedulerResult]

# --- Scheduler registry -----------------------------------------------------
# A, B, C, and D are the ONLY names for the schedulers, used everywhere a user
# or reader sees one: the `--scheduler` value, output filenames, the report
# header, and the docs. This block (plus docs/scheduler/) is the single place
# that says what they are. They differ only in how phase 1 picks
# non-conference matchups (phase 2 — week placement — is shared):
#   A (fixed-rank)         - a fixed conference-rank table + head-to-head history;
#                            needs the <season>.nonconf_history.json file.
#   B (full CP-SAT)        - one CP-SAT minimax solve over all matchups. The default.
#   C (fixed-place+CP-SAT) - NFL-like: [DivisionStandings] fixes 2 same-place
#                            games/team (5ths play each other), then one CP-SAT
#                            solve fills the rest by conference rank. No history.
#   D (fixed-place+CP-SAT, free-only) - C, but the line targets only the
#                            picked games (d_spread).
# Algorithms: docs/scheduler/phase-1-matchups.md (B), -fixed-rank.md (A),
# -fixed-cpsat.md (C), -fixed-cpsat-free.md (D).
SCHEDULER_A = "A"
SCHEDULER_B = "B"
SCHEDULER_C = "C"
SCHEDULER_D = "D"
DEFAULT_SCHEDULER = SCHEDULER_B

_SCHEDULER_NAMES = (SCHEDULER_A, SCHEDULER_B, SCHEDULER_C, SCHEDULER_D)

# Human-facing labels (e.g. for the report header).
_SCHEDULER_DISPLAY_NAMES = {
    SCHEDULER_A: "Scheduler A (fixed-rank)",
    SCHEDULER_B: "Scheduler B (full CP-SAT)",
    SCHEDULER_C: "Scheduler C (fixed-place + CP-SAT)",
    SCHEDULER_D: "Scheduler D (fixed-place + CP-SAT, free-only)",
}

# Only A reads the non-conference history; the others ignore it.
_SCHEDULERS_USING_HISTORY = frozenset({SCHEDULER_A})

# C and D read the league file's [DivisionStandings] section.
_SCHEDULERS_USING_DIVISION_STANDINGS = frozenset({SCHEDULER_C, SCHEDULER_D})

# B: overall-rank sine curve. C: conference-rank line (c_spread). D: same
# line, picked games only (d_spread). A: fixed table.
_SCHEDULERS_USING_DIFFICULTY_CURVE = frozenset({SCHEDULER_B})
_SCHEDULERS_USING_DIFFICULTY_LINE = frozenset({SCHEDULER_C})
_SCHEDULERS_USING_FREE_DIFFICULTY_LINE = frozenset({SCHEDULER_D})


def available_schedulers() -> tuple[str, ...]:
    """Return the registered scheduler keys (`A`, `B`, `C`, `D`)."""
    return _SCHEDULER_NAMES


def scheduler_display_name(name: str) -> str:
    """Human-facing label for a scheduler key (falls back to the key)."""
    return _SCHEDULER_DISPLAY_NAMES.get(name, name)


def scheduler_uses_history(name: str) -> bool:
    """Whether `name` needs the non-conference history file."""
    return name in _SCHEDULERS_USING_HISTORY


def scheduler_uses_division_standings(name: str) -> bool:
    """Whether `name` needs the league file's [DivisionStandings] section."""
    return name in _SCHEDULERS_USING_DIVISION_STANDINGS


def scheduler_uses_difficulty_curve(name: str) -> bool:
    """Whether `name` shapes difficulty with the overall-rank sine curve (B)."""
    return name in _SCHEDULERS_USING_DIFFICULTY_CURVE


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
    if name == SCHEDULER_B:
        from athc.scheduler.schedulers.scheduler import generate_schedule

        return generate_schedule
    if name == SCHEDULER_A:
        from athc.scheduler.schedulers.fixed_matchup_scheduler import generate_schedule

        return generate_schedule
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
