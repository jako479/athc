from __future__ import annotations

import configparser
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from os import PathLike
from pathlib import Path
from typing import Any, Final, Literal

from athc.config import STANDINGS_DIR, league_dir
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    League,
    RivalryPair,
    Team,
    build_league,
    lookup_team,
)

StrPath = str | PathLike[str]

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


class ConfigError(Exception):
    """The config file is missing, or present but invalid."""


@dataclass(frozen=True)
class LeagueConfig:
    """League shape the standings file does not carry."""

    weeks: int = DEFAULT_WEEKS


@dataclass(frozen=True)
class DifficultyConfig:
    """Non-conference difficulty tilt: `spread` covers the whole
    non-conference slate."""

    spread: float = DEFAULT_DIFFICULTY_SPREAD


@dataclass(frozen=True)
class SolverConfig:
    time_limit: float = DEFAULT_TIME_LIMIT
    phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT
    solver_workers: SolverWorkers = DEFAULT_SOLVER_WORKERS


@dataclass(frozen=True)
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
    # backstops. See docs/design/research/cpsat-rule-patterns.md.
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


@dataclass(frozen=True)
class RivalriesConfig:
    """Final-week rivalry pairs, as listed (first hosts in even seasons)."""

    pairs: tuple[tuple[str, str], ...] = ()
    rotate_home_by_season: bool = True


@dataclass(frozen=True)
class SchedulerConfig:
    league: LeagueConfig = field(default_factory=LeagueConfig)
    difficulty: DifficultyConfig = field(default_factory=DifficultyConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    phase2: Phase2Config = field(default_factory=Phase2Config)
    rivalries: RivalriesConfig = field(default_factory=RivalriesConfig)


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
            raise ConfigError(f"Config file not found: '{resolved}'.")
        return SchedulerConfig()
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
            solver_workers=_workers(solver, "solver_workers", resolved),
        ),
        phase2=_phase2(data.get("phase2", {}), resolved),
        rivalries=_rivalries(data.get("rivalries"), resolved),
    )


DIVISION_SECTION = "DivisionStandings"
CONFERENCE_SECTION = "ConferenceStandings"


def load_league(path: StrPath) -> League:
    """Read a league from `[OverallStandings]` (overall 1-18 `Order`) plus exactly
    one of `[DivisionStandings]` (per-division teams in finish order -- a league
    with divisions)
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
            f"Config file '{resolved}' must have exactly one of the "
            f"[{DIVISION_SECTION}] and [{CONFERENCE_SECTION}] sections."
        )
    _require_section(cp, resolved, "OverallStandings")
    overall = _required_multiline(cp, resolved, "OverallStandings", "Order")
    section = DIVISION_SECTION if has_divisions else CONFERENCE_SECTION
    standings = {key: _parse_multiline(cp, section, key) for key in cp.options(section)}
    try:
        return build_league(standings, overall, divisions=has_divisions)
    except ValueError as error:
        raise ConfigError(
            f"Config file '{resolved}' has invalid league data: {error}"
        ) from error


def find_league_path(league: str, season: int) -> Path:
    """`standings/<season>.league.ini` in the league's folder; ConfigError if
    missing, LeagueError when the league has no folder."""
    path = league_dir(league) / STANDINGS_DIR / f"{season}.league.ini"
    if not path.is_file():
        raise ConfigError(
            f"No standings file for {league} season {season}. Expected:\n  {path}\n"
            f"Run 'athc config path' to find the config dir, then add the file."
        )
    return path


def _number(section: Mapping[str, Any], key: str, default: float, path: Path) -> float:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"Config file '{path}': '{key}' must be a number.")
    return float(value)


def _bool(section: Mapping[str, Any], key: str, default: bool, path: Path) -> bool:
    if key not in section:
        return default
    value = section[key]
    if not isinstance(value, bool):
        raise ConfigError(f"Config file '{path}': '{key}' must be true or false.")
    return value


def _int(section: Mapping[str, Any], key: str, default: int, path: Path) -> int:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Config file '{path}': '{key}' must be an integer.")
    return value


def _workers(section: Mapping[str, Any], key: str, path: Path) -> SolverWorkers:
    if key not in section:
        return DEFAULT_SOLVER_WORKERS
    value = section[key]
    if value == AUTO_WORKERS:
        return AUTO_WORKERS
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigError(
            f"Config file '{path}': '{key}' must be a positive integer or "
            f'"{AUTO_WORKERS}".'
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
        raise ConfigError(
            f"Config file '{path}': unknown [{name}] key(s): {', '.join(unknown)}."
        )


def _phase2(table: Mapping[str, Any], path: Path) -> Phase2Config:
    defaults = Phase2Config()
    _reject_unknown(table, {f.name for f in fields(defaults)}, "phase2", path)
    values = {}
    for f in fields(defaults):
        default = getattr(defaults, f.name)
        parse = _bool if isinstance(default, bool) else _int
        values[f.name] = parse(table, f.name, default, path)
        if f.name in _NON_NEGATIVE_PHASE2_KEYS and values[f.name] < 0:
            raise ConfigError(
                f"Config file '{path}': '{f.name}' must be 0 (off) or positive."
            )
    return Phase2Config(**values)


def _league(table: Mapping[str, Any], path: Path) -> LeagueConfig:
    _reject_unknown(table, {"weeks"}, "league", path)
    weeks = _int(table, "weeks", DEFAULT_WEEKS, path)
    if weeks <= 0 or weeks % 2:
        raise ConfigError(
            f"Config file '{path}': 'weeks' must be a positive even integer."
        )
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


def _read_config(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.optionxform = str  # type: ignore[assignment]
    try:
        cp.read(path, encoding="utf-8")
    except configparser.Error as error:
        raise ConfigError(f"Config file '{path}' is not valid INI: {error}") from error
    return cp


def _require_section(cp: configparser.ConfigParser, path: Path, section: str) -> None:
    if not cp.has_section(section):
        raise ConfigError(
            f"Config file '{path}' is missing the required [{section}] section."
        )


def _required_multiline(
    cp: configparser.ConfigParser, path: Path, section: str, key: str
) -> tuple[str, ...]:
    if not cp.has_option(section, key):
        raise ConfigError(
            f"Config file '{path}' is missing required setting '{key}' in [{section}]."
        )
    values = _parse_multiline(cp, section, key)
    if not values:
        raise ConfigError(f"Config file '{path}' has an empty '{key}' in [{section}].")
    return values


def _parse_multiline(
    cp: configparser.ConfigParser, section: str, key: str
) -> tuple[str, ...]:
    raw = cp.get(section, key, fallback="")
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


# --- Checks that need both the rules and the league --------------------------

MAX_NONCONFERENCE_GAMES = TEAMS_PER_CONFERENCE  # each other-conference team once


def check_weeks(league: League, weeks: int) -> None:
    """`weeks` must be even and fit every team: more than its structural games,
    at most those plus one game against each other-conference team."""
    if weeks <= 0 or weeks % 2:
        raise ConfigError(
            f"[league] weeks must be a positive even integer; got {weeks}."
        )
    for team in league.teams:
        structural = league.structural_games(team)
        if not structural < weeks <= structural + MAX_NONCONFERENCE_GAMES:
            raise ConfigError(
                f"[league] weeks = {weeks} does not fit {team.metro}: it plays "
                f"{structural} structural games, so weeks must be "
                f"{structural + 1}..{structural + MAX_NONCONFERENCE_GAMES}."
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
            f"[phase2] opening_nonconference_weeks = {opening_weeks} leaves "
            f"{weeks - opening_weeks} weeks for {same_conference} same-conference "
            f"games, but a week holds at most {per_week}."
        )


def resolve_rivalries(
    league: League, rivalries: RivalriesConfig
) -> tuple[RivalryPair, ...]:
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
            teams = (
                lookup_team(league.teams, first),
                lookup_team(league.teams, second),
            )
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
