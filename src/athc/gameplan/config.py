"""Gameplan config: `play_path` and `gameplan.toml` (or the `gameplan_rules`
list) from the league folder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from athc.config import LEAGUE_FILE, ConfigFileError, load_league_config
from athc.fbpro98_play import CategoryLabels

GAMEPLAN_RULES_FILE = "gameplan.toml"
GAMEPLAN_RULES_KEY = "gameplan_rules"

__all__ = ["Config", "ConfigFileError", "load_config"]


@dataclass(frozen=True, slots=True)
class Config:
    play_path: Path
    league_file: Path  # the league.toml that sets play_path, for its errors
    rule_files: tuple[Path, ...] = ()
    categories: CategoryLabels = field(default_factory=CategoryLabels)


def load_config(
    league: str | None = None, *, rule_files: Sequence[Path] | None = None
) -> Config:
    """Assemble the gameplan config from the league folder (LeagueError when no
    league can be resolved). `rule_files` replaces the league's gameplan rules
    (`()` for none) for the commands that don't check gameplans."""
    cfg = load_league_config(league)
    play_path = cfg.path("play_path")
    if play_path is None:
        raise ConfigFileError(
            "No play_path for the league. Set play_path in this file.",
            cfg.dir / LEAGUE_FILE,
        )
    files = (
        tuple(rule_files)
        if rule_files is not None
        else cfg.rule_files(GAMEPLAN_RULES_KEY, GAMEPLAN_RULES_FILE)
    )
    return Config(
        play_path=play_path,
        league_file=cfg.dir / LEAGUE_FILE,
        rule_files=files,
        categories=cfg.categories,
    )
