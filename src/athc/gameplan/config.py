"""Gameplan config: league `PlayPath` / `PlayPoolRules` + `[gameplan] rule_files`
from `athc.ini`."""

from __future__ import annotations

import configparser
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.config import CONFIG_FILE, config_dir, load_league

SECTION = "gameplan"


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
) -> Config:
    """Assemble the gameplan config.

    `PlayPath` (required) and `PlayPoolRules` (optional playpool rules TOML) come
    from the league section, `rule_files` from `[gameplan]`. The `play_path` /
    `playpool_rules` / `rule_files` overrides win; the league is resolved only when
    a path is still needed. Config file: `config_dir()/athc.ini`.
    """
    league_cfg: dict[str, str] = {}
    if play_path is None:
        league_cfg = load_league(league)  # LeagueError if none

    pp = str(play_path) if play_path is not None else league_cfg.get("PlayPath")
    if not pp:
        raise ConfigFileError(
            "no PlayPath for the league; set PlayPath in the league "
            "section or pass --play-path"
        )
    ppr = (
        str(playpool_rules)
        if playpool_rules is not None
        else league_cfg.get("PlayPoolRules")
    )

    files = tuple(rule_files) if rule_files is not None else _config_rule_files()
    return Config(
        play_path=Path(pp),
        playpool_rules=Path(ppr) if ppr else None,
        rule_files=files,
    )


def _config_rule_files() -> tuple[Path, ...]:
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        try:
            cp.read(path, encoding="utf-8")
        except configparser.Error as e:
            raise ConfigFileError(f"{path}: {e}") from e
    raw = cp.get(SECTION, "rule_files", fallback="")
    return tuple(Path(line.strip()) for line in raw.splitlines() if line.strip())
