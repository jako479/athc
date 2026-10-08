"""convert-pdb config: the workbook options from `[convert-pdb]` in `athc.ini`
(app-wide, not league data) and, from the league folder, `play_path`, the
category labels, the optional `playpool.toml`, and `pdbtoexcel.toml`.

`play_path` / `playpool_rules` locate the play pool used to classify and
(optionally) tag plays. `pdbtoexcel.toml` is required: `[category_order]` lists,
per side, the categories the workbook shows and the order they sort in (the row
order within each team and the Options sheet lists the sort macros use), named
by the league's labels from `league.toml` (the game name where the league has
none); `[deleted_plays]` names plays removed from the pool whose stat lines are
skipped quietly instead of warning "Play file not found".
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from athc.config import ConfigFileError, load_league_config
from athc.config import load_config as load_athc_config
from athc.fbpro98_play import (
    CategoryLabels,
    DefensiveCategory,
    OffensiveCategory,
    PlayCategory,
)
from athc.pdbtoexcel.pdb import PLAY_DATA

PACKAGE_DIR = Path(__file__).resolve().parent
PLAYPOOL_RULES_FILE = "playpool.toml"  # in the league folder
PDBTOEXCEL_FILE = "pdbtoexcel.toml"  # in the league folder
SECTION = "convert-pdb"

ORDER_TABLE = "category_order"
DELETED_TABLE = "deleted_plays"
DELETED_KEY = "names"
# [category_order] key -> the PDB play type its list orders.
_ORDER_KEYS: Mapping[str, PLAY_DATA.PLAY_TYPE] = {
    "run": PLAY_DATA.PLAY_TYPE.RUN,
    "pass": PLAY_DATA.PLAY_TYPE.PASS,
    "defense": PLAY_DATA.PLAY_TYPE.DEFENSE,
}

# The configparser boolean spellings (case-insensitive).
_TRUE = frozenset({"1", "yes", "true", "on"})
_FALSE = frozenset({"0", "no", "false", "off"})

type CategoryOrder = Mapping[PLAY_DATA.PLAY_TYPE, tuple[PlayCategory, ...]]


def empty_category_order() -> CategoryOrder:
    """No categories listed for any play type (nothing exported)."""
    return dict.fromkeys(_ORDER_KEYS.values(), ())


@dataclass(frozen=True)
class Config:
    play_path: str = ""
    playpool_rules: Path | None = None  # optional; tags plays
    calculate_percentages: bool = True
    include_category_worksheets: bool = False
    exclude_sacks_from_pass_attempts: bool = True
    category_order: CategoryOrder = field(default_factory=empty_category_order)
    categories: CategoryLabels = field(default_factory=CategoryLabels)
    deleted_plays: frozenset[str] = (
        frozenset()
    )  # as written; matched case-insensitively


def get_runtime_path(filename: str) -> Path:
    return PACKAGE_DIR / "resources" / filename


def load_config(league: str | None = None) -> Config:
    """Locate the play pool and read the workbook options.

    `play_path`, the category labels, the playpool rules and `pdbtoexcel.toml`
    come from the league folder (LeagueError when no league can be resolved).
    A league folder without `play_path` yields "" and the caller reports it; one
    without `playpool.toml` yields None; one without `pdbtoexcel.toml` is a
    ConfigFileError. The workbook options come from `[convert-pdb]` in
    `athc.ini`; a missing key keeps its default, a non-boolean value is a
    ConfigFileError."""
    cfg = load_league_config(league)
    play_path = cfg.path("play_path")
    raw = load_athc_config().get(SECTION, {})
    category_order, deleted_plays = read_pdbtoexcel_toml(
        cfg.rules_file_path(PDBTOEXCEL_FILE), cfg.categories
    )
    return Config(
        play_path=str(play_path) if play_path else "",
        playpool_rules=cfg.rules_file(PLAYPOOL_RULES_FILE),
        calculate_percentages=_bool(raw, "calculate_percentages", True),
        include_category_worksheets=_bool(raw, "include_category_worksheets", False),
        exclude_sacks_from_pass_attempts=_bool(
            raw, "exclude_sacks_from_pass_attempts", True
        ),
        category_order=category_order,
        categories=cfg.categories,
        deleted_plays=deleted_plays,
    )


def read_pdbtoexcel_toml(
    path: Path, labels: CategoryLabels
) -> tuple[CategoryOrder, frozenset[str]]:
    """The category order and the deleted plays of a league's `pdbtoexcel.toml`.

    `[category_order]` needs all three of `run`, `pass` and `defense`, each an
    array of that side's category names under `labels` (a labeled category by
    its label, an unlabeled one by its game name), none repeated; an empty array
    exports nothing of that type. `[deleted_plays] names` is optional, an array
    of play names, matched case-insensitively. A missing file, bad TOML, an
    unknown key, a wrong type or a bad name is a ConfigFileError."""
    if not path.is_file():
        raise ConfigFileError(
            f"{path}: not found (convert-pdb needs the league's {PDBTOEXCEL_FILE})"
        )
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigFileError(f"{path}: {e}") from e
    for key in data:
        if key not in (ORDER_TABLE, DELETED_TABLE):
            raise ConfigFileError(
                f"{path}: unknown key {key!r} (expected {ORDER_TABLE}, {DELETED_TABLE})"
            )
    if ORDER_TABLE not in data:
        raise ConfigFileError(f"{path}: [{ORDER_TABLE}] is missing")
    order = _category_order(_table(data, ORDER_TABLE, path), labels, path)
    deleted = _deleted_plays(_table(data, DELETED_TABLE, path), path)
    return order, deleted


def _table(data: Mapping[str, Any], key: str, path: Path) -> Mapping[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ConfigFileError(f"{path}: [{key}] must be a table")
    return value


def _string_array(
    table: Mapping[str, Any], key: str, section: str, path: Path
) -> list[str]:
    value = table[key]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigFileError(
            f"{path}: [{section}] {key}: expected an array of strings"
        )
    return value


def _check_keys(
    table: Mapping[str, Any], expected: Iterable[str], section: str, path: Path
) -> None:
    allowed = sorted(expected)
    for key in table:
        if key not in allowed:
            expected = ", ".join(allowed)
            raise ConfigFileError(
                f"{path}: [{section}] {key}: unknown key (expected {expected})"
            )


def _category_order(
    table: Mapping[str, Any], labels: CategoryLabels, path: Path
) -> CategoryOrder:
    _check_keys(table, _ORDER_KEYS, ORDER_TABLE, path)
    offense = {labels.label(c): c for c in OffensiveCategory}
    defense = {labels.label(c): c for c in DefensiveCategory}
    # Per key: the names that belong in its list, and the whole side for the
    # wrong-side message.
    valid: dict[str, tuple[Mapping[str, PlayCategory], Mapping[str, PlayCategory]]] = {
        "run": ({n: c for n, c in offense.items() if c.is_run}, offense),
        "pass": ({n: c for n, c in offense.items() if c.is_pass}, offense),
        "defense": (defense, defense),
    }
    order: dict[PLAY_DATA.PLAY_TYPE, tuple[PlayCategory, ...]] = {}
    for key, play_type in _ORDER_KEYS.items():
        if key not in table:
            raise ConfigFileError(f"{path}: [{ORDER_TABLE}] {key}: missing")
        names = _string_array(table, key, ORDER_TABLE, path)
        order[play_type] = tuple(_resolve(names, key, *valid[key], path))
    return order


def _resolve(
    names: list[str],
    key: str,
    valid: Mapping[str, PlayCategory],
    side: Mapping[str, PlayCategory],
    path: Path,
) -> list[PlayCategory]:
    where = f"{path}: [{ORDER_TABLE}] {key}"
    members: list[PlayCategory] = []
    for name in names:
        member = valid.get(name)
        if member is None:
            other = side.get(name)
            if (
                other is not None
                and key != "defense"
                and (other.is_run or other.is_pass)
            ):
                kind = "run" if other.is_run else "pass"
                raise ConfigFileError(
                    f"{where}: {name!r} is a {kind} category, not a {key} category"
                )
            raise ConfigFileError(
                f"{where}: {name!r} is not a {key} category of this league. "
                f"Valid: {sorted(valid)}"
            )
        if member in members:
            raise ConfigFileError(f"{where}: {name!r} is listed twice")
        members.append(member)
    return members


def _deleted_plays(table: Mapping[str, Any], path: Path) -> frozenset[str]:
    _check_keys(table, (DELETED_KEY,), DELETED_TABLE, path)
    if DELETED_KEY not in table:
        return frozenset()
    return frozenset(_string_array(table, DELETED_KEY, DELETED_TABLE, path))


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
