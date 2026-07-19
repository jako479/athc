"""Shared fixtures for the scheduler suite.

The `fixed_cpsat` (C) and `fixed_cpsat_free` (D) folders each provide their
own `scheduler_result` / `schedule` / `matchup_plan` fixtures (via
`solve_and_report` below), so both schedulers are exercised end-to-end. Any
test using one of those fixtures is auto-marked `slow` plus its scheduler's
`slow_c`/`slow_d`, and skipped by default (`-m 'not slow'`); run all with
`pytest -m slow`, or one scheduler with e.g. `pytest -m slow_c`.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from pathlib import Path

import pytest
from click.testing import CliRunner

from athc.scheduler.config import SchedulerConfig, SolverConfig
from athc.scheduler.domain.league import Division, League, build_league
from athc.scheduler.schedulers.types import SchedulerResult, get_scheduler
from athc.scheduler.writers.report import HtmlReportWriter, build_schedule_report

SLOW_SOLVE_TIME_LIMIT = 1200.0  # cap each slow-test solve at 20 minutes

_DIVISIONS: dict[str, Sequence[str]] = {
    Division.AFC_EAST.name: ("New England", "Buffalo", "Miami", "Jacksonville"),
    Division.AFC_WEST.name: (
        "Cincinnati",
        "Denver",
        "Los Angeles",
        "Las Vegas",
        "Pittsburgh",
    ),
    Division.NFC_EAST.name: ("Philadelphia", "Washington", "New York", "Atlanta"),
    Division.NFC_WEST.name: (
        "Chicago",
        "Green Bay",
        "Minnesota",
        "Seattle",
        "San Francisco",
    ),
}


def _make_league(afc: Sequence[str], nfc: Sequence[str]) -> League:
    # Interleave the two 9-team conference orders into one overall 1-18 list so the
    # derived conference ranks still match afc/nfc (1st AFC, 1st NFC, 2nd AFC, ...).
    # Division standings follow the same order within each division.
    overall = [team for pair in zip(afc, nfc, strict=True) for team in pair]
    standings = {
        name: tuple(
            metro
            for metro in (afc if name.startswith("AFC") else nfc)
            if metro in set(members)
        )
        for name, members in _DIVISIONS.items()
    }
    return build_league(_DIVISIONS, overall, division_standings=standings)


LEAGUE_5_SLOTS = _make_league(
    (
        "New England",
        "Cincinnati",
        "Pittsburgh",
        "Denver",
        "Miami",
        "Buffalo",
        "Jacksonville",
        "Los Angeles",
        "Las Vegas",
    ),
    (
        "Washington",
        "Chicago",
        "Minnesota",
        "San Francisco",
        "Atlanta",
        "New York",
        "Philadelphia",
        "Green Bay",
        "Seattle",
    ),
)
LEAGUE_6_SLOTS = _make_league(
    (
        "New England",
        "Cincinnati",
        "Miami",
        "Pittsburgh",
        "Buffalo",
        "Jacksonville",
        "Denver",
        "Los Angeles",
        "Las Vegas",
    ),
    (
        "Washington",
        "Chicago",
        "Atlanta",
        "Minnesota",
        "New York",
        "Philadelphia",
        "San Francisco",
        "Green Bay",
        "Seattle",
    ),
)
LEAGUE_7_SLOTS = _make_league(
    (
        "New England",
        "Cincinnati",
        "Miami",
        "Buffalo",
        "Jacksonville",
        "Pittsburgh",
        "Denver",
        "Los Angeles",
        "Las Vegas",
    ),
    (
        "Washington",
        "Chicago",
        "Atlanta",
        "New York",
        "Philadelphia",
        "Minnesota",
        "San Francisco",
        "Green Bay",
        "Seattle",
    ),
)

# Three conference-ranking variants spanning the playoff-distribution splits:
# each conference has 4 playoff teams (2 division winners + 2 wild cards), and
# the 4-team (East) division supplies 1, 2, or 3 of them (label = 4 + that =
# 5/6/7), the 5-team (West) division the rest. This varies how many
# 5-non-conf-game teams rank near the top, which stresses the difficulty
# targets. The scheduler uses plain conference rank, not playoffs.
_ALL_LEAGUES = [
    pytest.param(LEAGUE_5_SLOTS, id="5-free-slots"),
    pytest.param(LEAGUE_6_SLOTS, id="6-free-slots"),
    pytest.param(LEAGUE_7_SLOTS, id="7-free-slots"),
]

_SOLVER_FIXTURES = frozenset({"scheduler_result", "schedule", "matchup_plan"})


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# Folder -> per-scheduler slow marker, so one scheduler's slow tests can run
# alone (e.g. `pytest -m slow_c`).
_SCHEDULER_SLOW_MARKERS = {
    "fixed_cpsat": "slow_c",
    "fixed_cpsat_free": "slow_d",
}


def pytest_collection_modifyitems(config, items):
    """Mark solver-backed tests (those that build a schedule) as `slow`, plus
    the per-scheduler `slow_c`/`slow_d` marker."""
    for item in items:
        if _SOLVER_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.slow)
            for folder, name in _SCHEDULER_SLOW_MARKERS.items():
                if folder in item.path.parts:
                    item.add_marker(getattr(pytest.mark, name))


_solve_cache: dict[tuple[int, str], SchedulerResult] = {}


@pytest.fixture(params=_ALL_LEAGUES, scope="session")
def league(request) -> League:
    return request.param


@pytest.fixture(scope="session")
def teams(league: League):
    return league.teams


def solve_and_report(league, scheduler_kind, tmp_path_factory) -> SchedulerResult:
    """Solve `league` with `scheduler_kind` once (cached) and write its report.

    Each scheduler folder's conftest wraps this in its own `scheduler_result`
    fixture, so both schedulers are exercised end-to-end.
    """
    key = (id(league), scheduler_kind)
    if key not in _solve_cache:
        seed = random.randint(0, 1_000_000)
        print(f"\nScheduler seed ({scheduler_kind}): {seed}")
        result = get_scheduler(scheduler_kind)(
            league=league,
            seed=seed,
            scheduler_config=SchedulerConfig(
                solver=SolverConfig(time_limit=SLOW_SOLVE_TIME_LIMIT)
            ),
        )
        _solve_cache[key] = result
        report = build_schedule_report(
            schedule=result.schedule,
            matchup_plan=result.matchup_plan,
            league=league,
            seed=seed,
            scheduler_kind=scheduler_kind,
            config_path=Path("test-config.ini"),
            elapsed_time_seconds=0.0,
        )
        report_path = tmp_path_factory.mktemp("schedule_report") / "report.html"
        HtmlReportWriter(str(report_path)).write(report)
        print(f"Schedule report: {report_path}")
    return _solve_cache[key]
