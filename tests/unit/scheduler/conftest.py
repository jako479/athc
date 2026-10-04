"""Shared fixtures for the scheduler suite.

Solved schedules are built once per league case by `solve_and_report` and
shared through the `solved*` fixtures, so the scheduler is exercised end to end.
Any test using one of those fixtures is auto-marked `slow` and skipped by
default (`-m 'not slow'`); run with `pytest -m slow`.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from click.testing import CliRunner

from athc.scheduler.config import (
    DifficultyConfig,
    LeagueConfig,
    Phase2Config,
    RivalriesConfig,
    SchedulerConfig,
    SolverConfig,
)
from athc.scheduler.domain.league import League, build_league
from athc.scheduler.domain.schedule import Schedule
from athc.scheduler.schedulers.types import SchedulerResult, get_scheduler
from athc.scheduler.writers.report import HtmlReportWriter, build_schedule_report

SLOW_SOLVE_TIME_LIMIT = 1200.0  # cap each slow-test solve at 20 minutes

# --- A league with divisions: two 4-team and two 5-team divisions -------------

_DIVISIONS: dict[str, Sequence[str]] = {
    "AFC_EAST": ("New England", "Buffalo", "Miami", "Jacksonville"),
    "AFC_WEST": (
        "Cincinnati",
        "Denver",
        "Los Angeles",
        "Las Vegas",
        "Pittsburgh",
    ),
    "NFC_EAST": ("Philadelphia", "Washington", "New York", "Atlanta"),
    "NFC_WEST": (
        "Chicago",
        "Green Bay",
        "Minnesota",
        "Seattle",
        "San Francisco",
    ),
}


def _divisional_league(first: Sequence[str], second: Sequence[str]) -> League:
    # Interleave the two 9-team conference orders into one overall 1-18 list so
    # the derived conference ranks still match (1st of each, 2nd of each, ...).
    # Each division's finish order is its conference's order among its members.
    overall = [team for pair in zip(first, second, strict=True) for team in pair]
    standings = {
        name: tuple(
            metro
            for metro in (first if name.startswith("AFC") else second)
            if metro in set(members)
        )
        for name, members in _DIVISIONS.items()
    }
    return build_league(standings, overall, divisions=True)


# Two test leagues: same teams and divisions, different standings. They differ
# in how many of each conference's four playoff teams came from the 4-team
# division: 1 or 3. With three, it's harder to find a schedule that meets all the
# league rules, as well as, to stay close to the strength-of-schedule targets.
ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION = _divisional_league(
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
THREE_PLAYOFF_TEAMS_FROM_4_TEAM_DIVISION = _divisional_league(
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
DIVISIONS_CONFIG = SchedulerConfig(
    solver=SolverConfig(time_limit=SLOW_SOLVE_TIME_LIMIT)
)

# --- A league without divisions: two conferences of nine, 12 weeks, rivalry week

CONFERENCES_WEST = (
    "Ohio State",
    "Notre Dame",
    "UCLA",
    "Washington",
    "Oklahoma",
    "USC",
    "Colorado",
    "Oregon",
    "Michigan",
)
CONFERENCES_EAST = (
    "Texas",
    "Tennessee",
    "Boston College",
    "Arkansas",
    "LSU",
    "Clemson",
    "Georgia",
    "Penn State",
    "Miami",
)
CONFERENCES_OVERALL = (
    "Texas",
    "Tennessee",
    "Notre Dame",
    "Arkansas",
    "Ohio State",
    "Boston College",
    "LSU",
    "UCLA",
    "Washington",
    "Clemson",
    "Oklahoma",
    "Georgia",
    "Penn State",
    "USC",
    "Colorado",
    "Miami",
    "Oregon",
    "Michigan",
)
CONFERENCES_LEAGUE = build_league(
    {"WESTERN": CONFERENCES_WEST, "EASTERN": CONFERENCES_EAST},
    CONFERENCES_OVERALL,
    divisions=False,
)
CONFERENCES_RIVALRIES = (
    ("Michigan", "Ohio State"),
    ("USC", "UCLA"),
    ("Washington", "Oregon"),
    ("Notre Dame", "Colorado"),
    ("Oklahoma", "Texas"),
    ("LSU", "Arkansas"),
    ("Georgia", "Tennessee"),
    ("Clemson", "Miami"),
    ("Penn State", "Boston College"),
)
CONFERENCES_AMOUNTS = Phase2Config(
    max_consecutive_home_or_away=3,
    max_consecutive_conference_home_or_away=2,
    opening_nonconference_weeks=3,
    require_home_balance_per_six_weeks=False,
    require_home_away_streak_caps=False,
    require_mixed_home_away_at_season_ends=False,
)
CONFERENCES_CONFIG = SchedulerConfig(
    league=LeagueConfig(weeks=12),
    difficulty=DifficultyConfig(spread=0.0),
    solver=SolverConfig(time_limit=SLOW_SOLVE_TIME_LIMIT),
    phase2=CONFERENCES_AMOUNTS,
    rivalries=RivalriesConfig(pairs=CONFERENCES_RIVALRIES, rotate_home_by_season=True),
)
NO_ROTATION_CONFIG = replace(
    CONFERENCES_CONFIG,
    rivalries=replace(CONFERENCES_CONFIG.rivalries, rotate_home_by_season=False),
)


@dataclass(frozen=True)
class LeagueCase:
    """A league, its rules and the season to schedule."""

    id: str
    league: League
    config: SchedulerConfig
    season: int
    seed: int | None = None  # None: a random seed, printed with the solve


LEAGUE_CASES = (
    LeagueCase(
        "one-playoff-team-from-4-team-division",
        ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION,
        DIVISIONS_CONFIG,
        2048,
    ),
    LeagueCase(
        "three-playoff-teams-from-4-team-division",
        THREE_PLAYOFF_TEAMS_FROM_4_TEAM_DIVISION,
        DIVISIONS_CONFIG,
        2048,
    ),
    LeagueCase(
        "conferences-even-season", CONFERENCES_LEAGUE, CONFERENCES_CONFIG, 2028, seed=7
    ),
    LeagueCase(
        "conferences-odd-season", CONFERENCES_LEAGUE, CONFERENCES_CONFIG, 2029, seed=7
    ),
    LeagueCase(
        "conferences-no-rotation", CONFERENCES_LEAGUE, NO_ROTATION_CONFIG, 2029, seed=7
    ),
)
CASE_BY_ID = {case.id: case for case in LEAGUE_CASES}
# One case per distinct league, for the phase-1 (matchup) tests.
MATCHUP_CASES = LEAGUE_CASES[:3]


@dataclass(frozen=True)
class Solved:
    case: LeagueCase
    result: SchedulerResult

    @property
    def league(self) -> League:
        return self.case.league

    @property
    def config(self) -> SchedulerConfig:
        return self.case.config

    @property
    def schedule(self) -> Schedule:
        return self.result.schedule


_SOLVED_FIXTURES = frozenset(
    {"solved", "solved_even_season", "solved_odd_season", "solved_no_rotation"}
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def pytest_collection_modifyitems(config, items):
    """Mark solver-backed tests (those that build a schedule) as `slow`."""
    for item in items:
        if _SOLVED_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.slow)


_solve_cache: dict[str, Solved] = {}


def solve_and_report(case: LeagueCase, tmp_path_factory) -> Solved:
    """Solve `case` once (cached) and write its report."""
    if case.id not in _solve_cache:
        seed = case.seed if case.seed is not None else random.randint(0, 1_000_000)
        print(f"\n{case.id}: scheduler seed {seed}")
        result = get_scheduler()(
            league=case.league,
            seed=seed,
            scheduler_config=case.config,
            season=case.season,
        )
        _solve_cache[case.id] = Solved(case, result)
        report = build_schedule_report(
            schedule=result.schedule,
            matchup_plan=result.matchup_plan,
            league=case.league,
            seed=seed,
            config_path=Path("test-config.toml"),
            elapsed_time_seconds=0.0,
            difficulty_spread=case.config.difficulty.spread,
        )
        report_path = tmp_path_factory.mktemp("schedule_report") / f"{case.id}.html"
        HtmlReportWriter(str(report_path), league_name=case.id).write(report)
        print(f"Schedule report: {report_path}")
    return _solve_cache[case.id]


@pytest.fixture(params=LEAGUE_CASES, ids=lambda case: case.id, scope="session")
def league_case(request) -> LeagueCase:
    return request.param


@pytest.fixture(params=MATCHUP_CASES, ids=lambda case: case.id, scope="session")
def matchup_case(request) -> LeagueCase:
    return request.param


@pytest.fixture(scope="session")
def solved(league_case: LeagueCase, tmp_path_factory) -> Solved:
    return solve_and_report(league_case, tmp_path_factory)


@pytest.fixture(scope="session")
def solved_even_season(tmp_path_factory) -> Solved:
    return solve_and_report(CASE_BY_ID["conferences-even-season"], tmp_path_factory)


@pytest.fixture(scope="session")
def solved_odd_season(tmp_path_factory) -> Solved:
    return solve_and_report(CASE_BY_ID["conferences-odd-season"], tmp_path_factory)


@pytest.fixture(scope="session")
def solved_no_rotation(tmp_path_factory) -> Solved:
    return solve_and_report(CASE_BY_ID["conferences-no-rotation"], tmp_path_factory)
