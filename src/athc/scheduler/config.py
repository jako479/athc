from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from os import PathLike
from pathlib import Path
from typing import Any, Final, Literal

from athc.config import league_dir
from athc.errors import (
    ConfigFileError,
    missing_reason,
    reason_of,
    sentence,
    toml_reason,
)
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    League,
    RivalryPair,
    Team,
    lookup_team,
)

StrPath = str | PathLike[str]

# `[renames.<season>]` tables: the upcoming season -> each renamed team's
# previous name -> its new name.
type Renames = Mapping[int, Mapping[str, str]]

SCHEDULER_RULES_FILE = "scheduler.toml"  # in the league folder
DEFAULT_WEEKS = 16  # regular-season weeks when the rules file sets none

# Scheduler tunables; overridable in scheduler.toml (missing -> these).
# Both phases run multithreaded (interleave_search) and stop on deterministic
# time, not wall-clock seconds.
DEFAULT_TIME_LIMIT = 300.0  # phase-2 (week-placement) solve, deterministic time
DEFAULT_PHASE1_TIME_LIMIT = 120.0  # phase-1 (matchup) solve, deterministic time
DEFAULT_DIFFICULTY_SPREAD = 2.5  # difficulty tilt on the 1-9 conference scale

# Parallel search width for both phases: a worker count, or "auto" for this
# machine's fast threads minus two (see cpu.py). CP-SAT interleave search is
# reproducible only at a FIXED worker count -- the result changes with the count
# -- so the same seed gives the same matchups and schedule only at the same
# count. "auto" therefore varies by machine; the report shows the count used,
# and setting that number reproduces the schedule anywhere. Not CLI-overridable.
AUTO_WORKERS: Final = "auto"
type SolverWorkers = int | Literal["auto"]
DEFAULT_SOLVER_WORKERS: SolverWorkers = AUTO_WORKERS


@dataclass(frozen=True, slots=True)
class LeagueConfig:
    """League shape the league files do not carry."""

    weeks: int = DEFAULT_WEEKS


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    """Non-conference difficulty tilt: `spread` covers the whole
    non-conference slate."""

    spread: float = DEFAULT_DIFFICULTY_SPREAD


@dataclass(frozen=True, slots=True)
class SolverConfig:
    time_limit: float = DEFAULT_TIME_LIMIT
    phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT
    solver_workers: SolverWorkers = DEFAULT_SOLVER_WORKERS


@dataclass(frozen=True, slots=True)
class Phase2Config:
    """Phase-2 (week-placement) rule amounts and toggles; defaults are the
    current values. The rules themselves and league/conference sizes are fixed.
    """

    # Home/away sequencing
    max_consecutive_home_or_away: int = 3
    min_home_per_six_weeks: int = 2
    max_home_per_six_weeks: int = 4
    max_three_game_home_away_streaks: int = 1
    # Conference-sequence streak cap (0 = off): along a team's conference games,
    # ignoring non-conference games between them.
    max_consecutive_conference_home_or_away: int = 0
    # Weeks 1..N hold no same-conference game (0 = off).
    opening_nonconference_weeks: int = 0
    # NFL-pattern home/away rules; a league without them turns these off.
    require_home_balance_per_six_weeks: bool = True
    require_home_away_streak_caps: bool = True
    require_mixed_home_away_at_season_ends: bool = True
    # Divisional sequencing
    max_consecutive_divisional: int = 3
    max_three_game_divisional_streaks: int = 1
    max_non_interleaved_divisional_opponents: int = 2
    max_teams_divisional_weeks_1_and_2: int = 4
    # Divisional density (max divisional games within a span of weeks)
    five_team_max_divisional_in_9: int = 6
    four_team_max_divisional_in_7: int = 4
    # Divisional front-load caps (max divisional games in the first N weeks)
    five_team_max_divisional_first_5: int = 3
    five_team_max_divisional_first_6: int = 4
    five_team_max_divisional_first_8: int = 5
    five_team_max_divisional_first_10: int = 6
    four_team_max_divisional_first_4: int = 2
    four_team_max_divisional_first_8: int = 3
    four_team_max_divisional_first_10: int = 4
    # Cap on teams opening weeks 1-2 both divisional (a divisional pair), by size.
    four_team_max_teams_open_divisional_pair: int = 1
    five_team_max_teams_open_divisional_pair: int = 2
    # League-wide caps (prevent per-team rules piling up across teams)
    max_teams_with_home_streak: int = 9
    max_teams_with_away_streak: int = 3
    max_teams_with_divisional_streak: int = 6
    max_teams_with_two_bunched_rivals: int = 2
    max_close_rematches: int = 3
    # Soft objective: penalize each metric outside its NFL-typical band [lo, hi],
    # weighted by rarity (1/scaled-SD). Bands are the NFL per-season spread scaled
    # to an 18-team league (teams x18/32, rematches x26/48). The hard caps above stay as
    # backstops. See docs/research/cpsat-rule-patterns.md.
    soft_home_streak_lo: int = 5
    soft_home_streak_hi: int = 7
    soft_home_streak_weight: int = 155
    soft_away_streak_lo: int = 0
    soft_away_streak_hi: int = 4
    soft_away_streak_weight: int = 115
    soft_divisional_streak_lo: int = 2
    soft_divisional_streak_hi: int = 6
    soft_divisional_streak_weight: int = 109
    soft_four_team_frontload_lo: int = 3
    soft_four_team_frontload_hi: int = 5
    soft_four_team_frontload_weight: int = 111
    soft_five_team_frontload_lo: int = 2
    soft_five_team_frontload_hi: int = 5
    soft_five_team_frontload_weight: int = 68
    soft_non_interleaved_lo: int = 0
    soft_non_interleaved_hi: int = 3
    soft_non_interleaved_weight: int = 116
    soft_close_rematches_lo: int = 0
    soft_close_rematches_hi: int = 2
    soft_close_rematches_weight: int = 215
    soft_open_weeks_1_2_lo: int = 0
    soft_open_weeks_1_2_hi: int = 4
    soft_open_weeks_1_2_weight: int = 100
    # Season ending
    require_final_week_divisional: bool = True
    require_divisional_in_final_two_weeks: bool = True


@dataclass(frozen=True, slots=True)
class RivalriesConfig:
    """Final-week rivalry pairs, as listed (first hosts in even seasons)."""

    pairs: tuple[tuple[str, str], ...] = ()
    rotate_home_by_season: bool = True


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    league: LeagueConfig = field(default_factory=LeagueConfig)
    difficulty: DifficultyConfig = field(default_factory=DifficultyConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    phase2: Phase2Config = field(default_factory=Phase2Config)
    rivalries: RivalriesConfig = field(default_factory=RivalriesConfig)
    renames: Renames = field(default_factory=dict)
    # The scheduler.toml these came from (or would have), so the checks that
    # need the league too can name it; where a value came from is not a value.
    source: Path | None = field(default=None, compare=False)


def scheduler_rules_path(league: str) -> Path:
    """The league's scheduler tunables file, `scheduler.toml` in its league folder
    (may not exist; values then default). LeagueError when the league has no
    folder."""
    return league_dir(league) / SCHEDULER_RULES_FILE


def load_scheduler_config(path: StrPath, *, required: bool = True) -> SchedulerConfig:
    """Read scheduler tunables from `path`, defaulting any absent key. A missing
    file errors when `required`, else gives every default (the league's rules
    file is optional). Invalid TOML or a bad value errors."""
    resolved = Path(path)
    if not resolved.is_file():
        if required:
            raise ConfigFileError(missing_reason(resolved), resolved)
        return SchedulerConfig(source=resolved)
    try:
        data = tomllib.loads(resolved.read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise ConfigFileError(reason_of(error), resolved) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigFileError(toml_reason(error), resolved) from error
    difficulty = data.get("difficulty", {})
    solver = data.get("solver", {})
    return SchedulerConfig(
        league=_league(data.get("league", {}), resolved),
        difficulty=DifficultyConfig(
            spread=_number(
                difficulty, "difficulty", "spread", DEFAULT_DIFFICULTY_SPREAD, resolved
            ),
        ),
        solver=SolverConfig(
            time_limit=_positive_number(
                solver, "solver", "time_limit", DEFAULT_TIME_LIMIT, resolved
            ),
            phase1_time_limit=_positive_number(
                solver,
                "solver",
                "phase1_time_limit",
                DEFAULT_PHASE1_TIME_LIMIT,
                resolved,
            ),
            solver_workers=_workers(solver, "solver_workers", resolved),
        ),
        phase2=_phase2(data.get("phase2", {}), resolved),
        rivalries=_rivalries(data.get("rivalries"), resolved),
        renames=_renames(data.get("renames"), resolved),
        source=resolved,
    )


def _number(
    section: Mapping[str, Any], name: str, key: str, default: float, path: Path
) -> float:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigFileError(f"[{name}] {key}: Must be a number.", path)
    return float(value)


def _positive_number(
    section: Mapping[str, Any], name: str, key: str, default: float, path: Path
) -> float:
    # A solver budget of 0 or less finds nothing; say so before any solve.
    value = _number(section, name, key, default, path)
    if value <= 0:
        raise ConfigFileError(f"[{name}] {key}: Must be a positive number.", path)
    return value


def _bool(
    section: Mapping[str, Any], name: str, key: str, default: bool, path: Path
) -> bool:
    if key not in section:
        return default
    value = section[key]
    if not isinstance(value, bool):
        raise ConfigFileError(f"[{name}] {key}: Must be true or false.", path)
    return value


def _int(
    section: Mapping[str, Any], name: str, key: str, default: int, path: Path
) -> int:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigFileError(f"[{name}] {key}: Must be an integer.", path)
    return value


def _workers(section: Mapping[str, Any], key: str, path: Path) -> SolverWorkers:
    if key not in section:
        return DEFAULT_SOLVER_WORKERS
    value = section[key]
    if value == AUTO_WORKERS:
        return AUTO_WORKERS
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigFileError(
            f'[solver] {key}: Must be a positive integer or "{AUTO_WORKERS}".', path
        )
    return value


_NON_NEGATIVE_PHASE2_KEYS = frozenset(
    {"max_consecutive_conference_home_or_away", "opening_nonconference_weeks"}
)


def _reject_unknown(
    table: Mapping[str, Any], known: set[str], name: str, path: Path
) -> None:
    unknown = sorted(set(table) - known)
    if unknown:
        names, valid = ", ".join(unknown), ", ".join(sorted(known))
        raise ConfigFileError(
            f"[{name}]: Unknown key(s): {names}. Valid: {valid}.", path
        )


def _phase2(table: Mapping[str, Any], path: Path) -> Phase2Config:
    defaults = Phase2Config()
    _reject_unknown(table, {f.name for f in fields(defaults)}, "phase2", path)
    values = {}
    for f in fields(defaults):
        default = getattr(defaults, f.name)
        parse = _bool if isinstance(default, bool) else _int
        values[f.name] = parse(table, "phase2", f.name, default, path)
        if f.name in _NON_NEGATIVE_PHASE2_KEYS and values[f.name] < 0:
            raise ConfigFileError(
                f"[phase2] {f.name}: Must be 0 (off) or positive.", path
            )
    return Phase2Config(**values)


def _league(table: Mapping[str, Any], path: Path) -> LeagueConfig:
    _reject_unknown(table, {"weeks"}, "league", path)
    weeks = _int(table, "league", "weeks", DEFAULT_WEEKS, path)
    if weeks <= 0 or weeks % 2:
        raise ConfigFileError("[league] weeks: Must be a positive even integer.", path)
    return LeagueConfig(weeks=weeks)


def _rivalries(table: Mapping[str, Any] | None, path: Path) -> RivalriesConfig:
    if table is None:
        return RivalriesConfig()
    _reject_unknown(table, {"pairs", "rotate_home_by_season"}, "rivalries", path)
    raw = table.get("pairs")
    if not isinstance(raw, list) or not raw:
        raise ConfigFileError("[rivalries] pairs: Must be a non-empty list.", path)
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or not all(isinstance(name, str) and name.strip() for name in entry)
        ):
            raise ConfigFileError(
                "[rivalries] pairs: Each pair must be two team names, "
                f"got {_plain(entry)}.",
                path,
            )
        first, second = (name.strip() for name in entry)
        if first == second:
            raise ConfigFileError(
                f"[rivalries] pairs: A pair names the same team twice: {first!r}.",
                path,
            )
        pairs.append((first, second))
    return RivalriesConfig(
        pairs=tuple(pairs),
        rotate_home_by_season=_bool(
            table, "rivalries", "rotate_home_by_season", True, path
        ),
    )


def _renames(value: object, path: Path) -> dict[int, dict[str, str]]:
    """`[renames.<season>]` tables: each key a previous team name, each value
    the team's name in that season."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigFileError("[renames]: Must be a table.", path)
    renames: dict[int, dict[str, str]] = {}
    for key, table in value.items():
        if not (isinstance(key, str) and key.isdecimal()):
            raise ConfigFileError(
                f"[renames] {key}: Must be a season year, e.g. 2048.", path
            )
        name = f"renames.{key}"
        if not isinstance(table, Mapping):
            raise ConfigFileError(f"[{name}]: Must be a table.", path)
        entries: dict[str, str] = {}
        for old, new in table.items():
            old = str(old).strip()
            if not old:
                raise ConfigFileError(f"[{name}]: A team name is blank.", path)
            if not isinstance(new, str) or not new.strip():
                raise ConfigFileError(f"[{name}] {old}: Must be a team name.", path)
            new = new.strip()
            if new == old:
                raise ConfigFileError(
                    f"[{name}] {old}: Renames the team to itself.", path
                )
            if old in entries:
                raise ConfigFileError(f"[{name}] {old}: Listed twice.", path)
            if new in entries.values():
                raise ConfigFileError(f"[{name}]: Two teams renamed to {new}.", path)
            entries[old] = new
        renames[int(key)] = entries
    return renames


def _plain(value: object) -> str:
    """A TOML value as a user wrote it, without Python's brackets and quotes."""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


# --- Checks that need both the rules and the league --------------------------

MAX_NONCONFERENCE_GAMES = TEAMS_PER_CONFERENCE  # each other-conference team once


def check_weeks(league: League, weeks: int, *, path: Path | None = None) -> None:
    """`weeks` must be even and fit every team: more than its structural games,
    at most those plus one game against each other-conference team."""
    if weeks <= 0 or weeks % 2:
        raise ConfigFileError(
            f"[league] weeks: Must be a positive even integer, got {weeks}.", path
        )
    for team in league.teams:
        structural = league.structural_games(team)
        if not structural < weeks <= structural + MAX_NONCONFERENCE_GAMES:
            raise ConfigFileError(
                f"[league] weeks: Must be {structural + 1}.."
                f"{structural + MAX_NONCONFERENCE_GAMES}, got {weeks}. "
                f"{team.metro} plays {structural} structural games.",
                path,
            )


def check_opening_weeks(
    league: League, weeks: int, opening_weeks: int, *, path: Path | None = None
) -> None:
    """The weeks after the opening non-conference weeks must hold every
    same-conference game (a 9-team conference fits at most 4 a week)."""
    if opening_weeks == 0:
        return
    same_conference = sum(league.structural_games(t) for t in league.teams) // 2
    per_week = sum(TEAMS_PER_CONFERENCE // 2 for _ in league.conferences)
    if (weeks - opening_weeks) * per_week < same_conference:
        raise ConfigFileError(
            f"[phase2] opening_nonconference_weeks: Too many, got {opening_weeks}. "
            f"The other {weeks - opening_weeks} weeks hold at most {per_week} "
            f"same-conference games each, and the league plays {same_conference}.",
            path,
        )


def resolve_rivalries(
    league: League, rivalries: RivalriesConfig, *, path: Path | None = None
) -> tuple[RivalryPair, ...]:
    """Turn the listed name pairs into teams, in listed order: every team once,
    exactly one cross-conference pair (each conference strands one team)."""
    if not rivalries.pairs:
        return ()
    expected = len(league.teams) // 2
    if len(rivalries.pairs) != expected:
        raise ConfigFileError(
            f"[rivalries] pairs: Must list {expected} pairs, "
            f"got {len(rivalries.pairs)}.",
            path,
        )
    pairs: list[RivalryPair] = []
    seen: list[Team] = []
    for first, second in rivalries.pairs:
        try:
            teams = (
                lookup_team(league.teams, first),
                lookup_team(league.teams, second),
            )
        except ValueError as error:
            raise ConfigFileError(
                sentence(f"[rivalries] pairs: {error}"), path
            ) from error
        for team in teams:
            if team in seen:
                raise ConfigFileError(
                    "[rivalries] pairs: Must name every team once; "
                    f"{team.metro} repeats.",
                    path,
                )
            seen.append(team)
        pairs.append(teams)
    cross = sum(1 for a, b in pairs if a.conference != b.conference)
    if cross != 1:
        raise ConfigFileError(
            "[rivalries] pairs: Must have exactly one cross-conference pair, "
            f"got {cross}.",
            path,
        )
    return tuple(pairs)
