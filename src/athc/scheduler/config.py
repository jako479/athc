from __future__ import annotations

import configparser
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from os import PathLike
from pathlib import Path
from typing import Any

from athc.config import config_dir
from athc.scheduler.domain.league import League, build_league

StrPath = str | PathLike[str]

LEAGUE_FILE = "league.ini"  # actual file is "<season>.league.ini"
SCHEDULER_RULES_FILE = "PNFL.scheduler.toml"  # in the config dir's rules/ folder

# Scheduler tunables; overridable in PNFL.scheduler.toml (missing -> these).
DEFAULT_TIME_LIMIT = 1800.0  # phase-2 (week-placement) solve seconds
DEFAULT_PHASE1_TIME_LIMIT = 60.0  # phase-1 (matchup) solve seconds
DEFAULT_DIFFICULTY_C_SPREAD = 2.5  # Scheduler C: tilt on the 1-9 conference scale
DEFAULT_DIFFICULTY_D_SPREAD = 1.5  # Scheduler D: same tilt, picked games only


class ConfigError(Exception):
    """The config file is missing, or present but invalid."""


@dataclass(frozen=True)
class DifficultyConfig:
    """Non-conference difficulty tilts: `c_spread` covers Scheduler C's whole
    slate; `d_spread` covers Scheduler D's picked games only."""

    c_spread: float = DEFAULT_DIFFICULTY_C_SPREAD
    d_spread: float = DEFAULT_DIFFICULTY_D_SPREAD


@dataclass(frozen=True)
class SolverConfig:
    time_limit: float = DEFAULT_TIME_LIMIT
    phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT


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
    # Divisional sequencing
    max_consecutive_divisional: int = 3
    max_three_game_divisional_streaks: int = 1
    max_non_interleaved_divisional_opponents: int = 2
    max_teams_divisional_weeks_1_and_2: int = 4
    # Divisional density (max divisional games within a span of weeks)
    five_team_max_divisional_in_10: int = 7
    five_team_max_divisional_in_9: int = 6
    four_team_max_divisional_in_8: int = 5
    four_team_max_divisional_in_7: int = 4
    # Divisional front-load caps (max divisional games in the first N weeks)
    five_team_max_divisional_first_6: int = 4
    five_team_max_divisional_first_8: int = 5
    five_team_max_divisional_first_10: int = 6
    four_team_max_divisional_first_6: int = 3
    four_team_max_divisional_first_8: int = 4
    # League-wide caps (prevent per-team rules piling up across teams)
    max_teams_with_home_streak: int = 9
    max_teams_with_away_streak: int = 3
    max_teams_with_divisional_streak: int = 6
    max_teams_at_front_load_max: int = 3
    max_teams_with_two_bunched_rivals: int = 2
    max_close_rematches: int = 3
    # Season ending
    require_final_week_divisional: bool = True
    require_divisional_in_final_two_weeks: bool = True


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
    and the optional `[DivisionStandings]` (per-division finish; both
    schedulers need it). Per-conference 1-9 ranks derive from the order.
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


def find_config_path() -> Path:
    """Scheduler config path, for report provenance (may not exist)."""
    return scheduler_rules_path()


def find_league_path(season: int) -> Path:
    """The `<season>.league.ini` file in the config dir; ConfigError if missing."""
    return _require_season_file(season, LEAGUE_FILE, "league")


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


def _phase2(table: Mapping[str, Any], path: Path) -> Phase2Config:
    defaults = Phase2Config()
    unknown = sorted(set(table) - {f.name for f in fields(defaults)})
    if unknown:
        raise ConfigError(
            f"Config file '{path}': unknown [phase2] key(s): {', '.join(unknown)}."
        )
    values = {}
    for f in fields(defaults):
        default = getattr(defaults, f.name)
        parse = _bool if isinstance(default, bool) else _int
        values[f.name] = parse(table, f.name, default, path)
    return Phase2Config(**values)


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
