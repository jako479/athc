# PCFL Scheduler (second league format) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One matchup builder and one schedule builder produce schedules for both the PNFL (18 teams, 4 divisions, 16 weeks) and the PCFL (18 teams, no divisions, 12 weeks, rivalry week), driven by the league file and the scheduler rules file.

**Architecture:** The domain model replaces the PNFL enums with plain `Conference` / `Division` / `Team` values so a team may have no division; `League` answers structural questions (opponent classes, non-conference count for a given number of weeks). Phase 1 (matchup inventory) and phase 2 (CP-SAT week placement) read that structure plus `weeks`, rivalries and new phase-2 amounts; every PNFL-only rule is gated so the PNFL CP-SAT model stays byte-identical (a fast fingerprint test pins it; the slow golden test proves it end to end).

**Tech Stack:** Python 3.12 (pyright pinned to 3.12; the venv is 3.13 — no 3.13-only syntax), OR-Tools CP-SAT, `tomllib`, `configparser`, pytest (coverage floor 92%), ruff, pyright standard.

**Spec:** `docs/superpowers/specs/2026-09-27-pcfl-scheduler-design.md`

## Global Constraints

- Work only in this worktree: `C:\Users\Brian\Projects\PNFL\athc\.claude\worktrees\pcfl-scheduler`. Never touch the parent checkout or other worktrees.
- Do not change `src/athc/cli/*`, `src/athc/config.py`, `dev/athc.ini`, `dev/rules/*`, `release/*`. The PCFL data files go under `dev/leagues/PCFL/` exactly as named below.
- The PNFL CP-SAT models (phase 1 and phase 2) must stay byte-identical: same variables, same names, same constraint order. Gated rules add nothing when off. The fingerprint test (Task 1) must pass after every task.
- Only the PCFL rules listed in the spec apply to a league without divisions.
- Team count stays 18 (two conferences of 9); do not generalize it.
- Commands, one per call, never chained: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`. All four green before a task is done. Never run them as a baseline before changing anything.
- Every limit or range introduced gets tests at the limit (accepted) and one past it (rejected).
- Commit messages: one line, prefixed `scheduler:`; never mention Claude, Anthropic or AI; no trailers.
- Never edit expected test data or assertions to make a failing test pass; investigate the code.
- Docs: very simple, clear, high-level. New CHANGELOG / STATUS / WORKLOG entries go at the top of their section. Do not edit `TODO.md`.
- Comments explain why, not what.

## Review Focus

Inputs the spec implies that a person will hit; each has its test pinned to the owning task:

1. A PCFL rules file with `opening_nonconference_weeks = 4` (the user's original wording) must fail with a clear `ConfigError`, not a solver "no feasible schedule" — Task 3.
2. A rivalry list that names a team twice, misses a team, or has three cross-conference pairs must fail at resolution, not in the solver — Task 3.
3. A standings file with both `[DivisionStandings]` and `[ConferenceStandings]`, or neither, must fail naming the sections — Task 2.
4. A PNFL rules file that turns `require_home_away_streak_caps` off must fail at builder construction (the soft objective needs the flags), not with a `KeyError` — Task 6.
5. Rivalry rotation with no season must fail at construction, not silently host the first-listed team — Task 7.

---

### Task 1: Pin the PNFL models (fingerprint test) and sort the fixed pairs

The refactor must not change the PNFL CP-SAT models. Freeze a SHA-256 of both phase models for the golden league before touching anything else. Phase 1 today iterates a `frozenset` of fixed pairs when pinning them (`_add_fixed_pair_constraints`), which is hash-randomized per process; sort them first so the proto is deterministic (the golden already passes under every order, so this is safe).

**Files:**
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_builder.py` (`_add_fixed_pair_constraints`, `_solve_nonconference_pairs`)
- Create: `tests/unit/scheduler/test_pnfl_model_fingerprint.py`

**Interfaces:**
- Produces: `FixedCpsatMatchupBuilder._nonconference_model(fixed_pairs) -> _FixedCpsatNonConferenceModel` (built, unsolved). Later tasks keep this method and the test.

- [ ] **Step 1: Sort the fixed pairs when pinning them**

In `fixed_cpsat_builder.py`, replace the body of `_add_fixed_pair_constraints`:

```python
    def _add_fixed_pair_constraints(self) -> None:
        # Sorted: a frozenset iterates in hash order, which differs per process,
        # and the built model must be identical for a seed to reproduce.
        for team_a, team_b in sorted(
            self.fixed_pairs, key=lambda pair: (pair[0].metro, pair[1].metro)
        ):
            afc, nfc = (
                (team_a, team_b)
                if team_a.conference == Conference.AFC
                else (team_b, team_a)
            )
            self.model.add(self.x[afc, nfc] == 1)
```

- [ ] **Step 2: Split model building from solving**

Replace `_solve_nonconference_pairs` in `FixedCpsatMatchupBuilder` with:

```python
    def _nonconference_model(
        self, fixed_pairs: set[Matchup]
    ) -> _FixedCpsatNonConferenceModel:
        """The built (unsolved) non-conference model; tests fingerprint it."""
        model = _FixedCpsatNonConferenceModel(
            ranked_teams_by_conf=self.ranked_teams_by_conf,
            conf_rank=self.conf_rank,
            fixed_pairs=frozenset(fixed_pairs),
            spread=self.spread,
        )
        model.build()
        return model

    def _solve_nonconference_pairs(self, fixed_pairs: set[Matchup]) -> set[Matchup]:
        return self._nonconference_model(fixed_pairs).solve(
            seed=self.seed, time_limit=self.phase1_time_limit
        )
```

- [ ] **Step 3: Write the fingerprint test with placeholder hashes**

Create `tests/unit/scheduler/test_pnfl_model_fingerprint.py`:

```python
"""The PNFL CP-SAT models must not drift.

A seed's schedule is a function of the exact model, so both phase models for
the golden league are hashed and pinned here (fast; no solve of phase 2). The
slow golden test in tests/integration is the end-to-end proof. Re-pin only
after an intentional PNFL model change, together with the goldens.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from athc.scheduler.config import SchedulerConfig, load_league, load_scheduler_config
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_cpsat_builder import FixedCpsatMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder

DATA = Path(__file__).resolve().parents[2] / "integration" / "data"
GOLDEN_LEAGUE = DATA / "league.ini"
GOLDEN_RULES = DATA / "PNFL.scheduler.toml"

PHASE1_SHA256 = "pending"
PHASE2_SHA256 = "pending"


def _sha256(model) -> str:
    return hashlib.sha256(model.proto.SerializeToString()).hexdigest()


def _golden_config(config_dir: Path) -> SchedulerConfig:
    rules = config_dir / "rules"
    rules.mkdir(exist_ok=True)
    shutil.copy(GOLDEN_RULES, rules / "PNFL.scheduler.toml")
    return load_scheduler_config()


def test_pnfl_phase_models_are_unchanged(config_dir: Path) -> None:
    league = load_league(GOLDEN_LEAGUE)
    config = _golden_config(config_dir)

    builder = FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        seed=0,
    )
    phase1 = _sha256(builder._nonconference_model(builder._fixed_place_pairs()).model)
    plan = builder.build_matchup_plan()

    schedule_builder = ScheduleBuilder(league.teams, SchedulerError, config.phase2)
    schedule_builder._populate_model(plan.matchups)
    phase2 = _sha256(schedule_builder.model)

    assert (phase1, phase2) == (PHASE1_SHA256, PHASE2_SHA256), (
        f"PNFL model changed: phase1={phase1} phase2={phase2}"
    )
```

- [ ] **Step 4: Run it to capture the hashes**

Run: `uv run pytest tests/unit/scheduler/test_pnfl_model_fingerprint.py -v`
Expected: FAIL with `PNFL model changed: phase1=<64 hex> phase2=<64 hex>`. Copy both values into `PHASE1_SHA256` / `PHASE2_SHA256`.

- [ ] **Step 5: Verify the hashes are stable across hash seeds**

Run: `PYTHONHASHSEED=1 uv run pytest tests/unit/scheduler/test_pnfl_model_fingerprint.py -q`
Run: `PYTHONHASHSEED=2 uv run pytest tests/unit/scheduler/test_pnfl_model_fingerprint.py -q`
Expected: both PASS. If either fails, the model still depends on iteration order somewhere — find the `set`/`frozenset` iteration (grep `for .* in .*set` in both builders) and sort it before continuing.

- [ ] **Step 6: Run the fast suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/athc/scheduler/schedulers/fixed_cpsat_builder.py tests/unit/scheduler/test_pnfl_model_fingerprint.py
git commit -m "scheduler: pin the PNFL phase models with a fingerprint test; pin fixed pairs in sorted order"
```

---

### Task 2: Domain model — plain conferences/divisions, division-less teams, both league formats

Replace the enums with dataclasses, add `Team.same_division`, `League.conferences` / `has_divisions` / opponent helpers, `build_conference_league`, and load `[ConferenceStandings]`. Update every consumer so the PNFL behaves exactly as before (fingerprint unchanged).

**Files:**
- Modify: `src/athc/scheduler/domain/league.py` (rewrite)
- Modify: `src/athc/scheduler/domain/schedule.py` (drop season constants)
- Modify: `src/athc/scheduler/config.py` (`load_league`)
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_builder.py` (enum references only)
- Modify: `src/athc/scheduler/schedulers/schedule_builder.py` (enum references only)
- Modify: `src/athc/scheduler/writers/report.py` (docstring only), `src/athc/scheduler/writers/html_writer.py` (none — uses `ordered_teams`)
- Modify: `tests/integration/schedule_validation.py`, `tests/unit/scheduler/conftest.py`, `tests/unit/scheduler/test_config.py`, `tests/unit/scheduler/test_writers.py`, `tests/unit/scheduler/test_schedule_builder.py`, `tests/unit/scheduler/fixed_cpsat/test_fixed_cpsat_inventory.py`, `tests/unit/scheduler/fixed_cpsat/test_schedule_rules.py`, `tests/unit/scheduler/fixed_cpsat/test_schedule_structure.py`
- Modify: `research/scheduler/build_real_reports.py:24,95`, `research/scheduler/build_real_2048_report.py:19,260`
- Create: `tests/unit/scheduler/test_league.py`

**Interfaces:**
- Produces (`athc.scheduler.domain.league`):
  - `Conference(name: str)`, `Division(name: str, conference: Conference, expected_size: int)` — frozen dataclasses.
  - `AFC`, `NFC`, `AFC_EAST`, `AFC_WEST`, `NFC_EAST`, `NFC_WEST`, `PNFL_DIVISIONS: tuple[Division, ...]`, `PNFL_DIVISIONS_BY_NAME: dict[str, Division]`.
  - `Team(metro: str, conference: Conference, division: Division | None = None)`, `Team.same_division(other) -> bool`.
  - `RivalryPair = tuple[Team, Team]` (listed order; the first hosts in even seasons).
  - `ConferenceRankings(by_conference: Mapping[Conference, tuple[Team, ...]], overall: tuple[Team, ...])` with `ranked(conference)`, `rank_of(team)`, `overall_rank(team)`.
  - `League(teams, conferences, rankings, division_standings)` with `has_divisions`, `divisions`, `divisional_opponents(team)`, `conference_opponents(team)`, `same_conference_opponents(team)`, `structural_games(team)`, `nonconference_games(team, weeks)`, `max_divisional_games_per_week`.
  - `build_teams(divisions)`, `build_conference_teams(conferences)`, `build_league(division_standings, overall_ranking)`, `build_conference_league(conference_standings, overall_ranking)`, `ordered_teams(teams)`, `team_by_metro`, `lookup_team`.
- Produces (`athc.scheduler.domain.schedule`): `GAMES_PER_WEEK`, `Game`, `Schedule` only.
- Produces (`athc.scheduler.config`): `load_league(path)` handles both formats.

- [ ] **Step 1: Write the domain tests**

Create `tests/unit/scheduler/test_league.py`:

```python
"""League structure: both formats (divisions / conferences only)."""

from __future__ import annotations

import pytest

from athc.scheduler.domain.league import (
    AFC,
    AFC_EAST,
    AFC_WEST,
    NFC,
    NFC_EAST,
    NFC_WEST,
    Conference,
    Team,
    build_conference_league,
    build_league,
    ordered_teams,
)

from .conftest import LEAGUE_5_SLOTS, PCFL_EAST, PCFL_LEAGUE, PCFL_OVERALL, PCFL_WEST

EASTERN = Conference("EASTERN")
WESTERN = Conference("WESTERN")


def _pcfl(**overrides):
    standings = {"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}
    standings.update(overrides)
    return build_conference_league(standings, PCFL_OVERALL)


# --- Team ---------------------------------------------------------------------


def test_team_division_must_belong_to_its_conference() -> None:
    with pytest.raises(ValueError, match="AFC_EAST"):
        Team("Nowhere", NFC, AFC_EAST)


def test_same_division_is_false_for_division_less_teams() -> None:
    a = Team("A", WESTERN)
    b = Team("B", WESTERN)
    assert not a.same_division(b)


def test_same_division_compares_divisions() -> None:
    a = Team("A", AFC, AFC_EAST)
    b = Team("B", AFC, AFC_EAST)
    c = Team("C", AFC, AFC_WEST)
    assert a.same_division(b)
    assert not a.same_division(c)


# --- Conference-only league ---------------------------------------------------


def test_conference_league_has_no_divisions() -> None:
    assert not PCFL_LEAGUE.has_divisions
    assert PCFL_LEAGUE.divisions == ()
    assert PCFL_LEAGUE.division_standings == {}
    assert all(t.division is None for t in PCFL_LEAGUE.teams)


def test_conference_league_conferences_are_sorted_by_name() -> None:
    assert PCFL_LEAGUE.conferences == (EASTERN, WESTERN)


def test_conference_league_opponent_classes() -> None:
    team = next(t for t in PCFL_LEAGUE.teams if t.metro == "Michigan")
    assert PCFL_LEAGUE.divisional_opponents(team) == ()
    conference = PCFL_LEAGUE.conference_opponents(team)
    assert len(conference) == 8
    assert all(t.conference == WESTERN and t != team for t in conference)
    assert PCFL_LEAGUE.same_conference_opponents(team) == conference
    assert PCFL_LEAGUE.structural_games(team) == 8
    assert PCFL_LEAGUE.nonconference_games(team, 12) == 4
    assert PCFL_LEAGUE.max_divisional_games_per_week == 0


def test_conference_league_ranks_derive_from_overall_order() -> None:
    texas = next(t for t in PCFL_LEAGUE.teams if t.metro == "Texas")
    notre_dame = next(t for t in PCFL_LEAGUE.teams if t.metro == "Notre Dame")
    assert PCFL_LEAGUE.rankings.overall_rank(texas) == 1
    assert PCFL_LEAGUE.rankings.rank_of(texas) == 1
    assert PCFL_LEAGUE.rankings.overall_rank(notre_dame) == 3
    assert PCFL_LEAGUE.rankings.rank_of(notre_dame) == 1
    assert PCFL_LEAGUE.rankings.ranked(WESTERN)[0] == notre_dame


def test_conference_league_rejects_one_conference() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        build_conference_league({"WESTERN": PCFL_WEST}, PCFL_OVERALL)


def test_conference_league_rejects_three_conferences() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        _pcfl(EXTRA=("Nowhere",))


@pytest.mark.parametrize("size", [8, 10])
def test_conference_league_rejects_wrong_conference_size(size: int) -> None:
    west = PCFL_WEST[:8] if size == 8 else (*PCFL_WEST, "Nowhere")
    with pytest.raises(ValueError, match="exactly 9 teams"):
        _pcfl(WESTERN=west)


def test_conference_league_rejects_duplicate_team() -> None:
    with pytest.raises(ValueError, match="Duplicate team"):
        _pcfl(EASTERN=(*PCFL_EAST[:8], "Michigan"))


def test_conference_league_rejects_overall_missing_a_team() -> None:
    with pytest.raises(ValueError, match="all 18 teams"):
        build_conference_league(
            {"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}, PCFL_OVERALL[:-1]
        )


def test_conference_league_ordered_teams_by_conference_then_metro() -> None:
    order = [t.metro for t in ordered_teams(PCFL_LEAGUE.teams)]
    assert order == sorted(PCFL_EAST) + sorted(PCFL_WEST)
    assert list(PCFL_LEAGUE.teams) == ordered_teams(PCFL_LEAGUE.teams)


# --- Divisional league (PNFL) -------------------------------------------------


def test_divisional_league_structure() -> None:
    league = LEAGUE_5_SLOTS
    assert league.has_divisions
    assert league.conferences == (AFC, NFC)
    assert league.divisions == (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)
    assert league.max_divisional_games_per_week == 8
    four = next(t for t in league.teams if t.division == AFC_EAST)
    five = next(t for t in league.teams if t.division == AFC_WEST)
    assert len(league.divisional_opponents(four)) == 3
    assert len(league.conference_opponents(four)) == 5
    assert len(league.same_conference_opponents(four)) == 8
    assert league.structural_games(four) == 11
    assert league.nonconference_games(four, 16) == 5
    assert len(league.divisional_opponents(five)) == 4
    assert len(league.conference_opponents(five)) == 4
    assert league.structural_games(five) == 12
    assert league.nonconference_games(five, 16) == 4


def test_divisional_league_ordered_teams_by_division_then_metro() -> None:
    teams = ordered_teams(LEAGUE_5_SLOTS.teams)
    divisions = [t.division for t in teams]
    assert divisions == sorted(divisions, key=lambda d: d.name if d else "")
    assert list(LEAGUE_5_SLOTS.teams) == teams


def test_build_league_rejects_mixed_conference_keys() -> None:
    with pytest.raises(ValueError, match="Unknown division key"):
        build_league({"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}, PCFL_OVERALL)
```

- [ ] **Step 2: Add the PCFL constants to the shared conftest**

In `tests/unit/scheduler/conftest.py`, after the `_ALL_LEAGUES` block, add:

```python
# A league without divisions (the PCFL): two conferences of 9. Conference lists
# are the regular-season finish (record, then point differential); the overall
# order ranks playoff finish first.
PCFL_WEST = (
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
PCFL_EAST = (
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
PCFL_OVERALL = (
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
PCFL_LEAGUE = build_conference_league(
    {"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}, PCFL_OVERALL
)
```

and change the import line to `from athc.scheduler.domain.league import AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST, League, build_conference_league, build_league` and `_DIVISIONS` keys to `AFC_EAST.name`, `AFC_WEST.name`, `NFC_EAST.name`, `NFC_WEST.name`.

- [ ] **Step 3: Run the new tests to see them fail**

Run: `uv run pytest tests/unit/scheduler/test_league.py -q`
Expected: FAIL (ImportError: cannot import `AFC` ...).

- [ ] **Step 4: Rewrite `domain/league.py`**

```python
"""League structure: conferences, divisions, teams, and conference rankings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

TOTAL_TEAMS = 18
TEAMS_PER_CONFERENCE = 9
CONFERENCES_PER_LEAGUE = 2


@dataclass(frozen=True)
class Conference:
    name: str


@dataclass(frozen=True)
class Division:
    name: str
    conference: Conference
    expected_size: int


AFC = Conference("AFC")
NFC = Conference("NFC")
AFC_EAST = Division("AFC_EAST", AFC, 4)
AFC_WEST = Division("AFC_WEST", AFC, 5)
NFC_EAST = Division("NFC_EAST", NFC, 4)
NFC_WEST = Division("NFC_WEST", NFC, 5)

# The PNFL's divisions in canonical order, keyed by their [DivisionStandings] names.
PNFL_DIVISIONS: tuple[Division, ...] = (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)
PNFL_DIVISIONS_BY_NAME: dict[str, Division] = {d.name: d for d in PNFL_DIVISIONS}


@dataclass(frozen=True)
class Team:
    metro: str
    conference: Conference
    division: Division | None = None  # None in a league without divisions

    def __post_init__(self) -> None:
        if self.division is not None and self.division.conference != self.conference:
            raise ValueError(
                f"{self.metro}: division {self.division.name} is not in conference "
                f"{self.conference.name}"
            )

    def same_division(self, other: Team) -> bool:
        """Whether both teams share a division. Division-less teams never do --
        a bare `division == division` would call every such pair divisional."""
        return self.division is not None and self.division == other.division


# A rivalry as listed in the rules file: the first team hosts in even seasons.
RivalryPair = tuple[Team, Team]


@dataclass(frozen=True)
class ConferenceRankings:
    """The overall 1-18 standings (`overall`) plus the per-conference 1-9 ranks
    derived from it."""

    by_conference: Mapping[Conference, tuple[Team, ...]]
    overall: tuple[Team, ...]

    def ranked(self, conference: Conference) -> tuple[Team, ...]:
        return self.by_conference[conference]

    def rank_of(self, team: Team) -> int:
        """Return 1-based conference rank."""
        return self.by_conference[team.conference].index(team) + 1

    def overall_rank(self, team: Team) -> int:
        """Return 1-based overall rank (1-18)."""
        return self.overall.index(team) + 1


def _division_name(team: Team) -> str:
    return team.division.name if team.division is not None else ""


def ordered_teams(teams: Sequence[Team]) -> list[Team]:
    """Canonical order: conference name, division name, metro."""
    return sorted(teams, key=lambda t: (t.conference.name, _division_name(t), t.metro))


def build_teams(divisions: Mapping[str, Sequence[str]]) -> tuple[Team, ...]:
    """Build the PNFL teams tuple from division-keyed metro lists.

    Validates that all four divisions are present, that each has its expected
    size, and that no metro is duplicated. Teams are returned in canonical order
    (division, then metro); the input line order (a division's finish) is kept
    separately in `division_standings`.
    """
    by_division: dict[Division, Sequence[str]] = {}
    for key, metros in divisions.items():
        division = PNFL_DIVISIONS_BY_NAME.get(key)
        if division is None:
            valid = ", ".join(d.name for d in PNFL_DIVISIONS)
            raise ValueError(f"Unknown division key {key!r}; expected one of {valid}")
        by_division[division] = metros

    missing = [d.name for d in PNFL_DIVISIONS if d.name not in divisions]
    if missing:
        raise ValueError(f"Missing divisions: {missing}")

    teams: list[Team] = []
    seen_metros: set[str] = set()
    for division in PNFL_DIVISIONS:
        metros = tuple(sorted(m.strip() for m in by_division[division] if m.strip()))
        if len(metros) != division.expected_size:
            raise ValueError(
                f"{division.name} must list exactly {division.expected_size} teams; "
                f"got {len(metros)}"
            )
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in divisions config: {metro}")
            teams.append(Team(metro=metro, conference=division.conference, division=division))
            seen_metros.add(metro)

    expected_teams = sum(d.expected_size for d in PNFL_DIVISIONS)
    if len(teams) != expected_teams:
        raise ValueError(
            f"Expected exactly {expected_teams} teams across all divisions, got "
            f"{len(teams)}"
        )
    return tuple(teams)


def build_conference_teams(conferences: Mapping[str, Sequence[str]]) -> tuple[Team, ...]:
    """Build a division-less teams tuple from conference-keyed metro lists: exactly
    two conferences of nine, no metro twice. Canonical order: conference name,
    then metro."""
    if len(conferences) != CONFERENCES_PER_LEAGUE:
        raise ValueError(
            f"Expected exactly {CONFERENCES_PER_LEAGUE} conferences, got "
            f"{len(conferences)}: {sorted(conferences)}"
        )
    teams: list[Team] = []
    seen_metros: set[str] = set()
    for name in sorted(conferences):
        conference = Conference(name)
        metros = tuple(sorted(m.strip() for m in conferences[name] if m.strip()))
        if len(metros) != TEAMS_PER_CONFERENCE:
            raise ValueError(
                f"{name} must list exactly {TEAMS_PER_CONFERENCE} teams; got {len(metros)}"
            )
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in conferences config: {metro}")
            teams.append(Team(metro=metro, conference=conference))
            seen_metros.add(metro)
    return tuple(teams)


def team_by_metro(teams: Sequence[Team]) -> dict[str, Team]:
    return {team.metro: team for team in teams}


def lookup_team(teams: Sequence[Team], metro: str) -> Team:
    by_metro = team_by_metro(teams)
    if metro not in by_metro:
        raise ValueError(f"Unknown team: {metro!r}. Valid: {sorted(by_metro)}")
    return by_metro[metro]


@dataclass(frozen=True)
class League:
    """Teams in canonical order, the two conferences (sorted by name), the
    standings-derived rankings, and each division's previous-season finish
    order (empty for a league without divisions)."""

    teams: tuple[Team, ...]
    conferences: tuple[Conference, ...]
    rankings: ConferenceRankings
    division_standings: Mapping[Division, tuple[Team, ...]]

    @property
    def has_divisions(self) -> bool:
        return self.teams[0].division is not None

    @property
    def divisions(self) -> tuple[Division, ...]:
        return tuple(self.division_standings)

    @property
    def max_divisional_games_per_week(self) -> int:
        """Divisional games one week can hold (each odd division strands a team)."""
        return sum(d.expected_size // 2 for d in self.divisions)

    def divisional_opponents(self, team: Team) -> tuple[Team, ...]:
        return tuple(t for t in self.teams if t != team and team.same_division(t))

    def conference_opponents(self, team: Team) -> tuple[Team, ...]:
        """Same conference, outside the division (the whole conference when there
        are no divisions)."""
        return tuple(
            t
            for t in self.teams
            if t != team and t.conference == team.conference and not team.same_division(t)
        )

    def same_conference_opponents(self, team: Team) -> tuple[Team, ...]:
        return tuple(
            t for t in self.teams if t != team and t.conference == team.conference
        )

    def structural_games(self, team: Team) -> int:
        """Games fixed by structure: every divisional rival twice, the rest of
        the conference once."""
        return 2 * len(self.divisional_opponents(team)) + len(
            self.conference_opponents(team)
        )

    def nonconference_games(self, team: Team, weeks: int) -> int:
        return weeks - self.structural_games(team)


def build_league(
    division_standings: Mapping[str, Sequence[str]],  # "AFC_EAST" -> finish order
    overall_ranking: Sequence[str],  # all 18 metros, best to worst
) -> League:
    """Build a PNFL-style `League`: `[DivisionStandings]` defines membership and
    each division's finish order; `[OverallStandings]` gives the 1-18 order."""
    teams = build_teams(division_standings)
    by_division = {
        PNFL_DIVISIONS_BY_NAME[key]: tuple(lookup_team(teams, metro) for metro in metros)
        for key, metros in division_standings.items()
    }
    return _finish_league(teams, overall_ranking, by_division)


def build_conference_league(
    conference_standings: Mapping[str, Sequence[str]],  # "WESTERN" -> finish order
    overall_ranking: Sequence[str],
) -> League:
    """Build a division-less `League`: `[ConferenceStandings]` defines the two
    conferences; `[OverallStandings]` gives the 1-18 order."""
    teams = build_conference_teams(conference_standings)
    return _finish_league(teams, overall_ranking, {})


def _finish_league(
    teams: tuple[Team, ...],
    overall_ranking: Sequence[str],
    division_standings: Mapping[Division, tuple[Team, ...]],
) -> League:
    overall = tuple(lookup_team(teams, metro) for metro in overall_ranking)
    _validate_overall(overall, teams)
    conferences = tuple(sorted({t.conference for t in teams}, key=lambda c: c.name))
    by_conference = {
        conference: tuple(t for t in overall if t.conference == conference)
        for conference in conferences
    }
    return League(
        teams=teams,
        conferences=conferences,
        rankings=ConferenceRankings(by_conference=by_conference, overall=overall),
        division_standings=division_standings,
    )


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Overall standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"Overall standings have duplicate teams: {duplicates}")
```

- [ ] **Step 5: Trim `domain/schedule.py`**

Replace the constants block so the file keeps only:

```python
from athc.scheduler.domain.league import Team

GAMES_PER_WEEK = 9  # 18 teams, all playing every week
```

(delete `NUM_WEEKS`, `HOME_GAMES_PER_TEAM`, `WEEK_16_DIVISIONAL_GAMES`, `nonconference_games_for`, and the `Division` import). `Game` and `Schedule` stay.

- [ ] **Step 6: Load both standings formats in `config.py`**

Replace `load_league`:

```python
DIVISION_SECTION = "DivisionStandings"
CONFERENCE_SECTION = "ConferenceStandings"


def load_league(path: StrPath) -> League:
    """Read a league from `[OverallStandings]` (overall 1-18 `Order`) plus exactly
    one of `[DivisionStandings]` (per-division teams in finish order -- the PNFL)
    or `[ConferenceStandings]` (per-conference teams in finish order -- a league
    without divisions). Per-conference 1-9 ranks derive from the overall order.
    """
    resolved = Path(path)
    if not resolved.is_file():
        raise ConfigError(f"Config file not found: '{resolved}'.")
    cp = _read_config(resolved)
    has_divisions = cp.has_section(DIVISION_SECTION)
    has_conferences = cp.has_section(CONFERENCE_SECTION)
    if has_divisions == has_conferences:
        raise ConfigError(
            f"Config file '{resolved}' must have exactly one of the [{DIVISION_SECTION}] "
            f"and [{CONFERENCE_SECTION}] sections."
        )
    _require_section(cp, resolved, "OverallStandings")
    overall = _required_multiline(cp, resolved, "OverallStandings", "Order")
    section = DIVISION_SECTION if has_divisions else CONFERENCE_SECTION
    standings = {key: _parse_multiline(cp, section, key) for key in cp.options(section)}
    try:
        if has_divisions:
            return build_league(standings, overall_ranking=overall)
        return build_conference_league(standings, overall_ranking=overall)
    except ValueError as error:
        raise ConfigError(
            f"Config file '{resolved}' has invalid league data: {error}"
        ) from error
```

and the import: `from athc.scheduler.domain.league import League, build_conference_league, build_league`.

- [ ] **Step 7: Update the builders' enum references (behaviour unchanged)**

`fixed_cpsat_builder.py` — this task only swaps names; the full generic rewrite is Task 4:
- Import: `from athc.scheduler.domain.league import AFC, AFC_EAST, AFC_WEST, NFC, NFC_EAST, NFC_WEST, PNFL_DIVISIONS, TEAMS_PER_CONFERENCE, Conference, ConferenceRankings, Division, Team` and `from athc.scheduler.domain.schedule import GAMES_PER_WEEK`.
- `FIXED_NONCONF_PLACE_OPPONENTS`: replace every `Division.AFC_EAST` with `AFC_EAST` etc. (keys stay `Division` objects for now).
- `_validate_fixed_place_table`: `for division in Division` → `for division in PNFL_DIVISIONS`.
- Add module constant `NUM_WEEKS = 16` (temporary, removed in Task 4) and a local helper used wherever `nonconference_games_for(team.division)` was called:

```python
def _nonconference_games_for(team: Team) -> int:
    # 16 weeks minus the structural games: 4-team divisions play 5, 5-team play 4.
    return 5 if team.division is not None and team.division.expected_size == 4 else 4
```
- `Conference.AFC` → `AFC`, `Conference.NFC` → `NFC`; `rankings.afc` → `rankings.ranked(AFC)`, `rankings.nfc` → `rankings.ranked(NFC)`.
- `_add_divisional_matchups`: `team_i.division == team_j.division` → `team_i.same_division(team_j)`; `_add_conference_matchups`: `team_i.division != team_j.division` → `not team_i.same_division(team_j)`.

`schedule_builder.py` — names only (the gating is Task 5):
- Import `from athc.scheduler.domain.league import League, Team` (keep `Team`), drop the `domain.schedule` constants import and add module constants `NUM_WEEKS = 16`, `HOME_GAMES_PER_TEAM = 8`, `WEEK_16_DIVISIONAL_GAMES = 8` at the top (temporary, removed in Task 5).
- `opp.division == team.division and opp != team` → `opp != team and team.same_division(opp)`.
- `t.division.expected_size == 4` → `t.division is not None and t.division.expected_size == 4` (same for 5).
- pair classification: `if team_i.division == team_j.division:` → `if team_i.same_division(team_j):`.

`writers/report.py`: no code change (uses `ordered_teams`, `rank_of`, `overall_rank`).

- [ ] **Step 8: Update the validation helper and tests**

`tests/integration/schedule_validation.py`:
- Imports: `from athc.scheduler.domain.league import AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST, League, Team, team_by_metro` and `from athc.scheduler.domain.schedule import GAMES_PER_WEEK, Game, Schedule`.
- Module constants (this validator is PNFL-only):

```python
NUM_WEEKS = 16
HOME_GAMES_PER_TEAM = 8
WEEK_16_DIVISIONAL_GAMES = 8
FIVE_TEAM_DIVISIONS = (AFC_WEST, NFC_WEST)
FOUR_TEAM_DIVISIONS = (AFC_EAST, NFC_EAST)


def nonconference_games_for(team: Team) -> int:
    return 5 if team.division in FOUR_TEAM_DIVISIONS else 4
```

- `nonconference_games_for(team.division)` → `nonconference_games_for(team)` (`_validate_inventory`).
- Every `x.division == y.division` → `x.same_division(y)`; every `x.division != y.division` → `not x.same_division(y)` (lines 179, 204, 229, 285, 442, 472, 539, 553 and the `_validate_home_balance` comprehensions).

`tests/unit/scheduler/fixed_cpsat/test_schedule_rules.py` and `test_schedule_structure.py`: replace the `domain.schedule` constant imports with local `NUM_WEEKS = 16`, `WEEK_16_DIVISIONAL_GAMES = 8` (and `GAMES_PER_WEEK` still from `domain.schedule`); `from athc.scheduler.domain.league import AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST`; replace `Division.AFC_EAST` → `AFC_EAST` etc.

`tests/unit/scheduler/fixed_cpsat/test_fixed_cpsat_inventory.py`: import `AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST, PNFL_DIVISIONS, League, Team, build_league`; `Division.X` → `X`; `for division in Division` → `for division in PNFL_DIVISIONS`; `for ranked in (league.rankings.afc, league.rankings.nfc)` → `for conference in league.conferences:` with `ranked = league.rankings.ranked(conference)`.

`tests/unit/scheduler/test_config.py`: import `AFC_EAST, NFC_WEST, League`; `Division.AFC_EAST` → `AFC_EAST`, `Division.NFC_WEST` → `NFC_WEST`.

`tests/unit/scheduler/test_writers.py`: `from athc.scheduler.domain.league import AFC, AFC_EAST, Team`; `Team("Alpha", AFC, AFC_EAST)`, `Team("Beta", AFC, AFC_EAST)`.

`tests/unit/scheduler/test_schedule_builder.py`: `from athc.scheduler.domain.league import AFC, AFC_EAST, Team`; `Team(metro="Nowhere", conference=AFC, division=AFC_EAST)`.

`research/scheduler/build_real_reports.py` and `build_real_2048_report.py`: drop `nonconference_games_for` from the import and replace the call with `5 if team.division is not None and team.division.expected_size == 4 else 4`.

- [ ] **Step 9: Run the fast suite, lint, format, types**

Run: `uv run pytest`
Expected: PASS, including `test_pnfl_model_fingerprint.py` (unchanged hashes) and `test_league.py`.
Run: `uv run ruff check .` / `uv run ruff format .` / `uv run pyright` — all clean.

- [ ] **Step 10: Commit**

```bash
git add -A src tests research
git commit -m "scheduler: plain conference/division values; a league may have no divisions"
```

---

### Task 3: Config — `[league] weeks`, new `[phase2]` keys, `[rivalries]`, explicit path, league-resolved checks

**Files:**
- Modify: `src/athc/scheduler/config.py`
- Modify: `tests/unit/scheduler/test_config.py`
- Modify: `tests/unit/scheduler/test_pnfl_model_fingerprint.py` (use the path parameter)
- Modify: `tests/integration/data/PNFL.scheduler.toml` (explicit new keys — no model change)

**Interfaces:**
- Produces (`athc.scheduler.config`):
  - `DEFAULT_WEEKS = 16`, `LeagueConfig(weeks: int = 16)`, `RivalriesConfig(pairs: tuple[tuple[str, str], ...] = (), rotate_home_by_season: bool = True)`.
  - `Phase2Config` new fields: `max_consecutive_conference_home_or_away: int = 0`, `opening_nonconference_weeks: int = 0`, `require_home_balance_per_six_weeks: bool = True`, `require_home_away_streak_caps: bool = True`, `require_mixed_home_away_at_season_ends: bool = True`.
  - `SchedulerConfig(league, difficulty, solver, phase2, rivalries)`.
  - `load_scheduler_config(path: StrPath | None = None)`.
  - `check_weeks(league, weeks) -> None`, `check_opening_weeks(league, weeks, opening_weeks) -> None`, `resolve_rivalries(league, rivalries) -> tuple[RivalryPair, ...]` — all raise `ConfigError`.

- [ ] **Step 1: Write the config tests**

Append to `tests/unit/scheduler/test_config.py` (add `from athc.scheduler.config import LeagueConfig, Phase2Config, RivalriesConfig, SchedulerConfig, check_opening_weeks, check_weeks, resolve_rivalries` and `from .conftest import LEAGUE_5_SLOTS, PCFL_LEAGUE` to the imports):

```python
# ---------------------------------------------------------------------------
# [league] weeks
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_weeks(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[league]\nweeks = 12\n")
    assert load_scheduler_config().league.weeks == 12


def test_weeks_defaults_to_sixteen() -> None:
    assert SchedulerConfig().league.weeks == 16


@pytest.mark.parametrize("weeks", ["11", "0", "'12'"])
def test_load_scheduler_config_rejects_bad_weeks(config_dir: Path, weeks: str) -> None:
    _write_scheduler_toml(config_dir, f"[league]\nweeks = {weeks}\n")
    with pytest.raises(ConfigError, match="weeks"):
        load_scheduler_config()


def test_load_scheduler_config_rejects_unknown_league_key(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[league]\nteams = 18\n")
    with pytest.raises(ConfigError, match="unknown \\[league\\] key"):
        load_scheduler_config()


def test_load_scheduler_config_from_explicit_path(tmp_path: Path) -> None:
    path = _write(tmp_path / "other.toml", "[league]\nweeks = 12\n")
    assert load_scheduler_config(path).league.weeks == 12


def test_load_scheduler_config_explicit_path_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_scheduler_config(tmp_path / "missing.toml")


# ---------------------------------------------------------------------------
# [phase2] new keys
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_new_phase2_keys(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [phase2]
        max_consecutive_conference_home_or_away = 2
        opening_nonconference_weeks = 3
        require_home_balance_per_six_weeks = false
        require_home_away_streak_caps = false
        require_mixed_home_away_at_season_ends = false
        """,
    )
    phase2 = load_scheduler_config().phase2
    assert phase2.max_consecutive_conference_home_or_away == 2
    assert phase2.opening_nonconference_weeks == 3
    assert phase2.require_home_balance_per_six_weeks is False
    assert phase2.require_home_away_streak_caps is False
    assert phase2.require_mixed_home_away_at_season_ends is False


def test_new_phase2_keys_default_to_pnfl_behaviour() -> None:
    phase2 = Phase2Config()
    assert phase2.max_consecutive_conference_home_or_away == 0
    assert phase2.opening_nonconference_weeks == 0
    assert phase2.require_home_balance_per_six_weeks is True
    assert phase2.require_home_away_streak_caps is True
    assert phase2.require_mixed_home_away_at_season_ends is True


@pytest.mark.parametrize(
    "key", ["max_consecutive_conference_home_or_away", "opening_nonconference_weeks"]
)
def test_zero_is_off_and_negative_is_rejected(config_dir: Path, key: str) -> None:
    _write_scheduler_toml(config_dir, f"[phase2]\n{key} = 0\n")
    assert getattr(load_scheduler_config().phase2, key) == 0
    _write_scheduler_toml(config_dir, f"[phase2]\n{key} = -1\n")
    with pytest.raises(ConfigError, match=key):
        load_scheduler_config()


# ---------------------------------------------------------------------------
# [rivalries]
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_rivalries(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [rivalries]
        rotate_home_by_season = false
        pairs = [[" Michigan ", "Ohio State"], ["USC", "UCLA"]]
        """,
    )
    rivalries = load_scheduler_config().rivalries
    assert rivalries.pairs == (("Michigan", "Ohio State"), ("USC", "UCLA"))
    assert rivalries.rotate_home_by_season is False


def test_rivalries_default_to_none() -> None:
    assert SchedulerConfig().rivalries == RivalriesConfig()
    assert RivalriesConfig().rotate_home_by_season is True


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("[rivalries]\nrotate_home_by_season = true\n", id="no-pairs"),
        pytest.param("[rivalries]\npairs = []\n", id="empty"),
        pytest.param('[rivalries]\npairs = [["A"]]\n', id="one-name"),
        pytest.param('[rivalries]\npairs = [["A", "B", "C"]]\n', id="three-names"),
        pytest.param('[rivalries]\npairs = [["A", "A"]]\n', id="same-team"),
        pytest.param('[rivalries]\npairs = [["A", " "]]\n', id="blank-name"),
        pytest.param("[rivalries]\npairs = [[1, 2]]\n", id="non-string"),
        pytest.param('[rivalries]\npairs = "A, B"\n', id="not-a-list"),
        pytest.param('[rivalries]\npairs = [["A", "B"]]\nweek = 12\n', id="unknown-key"),
    ],
)
def test_load_scheduler_config_rejects_bad_rivalries(config_dir: Path, body: str) -> None:
    _write_scheduler_toml(config_dir, body)
    with pytest.raises(ConfigError, match="rivalries"):
        load_scheduler_config()


# ---------------------------------------------------------------------------
# League-resolved checks
# ---------------------------------------------------------------------------

PCFL_RIVALRIES = (
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


@pytest.mark.parametrize("weeks", [10, 16])
def test_check_weeks_accepts_pcfl_range(weeks: int) -> None:
    check_weeks(PCFL_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [8, 18, 11])
def test_check_weeks_rejects_outside_pcfl_range(weeks: int) -> None:
    with pytest.raises(ConfigError, match="weeks"):
        check_weeks(PCFL_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [14, 20])
def test_check_weeks_accepts_pnfl_range(weeks: int) -> None:
    check_weeks(LEAGUE_5_SLOTS, weeks)


@pytest.mark.parametrize("weeks", [12, 22])
def test_check_weeks_rejects_outside_pnfl_range(weeks: int) -> None:
    with pytest.raises(ConfigError, match="weeks"):
        check_weeks(LEAGUE_5_SLOTS, weeks)


@pytest.mark.parametrize("opening", [0, 3])
def test_check_opening_weeks_accepts(opening: int) -> None:
    check_opening_weeks(PCFL_LEAGUE, 12, opening)


def test_check_opening_weeks_rejects_four_for_the_pcfl() -> None:
    with pytest.raises(ConfigError, match="opening_nonconference_weeks"):
        check_opening_weeks(PCFL_LEAGUE, 12, 4)


def test_resolve_rivalries_returns_team_pairs_in_listed_order() -> None:
    pairs = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))
    assert [(a.metro, b.metro) for a, b in pairs] == list(PCFL_RIVALRIES)
    assert sum(1 for a, b in pairs if a.conference != b.conference) == 1


def test_resolve_rivalries_with_no_pairs_is_empty() -> None:
    assert resolve_rivalries(PCFL_LEAGUE, RivalriesConfig()) == ()


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        pytest.param(PCFL_RIVALRIES[:8], "9 pairs", id="eight-pairs"),
        pytest.param((*PCFL_RIVALRIES, ("Michigan", "USC")), "9 pairs", id="ten-pairs"),
        pytest.param(
            (*PCFL_RIVALRIES[:8], ("Penn State", "Michigan")), "once", id="team-twice"
        ),
        pytest.param(
            (*PCFL_RIVALRIES[:8], ("Penn State", "Nowhere")), "Unknown team", id="unknown"
        ),
        pytest.param(
            (
                ("Michigan", "Texas"),
                ("USC", "Tennessee"),
                ("Washington", "Boston College"),
                ("Notre Dame", "Colorado"),
                ("Oklahoma", "Ohio State"),
                ("UCLA", "Oregon"),
                ("LSU", "Arkansas"),
                ("Georgia", "Clemson"),
                ("Miami", "Penn State"),
            ),
            "cross-conference",
            id="three-cross",
        ),
    ],
)
def test_resolve_rivalries_rejects(pairs, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=pairs))
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/scheduler/test_config.py -q`
Expected: FAIL (ImportError on `LeagueConfig`).

- [ ] **Step 3: Implement the config changes**

In `config.py`:

```python
DEFAULT_WEEKS = 16  # regular-season weeks (the PNFL)


@dataclass(frozen=True)
class LeagueConfig:
    """League shape the standings file does not carry."""

    weeks: int = DEFAULT_WEEKS


@dataclass(frozen=True)
class RivalriesConfig:
    """Final-week rivalry pairs, as listed (first hosts in even seasons)."""

    pairs: tuple[tuple[str, str], ...] = ()
    rotate_home_by_season: bool = True
```

Add to `Phase2Config` after `max_three_game_home_away_streaks`:

```python
    # Conference-sequence streak cap (0 = off): along a team's conference games,
    # ignoring non-conference games between them.
    max_consecutive_conference_home_or_away: int = 0
    # Weeks 1..N hold no same-conference game (0 = off).
    opening_nonconference_weeks: int = 0
    # NFL-pattern home/away rules; a league without them turns these off.
    require_home_balance_per_six_weeks: bool = True
    require_home_away_streak_caps: bool = True
    require_mixed_home_away_at_season_ends: bool = True
```

`SchedulerConfig`:

```python
@dataclass(frozen=True)
class SchedulerConfig:
    league: LeagueConfig = field(default_factory=LeagueConfig)
    difficulty: DifficultyConfig = field(default_factory=DifficultyConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    phase2: Phase2Config = field(default_factory=Phase2Config)
    rivalries: RivalriesConfig = field(default_factory=RivalriesConfig)
```

`load_scheduler_config`:

```python
def load_scheduler_config(path: StrPath | None = None) -> SchedulerConfig:
    """Read scheduler tunables from `rules/PNFL.scheduler.toml` (or `path`),
    defaulting when the default file or any key is absent. An explicit `path`
    must exist. Invalid TOML or a bad value errors."""
    if path is None:
        resolved = scheduler_rules_path()
        if not resolved.is_file():
            return SchedulerConfig()
    else:
        resolved = Path(path)
        if not resolved.is_file():
            raise ConfigError(f"Config file not found: '{resolved}'.")
    try:
        data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(
            f"Config file '{resolved}' is not valid TOML: {error}"
        ) from error
    difficulty = data.get("difficulty", {})
    solver = data.get("solver", {})
    return SchedulerConfig(
        league=_league(data.get("league", {}), resolved),
        difficulty=DifficultyConfig(
            spread=_number(difficulty, "spread", DEFAULT_DIFFICULTY_SPREAD, resolved),
        ),
        solver=SolverConfig(
            time_limit=_number(solver, "time_limit", DEFAULT_TIME_LIMIT, resolved),
            phase1_time_limit=_number(
                solver, "phase1_time_limit", DEFAULT_PHASE1_TIME_LIMIT, resolved
            ),
            solver_workers=_int(
                solver, "solver_workers", DEFAULT_SOLVER_WORKERS, resolved
            ),
        ),
        phase2=_phase2(data.get("phase2", {}), resolved),
        rivalries=_rivalries(data.get("rivalries"), resolved),
    )
```

Parsers (keep `_number`, `_bool`, `_int` as they are; add):

```python
_NON_NEGATIVE_PHASE2_KEYS = frozenset(
    {"max_consecutive_conference_home_or_away", "opening_nonconference_weeks"}
)


def _reject_unknown(table: Mapping[str, Any], known: set[str], name: str, path: Path) -> None:
    unknown = sorted(set(table) - known)
    if unknown:
        raise ConfigError(
            f"Config file '{path}': unknown [{name}] key(s): {', '.join(unknown)}."
        )


def _league(table: Mapping[str, Any], path: Path) -> LeagueConfig:
    _reject_unknown(table, {"weeks"}, "league", path)
    weeks = _int(table, "weeks", DEFAULT_WEEKS, path)
    if weeks <= 0 or weeks % 2:
        raise ConfigError(f"Config file '{path}': 'weeks' must be a positive even integer.")
    return LeagueConfig(weeks=weeks)


def _rivalries(table: Mapping[str, Any] | None, path: Path) -> RivalriesConfig:
    if table is None:
        return RivalriesConfig()
    _reject_unknown(table, {"pairs", "rotate_home_by_season"}, "rivalries", path)
    raw = table.get("pairs")
    if not isinstance(raw, list) or not raw:
        raise ConfigError(
            f"Config file '{path}': [rivalries] needs a non-empty 'pairs' list."
        )
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or not all(isinstance(name, str) and name.strip() for name in entry)
        ):
            raise ConfigError(
                f"Config file '{path}': each [rivalries] pair is two team names; "
                f"got {entry!r}."
            )
        first, second = (name.strip() for name in entry)
        if first == second:
            raise ConfigError(
                f"Config file '{path}': [rivalries] pair names the same team twice: "
                f"{first!r}."
            )
        pairs.append((first, second))
    return RivalriesConfig(
        pairs=tuple(pairs),
        rotate_home_by_season=_bool(table, "rotate_home_by_season", True, path),
    )
```

In `_phase2`, after `values[f.name] = parse(...)` add:

```python
        if f.name in _NON_NEGATIVE_PHASE2_KEYS and values[f.name] < 0:
            raise ConfigError(
                f"Config file '{path}': '{f.name}' must be 0 (off) or positive."
            )
```

League-resolved checks (append to `config.py`; import `RivalryPair, Team, TEAMS_PER_CONFERENCE, lookup_team` from the domain):

```python
# --- Checks that need both the rules and the league --------------------------

MAX_NONCONFERENCE_GAMES = TEAMS_PER_CONFERENCE  # each other-conference team once


def check_weeks(league: League, weeks: int) -> None:
    """`weeks` must be even and fit every team: more than its structural games,
    at most those plus one game against each other-conference team."""
    if weeks <= 0 or weeks % 2:
        raise ConfigError(f"weeks must be a positive even integer; got {weeks}.")
    for team in league.teams:
        structural = league.structural_games(team)
        if not structural < weeks <= structural + MAX_NONCONFERENCE_GAMES:
            raise ConfigError(
                f"weeks = {weeks} does not fit {team.metro}: it plays {structural} "
                f"structural games, so weeks must be {structural + 1}.."
                f"{structural + MAX_NONCONFERENCE_GAMES}."
            )


def check_opening_weeks(league: League, weeks: int, opening_weeks: int) -> None:
    """The weeks after the opening non-conference weeks must hold every
    same-conference game (a 9-team conference fits at most 4 a week)."""
    if opening_weeks == 0:
        return
    same_conference = sum(league.structural_games(t) for t in league.teams) // 2
    per_week = sum(TEAMS_PER_CONFERENCE // 2 for _ in league.conferences)
    if (weeks - opening_weeks) * per_week < same_conference:
        raise ConfigError(
            f"opening_nonconference_weeks = {opening_weeks} leaves "
            f"{weeks - opening_weeks} weeks for {same_conference} same-conference "
            f"games, but a week holds at most {per_week}."
        )


def resolve_rivalries(league: League, rivalries: RivalriesConfig) -> tuple[RivalryPair, ...]:
    """Turn the listed name pairs into teams, in listed order: every team once,
    exactly one cross-conference pair (each conference strands one team)."""
    if not rivalries.pairs:
        return ()
    expected = len(league.teams) // 2
    if len(rivalries.pairs) != expected:
        raise ConfigError(
            f"[rivalries] must list {expected} pairs; got {len(rivalries.pairs)}."
        )
    pairs: list[RivalryPair] = []
    seen: list[Team] = []
    for first, second in rivalries.pairs:
        try:
            teams = (lookup_team(league.teams, first), lookup_team(league.teams, second))
        except ValueError as error:
            raise ConfigError(f"[rivalries]: {error}") from error
        for team in teams:
            if team in seen:
                raise ConfigError(
                    f"[rivalries] must name every team once; {team.metro} repeats."
                )
            seen.append(team)
        pairs.append(teams)
    cross = sum(1 for a, b in pairs if a.conference != b.conference)
    if cross != 1:
        raise ConfigError(
            f"[rivalries] must have exactly one cross-conference pair; got {cross}."
        )
    return tuple(pairs)
```

- [ ] **Step 4: Point the fingerprint test at the path parameter**

In `test_pnfl_model_fingerprint.py` delete `_golden_config` and the `shutil` import; replace `config = _golden_config(config_dir)` with `config = load_scheduler_config(GOLDEN_RULES)` and drop the `config_dir` parameter.

- [ ] **Step 5: Make the golden rules file explicit about the new keys**

In `tests/integration/data/PNFL.scheduler.toml`, insert after the `schema_version = 1` line:

```toml
[league]
weeks = 16
```

and add to the end of the `[phase2]` table:

```toml
max_consecutive_conference_home_or_away = 0  # off: no conference-sequence streak cap
opening_nonconference_weeks = 0              # off: no all-non-conference opening weeks
require_home_balance_per_six_weeks = true
require_home_away_streak_caps = true
require_mixed_home_away_at_season_ends = true
```

(These equal the defaults; the file's contract is that nothing rides on defaults.)

- [ ] **Step 6: Run the tests, lint, format, types**

Run: `uv run pytest` — PASS (fingerprint hashes unchanged).
Run: `uv run ruff check .` / `uv run ruff format .` / `uv run pyright` — clean.

- [ ] **Step 7: Update the config test matrix**

In `tests/unit/scheduler/test-matrix-config-loading.md` add these rows (under the tunables table, a new `[league]` / `[rivalries]` / league-resolved table, and the league table):

```markdown
| `[league] weeks` | parsed; default 16; odd/zero/non-int/unknown key error | `test_load_scheduler_config_reads_weeks`, `test_weeks_defaults_to_sixteen`, `test_load_scheduler_config_rejects_bad_weeks`, `test_load_scheduler_config_rejects_unknown_league_key` | ☑ |
| Explicit path | reads it; missing errors | `test_load_scheduler_config_from_explicit_path`, `test_load_scheduler_config_explicit_path_must_exist` | ☑ |
| New `[phase2]` keys | parsed; PNFL defaults; 0 off, -1 error | `test_load_scheduler_config_reads_new_phase2_keys`, `test_new_phase2_keys_default_to_pnfl_behaviour`, `test_zero_is_off_and_negative_is_rejected` | ☑ |
| `[rivalries]` | pairs + toggle parsed, names stripped; bad shapes error | `test_load_scheduler_config_reads_rivalries`, `test_rivalries_default_to_none`, `test_load_scheduler_config_rejects_bad_rivalries` | ☑ |
| `check_weeks` | PCFL 10/16 ok, 8/18/11 error; PNFL 14/20 ok, 12/22 error | `test_check_weeks_*` | ☑ |
| `check_opening_weeks` | 0/3 ok, 4 error | `test_check_opening_weeks_*` | ☑ |
| `resolve_rivalries` | listed order; 8/10 pairs, repeat, unknown, 3 cross error | `test_resolve_rivalries_*` | ☑ |
| `[ConferenceStandings]` | loads a division-less league | `test_load_league_reads_conference_standings` (Task 4) | ☑ |
| Both / neither section | `ConfigError` naming both | `test_load_league_errors_with_both_sections`, `test_load_league_errors_when_division_standings_section_missing` (Task 4) | ☑ |
```

- [ ] **Step 8: Commit**

```bash
git add src/athc/scheduler/config.py tests/unit/scheduler/test_config.py tests/unit/scheduler/test_pnfl_model_fingerprint.py tests/integration/data/PNFL.scheduler.toml tests/unit/scheduler/test-matrix-config-loading.md
git commit -m "scheduler: rules file gains [league] weeks, [rivalries] and the PCFL phase-2 keys"
```

---

### Task 4: Standings loading tests for `[ConferenceStandings]` and the PCFL data files

**Files:**
- Create: `dev/leagues/PCFL/standings/2029.league.ini`
- Create: `dev/leagues/PCFL/rules/scheduler.toml`
- Modify: `tests/unit/scheduler/test_config.py`

- [ ] **Step 1: Write the tests**

Append to `tests/unit/scheduler/test_config.py`:

```python
# ---------------------------------------------------------------------------
# load_league — [ConferenceStandings] (a league without divisions)
# ---------------------------------------------------------------------------

DEV_PCFL = Path(__file__).resolve().parents[3] / "dev" / "leagues" / "PCFL"

CONFERENCE_STANDINGS = """\
[ConferenceStandings]
WESTERN =
    Ohio State
    Notre Dame
    UCLA
    Washington
    Oklahoma
    USC
    Colorado
    Oregon
    Michigan
EASTERN =
    Texas
    Tennessee
    Boston College
    Arkansas
    LSU
    Clemson
    Georgia
    Penn State
    Miami
"""

PCFL_OVERALL_STANDINGS = """\
[OverallStandings]
Order =
    Texas
    Tennessee
    Notre Dame
    Arkansas
    Ohio State
    Boston College
    LSU
    UCLA
    Washington
    Clemson
    Oklahoma
    Georgia
    Penn State
    USC
    Colorado
    Miami
    Oregon
    Michigan
"""


def test_load_league_reads_conference_standings(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", CONFERENCE_STANDINGS + "\n" + PCFL_OVERALL_STANDINGS)
    league = load_league(ini)
    assert league == PCFL_LEAGUE
    assert not league.has_divisions


def test_load_league_errors_with_both_sections(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", VALID_LEAGUE + "\n" + CONFERENCE_STANDINGS)
    with pytest.raises(ConfigError, match="DivisionStandings.*ConferenceStandings"):
        load_league(ini)


def test_load_league_errors_on_wrong_conference_size(tmp_path: Path) -> None:
    text = CONFERENCE_STANDINGS.replace("    Michigan\n", "") + PCFL_OVERALL_STANDINGS
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError, match="exactly 9 teams"):
        load_league(ini)


def test_dev_pcfl_league_file_loads() -> None:
    league = load_league(DEV_PCFL / "standings" / "2029.league.ini")
    assert league == PCFL_LEAGUE


def test_dev_pcfl_rules_file_loads() -> None:
    config = load_scheduler_config(DEV_PCFL / "rules" / "scheduler.toml")
    assert config.league.weeks == 12
    assert config.difficulty.spread == 0.0
    assert config.phase2.max_consecutive_home_or_away == 3
    assert config.phase2.max_consecutive_conference_home_or_away == 2
    assert config.phase2.opening_nonconference_weeks == 3
    assert config.phase2.require_home_balance_per_six_weeks is False
    assert config.phase2.require_home_away_streak_caps is False
    assert config.phase2.require_mixed_home_away_at_season_ends is False
    assert config.rivalries.rotate_home_by_season is True
    assert config.rivalries.pairs == PCFL_RIVALRIES
    check_weeks(PCFL_LEAGUE, config.league.weeks)
    check_opening_weeks(PCFL_LEAGUE, config.league.weeks, config.phase2.opening_nonconference_weeks)
    assert len(resolve_rivalries(PCFL_LEAGUE, config.rivalries)) == 9
```

Also update `test_load_league_errors_when_division_standings_section_missing` to match both names: `match="DivisionStandings.*ConferenceStandings"` stays compatible with the existing `match="DivisionStandings"` (leave it).

- [ ] **Step 2: Run them to see the data-file tests fail**

Run: `uv run pytest tests/unit/scheduler/test_config.py -q -k "conference or dev_pcfl"`
Expected: the two `dev_pcfl` tests FAIL (file not found); the others PASS.

- [ ] **Step 3: Write `dev/leagues/PCFL/standings/2029.league.ini`**

```ini
# League structure for the 2029 schedule: conference membership and the previous
# season's (2028) final overall standings. Each new season needs its own
# <season>.league.ini.


[OverallStandings]
# Previous season's final overall standings: all 18 teams, one per line, ranked
# 1st through 18th by line order (first line = best finish). Playoff finish
# first (champion, runner-up, semifinalists, wild-card losers), then record,
# then point differential. Per-conference 1-9 ranks derive from this order.
Order =
    Texas
    Tennessee
    Notre Dame
    Arkansas
    Ohio State
    Boston College
    LSU
    UCLA
    Washington
    Clemson
    Oklahoma
    Georgia
    Penn State
    USC
    Colorado
    Miami
    Oregon
    Michigan


[ConferenceStandings]
# Previous season's REGULAR-SEASON conference finish (excludes playoffs; record,
# then point differential), best finish first. This section defines each
# conference's teams; line order = finish.
WESTERN =
    Ohio State
    Notre Dame
    UCLA
    Washington
    Oklahoma
    USC
    Colorado
    Oregon
    Michigan
EASTERN =
    Texas
    Tennessee
    Boston College
    Arkansas
    LSU
    Clemson
    Georgia
    Penn State
    Miami
```

- [ ] **Step 4: Write `dev/leagues/PCFL/rules/scheduler.toml`**

```toml
# Scheduler tuning for `athc generate-schedule` (PCFL). Installed to the league's
# rules\ folder but not advertised; the commissioner edits it. A missing file or
# key falls back to the built-in default, which is the PNFL's, so every rule the
# PCFL does differently is set here.

schema_version = 1

[league]
weeks = 12               # regular-season weeks (even): 8 conference + 4 non-conference games

[difficulty]
# Nothing is fixed by standings (no divisions): the solver picks every
# non-conference game, tilting each team's average opponent conference rank
# (1-9) by spread. 0.0 = flat: every team's opponents average near rank 5.
# 2.5 = max: #1's opponents average near 3.0. Linear between.
spread = 0.0

[solver]
time_limit = 300.0       # max deterministic time for the week-placement (phase-2) solve
phase1_time_limit = 60.0 # max seconds for the matchup (phase-1) solve
solver_workers = 8       # keep fixed everywhere: the schedule changes with the worker count

[phase2]
# Fixed policy rules (always enforced, no setting):
# - Every conference team once: 4 home / 4 away.
# - Non-conference: 2 home / 2 away.
# - A 9-team conference cannot pair up, so each week after the opening weeks
#   holds one cross-conference game between the two idle teams (each team's
#   fourth non-conference game).

max_consecutive_home_or_away = 3
max_consecutive_conference_home_or_away = 2  # along the sequence of conference games
opening_nonconference_weeks = 3              # weeks 1-3 are all non-conference

# PNFL home/away pattern rules, off for the PCFL
require_home_balance_per_six_weeks = false
require_home_away_streak_caps = false
require_mixed_home_away_at_season_ends = false

[rivalries]
# The final week is rivalry week: every team plays its rival. Eight pairs are
# within a conference; one crosses (each conference's leftover team).
rotate_home_by_season = true   # first-listed hosts in even seasons, second in odd
pairs = [
    ["Michigan", "Ohio State"],
    ["USC", "UCLA"],
    ["Washington", "Oregon"],
    ["Notre Dame", "Colorado"],
    ["Oklahoma", "Texas"],
    ["LSU", "Arkansas"],
    ["Georgia", "Tennessee"],
    ["Clemson", "Miami"],
    ["Penn State", "Boston College"],
]
```

- [ ] **Step 5: Run the suite, lint, format, types**

Run: `uv run pytest` — PASS. Run ruff check / ruff format / pyright — clean.

- [ ] **Step 6: Commit**

```bash
git add dev/leagues/PCFL tests/unit/scheduler/test_config.py
git commit -m "scheduler: PCFL 2029 standings and rules files; [ConferenceStandings] loading tests"
```

---

### Task 5: Phase 1 — structure-driven matchup builder

**Files:**
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_builder.py` (rewrite)
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_scheduler.py` (constructor call only — full wiring in Task 7)
- Modify: `tests/unit/scheduler/fixed_cpsat/test_fixed_cpsat_inventory.py`, `tests/unit/scheduler/test_report.py`, `tests/unit/scheduler/test_pnfl_model_fingerprint.py`
- Create: `tests/unit/scheduler/conference_league/__init__.py`, `tests/unit/scheduler/conference_league/test_inventory.py`

**Interfaces:**
- Produces: `FixedCpsatMatchupBuilder(league: League, *, weeks: int = DEFAULT_WEEKS, rivalries: Sequence[RivalryPair] = (), spread: float = DEFAULT_DIFFICULTY_SPREAD, phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT, seed: int = 0)` with `build_matchup_plan() -> MatchupPlan`, `_fixed_place_pairs() -> set[Matchup]`, `_rivalry_pairs() -> set[Matchup]`, `_nonconference_model(fixed_pairs) -> _FixedCpsatNonConferenceModel`.
- `FIXED_NONCONF_PLACE_OPPONENTS: dict[tuple[str, int], tuple[tuple[str, int], ...]]` (division names); `_validate_fixed_place_table(divisions: Sequence[Division])`.

- [ ] **Step 1: Write the PCFL inventory tests**

Create `tests/unit/scheduler/conference_league/__init__.py` (empty) and `tests/unit/scheduler/conference_league/test_inventory.py`:

```python
"""Phase-1 inventory for a league without divisions (the PCFL)."""

from __future__ import annotations

from collections import Counter

import pytest

from athc.scheduler.config import RivalriesConfig, resolve_rivalries
from athc.scheduler.schedulers.fixed_cpsat_builder import (
    FixedCpsatMatchupBuilder,
    difficulty_target,
)
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))


def _plan(spread: float = 0.0, weeks: int = 12) -> MatchupPlan:
    return FixedCpsatMatchupBuilder(
        PCFL_LEAGUE, weeks=weeks, rivalries=RIVALRIES, spread=spread
    ).build_matchup_plan()


@pytest.fixture(scope="module")
def plan() -> MatchupPlan:
    return _plan()


def _nonconference(team, matchups):
    return [
        (j if i == team else i)
        for i, j in matchups
        if team in (i, j) and i.conference != j.conference
    ]


def test_inventory_totals(plan) -> None:
    assert len(plan.matchups) == 12 * 9
    counts = Counter(t for pair in plan.matchups for t in pair)
    assert all(counts[t] == 12 for t in PCFL_LEAGUE.teams)


def test_every_conference_pair_once_and_no_divisional_repeats(plan) -> None:
    pair_counts = Counter(plan.matchups)
    for i, a in enumerate(PCFL_LEAGUE.teams):
        for b in PCFL_LEAGUE.teams[i + 1 :]:
            expected = 1 if a.conference == b.conference else None
            if expected is not None:
                assert pair_counts[make_matchup(a, b)] == 1, (a.metro, b.metro)
            else:
                assert pair_counts[make_matchup(a, b)] <= 1, (a.metro, b.metro)


def test_every_team_has_four_distinct_nonconference_opponents(plan) -> None:
    for team in PCFL_LEAGUE.teams:
        opponents = _nonconference(team, plan.matchups)
        assert len(opponents) == 4 and len(set(opponents)) == 4, team.metro


def test_cross_conference_rivalry_is_fixed(plan) -> None:
    oklahoma_texas = {make_matchup(a, b) for a, b in RIVALRIES if a.conference != b.conference}
    assert len(oklahoma_texas) == 1
    assert plan.fixed_nonconference_pairs == frozenset(oklahoma_texas)
    assert oklahoma_texas <= set(plan.matchups)


def test_each_team_draws_a_top_and_bottom_half_opponent(plan) -> None:
    for team in PCFL_LEAGUE.teams:
        ranks = [PCFL_LEAGUE.rankings.rank_of(o) for o in _nonconference(team, plan.matchups)]
        assert any(r <= 5 for r in ranks) and any(r >= 5 for r in ranks), team.metro


@pytest.mark.parametrize("spread", [0.0, 2.5])
def test_difficulty_is_near_line_target(spread: float) -> None:
    plan = _plan(spread=spread)
    for team in PCFL_LEAGUE.teams:
        ranks = [PCFL_LEAGUE.rankings.rank_of(o) for o in _nonconference(team, plan.matchups)]
        target = difficulty_target(PCFL_LEAGUE.rankings.rank_of(team), spread)
        assert abs(sum(ranks) / 4 - target) <= 1.0, team.metro


def test_inventory_is_deterministic() -> None:
    assert Counter(_plan().matchups) == Counter(_plan().matchups)


def test_ten_week_season_gives_two_nonconference_games() -> None:
    plan = _plan(weeks=10)
    assert len(plan.matchups) == 90
    for team in PCFL_LEAGUE.teams:
        assert len(_nonconference(team, plan.matchups)) == 2, team.metro
```

Add `PCFL_RIVALRIES` to `tests/unit/scheduler/conftest.py` (after `PCFL_LEAGUE`), and make `test_config.py` import it from there instead of defining its own:

```python
PCFL_RIVALRIES = (
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/scheduler/conference_league -q`
Expected: FAIL (`FixedCpsatMatchupBuilder.__init__` got an unexpected argument).

- [ ] **Step 3: Rewrite `fixed_cpsat_builder.py`**

```python
"""Phase-1 matchup builder for the scheduler (fixed-place + CP-SAT).

Structure fixes the same-conference games: every divisional rival twice (a
league with divisions) and every other conference team once. The rest of each
team's `weeks` are non-conference games. Some are fixed -- the PNFL's same-place
division pairs (5th places play each other) and any cross-conference rivalry --
and one CP-SAT solve picks the remainder, tilting each team's average opponent
conference rank (1-9, whole slate) by `spread`: best team hardest, worst
easiest, linear between.

Self-contained on purpose: owns its table and difficulty line.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_DIFFICULTY_SPREAD,
    DEFAULT_PHASE1_TIME_LIMIT,
    DEFAULT_WEEKS,
)
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    Division,
    League,
    RivalryPair,
    Team,
)
from athc.scheduler.domain.schedule import GAMES_PER_WEEK
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.types import Matchup, MatchupPlan, make_matchup

# Fixed non-conference games per (division name, place) slot (symmetric): places
# 1-4 play both same-place finishers; the 5th places play each other. The PNFL
# only -- a league with other divisions has no table and errors.
_PlaceSlot = tuple[str, int]
FIXED_NONCONF_PLACE_OPPONENTS: dict[_PlaceSlot, tuple[_PlaceSlot, ...]] = {
    ("AFC_EAST", 1): (("NFC_EAST", 1), ("NFC_WEST", 1)),
    ("AFC_EAST", 2): (("NFC_EAST", 2), ("NFC_WEST", 2)),
    ("AFC_EAST", 3): (("NFC_EAST", 3), ("NFC_WEST", 3)),
    ("AFC_EAST", 4): (("NFC_EAST", 4), ("NFC_WEST", 4)),
    ("AFC_WEST", 1): (("NFC_EAST", 1), ("NFC_WEST", 1)),
    ("AFC_WEST", 2): (("NFC_EAST", 2), ("NFC_WEST", 2)),
    ("AFC_WEST", 3): (("NFC_EAST", 3), ("NFC_WEST", 3)),
    ("AFC_WEST", 4): (("NFC_EAST", 4), ("NFC_WEST", 4)),
    ("AFC_WEST", 5): (("NFC_WEST", 5),),
    ("NFC_EAST", 1): (("AFC_EAST", 1), ("AFC_WEST", 1)),
    ("NFC_EAST", 2): (("AFC_EAST", 2), ("AFC_WEST", 2)),
    ("NFC_EAST", 3): (("AFC_EAST", 3), ("AFC_WEST", 3)),
    ("NFC_EAST", 4): (("AFC_EAST", 4), ("AFC_WEST", 4)),
    ("NFC_WEST", 1): (("AFC_EAST", 1), ("AFC_WEST", 1)),
    ("NFC_WEST", 2): (("AFC_EAST", 2), ("AFC_WEST", 2)),
    ("NFC_WEST", 3): (("AFC_EAST", 3), ("AFC_WEST", 3)),
    ("NFC_WEST", 4): (("AFC_EAST", 4), ("AFC_WEST", 4)),
    ("NFC_WEST", 5): (("AFC_WEST", 5),),
}

TOP_HALF_MAX_RANK = 5
BOTTOM_HALF_MIN_RANK = 5

# Difficulty line: target average opponent conference rank (1-9). spread
# tilts it (0 = flat at 5; 2.5 = max useful tilt).
CONF_RANK_CENTER = 5
CONF_RANK_HALF_RANGE = 4

# Deviations are scored in 1/scale-rank units. The scale is the LCM of this and
# every non-conference game count, so opponent_rank_sum * (scale / games) is an
# exact integer for every team (20 for both leagues' 4- and 5-game teams).
DIFFICULTY_SCALE = 20


def _validate_fixed_place_table(divisions: Sequence[Division]) -> None:
    by_name = {division.name: division for division in divisions}
    expected_slots = {
        (division.name, place)
        for division in divisions
        for place in range(1, division.expected_size + 1)
    }
    if set(FIXED_NONCONF_PLACE_OPPONENTS) != expected_slots:
        raise SchedulerError(
            "Fixed non-conference place table must define every (division, place)"
        )
    for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items():
        name, place = slot
        label = f"{name} place {place}"
        expected = 1 if place == 5 else 2
        if len(opponents) != expected or len(set(opponents)) != expected:
            raise SchedulerError(
                f"{label} must have exactly {expected} distinct fixed opponents"
            )
        for opp in opponents:
            if opp not in FIXED_NONCONF_PLACE_OPPONENTS:
                raise SchedulerError(f"{label} references invalid slot {opp}")
            if by_name[opp[0]].conference == by_name[name].conference:
                raise SchedulerError(f"{label} references a same-conference slot")
            if slot not in FIXED_NONCONF_PLACE_OPPONENTS[opp]:
                raise SchedulerError(
                    f"Fixed non-conference place table is not symmetric: {label} -> "
                    f"{opp[0]} place {opp[1]} without the reverse edge"
                )


def difficulty_target(
    conf_rank: int, spread: float = DEFAULT_DIFFICULTY_SPREAD
) -> float:
    """Target average opponent conference rank for a team of `conf_rank` (1-9)."""
    return CONF_RANK_CENTER + spread * (conf_rank - CONF_RANK_CENTER) / (
        CONF_RANK_HALF_RANGE
    )


class _FixedCpsatNonConferenceModel:
    """Select every cross-conference matchup with the fixed pairs forced in.

    `rows` are the first conference's teams and `columns` the second's, both in
    conference-rank order (the grid order is part of the pinned PNFL model).
    `fixed_pairs` are pinned to 1 before solving, so the line objective only
    chooses the remaining slots around them.
    """

    def __init__(
        self,
        rows: Sequence[Team],
        columns: Sequence[Team],
        conf_rank: Mapping[Team, int],
        nonconference_games: Mapping[Team, int],
        fixed_pairs: frozenset[Matchup],
        spread: float = DEFAULT_DIFFICULTY_SPREAD,
    ) -> None:
        self.model = cp_model.CpModel()
        self.conf_rank = conf_rank
        self.nonconference_games = nonconference_games
        self.fixed_pairs = fixed_pairs
        self.spread = spread
        self.rows = list(rows)
        self.columns = list(columns)
        self.row_conference = self.rows[0].conference
        self.teams = tuple(self.rows + self.columns)
        self.scale = math.lcm(DIFFICULTY_SCALE, *nonconference_games.values())
        # Name "x" is OR-Tools convention; key is [row team, column team].
        self.x: dict[tuple[Team, Team], cp_model.IntVar] = {}
        self.opponent_rank_sum: dict[Team, cp_model.IntVar] = {}

        for row in self.rows:
            for column in self.columns:
                self.x[row, column] = self.model.new_bool_var(
                    f"nc_{row.metro}_{column.metro}"
                )

    def _var_for_pair(self, team: Team, opponent: Team) -> cp_model.IntVar:
        if team.conference == self.row_conference:
            return self.x[team, opponent]
        return self.x[opponent, team]

    def _opponents_for(self, team: Team) -> list[Team]:
        return self.columns if team.conference == self.row_conference else self.rows

    def _add_fixed_pair_constraints(self) -> None:
        # Sorted: a frozenset iterates in hash order, which differs per process,
        # and the built model must be identical for a seed to reproduce.
        for team_a, team_b in sorted(
            self.fixed_pairs, key=lambda pair: (pair[0].metro, pair[1].metro)
        ):
            row, column = (
                (team_a, team_b)
                if team_a.conference == self.row_conference
                else (team_b, team_a)
            )
            self.model.add(self.x[row, column] == 1)

    def _add_degree_constraints(self) -> None:
        for row in self.rows:
            self.model.add(
                sum(self.x[row, column] for column in self.columns)
                == self.nonconference_games[row]
            )
        for column in self.columns:
            self.model.add(
                sum(self.x[row, column] for row in self.rows)
                == self.nonconference_games[column]
            )

    def _add_top_bottom_constraints(self) -> None:
        for team in self.teams:
            opponents = self._opponents_for(team)
            top_half_vars = [
                self._var_for_pair(team, opponent)
                for opponent in opponents
                if self.conf_rank[opponent] <= TOP_HALF_MAX_RANK
            ]
            bottom_half_vars = [
                self._var_for_pair(team, opponent)
                for opponent in opponents
                if self.conf_rank[opponent] >= BOTTOM_HALF_MIN_RANK
            ]
            self.model.add(sum(top_half_vars) >= 1)
            self.model.add(sum(bottom_half_vars) >= 1)

    def _add_opponent_rank_sum_constraints(self) -> None:
        for team in self.teams:
            opponents = self._opponents_for(team)
            games = self.nonconference_games[team]
            score = self.model.new_int_var(
                games, TEAMS_PER_CONFERENCE * games, f"nc_rank_sum_{team.metro}"
            )
            self.model.add(
                score
                == sum(
                    self.conf_rank[opponent] * self._var_for_pair(team, opponent)
                    for opponent in opponents
                )
            )
            self.opponent_rank_sum[team] = score

    def _set_line_objective(self) -> None:
        # Score each team's deviation from its line target in 1/scale-rank
        # units, then minimize the largest deviation (minimax) and, as a
        # tie-break, the total (minisum). The tie-break weight exceeds any
        # possible total, so the largest is minimized first.
        deviations: list[cp_model.IntVar] = []
        max_dev = self.scale * TEAMS_PER_CONFERENCE
        for team in self.teams:
            games = self.nonconference_games[team]
            scaled_sum = self.opponent_rank_sum[team] * (self.scale // games)
            target = round(
                difficulty_target(self.conf_rank[team], self.spread) * self.scale
            )
            dev = self.model.new_int_var(0, max_dev, f"nc_dev_{team.metro}")
            self.model.add(dev >= scaled_sum - target)
            self.model.add(dev >= target - scaled_sum)
            deviations.append(dev)
        worst = self.model.new_int_var(0, max_dev, "nc_worst_dev")
        for dev in deviations:
            self.model.add(worst >= dev)
        tie_break = len(self.teams) * max_dev + 1
        self.model.minimize(tie_break * worst + sum(deviations))

    def build(self) -> None:
        self._add_fixed_pair_constraints()
        self._add_degree_constraints()
        self._add_top_bottom_constraints()
        self._add_opponent_rank_sum_constraints()
        self._set_line_objective()

    def solve(self, seed: int = 0, time_limit: float | None = None) -> set[Matchup]:
        solver = cp_model.CpSolver()
        # Single worker + fixed seed = reproducible; the seed picks among
        # equally-optimal matchup sets.
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = seed
        solver.parameters.randomize_search = True
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit

        status = solver.solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulerError(
                f"Fixed-place + CP-SAT non-conference model returned status "
                f"{solver.status_name(status)} - no feasible inventory"
            )

        return {
            make_matchup(row, column)
            for (row, column), var in self.x.items()
            if solver.value(var) == 1
        }


class FixedCpsatMatchupBuilder:
    def __init__(
        self,
        league: League,
        *,
        weeks: int = DEFAULT_WEEKS,
        rivalries: Sequence[RivalryPair] = (),
        spread: float = DEFAULT_DIFFICULTY_SPREAD,
        phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        seed: int = 0,
    ) -> None:
        self.league = league
        self.teams = league.teams
        self.rankings = league.rankings
        self.weeks = weeks
        self.rivalries = tuple(rivalries)
        self.spread = spread
        self.phase1_time_limit = phase1_time_limit
        self.seed = seed

        self.conf_rank = {team: league.rankings.rank_of(team) for team in self.teams}
        self.nonconference_games = {
            team: league.nonconference_games(team, weeks) for team in self.teams
        }
        self.matchups: list[Matchup] = []
        self.selected_nonconference: set[Matchup] = set()
        self.remaining_nonconference = dict(self.nonconference_games)
        self.fixed_nonconference_pairs: set[Matchup] = set()

    def _add_divisional_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if team_i.same_division(team_j):
                    pair = make_matchup(team_i, team_j)
                    self.matchups.append(pair)
                    self.matchups.append(pair)

    def _add_conference_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if (
                    team_i.conference == team_j.conference
                    and not team_i.same_division(team_j)
                ):
                    self.matchups.append(make_matchup(team_i, team_j))

    def _add_nonconference_pairs(self, pairs: set[Matchup]) -> None:
        for i, j in sorted(pairs, key=lambda p: (p[0].metro, p[1].metro)):
            pair = (i, j)
            if pair in self.selected_nonconference:
                raise SchedulerError(
                    f"Duplicate non-conference pair in phase-1 inventory: {pair}"
                )
            self.matchups.append(pair)
            self.selected_nonconference.add(pair)
            self.remaining_nonconference[i] -= 1
            self.remaining_nonconference[j] -= 1
            if (
                self.remaining_nonconference[i] < 0
                or self.remaining_nonconference[j] < 0
            ):
                raise SchedulerError(
                    f"Non-conference slot count went negative after reserving pair "
                    f"{pair}"
                )

    def _fixed_place_pairs(self) -> set[Matchup]:
        """The PNFL's same-place pairs; none for a league without divisions."""
        if not self.league.has_divisions:
            return set()
        _validate_fixed_place_table(self.league.divisions)
        team_at: dict[_PlaceSlot, Team] = {
            (division.name, index + 1): team
            for division, order in self.league.division_standings.items()
            for index, team in enumerate(order)
        }
        return {
            make_matchup(team_at[slot], team_at[opp])
            for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
            for opp in opponents
        }

    def _rivalry_pairs(self) -> set[Matchup]:
        """Cross-conference rivalries are non-conference games the solver must keep."""
        return {
            make_matchup(a, b) for a, b in self.rivalries if a.conference != b.conference
        }

    def _nonconference_model(
        self, fixed_pairs: set[Matchup]
    ) -> _FixedCpsatNonConferenceModel:
        """The built (unsolved) non-conference model; tests fingerprint it."""
        first, second = self.league.conferences
        model = _FixedCpsatNonConferenceModel(
            rows=self.rankings.ranked(first),
            columns=self.rankings.ranked(second),
            conf_rank=self.conf_rank,
            nonconference_games=self.nonconference_games,
            fixed_pairs=frozenset(fixed_pairs),
            spread=self.spread,
        )
        model.build()
        return model

    def build_matchup_plan(self) -> MatchupPlan:
        self._add_divisional_matchups()
        self._add_conference_matchups()

        fixed_pairs = self._fixed_place_pairs() | self._rivalry_pairs()
        self.fixed_nonconference_pairs = set(fixed_pairs)
        nonconference_pairs = self._nonconference_model(fixed_pairs).solve(
            seed=self.seed, time_limit=self.phase1_time_limit
        )
        if not fixed_pairs <= nonconference_pairs:
            raise SchedulerError("CP-SAT solve dropped a fixed non-conference pair")
        self._add_nonconference_pairs(nonconference_pairs)

        if any(slots != 0 for slots in self.remaining_nonconference.values()):
            unresolved = {
                team.metro: slots
                for team, slots in self.remaining_nonconference.items()
                if slots != 0
            }
            raise SchedulerError(
                f"Non-conference inventory left unresolved slots: {unresolved}"
            )
        expected_nonconference = sum(self.nonconference_games.values()) // 2
        if len(self.selected_nonconference) != expected_nonconference:
            raise SchedulerError(
                f"Expected {expected_nonconference} non-conference games, got "
                f"{len(self.selected_nonconference)}"
            )
        expected_total = self.weeks * GAMES_PER_WEEK
        if len(self.matchups) != expected_total:
            raise SchedulerError(
                f"Expected {expected_total} total matchups in phase-1 inventory, got "
                f"{len(self.matchups)}"
            )

        return MatchupPlan(
            matchups=tuple(self.matchups),
            fixed_nonconference_pairs=frozenset(self.fixed_nonconference_pairs),
        )
```

- [ ] **Step 4: Update the callers**

`fixed_cpsat_scheduler.py`: `FixedCpsatMatchupBuilder(league, spread=config.difficulty.spread, phase1_time_limit=config.solver.phase1_time_limit, seed=seed)` (weeks and rivalries are wired in Task 7).

`test_pnfl_model_fingerprint.py`: `builder = FixedCpsatMatchupBuilder(league, weeks=config.league.weeks, spread=config.difficulty.spread, phase1_time_limit=config.solver.phase1_time_limit, seed=0)`.

`test_report.py`: `FixedCpsatMatchupBuilder(league).build_matchup_plan()`.

`test_fixed_cpsat_inventory.py`:
- fixture and every constructor call → `FixedCpsatMatchupBuilder(league)` / `FixedCpsatMatchupBuilder(league, spread=spread)`.
- `_place_pairs_from`: `(division.name, index + 1)` keys.
- `test_place_table_covers_every_division_place`: `(division.name, place)` slots over `PNFL_DIVISIONS`.
- `test_place_table_is_symmetric_and_cross_conference`: compare `PNFL_DIVISIONS_BY_NAME[opp_division].conference != PNFL_DIVISIONS_BY_NAME[division].conference` (import `PNFL_DIVISIONS_BY_NAME`).
- `test_place_table_is_same_place_only`: iterate `PNFL_DIVISIONS`, build expected with `(other.name, place)`, and assert `FIXED_NONCONF_PLACE_OPPONENTS["AFC_WEST", 5] == (("NFC_WEST", 5),)` (and the mirror).
- `bad_table` params: string keys (`("AFC_EAST", 1)`, `("NFC_EAST", 3)`, `("NFC_WEST", 3)`, `("AFC_WEST", 1)`); `_validate_fixed_place_table()` → `_validate_fixed_place_table(PNFL_DIVISIONS)`.
- `test_fixed_pairs_follow_division_standings_not_rank`: `FixedCpsatMatchupBuilder(league)`.
- `_avg_opponent_conf_rank`: `games = league.nonconference_games(team, 16)` — pass `league` in (or keep the `(AFC_EAST, NFC_EAST)` check).

- [ ] **Step 5: Run everything**

Run: `uv run pytest` — PASS; the fingerprint's phase-1 hash is unchanged (the grid, names, constraint order and `scale == 20` are the same for the PNFL).
Run ruff check / ruff format / pyright — clean.

- [ ] **Step 6: Update the phase-1 test matrix**

Append to `tests/unit/scheduler/fixed_cpsat/test-matrix-phase-1-matchups-fixed-cpsat.md` a section:

```markdown
### League without divisions (`tests/unit/scheduler/conference_league/test_inventory.py`)
| Case | Expected | Test | Status |
|---|---|---|---|
| Totals | 108 pairings, 12 per team | `test_inventory_totals` | ☑ |
| Conference once, no repeats | each conference pair 1×, cross ≤1× | `test_every_conference_pair_once_and_no_divisional_repeats` | ☑ |
| Non-conference degree | 4 distinct opponents | `test_every_team_has_four_distinct_nonconference_opponents` | ☑ |
| Cross-conference rivalry | fixed and kept | `test_cross_conference_rivalry_is_fixed` | ☑ |
| Top/bottom guard | ≥1 each | `test_each_team_draws_a_top_and_bottom_half_opponent` | ☑ |
| Line target | within 1.0 at spread 0 and 2.5 | `test_difficulty_is_near_line_target` | ☑ |
| Deterministic | same plan twice | `test_inventory_is_deterministic` | ☑ |
| Fewer weeks | 10 weeks → 2 non-conference | `test_ten_week_season_gives_two_nonconference_games` | ☑ |
```

- [ ] **Step 7: Commit**

```bash
git add -A src tests
git commit -m "scheduler: phase 1 builds the inventory from league structure, weeks and rivalries"
```

---

### Task 6: Phase 2 — league-driven builder with gated rules (PNFL model unchanged)

Rework `ScheduleBuilder` to take the league and `weeks`, gate every PNFL-only rule, and make the hosting policy generic. No new rules yet (Task 7). The fingerprint must not change.

**Files:**
- Modify: `src/athc/scheduler/schedulers/schedule_builder.py`
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_scheduler.py` (constructor call)
- Modify: `tests/unit/scheduler/test_schedule_builder.py`, `tests/unit/scheduler/test_report.py`, `tests/unit/scheduler/test_pnfl_model_fingerprint.py`

**Interfaces:**
- Produces: `ScheduleBuilder(league: League, error_cls: type[RuntimeError], amounts: Phase2Config | None = None, *, weeks: int = DEFAULT_WEEKS, rivalries: Sequence[RivalryPair] = (), rotate_rivalry_home_by_season: bool = True, season: int | None = None)`; `build_schedule(matchups, seed, time_limit, workers) -> Schedule`; `_populate_model(matchups)`.
- Attributes later tasks use: `self.league`, `self.teams`, `self.num_weeks`, `self.weeks` (range), `self.x`, `self.h`, `self.rivalries`, `self.rotate_rivalry_home_by_season`, `self.season`.

- [ ] **Step 1: Write the gate tests**

Replace the body of `tests/unit/scheduler/test_schedule_builder.py` with:

```python
"""Phase-2 ScheduleBuilder: inventory guards, rule gating, solver wiring.

Seed determinism and schedule correctness are covered end-to-end by the golden
regression test in tests/integration/test_generate_schedule.py; the PNFL model
itself is pinned by test_pnfl_model_fingerprint.py.
"""

from __future__ import annotations

import pytest

from athc.scheduler.config import ConfigError, Phase2Config
from athc.scheduler.domain.league import AFC, AFC_EAST, Team
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import make_matchup

from .conftest import LEAGUE_5_SLOTS, PCFL_LEAGUE

def _off_dict() -> dict[str, bool]:
    return {
        "require_home_balance_per_six_weeks": False,
        "require_home_away_streak_caps": False,
        "require_mixed_home_away_at_season_ends": False,
    }


PCFL_AMOUNTS = Phase2Config(**_off_dict())


def _pcfl_model(amounts: Phase2Config = PCFL_AMOUNTS, **kwargs) -> ScheduleBuilder:
    builder = ScheduleBuilder(PCFL_LEAGUE, SchedulerError, amounts, weeks=12, **kwargs)
    builder._populate_model(matchups=[])
    return builder


def _counts(builder: ScheduleBuilder) -> tuple[int, int]:
    return len(builder.model.proto.variables), len(builder.model.proto.constraints)


def test_unknown_pair_in_inventory_raises() -> None:
    teams = LEAGUE_5_SLOTS.teams
    foreign = Team(metro="Nowhere", conference=AFC, division=AFC_EAST)
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([make_matchup(foreign, teams[0])], seed=0, time_limit=5)


def test_empty_inventory_is_infeasible() -> None:
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([], seed=0, time_limit=30)


def test_soft_objective_is_added_to_the_model() -> None:
    # Building the model (no solve) wires the soft objective: 8 metrics, each
    # with an over- and under-slack term -> 16 objective terms.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    builder._populate_model(matchups=[])
    assert len(builder.model.proto.objective.vars) == 16


def test_solver_is_configured_for_reproducible_parallel_search() -> None:
    # The worker count must reach the solver as a fixed interleave width (both
    # num_search_workers and interleave_batch_size), stopping on deterministic
    # time -- this is what keeps a seed reproducible across machines.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    params = builder._make_solver(seed=3, time_limit=42.0, workers=5).parameters
    assert params.random_seed == 3
    assert params.num_search_workers == 5
    assert params.interleave_search is True
    assert params.interleave_batch_size == 5
    assert params.max_deterministic_time == 42.0


# --- Rule gating for a league without divisions -------------------------------


def test_league_without_divisions_has_no_divisional_model_parts() -> None:
    builder = _pcfl_model()
    assert len(builder.model.proto.objective.vars) == 0  # no soft objective
    names = [v.name for v in builder.model.proto.variables]
    assert not any(n.startswith(("d_", "s3d_", "has3", "open2div_", "gap_")) for n in names)
    assert builder.home_games_per_team == 6
    assert builder.num_weeks == 12


@pytest.mark.parametrize(
    "toggle",
    [
        "require_home_balance_per_six_weeks",
        "require_home_away_streak_caps",
        "require_mixed_home_away_at_season_ends",
    ],
)
def test_home_away_toggles_add_constraints_only_when_on(toggle: str) -> None:
    off = _counts(_pcfl_model())
    on = _counts(_pcfl_model(Phase2Config(**{**_off_dict(), toggle: True})))
    assert on[1] > off[1]


def test_streak_caps_off_with_divisions_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="require_home_away_streak_caps"):
        ScheduleBuilder(
            LEAGUE_5_SLOTS,
            SchedulerError,
            Phase2Config(require_home_away_streak_caps=False),
        )


def test_streak_caps_on_without_divisions_is_allowed() -> None:
    builder = _pcfl_model(Phase2Config(**{**_off_dict(), "require_home_away_streak_caps": True}))
    names = [v.name for v in builder.model.proto.variables]
    assert any(n.startswith("has3h_") for n in names)
    assert not any(n.startswith("has3d_") for n in names)


def test_max_consecutive_window_follows_the_cap() -> None:
    # cap 2 -> 3-week windows: 10 per team for 12 weeks, two constraints each.
    two = _counts(_pcfl_model(Phase2Config(**_off_dict(), max_consecutive_home_or_away=2)))
    three = _counts(_pcfl_model(Phase2Config(**_off_dict(), max_consecutive_home_or_away=3)))
    assert two[1] - three[1] == 18 * 2 * (10 - 9)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/scheduler/test_schedule_builder.py -q`
Expected: FAIL (constructor signature).

- [ ] **Step 3: Rework `ScheduleBuilder`**

Replace the module docstring's first paragraph with a short note that the rules below are the PNFL's; a league without divisions gets only the structural and toggled rules (see `docs/scheduler/phase-2-schedule.md`). Delete the temporary `NUM_WEEKS` / `HOME_GAMES_PER_TEAM` / `WEEK_16_DIVISIONAL_GAMES` constants from Task 2. Imports:

```python
from athc.scheduler.config import (
    DEFAULT_SOLVER_WORKERS,
    DEFAULT_TIME_LIMIT,
    DEFAULT_WEEKS,
    ConfigError,
    Phase2Config,
)
from athc.scheduler.domain.league import League, RivalryPair, Team
from athc.scheduler.domain.schedule import Game, Schedule
```

Constructor:

```python
    def __init__(
        self,
        league: League,
        error_cls: type[RuntimeError],
        amounts: Phase2Config | None = None,
        *,
        weeks: int = DEFAULT_WEEKS,
        rivalries: Sequence[RivalryPair] = (),
        rotate_rivalry_home_by_season: bool = True,
        season: int | None = None,
    ) -> None:
        self.model = cp_model.CpModel()
        self.league = league
        self.teams = tuple(league.teams)
        self.error_cls = error_cls
        self.amounts = amounts or Phase2Config()
        self.num_weeks = weeks
        self.weeks = range(weeks)
        self.home_games_per_team = weeks // 2
        self.rivalries = tuple(rivalries)
        self.rotate_rivalry_home_by_season = rotate_rivalry_home_by_season
        self.season = season

        if league.has_divisions and not self.amounts.require_home_away_streak_caps:
            raise ConfigError(
                "require_home_away_streak_caps must be true for a league with "
                "divisions: the soft objective needs the streak flags."
            )
        if self.rivalries and rotate_rivalry_home_by_season and season is None:
            raise error_cls("A season is required to rotate rivalry hosting.")

        self.div_opponents: dict[Team, list[Team]] = {
            team: list(league.divisional_opponents(team)) for team in self.teams
        }

        self.four_team_set: set[Team] = {
            t for t in self.teams if t.division is not None and t.division.expected_size == 4
        }
        self.five_team_set: set[Team] = {
            t for t in self.teams if t.division is not None and t.division.expected_size == 5
        }
        # ... (four_team_teams / five_team_teams tuples unchanged)

        # pair classification: same_division / same conference / else (unchanged)

        # x and h creation unchanged.

        # d is only meaningful with divisions; a divisionless league gets none.
        self.d: dict[tuple[Team, int], cp_model.IntVar] = {}
        if league.has_divisions:
            for team_i in self.teams:
                for w in self.weeks:
                    self.d[team_i, w] = self.model.new_bool_var(f"d_{team_i.metro}_w{w}")
                    self.model.add(
                        self.d[team_i, w]
                        == sum(
                            self.x[team_i, opp, w] + self.x[opp, team_i, w]
                            for opp in self.div_opponents[team_i]
                        )
                    )
```

Then apply these edits, method by method (every `NUM_WEEKS` → `self.num_weeks`):

- `_constraint_no_four_straight_home_or_away` → generalized window, same two-loop order and explicit chained sums:

```python
    def _constraint_max_consecutive_home_or_away(self) -> None:
        # Every (cap + 1)-week window holds at most cap home games and at least
        # one, so neither a home nor an away streak exceeds cap.
        cap = self.amounts.max_consecutive_home_or_away
        window = cap + 1
        for team_i in self.teams:
            for w in range(self.num_weeks - cap):
                self.model.add(self._window_sum(self.h, team_i, w, window) <= cap)
            for w in range(self.num_weeks - cap):
                self.model.add(self._window_sum(self.h, team_i, w, window) >= 1)

    def _window_sum(self, var, team: Team, start: int, length: int):
        # Chained addition (not sum()) keeps the expression shape the pinned
        # PNFL model was built with.
        expr = var[team, start]
        for k in range(1, length):
            expr = expr + var[team, start + k]
        return expr
```

- `_constraint_home_away_balance_in_six_game_windows`: first line `if not self.amounts.require_home_balance_per_six_weeks: return`.
- `_constraint_no_three_game_home_or_away_streak_at_season_start_or_end`: first line `if not self.amounts.require_mixed_home_away_at_season_ends: return`.
- `_constraint_max_one_total_three_game_home_or_away_streak`: first line `if not self.amounts.require_home_away_streak_caps: return` (keep initializing `self._streak3h = {}` / `self._streak3a = {}` before the return so attributes exist).
- `_constraint_no_back_to_back`, `_constraint_max_close_rematches`, `_constraint_divisional_home_balance`, `_constraint_max_consecutive_division`, `_constraint_max_teams_divisional_weeks_1_and_2`, `_constraint_no_three_game_divisional_streak_at_season_start_or_end`, `_constraint_max_one_total_three_game_divisional_streak`, `_constraint_division_density`, `_constraint_divisional_front_load`, `_constraint_max_two_non_interleaved_divisional_opponents`, `_constraint_late_divisional_presence`: first line `if not self.league.has_divisions: return`. In the streak one initialize `self._streak3d = {}` before the return; in the rematch and interleave ones initialize `self._close_rematch_flags = []` / `self._two_bunched_flags = []`; in the weeks-1-2 one `self._opening_two_div_flags = []`.
- `_constraint_week_16_matchups` → rename `_constraint_final_week_divisional`; gate `if not self.league.has_divisions or not self.amounts.require_final_week_divisional: return`; `== self.league.max_divisional_games_per_week`.
- Hosting:

```python
    def _constraint_conference_home_balance(self) -> None:
        # Balanced hosting: each team hosts half its conference games (2 of 4;
        # 2 or 3 of 5; 4 of 8).
        for team_i in self.teams:
            opponents = self.league.conference_opponents(team_i)
            self._add_half_home(team_i, opponents, len(opponents))

    def _constraint_nonconference_home_balance(self) -> None:
        # Balanced hosting: each team hosts half its non-conference games. The
        # sum spans every other-conference team; the inventory decides which of
        # them are played, so the bounds come from the team's game count.
        for team_i in self.teams:
            opponents = [t for t in self.teams if t.conference != team_i.conference]
            count = self.league.nonconference_games(team_i, self.num_weeks)
            self._add_half_home(team_i, opponents, count)

    def _add_half_home(
        self, team_i: Team, opponents: Sequence[Team], count: int
    ) -> None:
        # One `==` when the half is exact, else `>=` then `<=`: the shapes the
        # pinned PNFL model was built with.
        home_games = sum(
            self.x[team_i, team_j, w] for team_j in opponents for w in self.weeks
        )
        lo, hi = count // 2, (count + 1) // 2
        if lo == hi:
            self.model.add(home_games == lo)
        else:
            self.model.add(home_games >= lo)
            self.model.add(home_games <= hi)
```

  (The opponent lists iterate `self.teams` in canonical order, as today.)

- `_constraint_max_teams_with_streaks`:

```python
        caps: list[tuple[dict[Team, list[cp_model.IntVar]], str, int]] = []
        if self.amounts.require_home_away_streak_caps:
            caps.append((self._streak3h, "has3h", self.amounts.max_teams_with_home_streak))
            caps.append((self._streak3a, "has3a", self.amounts.max_teams_with_away_streak))
        if self.league.has_divisions:
            caps.append((self._streak3d, "has3d", self.amounts.max_teams_with_divisional_streak))
        for streaks, label, cap in caps:
            ...  # unchanged loop
```

- `_add_soft_objective`: first line `if not self.league.has_divisions: return`.
- `_populate_model`: same order, with the renamed methods:

```python
    def _populate_model(self, matchups: Matchups) -> None:
        self._constraint_one_game_per_week()
        self._constraint_home_balance()
        self._constraint_max_consecutive_home_or_away()
        self._constraint_home_away_balance_in_six_game_windows()
        self._constraint_no_three_game_home_or_away_streak_at_season_start_or_end()
        self._constraint_max_one_total_three_game_home_or_away_streak()
        self._constraint_no_back_to_back()
        self._constraint_max_close_rematches()
        self._constraint_phase_one_inventory(matchups)
        self._constraint_divisional_home_balance()
        self._constraint_conference_home_balance()
        self._constraint_nonconference_home_balance()
        self._constraint_max_consecutive_division()
        self._constraint_max_teams_divisional_weeks_1_and_2()
        self._constraint_no_three_game_divisional_streak_at_season_start_or_end()
        self._constraint_max_one_total_three_game_divisional_streak()
        self._constraint_max_teams_with_streaks()
        self._constraint_division_density()
        self._constraint_divisional_front_load()
        self._constraint_max_two_non_interleaved_divisional_opponents()
        self._constraint_final_week_divisional()
        self._constraint_late_divisional_presence()
        self._add_soft_objective()
```

- [ ] **Step 4: Update the callers**

`fixed_cpsat_scheduler.py`: `ScheduleBuilder(league, error_cls=SchedulerError, amounts=config.phase2)` (weeks/rivalries wired in Task 7).
`test_report.py`: `ScheduleBuilder(league, SchedulerError)`.
`test_pnfl_model_fingerprint.py`: `ScheduleBuilder(league, SchedulerError, config.phase2, weeks=config.league.weeks)`.

- [ ] **Step 5: Run everything**

Run: `uv run pytest` — PASS with the phase-2 fingerprint unchanged. If the fingerprint fails, diff the two protos (write `model.proto` to text with `str(model.proto)` before and after, for the golden league) and fix the shape difference — do not re-pin.
Run ruff check / ruff format / pyright — clean.

- [ ] **Step 6: Commit**

```bash
git add -A src tests
git commit -m "scheduler: phase 2 takes the league and weeks; PNFL-only rules are gated"
```

---

### Task 7: Phase 2 — the PCFL rules (opening weeks, conference-sequence cap, rivalry week)

**Files:**
- Modify: `src/athc/scheduler/schedulers/schedule_builder.py`
- Modify: `tests/unit/scheduler/test_schedule_builder.py`

- [ ] **Step 1: Write the model-build tests**

Append to `tests/unit/scheduler/test_schedule_builder.py`:

```python
from athc.scheduler.config import RivalriesConfig, resolve_rivalries  # noqa: E402

from .conftest import PCFL_RIVALRIES  # noqa: E402

RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))


def test_opening_nonconference_weeks_add_one_constraint_per_team_week() -> None:
    off = _counts(_pcfl_model())
    on = _counts(_pcfl_model(Phase2Config(**_off_dict(), opening_nonconference_weeks=3)))
    assert on[1] - off[1] == 18 * 3


def test_conference_streak_cap_adds_two_constraints_per_window() -> None:
    # cap 2: every window of 3..12 weeks -> 55 windows per team, two each.
    off = _counts(_pcfl_model())
    on = _counts(
        _pcfl_model(Phase2Config(**_off_dict(), max_consecutive_conference_home_or_away=2))
    )
    assert on[1] - off[1] == 18 * 2 * 55


def test_rivalry_week_adds_one_constraint_per_pair() -> None:
    off = _counts(_pcfl_model())
    rotating = _counts(_pcfl_model(rivalries=RIVALRIES, season=2028))
    free = _counts(_pcfl_model(rivalries=RIVALRIES, rotate_rivalry_home_by_season=False))
    assert rotating[1] - off[1] == 9
    assert free[1] - off[1] == 9


def test_rivalry_rotation_needs_a_season() -> None:
    with pytest.raises(SchedulerError, match="season"):
        ScheduleBuilder(PCFL_LEAGUE, SchedulerError, PCFL_AMOUNTS, weeks=12, rivalries=RIVALRIES)


def test_rivalry_rotation_pins_the_host_by_season_parity() -> None:
    # Even season: the first-listed team hosts. The pinned literal is x[first, second, last].
    even = _pcfl_model(rivalries=RIVALRIES, season=2028)
    odd = _pcfl_model(rivalries=RIVALRIES, season=2029)
    first, second = RIVALRIES[0]
    even_var = even.x[first, second, 11].index
    odd_var = odd.x[second, first, 11].index
    even_pinned = {c.linear.vars[0] for c in even.model.proto.constraints if len(c.linear.vars) == 1 and list(c.linear.domain) == [1, 1]}
    odd_pinned = {c.linear.vars[0] for c in odd.model.proto.constraints if len(c.linear.vars) == 1 and list(c.linear.domain) == [1, 1]}
    assert even_var in even_pinned
    assert odd_var in odd_pinned
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/scheduler/test_schedule_builder.py -q`
Expected: the three "adds constraints" tests FAIL (difference 0) and the parity test FAILs.

- [ ] **Step 3: Add the rules**

In `schedule_builder.py`, add after `_constraint_late_divisional_presence`:

```python
    def _same_conference_opponents(self, team: Team) -> tuple[Team, ...]:
        return self.league.same_conference_opponents(team)

    def _constraint_opening_nonconference_weeks(self) -> None:
        # Weeks 1..N hold no same-conference game (divisional or conference).
        n = self.amounts.opening_nonconference_weeks
        if n == 0:
            return
        for team_i in self.teams:
            opponents = self._same_conference_opponents(team_i)
            for w in range(n):
                self.model.add(
                    sum(self.x[team_i, opp, w] + self.x[opp, team_i, w] for opp in opponents)
                    == 0
                )

    def _constraint_max_consecutive_conference_home_or_away(self) -> None:
        # Along a team's sequence of conference games (non-conference games
        # between them do not break a streak): no cap + 1 straight at home or
        # away. For every window of weeks at least cap + 1 long, the conference
        # home games are capped unless the window also holds a conference away
        # game (which makes the bound slack), and the mirror.
        cap = self.amounts.max_consecutive_conference_home_or_away
        if cap == 0:
            return
        for team_i in self.teams:
            opponents = self._same_conference_opponents(team_i)
            home = [sum(self.x[team_i, opp, w] for opp in opponents) for w in self.weeks]
            away = [sum(self.x[opp, team_i, w] for opp in opponents) for w in self.weeks]
            for length in range(cap + 1, self.num_weeks + 1):
                for start in range(self.num_weeks - length + 1):
                    span = range(start, start + length)
                    home_in = sum(home[w] for w in span)
                    away_in = sum(away[w] for w in span)
                    self.model.add(home_in <= cap + length * away_in)
                    self.model.add(away_in <= cap + length * home_in)

    def _constraint_rivalry_final_week(self) -> None:
        # Rivalry week: every listed pair meets in the last week. With rotation,
        # the first-listed team hosts in even seasons and the second in odd.
        if not self.rivalries:
            return
        last = self.num_weeks - 1
        for first, second in self.rivalries:
            if self.rotate_rivalry_home_by_season:
                assert self.season is not None  # checked in __init__
                home, away = (first, second) if self.season % 2 == 0 else (second, first)
                self.model.add(self.x[home, away, last] == 1)
            else:
                self.model.add(self.x[first, second, last] + self.x[second, first, last] == 1)
```

And in `_populate_model`, insert before `self._add_soft_objective()`:

```python
        self._constraint_opening_nonconference_weeks()
        self._constraint_max_consecutive_conference_home_or_away()
        self._constraint_rivalry_final_week()
```

- [ ] **Step 4: Run everything**

Run: `uv run pytest` — PASS; fingerprint unchanged (the three rules add nothing for the PNFL: 0, 0 and no rivalries).
Run ruff check / ruff format / pyright — clean. (pyright: the `assert self.season is not None` narrows the Optional.)

- [ ] **Step 5: Commit**

```bash
git add src/athc/scheduler/schedulers/schedule_builder.py tests/unit/scheduler/test_schedule_builder.py
git commit -m "scheduler: opening non-conference weeks, conference-sequence streak cap and rivalry week rules"
```

---

### Task 8: Wire the scheduler entry and `main.py`; PCFL end-to-end tests

**Files:**
- Modify: `src/athc/scheduler/schedulers/fixed_cpsat_scheduler.py`, `src/athc/scheduler/main.py`
- Modify: `tests/unit/scheduler/fixed_cpsat/conftest.py` (pass a season)
- Create: `tests/unit/scheduler/conference_league/conftest.py`, `tests/unit/scheduler/conference_league/test_schedule_rules.py`

**Interfaces:**
- Produces: `generate_schedule(league: League, seed: int = 0, scheduler_config: SchedulerConfig | None = None, *, season: int) -> SchedulerResult`.

- [ ] **Step 1: Write the end-to-end tests**

`tests/unit/scheduler/conference_league/conftest.py`:

```python
"""Solved PCFL schedules: an even season, an odd season, and rotation off.

These solves have no objective, so CP-SAT stops at the first feasible schedule
and they are fast enough for the default suite. If a machine makes them slow,
mark them `slow` (see the module note in test_schedule_rules.py).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from athc.scheduler.config import (
    DifficultyConfig,
    LeagueConfig,
    Phase2Config,
    RivalriesConfig,
    SchedulerConfig,
)
from athc.scheduler.schedulers.types import SchedulerResult, get_scheduler

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

PCFL_CONFIG = SchedulerConfig(
    league=LeagueConfig(weeks=12),
    difficulty=DifficultyConfig(spread=0.0),
    phase2=Phase2Config(
        max_consecutive_home_or_away=3,
        max_consecutive_conference_home_or_away=2,
        opening_nonconference_weeks=3,
        require_home_balance_per_six_weeks=False,
        require_home_away_streak_caps=False,
        require_mixed_home_away_at_season_ends=False,
    ),
    rivalries=RivalriesConfig(pairs=PCFL_RIVALRIES, rotate_home_by_season=True),
)
NO_ROTATION_CONFIG = replace(
    PCFL_CONFIG, rivalries=replace(PCFL_CONFIG.rivalries, rotate_home_by_season=False)
)


def _solve(season: int, config: SchedulerConfig = PCFL_CONFIG) -> SchedulerResult:
    return get_scheduler()(league=PCFL_LEAGUE, seed=7, scheduler_config=config, season=season)


@pytest.fixture(scope="session")
def pcfl_even() -> SchedulerResult:
    return _solve(2028)


@pytest.fixture(scope="session")
def pcfl_odd() -> SchedulerResult:
    return _solve(2029)


@pytest.fixture(scope="session")
def pcfl_free() -> SchedulerResult:
    return _solve(2029, NO_ROTATION_CONFIG)


@pytest.fixture(params=["pcfl_even", "pcfl_odd", "pcfl_free"])
def pcfl_result(request) -> SchedulerResult:
    return request.getfixturevalue(request.param)
```

`tests/unit/scheduler/conference_league/test_schedule_rules.py`:

```python
"""Every PCFL rule, checked on solved schedules (see conftest for the configs)."""

from __future__ import annotations

from collections import Counter

from athc.scheduler.config import RivalriesConfig, resolve_rivalries
from athc.scheduler.domain.schedule import Schedule
from athc.scheduler.schedulers.types import make_matchup
from athc.scheduler.writers.report import build_schedule_report

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

WEEKS = 12
RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))
TEAMS = PCFL_LEAGUE.teams


def _games(schedule: Schedule, team):
    return sorted(schedule.games_for(team), key=lambda g: g.week)


def _is_conference(game) -> bool:
    return game.home.conference == game.away.conference


def test_structure(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    assert len(schedule.games) == WEEKS * 9
    for week in range(1, WEEKS + 1):
        assert sum(1 for g in schedule.games if g.week == week) == 9, week
    for team in TEAMS:
        games = _games(schedule, team)
        assert [g.week for g in games] == list(range(1, WEEKS + 1)), team.metro
        assert len(schedule.home_games_for(team)) == 6, team.metro


def test_matches_phase_one_inventory(pcfl_result) -> None:
    counts = Counter(make_matchup(g.home, g.away) for g in pcfl_result.schedule.games)
    assert counts == Counter(pcfl_result.matchup_plan.matchups)


def test_conference_round_robin_four_home_four_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        conference = [g for g in _games(schedule, team) if _is_conference(g)]
        opponents = {g.away if g.home == team else g.home for g in conference}
        assert opponents == set(PCFL_LEAGUE.conference_opponents(team)), team.metro
        assert sum(1 for g in conference if g.home == team) == 4, team.metro


def test_nonconference_two_home_two_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        nonconference = [g for g in _games(schedule, team) if not _is_conference(g)]
        assert len(nonconference) == 4, team.metro
        assert sum(1 for g in nonconference if g.home == team) == 2, team.metro


def test_opening_weeks_are_all_nonconference(pcfl_result) -> None:
    for game in pcfl_result.schedule.games:
        if game.week <= 3:
            assert not _is_conference(game), game


def test_later_weeks_hold_exactly_one_cross_conference_game(pcfl_result) -> None:
    for week in range(4, WEEKS + 1):
        cross = [g for g in pcfl_result.schedule.games if g.week == week and not _is_conference(g)]
        assert len(cross) == 1, week


def test_max_three_consecutive_home_or_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        home = [g.home == team for g in _games(schedule, team)]
        for start in range(WEEKS - 3):
            assert 1 <= sum(home[start : start + 4]) <= 3, (team.metro, start + 1)


def test_max_two_consecutive_conference_home_or_away(pcfl_result) -> None:
    schedule = pcfl_result.schedule
    for team in TEAMS:
        venues = [g.home == team for g in _games(schedule, team) if _is_conference(g)]
        assert len(venues) == 8, team.metro
        for start in range(len(venues) - 2):
            assert len(set(venues[start : start + 3])) == 2, (team.metro, start)


def test_final_week_is_rivalry_week(pcfl_result) -> None:
    final = {make_matchup(g.home, g.away) for g in pcfl_result.schedule.games if g.week == WEEKS}
    assert final == {make_matchup(a, b) for a, b in RIVALRIES}


def test_even_season_first_listed_hosts(pcfl_even) -> None:
    hosts = {g.home for g in pcfl_even.schedule.games if g.week == WEEKS}
    assert hosts == {first for first, _ in RIVALRIES}


def test_odd_season_second_listed_hosts(pcfl_odd) -> None:
    hosts = {g.home for g in pcfl_odd.schedule.games if g.week == WEEKS}
    assert hosts == {second for _, second in RIVALRIES}


def test_rotation_off_still_plays_rivalries_in_the_final_week(pcfl_free) -> None:
    final = {make_matchup(g.home, g.away) for g in pcfl_free.schedule.games if g.week == WEEKS}
    assert final == {make_matchup(a, b) for a, b in RIVALRIES}


def test_report_builds_for_a_league_without_divisions(pcfl_even) -> None:
    report = build_schedule_report(
        schedule=pcfl_even.schedule,
        matchup_plan=pcfl_even.matchup_plan,
        league=PCFL_LEAGUE,
        seed=7,
        config_path="test",
        elapsed_time_seconds=0.0,
        difficulty_spread=0.0,
    )
    assert len(report.teams) == 18
    assert all(len(row.nonconference_opponents) == 4 for row in report.teams)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/scheduler/conference_league/test_schedule_rules.py -q`
Expected: FAIL (`generate_schedule` got an unexpected keyword `season`).

- [ ] **Step 3: Wire the scheduler entry**

Replace `fixed_cpsat_scheduler.generate_schedule`:

```python
def generate_schedule(
    league: League,
    seed: int = 0,
    scheduler_config: SchedulerConfig | None = None,
    *,
    season: int,
) -> SchedulerResult:
    """Build matchups, then build the final schedule for `season`."""
    config = scheduler_config or SchedulerConfig()
    weeks = config.league.weeks
    check_weeks(league, weeks)
    check_opening_weeks(league, weeks, config.phase2.opening_nonconference_weeks)
    rivalries = resolve_rivalries(league, config.rivalries)

    logger.info("Phase 1: selecting matchups")
    matchup_plan = FixedCpsatMatchupBuilder(
        league,
        weeks=weeks,
        rivalries=rivalries,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        seed=seed,
    ).build_matchup_plan()

    logger.info(
        "Phase 2: placing games into weeks. This usually takes several "
        "minutes and can take 30 minutes or more.",
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
        workers=config.solver.solver_workers,
    )
    return SchedulerResult(schedule=schedule, matchup_plan=matchup_plan)
```

with `from athc.scheduler.config import SchedulerConfig, check_opening_weeks, check_weeks, resolve_rivalries`. Update the module docstring: phase 1 fixes the PNFL's same-place games and any cross-conference rivalry; the rest by the spread line.

`main.py`: pass `season=season` in the `get_scheduler()(...)` call. `tests/unit/scheduler/fixed_cpsat/conftest.py` (`solve_and_report`): add `season=2048` to the `get_scheduler()(...)` call.

- [ ] **Step 4: Run the PCFL tests and time them**

Run: `uv run pytest tests/unit/scheduler/conference_league -q --durations=5`
Expected: PASS. Note the three solve fixture durations. If any exceeds ~15 s, add `pytestmark = pytest.mark.slow` to `test_schedule_rules.py`, and add a module note; otherwise leave them in the default suite.

- [ ] **Step 5: Run everything**

Run: `uv run pytest` — PASS. Run ruff check / ruff format / pyright — clean.

- [ ] **Step 6: Test matrix**

Create `tests/unit/scheduler/conference_league/test-matrix-conference-league.md`:

```markdown
# scheduler — Test Matrix: League Without Divisions (PCFL)

Cases for the conference-only format, end to end on solved schedules (`conftest.py`: even season, odd season, rotation off). Convention in [../../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-2-schedule.md](../../../../docs/scheduler/phase-2-schedule.md).

| Case | Expected | Test | Status |
|---|---|---|---|
| Structure | 108 games, 9 a week, 12 per team, 6 home | `test_structure` | ☑ |
| Inventory realized | matches phase 1 | `test_matches_phase_one_inventory` | ☑ |
| Conference round robin | every conference team once, 4 home / 4 away | `test_conference_round_robin_four_home_four_away` | ☑ |
| Non-conference hosting | 4 games, 2 home / 2 away | `test_nonconference_two_home_two_away` | ☑ |
| Opening weeks | weeks 1-3 all non-conference | `test_opening_weeks_are_all_nonconference` | ☑ |
| Idle-team game | weeks 4-12 hold one cross-conference game each | `test_later_weeks_hold_exactly_one_cross_conference_game` | ☑ |
| Home/away streaks | ≤3 straight | `test_max_three_consecutive_home_or_away` | ☑ |
| Conference-sequence streaks | ≤2 straight along conference games | `test_max_two_consecutive_conference_home_or_away` | ☑ |
| Rivalry week | week 12 is exactly the nine pairs | `test_final_week_is_rivalry_week` | ☑ |
| Rivalry hosting | even: first listed hosts; odd: second; off: free | `test_even_season_first_listed_hosts`, `test_odd_season_second_listed_hosts`, `test_rotation_off_still_plays_rivalries_in_the_final_week` | ☑ |
| Report | builds for a division-less league | `test_report_builds_for_a_league_without_divisions` | ☑ |
```

- [ ] **Step 7: Commit**

```bash
git add -A src tests
git commit -m "scheduler: the scheduler takes the season and applies the league's weeks and rivalries; PCFL end-to-end tests"
```

---

### Task 9: Documentation and project meta

**Files:**
- Modify: `docs/scheduler/README.md`, `docs/scheduler/ARCHITECTURE.md`, `docs/scheduler/phase-1-matchups-fixed-cpsat.md`, `docs/scheduler/phase-2-schedule.md`, `tests/unit/scheduler/test-matrix-phase-2-schedule.md`, `CHANGELOG.md`, `STATUS.md`, `WORKLOG.md`

No tests, lint or type runs for doc-only edits.

- [ ] **Step 1: README**

In `docs/scheduler/README.md`, after the "Two-phase model" paragraph add:

```markdown
## League formats

The same two phases serve two league shapes. Which one is in play comes from the league file; the number of weeks from the rules file.

| | PNFL | PCFL |
|---|---|---|
| League file | `[DivisionStandings]` + `[OverallStandings]` | `[ConferenceStandings]` + `[OverallStandings]` |
| Weeks | 16 (`[league] weeks`, the default) | 12 |
| Same-conference games | division rivals twice, rest of the conference once | every conference team once |
| Non-conference | 4-5; two fixed by division place, rest by the SOS line | 4; all by the SOS line (flat by default) |
| Season shape | NFL-style rules ([phase 2](phase-2-schedule.md)) | weeks 1-3 non-conference, one cross-conference game a week after that, rivalry week last |

The PCFL's rules live in `dev/leagues/PCFL/rules/scheduler.toml`; its 2029 league file in `dev/leagues/PCFL/standings/`. Selecting a league from the command line is not wired yet — tests build PCFL schedules directly.
```

In the Config section, extend the rules bullet: `[league] weeks` (even; default 16), the PCFL `[phase2]` keys (`max_consecutive_conference_home_or_away`, `opening_nonconference_weeks`, the three `require_*` toggles for the NFL-pattern home/away rules) and `[rivalries]` (`pairs`, `rotate_home_by_season`); and the league bullet: exactly one of `[DivisionStandings]` / `[ConferenceStandings]`.

- [ ] **Step 2: ARCHITECTURE**

In `docs/scheduler/ARCHITECTURE.md`: in "What this package enforces", replace the league-file bullet with "exactly one of `[DivisionStandings]` (per-division finish order; defines the divisions) or `[ConferenceStandings]` (two conferences of nine; no divisions), plus `[OverallStandings]`"; add a bullet "League-resolved rules: `weeks` must fit the league (structural games < weeks ≤ structural + 9, even); `opening_nonconference_weeks` must leave room for every same-conference game; `[rivalries]` must name every team once with exactly one cross-conference pair. All `ConfigError`." In "Domain": "Each conference has nine teams; a league has four PNFL divisions or none." Update the "Testing" list: add `test_league` (domain, both formats), `test_pnfl_model_fingerprint` (pins both PNFL CP-SAT models; re-pin only with the goldens), and the `conference_league/` folder (PCFL inventory + end-to-end rules; matrix in `test-matrix-conference-league.md`).

- [ ] **Step 3: Phase 1 doc**

In `docs/scheduler/phase-1-matchups-fixed-cpsat.md`: rewrite the intro line as "Structure fixes the same-conference games; the rest of each team's weeks are non-conference. Fixed non-conference games are the PNFL's same-place pairs (a league with divisions) and any cross-conference rivalry; one CP-SAT solve picks the rest along the difficulty line." Under "Fixed by league structure" add "Without divisions: every conference team once (the PCFL: 8 games, leaving 4 non-conference in 12 weeks)." In Validation: "`weeks × 9` total pairings and the league's non-conference total (40 for the PNFL, 36 for the PCFL)".

- [ ] **Step 4: Phase 2 doc**

In `docs/scheduler/phase-2-schedule.md`: after "## Model" add:

```markdown
## Which rules apply

| Rule group | Applies when |
|---|---|
| One game a week, host half the weeks, the phase-1 inventory | always |
| Max consecutive home/away (`max_consecutive_home_or_away`) | always |
| Balanced hosting: each team hosts half its conference games and half its non-conference games (2 of 4, 2-3 of 5, 4 of 8) | always |
| Every divisional rule, the divisional league caps, no back-to-back rematch, the soft objective | the league has divisions |
| 2-4 home in every 6 weeks | `require_home_balance_per_six_weeks` |
| ≤1 three-game home/away streak per team; league caps on such streaks | `require_home_away_streak_caps` (required with divisions) |
| First and last 3 weeks mix home and away | `require_mixed_home_away_at_season_ends` |
| Weeks 1..N hold no same-conference game | `opening_nonconference_weeks` (0 = off) |
| No cap + 1 straight home or away *conference* games, counted along the conference games only | `max_consecutive_conference_home_or_away` (0 = off) |
| Rivalry week: every `[rivalries]` pair meets in the last week; `rotate_home_by_season` makes the first-listed team host in even seasons and the second in odd | `[rivalries]` present |

The PCFL uses the first three rows plus the last three; its rules file turns the three `require_*` toggles off.
```

Change "16 weeks × 9 games" to "`weeks` × 9 games" and "hosts exactly 8" to "hosts `weeks / 2`", and "The final week is all-divisional: 8 of its 9 games" to "... (the most a week can hold: each 5-team division strands one team)".

- [ ] **Step 5: Phase-2 test matrix**

In `tests/unit/scheduler/test-matrix-phase-2-schedule.md` add under Edge:

```markdown
| Rule gating (no divisions) | no `d_`/streak/objective parts; toggles add only when on; window follows the cap | `test_league_without_divisions_has_no_divisional_model_parts`, `test_home_away_toggles_add_constraints_only_when_on`, `test_streak_caps_on_without_divisions_is_allowed`, `test_max_consecutive_window_follows_the_cap` | ☑ |
| Opening non-conference weeks | one constraint per team-week | `test_opening_nonconference_weeks_add_one_constraint_per_team_week` | ☑ |
| Conference-sequence cap | two constraints per window | `test_conference_streak_cap_adds_two_constraints_per_window` | ☑ |
| Rivalry week | one constraint per pair; host pinned by parity; season required | `test_rivalry_week_adds_one_constraint_per_pair`, `test_rivalry_rotation_pins_the_host_by_season_parity`, `test_rivalry_rotation_needs_a_season` | ☑ |
| PNFL model pinned | phase-1 and phase-2 proto hashes unchanged | `test_pnfl_phase_models_are_unchanged` | ☑ |
```

and under Error: `| Streak caps off with divisions | ConfigError | test_streak_caps_off_with_divisions_is_a_config_error | ☑ |`.

- [ ] **Step 6: CHANGELOG, STATUS, WORKLOG**

`CHANGELOG.md` — first line under `## scheduler`:

```markdown
- second league format: a league without divisions (`[ConferenceStandings]`), `[league] weeks`, opening non-conference weeks, a conference-sequence streak cap, rivalry week with home rotation by season; PCFL 2029 data files
```

`STATUS.md` — first bullet under `## scheduler — generate-schedule`:

```markdown
- Two league formats: the PNFL (divisions, 16 weeks) and the PCFL (two
  conferences of nine, 12 weeks, rivalry week). One matchup builder and one
  schedule builder; PNFL-only rules are toggles. The PCFL files are under
  `dev/leagues/PCFL/`; command-line league selection waits on the config rework.
```

`WORKLOG.md` — first entry:

```markdown
- 2026-09-28 — **scheduler**: the scheduler was hard-wired to the PNFL (four
  divisions, 16 weeks). A second league, the PCFL, has two conferences of nine,
  no divisions and 12 weeks with rivalry week last. The league file now takes
  `[ConferenceStandings]` instead of `[DivisionStandings]`, the rules file gains
  `[league] weeks`, three toggles for the NFL-pattern home/away rules, two PCFL
  rules and `[rivalries]`; every divisional rule applies only with divisions. A
  fingerprint test pins the PNFL CP-SAT models so the golden schedule is unchanged.
```

- [ ] **Step 7: Commit**

```bash
git add docs/scheduler tests/unit/scheduler/test-matrix-phase-2-schedule.md CHANGELOG.md STATUS.md WORKLOG.md
git commit -m "scheduler: docs for the second league format"
```

---

### Task 10: Full verification, golden test, hand-off

- [ ] **Step 1: The four commands**

Run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green; coverage ≥ 92%. If `ruff format` changed files, commit them (`scheduler: ruff format`).

- [ ] **Step 2: Slow suite including the golden**

Run: `uv run pytest -m slow tests/integration/test_generate_schedule.py -q` (several minutes).
Expected: PASS — the three golden files byte-match. If it fails on a golden diff, the PNFL model drifted despite the fingerprint (or the report/HTML output changed): do not re-bless; find the change (`ordered_teams` order, report columns, writer text) and fix it.

Run: `uv run pytest -m slow tests/unit/scheduler -q` (the PNFL end-to-end rule tests and report test; long).
Expected: PASS.

- [ ] **Step 3: Whole-branch review**

Dispatch a reviewer on the branch diff (`git diff main...HEAD`) against the spec; fix confirmed findings with the usual test-first cycle; re-run the four commands.

- [ ] **Step 4: Hand-off**

Leave the worktree (`ExitWorktree` with `keep`), then give the user two separate code blocks: the squash-merge + commit, and the worktree removal + branch deletion.

```bash
git merge --squash worktree-pcfl-scheduler
git commit -m "scheduler: second league format (PCFL): conferences without divisions, weeks, rivalry week"
```

```bash
git worktree remove .claude/worktrees/pcfl-scheduler
git branch -D worktree-pcfl-scheduler
```
