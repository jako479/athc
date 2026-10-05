"""Gameplan config: `play_path`, `rules\\gameplan.toml` (or the `gameplan_rules`
list) and `rules\\playpool.toml` from the league folder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.config import LeagueConfig, load_league_config

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
    league: str | None = None,
    *,
    play_path: Path | None = None,
    playpool_rules: Path | None = None,
    rule_files: Sequence[Path] | None = None,
    play_path_option: str | None = "--play-path",
) -> Config:
    """Assemble the gameplan config from the league folder.

    The `play_path` / `playpool_rules` / `rule_files` overrides win and stay
    CWD-relative; the league is resolved only while a value still comes from it
    (LeagueError when it can't be), so overriding `play_path` alone keeps the
    league's playpool rules. `play_path_option` is the caller's override flag the
    missing-play_path error suggests; None when it has none.
    """
    cfg: LeagueConfig | None = None

    def league_cfg() -> LeagueConfig:
        nonlocal cfg
        if cfg is None:
            cfg = load_league_config(league)
        return cfg

    if play_path is None:
        resolved = league_cfg().path("play_path")
        if resolved is None:
            hint = f" or pass {play_path_option}" if play_path_option else ""
            raise ConfigFileError(
                "no play_path for the league; set play_path in "
                f"{league_cfg().dir / 'league.ini'}{hint}"
            )
        play_path = resolved

    files = (
        tuple(rule_files)
        if rule_files is not None
        else league_cfg().rule_files(GAMEPLAN_RULES_KEY, GAMEPLAN_RULES_FILE)
    )

    if playpool_rules is None:
        playpool_rules = league_cfg().rules_file(PLAYPOOL_RULES_FILE)

    return Config(play_path=play_path, playpool_rules=playpool_rules, rule_files=files)
