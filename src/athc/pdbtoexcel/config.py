"""convert-pdb config: the workbook options from `[convert-pdb]` in `athc.ini`
(app-wide, not league data), `play_path` and `playpool.toml` from the
league folder, plus the default category order.

`play_path` / `playpool_rules` locate the play pool used to classify and (optionally)
tag plays; both come from the league folder, and the rules are none when the
league has no `playpool.toml`. Category order — the row sort order and
the Options sheet — defaults to the game's own category vocabulary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from athc.config import ConfigFileError, load_league_config
from athc.config import load_config as load_athc_config
from athc.fbpro98_play import CategoryLabels, DefensiveCategory, OffensiveCategory
from athc.pdbtoexcel.pdb import PLAY_DATA

PACKAGE_DIR = Path(__file__).resolve().parent
PLAYPOOL_RULES_FILE = "playpool.toml"  # in the league folder
SECTION = "convert-pdb"

# The configparser boolean spellings (case-insensitive).
_TRUE = frozenset({"1", "yes", "true", "on"})
_FALSE = frozenset({"0", "no", "false", "off"})

type CategoryOrder = Mapping[PLAY_DATA.PLAY_TYPE, list[str]]


@dataclass(frozen=True)
class Config:
    play_path: str = ""
    playpool_rules: Path | None = None  # optional; classifies + tags plays
    calculate_percentages: bool = True
    include_category_worksheets: bool = False
    exclude_sacks_from_pass_attempts: bool = True
    category_order: CategoryOrder = field(
        default_factory=lambda: default_category_order()
    )
    categories: CategoryLabels = field(default_factory=CategoryLabels)


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


def load_config(league: str | None = None) -> Config:
    """Locate the play pool and read the workbook options.

    `play_path` and the playpool rules come from the league folder (LeagueError
    when no league can be resolved). A league folder without `play_path` yields
    "" and the caller reports it; one without `playpool.toml` yields None.
    The workbook options come from `[convert-pdb]` in `athc.ini`; a missing key
    keeps its default, a non-boolean value is a ConfigFileError."""
    cfg = load_league_config(league)
    play_path = cfg.path("play_path")
    raw = load_athc_config().get(SECTION, {})
    return Config(
        play_path=str(play_path) if play_path else "",
        playpool_rules=cfg.rules_file(PLAYPOOL_RULES_FILE),
        calculate_percentages=_bool(raw, "calculate_percentages", True),
        include_category_worksheets=_bool(raw, "include_category_worksheets", False),
        exclude_sacks_from_pass_attempts=_bool(
            raw, "exclude_sacks_from_pass_attempts", True
        ),
        categories=cfg.categories,
    )


def _bool(raw: Mapping[str, str], key: str, default: bool) -> bool:
    """`raw[key]` as a configparser-style boolean; a missing key is `default`."""
    value = raw.get(key)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ConfigFileError(
        f"[{SECTION}] {key}: expected true or false (yes/no, on/off, 1/0 also "
        f"work), got {value!r}"
    )
