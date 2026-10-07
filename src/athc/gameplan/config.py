"""Gameplan config: `play_path`, `rules\\gameplan.toml` (or the `gameplan_rules`
list) and `rules\\playpool.toml` from the league folder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.config import load_league_config

GAMEPLAN_RULES_FILE = "gameplan.toml"
PLAYPOOL_RULES_FILE = "playpool.toml"
GAMEPLAN_RULES_KEY = "gameplan_rules"


class ConfigFileError(ValueError):
    """Raised when the gameplan config can't be read or lacks a required key."""


@dataclass(frozen=True)
class Config:
    play_path: Path
    playpool_rules: Path | None = None  # optional playpool rules TOML
    rule_files: tuple[Path, ...] = ()


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
            f"no play_path for the league; set play_path in {cfg.dir / 'league.ini'}"
        )
    files = (
        tuple(rule_files)
        if rule_files is not None
        else cfg.rule_files(GAMEPLAN_RULES_KEY, GAMEPLAN_RULES_FILE)
    )
    return Config(
        play_path=play_path,
        playpool_rules=cfg.rules_file(PLAYPOOL_RULES_FILE),
        rule_files=files,
    )
