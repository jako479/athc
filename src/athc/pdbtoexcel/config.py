"""convert-pdb config: `[convert-pdb]` from athc.ini, plus the default category order.

`play_path` / `playpool_rules` locate the play pool used to classify and (optionally)
tag plays. Category order — the row sort order and the Options sheet — defaults
to the game's own category vocabulary; nothing league-specific is baked in.
"""

from __future__ import annotations

import configparser
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from athc.config import CONFIG_FILE, config_dir, resolve_path
from athc.fbpro98_play import DefensiveCategory, OffensiveCategory
from athc.pdbtoexcel.pdb import PLAY_DATA

PACKAGE_DIR = Path(__file__).resolve().parent
SECTION = "convert-pdb"

type CategoryOrder = Mapping[PLAY_DATA.PLAY_TYPE, list[str]]


class ConfigFileError(ValueError):
    """Raised when the convert-pdb config INI cannot be read or parsed."""


@dataclass(frozen=True)
class Config:
    play_path: str = ""
    playpool_rules: Path | None = None  # optional; classifies + tags plays
    calculate_total_stats: bool = True
    calculate_percentages: bool = True
    include_category_worksheets: bool = False
    exclude_sacks_from_pass_attempts: bool = True
    category_order: CategoryOrder = field(
        default_factory=lambda: default_category_order()
    )


def get_runtime_path(filename: str) -> Path:
    return PACKAGE_DIR / "resources" / filename


def default_category_order() -> CategoryOrder:
    """Game category names per side, in the game's own (code) order — the default
    sort order and Options-sheet listing. Offense splits into run vs pass."""
    run = [c.long for c in OffensiveCategory if c.is_run]
    passing = [c.long for c in OffensiveCategory if c.is_pass]
    defense = [c.long for c in DefensiveCategory if c.is_run or c.is_pass]
    return {
        PLAY_DATA.PLAY_TYPE.RUN: run,
        PLAY_DATA.PLAY_TYPE.PASS: passing,
        PLAY_DATA.PLAY_TYPE.DEFENSE: defense,
    }


def load_config(
    *,
    play_path: str | None = None,
    playpool_rules: Path | None = None,
) -> Config:
    """Load convert-pdb config from `config_dir()/athc.ini` (set `ATHC_CONFIG_DIR` to
    override). Missing file/section/key → defaults. `play_path` / `playpool_rules`
    (CLI overrides) win over the file.
    """
    cp = _read(config_dir() / CONFIG_FILE)
    raw_rules = cp.get(SECTION, "playpool_rules", fallback="").strip()
    return Config(
        play_path=play_path or cp.get(SECTION, "play_path", fallback=""),
        playpool_rules=playpool_rules
        if playpool_rules is not None  # CLI override: keep CWD-relative
        else (resolve_path(raw_rules) if raw_rules else None),
        calculate_total_stats=cp.getboolean(
            SECTION, "calculate_total_stats", fallback=True
        ),
        calculate_percentages=cp.getboolean(
            SECTION, "calculate_percentages", fallback=True
        ),
        include_category_worksheets=cp.getboolean(
            SECTION, "include_category_worksheets", fallback=False
        ),
        exclude_sacks_from_pass_attempts=cp.getboolean(
            SECTION, "exclude_sacks_from_pass_attempts", fallback=True
        ),
    )


def _read(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    try:
        cp.read(path, encoding="utf-8")
    except configparser.Error as e:
        raise ConfigFileError(f"{path}: {e}") from e
    return cp
