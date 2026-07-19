from __future__ import annotations

import configparser
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from os import PathLike
from pathlib import Path
from typing import Any

from athc.config import config_dir
from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.domain.league import League, build_league

StrPath = str | PathLike[str]

LEAGUE_FILE = "league.ini"  # actual file is "<season>.league.ini"
HISTORY_FILE = "nonconf_history.json"  # actual file is "<season>.nonconf_history.json"
SCHEDULER_RULES_FILE = "PNFL.scheduler.toml"  # in the config dir's rules/ folder

# Scheduler tunables; overridable in PNFL.scheduler.toml (missing -> these).
DEFAULT_TIME_LIMIT = 1800.0  # phase-2 (week-placement) solve seconds
DEFAULT_PHASE1_TIME_LIMIT = 60.0  # phase-1 (matchup) solve seconds
DEFAULT_DIFFICULTY_SPREAD = 3.19  # linear trend ends 9.5 -/+ spread on the 1-18 scale
DEFAULT_DIFFICULTY_AMPLITUDE = 0.30  # sine height on that trend (0 = straight line)
DEFAULT_DIFFICULTY_PERIOD = 8.0  # sine period in ranks (shelf spacing)
DEFAULT_DIFFICULTY_C_SPREAD = 1.5  # Scheduler C: tilt on the 1-9 conference scale
DEFAULT_DIFFICULTY_D_SPREAD = 1.5  # Scheduler D: same tilt, picked games only


class ConfigError(Exception):
    """The config file is missing, or present but invalid."""


@dataclass(frozen=True)
class DifficultyConfig:
    """Non-conference difficulty knobs. `spread`/`amplitude`/`period` shape
    Scheduler B's curve; `c_spread` tilts Scheduler C's line; `d_spread`
    tilts Scheduler D's (picked games only)."""

    spread: float = DEFAULT_DIFFICULTY_SPREAD
    amplitude: float = DEFAULT_DIFFICULTY_AMPLITUDE
    period: float = DEFAULT_DIFFICULTY_PERIOD
    c_spread: float = DEFAULT_DIFFICULTY_C_SPREAD
    d_spread: float = DEFAULT_DIFFICULTY_D_SPREAD


@dataclass(frozen=True)
class SolverConfig:
    time_limit: float = DEFAULT_TIME_LIMIT
    phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT


@dataclass(frozen=True)
class Phase2Config:
    """Phase-2 (week-placement) rule amounts; defaults are the current values.

    Only amounts are configurable -- not the rules themselves, nor league or
    conference sizes.
    """

    # Home/away sequencing
    max_consecutive_home_or_away: int = 3
    min_home_per_six_weeks: int = 2
    max_home_per_six_weeks: int = 4
    max_three_game_home_away_streaks: int = 1
    # Divisional sequencing
    max_consecutive_divisional: int = 3
    max_three_game_divisional_streaks: int = 1
    max_non_interleaved_divisional_opponents: int = 2
    # Divisional density (max divisional games within a span of weeks)
    five_team_max_divisional_in_10: int = 7
    five_team_max_divisional_in_9: int = 6
    four_team_max_divisional_in_8: int = 5
    four_team_max_divisional_in_7: int = 3
    # Divisional games in the second half of the season
    five_team_second_half_divisional_min: int = 4
    four_team_second_half_divisional_min: int = 3
    # Conference cross-division home games hosted
    five_team_conference_home: int = 2
    four_team_conference_home_min: int = 2
    four_team_conference_home_max: int = 3
    # Non-conference home games hosted
    five_team_nonconference_home: int = 2
    four_team_nonconference_home_min: int = 2
    four_team_nonconference_home_max: int = 3
    # Week 16 / late season
    week_16_divisional_games: int = 8
    min_late_divisional_games: int = 1


@dataclass(frozen=True)
class SchedulerConfig:
    difficulty: DifficultyConfig = field(default_factory=DifficultyConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    phase2: Phase2Config = field(default_factory=Phase2Config)


def scheduler_rules_path() -> Path:
    """The scheduler tunables file (may not exist; values then default).

    Set `ATHC_CONFIG_DIR` to override the config dir.
    """
    return config_dir() / "rules" / SCHEDULER_RULES_FILE


def load_scheduler_config() -> SchedulerConfig:
    """Read scheduler tunables from `rules/PNFL.scheduler.toml`, defaulting when
    the file or any key is absent. Invalid TOML or a non-numeric value errors."""
    path = scheduler_rules_path()
    if not path.is_file():
        return SchedulerConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"Config file '{path}' is not valid TOML: {error}") from error
    difficulty = data.get("difficulty", {})
    solver = data.get("solver", {})
    phase2 = data.get("phase2", {})
    return SchedulerConfig(
        difficulty=DifficultyConfig(
            spread=_number(difficulty, "spread", DEFAULT_DIFFICULTY_SPREAD, path),
            amplitude=_number(
                difficulty, "amplitude", DEFAULT_DIFFICULTY_AMPLITUDE, path
            ),
            period=_number(difficulty, "period", DEFAULT_DIFFICULTY_PERIOD, path),
            c_spread=_number(difficulty, "c_spread", DEFAULT_DIFFICULTY_C_SPREAD, path),
            d_spread=_number(difficulty, "d_spread", DEFAULT_DIFFICULTY_D_SPREAD, path),
        ),
        solver=SolverConfig(
            time_limit=_number(solver, "time_limit", DEFAULT_TIME_LIMIT, path),
            phase1_time_limit=_number(
                solver, "phase1_time_limit", DEFAULT_PHASE1_TIME_LIMIT, path
            ),
        ),
        phase2=_phase2(phase2, path),
    )


def load_league(path: StrPath) -> League:
    """Read a league from `[Divisions]`, `[Standings]` (overall 1-18 `Order`),
    and the optional `[DivisionStandings]` (per-division finish; Scheduler C).

    All schedulers use the overall order; the per-conference 1-9 ranks are
    derived from it.
    """
    resolved = Path(path)
    if not resolved.is_file():
        raise ConfigError(f"Config file not found: '{resolved}'.")
    cp = _read_config(resolved)
    _require_section(cp, resolved, "Divisions")
    _require_section(cp, resolved, "Standings")
    divisions = {
        key: _parse_multiline(cp, "Divisions", key) for key in cp.options("Divisions")
    }
    overall = _required_multiline(cp, resolved, "Standings", "Order")
    division_standings = (
        {
            key: _parse_multiline(cp, "DivisionStandings", key)
            for key in cp.options("DivisionStandings")
        }
        if cp.has_section("DivisionStandings")
        else None
    )
    try:
        return build_league(
            divisions,
            overall_ranking=overall,
            division_standings=division_standings,
        )
    except ValueError as error:
        raise ConfigError(
            f"Config file '{resolved}' has invalid league data: {error}"
        ) from error


def load_history(path: StrPath, league: League) -> NonConfHistory:
    """Load non-conference history and check it against the league teams.

    Empty history if the file is absent. Invalid JSON, bad data, or teams that
    don't match the league raise ConfigError.
    """
    resolved = Path(path)
    try:
        history = NonConfHistory.load(resolved)
        history.validate_teams(league)
    except ValueError as error:
        raise ConfigError(f"History file '{resolved}' is invalid: {error}") from error
    return history


def find_config_path() -> Path:
    """Scheduler config path, for report provenance (may not exist)."""
    return scheduler_rules_path()


def find_league_path(season: int) -> Path:
    """The `<season>.league.ini` file in the config dir; ConfigError if missing."""
    return _require_season_file(season, LEAGUE_FILE, "league")


def find_history_path(season: int) -> Path:
    """The season's `<season>.nonconf_history.json`; ConfigError if missing."""
    return _require_season_file(season, HISTORY_FILE, "non-conference history")


def _require_season_file(season: int, suffix: str, label: str) -> Path:
    path = config_dir() / f"{season}.{suffix}"
    if not path.is_file():
        raise ConfigError(
            f"No {label} file for season {season}. Expected:\n  {path}\n"
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


def _int(section: Mapping[str, Any], key: str, default: int, path: Path) -> int:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Config file '{path}': '{key}' must be an integer.")
    return value


def _phase2(table: Mapping[str, Any], path: Path) -> Phase2Config:
    defaults = Phase2Config()
    unknown = sorted(set(table) - {f.name for f in fields(defaults)})
    if unknown:
        raise ConfigError(
            f"Config file '{path}': unknown [phase2] key(s): {', '.join(unknown)}."
        )
    return Phase2Config(
        **{
            f.name: _int(table, f.name, getattr(defaults, f.name), path)
            for f in fields(defaults)
        }
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
