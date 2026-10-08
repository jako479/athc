"""Profile config: `profile.toml` (or the `profile_rules` list) from the
league folder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from athc.config import load_league_config

PROFILE_RULES_FILE = "profile.toml"
PROFILE_RULES_KEY = "profile_rules"


@dataclass(frozen=True)
class Config:
    rule_files: tuple[Path, ...] = ()


def load_config(league: str | None = None) -> Config:
    """Rule files for `profile check`: the league folder's `profile_rules` list
    or fixed `profile.toml` (missing -> no rules). LeagueError when no
    league can be resolved."""
    cfg = load_league_config(league)
    return Config(rule_files=cfg.rule_files(PROFILE_RULES_KEY, PROFILE_RULES_FILE))
