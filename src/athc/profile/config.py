"""Profile config: `profile.toml` (or the `profile_rules` list) and the
category labels from the league folder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from athc.config import load_league_config
from athc.fbpro98_play import CategoryLabels

PROFILE_RULES_FILE = "profile.toml"
PROFILE_RULES_KEY = "profile_rules"


@dataclass(frozen=True, slots=True)
class Config:
    rule_files: tuple[Path, ...] = ()
    categories: CategoryLabels = field(default_factory=CategoryLabels)


def load_config(league: str | None = None) -> Config:
    """Rule files for `profile check`: the league folder's `profile_rules` list
    or fixed `profile.toml` (missing -> no rules), and the league's category
    labels. LeagueError when no league can be resolved."""
    cfg = load_league_config(league)
    return Config(
        rule_files=cfg.rule_files(PROFILE_RULES_KEY, PROFILE_RULES_FILE),
        categories=cfg.categories,
    )
