from __future__ import annotations

import configparser
import os
from pathlib import Path

from platformdirs import user_config_path

CONFIG_FILE = "athc.ini"


def config_dir() -> Path:
    if override := os.environ.get("ATHC_CONFIG_DIR"):
        return Path(override)
    return user_config_path("athc", appauthor=False, ensure_exists=False)


def config_file() -> Path:
    """Path to the athc settings file (it need not exist)."""
    return config_dir() / CONFIG_FILE


def load_config() -> dict[str, dict[str, str]]:
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        cp.read(path, encoding="utf-8")
    return {section: dict(cp[section]) for section in cp.sections()}


class LeagueError(ValueError):
    """Raised when no league can be resolved for a league-specific tool."""


class _CaseSensitiveParser(configparser.ConfigParser):
    """Keep key case (PlayPath, not playpath) so returned keys match the ini."""

    def optionxform(self, optionstr: str) -> str:
        return optionstr


def load_league(league: str | None = None) -> dict[str, str]:
    """Resolve the league and return its config section (with `%(key)s` resolved).

    Reads `config_dir()/athc.ini` (set `ATHC_CONFIG_DIR` to override). Priority:
    `league` arg → `ATHC_LEAGUE` env → `[athc] default_league`. Raises LeagueError
    if none resolves or the named league has no section.
    """
    path = config_dir() / CONFIG_FILE
    cp = _CaseSensitiveParser()  # BasicInterpolation: %(LeagueRoot)s works
    if path.is_file():
        cp.read(path, encoding="utf-8")
    name = (
        league
        or os.environ.get("ATHC_LEAGUE")
        or cp.get("athc", "default_league", fallback=None)
    )
    if not name:
        leagues = ", ".join(
            s.removeprefix("league.") for s in cp.sections() if s.startswith("league.")
        )
        hint = f" Configured leagues: {leagues}." if leagues else ""
        raise LeagueError(
            "no league selected; use --league, ATHC_LEAGUE, or "
            f"[athc] default_league.{hint}"
        )
    section = f"league.{name}"
    if not cp.has_section(section):
        raise LeagueError(f"league '{name}' has no [{section}] section in {path}")
    return dict(cp[section])
