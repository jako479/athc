"""convert-pdb config: `[convert-pdb]` in `athc.toml`, laid over key by key by
the same table in the league's `league.toml` (`layered_settings`), and, from
the league folder, `play_path` and the category labels.

`play_path` locates the play pool used to classify and tag plays. The settings
are the three workbook options; `[convert-pdb.category_order]`, which lists per
side the categories the workbook shows and the order they sort in (the row
order within each team and the Options sheet lists the sort macros use), named
by the league's labels from `league.toml` (the game name where the league has
none); and `deleted_plays`, plays removed from the pool whose stat lines are
skipped quietly instead of warning "Play file not found". Every key is
optional: a missing list is empty (nothing of that type exported).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from athc.config import (
    CONFIG_FILE,
    LEAGUE_FILE,
    ConfigFileError,
    Layered,
    config_file,
    layered_settings,
    load_league_config,
    not_set_line,
)
from athc.fbpro98_play import (
    CategoryLabels,
    DefensiveCategory,
    OffensiveCategory,
    PlayCategory,
)
from athc.pdbtoexcel.pdb import PLAY_DATA

PACKAGE_DIR = Path(__file__).resolve().parent
SECTION = "convert-pdb"

ORDER_TABLE = "category_order"
DELETED_KEY = "deleted_plays"
# The workbook options and what a missing one is.
_OPTIONS: Mapping[str, bool] = {
    "calculate_percentages": True,
    "include_category_worksheets": False,
    "exclude_sacks_from_pass_attempts": True,
}
_KEYS = (*_OPTIONS, ORDER_TABLE, DELETED_KEY)
# [convert-pdb.category_order] key -> the PDB play type its list orders.
_ORDER_KEYS: Mapping[str, PLAY_DATA.PLAY_TYPE] = {
    "run": PLAY_DATA.PLAY_TYPE.RUN,
    "pass": PLAY_DATA.PLAY_TYPE.PASS,
    "defense": PLAY_DATA.PLAY_TYPE.DEFENSE,
}
_ORDER_WHERE = f"[{SECTION}.{ORDER_TABLE}]"

type CategoryOrder = Mapping[PLAY_DATA.PLAY_TYPE, tuple[PlayCategory, ...]]


def empty_category_order() -> CategoryOrder:
    """No categories listed for any play type (nothing exported)."""
    return dict.fromkeys(_ORDER_KEYS.values(), ())


@dataclass(frozen=True, slots=True)
class Config:
    play_path: str = ""
    # The file deleted_plays came from, for the stale-entry warning.
    deleted_plays_file: Path = Path(CONFIG_FILE)
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
    """Locate the play pool and read the settings.

    `play_path` and the category labels come from the league folder
    (LeagueError when no league can be resolved); a league without `play_path`
    is a ConfigFileError. The settings are `[convert-pdb]` of `athc.toml` with
    the league's `[convert-pdb]` laid over it; a missing key keeps its default.
    An unknown key, a wrong type or a bad category name is a ConfigFileError
    naming the file the key came from."""
    cfg = load_league_config(league)
    play_path = cfg.path("play_path")
    if play_path is None:
        raise ConfigFileError(not_set_line("play_path"), cfg.dir / LEAGUE_FILE)
    settings = layered_settings(SECTION, cfg)
    _check_keys(settings, settings.values, (), _KEYS, f"[{SECTION}]")
    options = {key: _bool(settings, key, default) for key, default in _OPTIONS.items()}
    return Config(
        play_path=str(play_path),
        deleted_plays_file=settings.sources.get((DELETED_KEY,), config_file()),
        calculate_percentages=options["calculate_percentages"],
        include_category_worksheets=options["include_category_worksheets"],
        exclude_sacks_from_pass_attempts=options["exclude_sacks_from_pass_attempts"],
        category_order=_category_order(settings, cfg.categories),
        categories=cfg.categories,
        deleted_plays=_deleted_plays(settings),
    )


def _string_array(value: Any, where: str, path: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigFileError(f"{where}: Expected an array of strings.", path)
    return value


def _check_keys(
    settings: Layered,
    table: Mapping[str, Any],
    prefix: tuple[str, ...],
    expected: Iterable[str],
    where: str,
) -> None:
    """Unknown keys in `table` (at `prefix` in `settings`), by the file each
    came from; one file's keys per message, the first file's in path order."""
    allowed = sorted(expected)
    unknown: dict[Path, list[str]] = {}
    for key in table:
        if key not in allowed:
            unknown.setdefault(settings.source(*prefix, key), []).append(key)
    if unknown:
        path = min(unknown)
        names, valid = ", ".join(sorted(unknown[path])), ", ".join(allowed)
        raise ConfigFileError(
            f"{where}: Unknown key(s): {names}. Valid: {valid}.", path
        )


def _category_order(settings: Layered, labels: CategoryLabels) -> CategoryOrder:
    """`[convert-pdb.category_order]`: each of `run`, `pass` and `defense` an
    array of that side's category names under `labels` (a labeled category by
    its label, an unlabeled one by its game name), none repeated; a missing
    list is empty."""
    table = settings.values.get(ORDER_TABLE, {})
    if not isinstance(table, Mapping):
        raise ConfigFileError(
            f"{_ORDER_WHERE}: Must be a table.", settings.source(ORDER_TABLE)
        )
    _check_keys(settings, table, (ORDER_TABLE,), _ORDER_KEYS, _ORDER_WHERE)
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
            order[play_type] = ()
            continue
        where = f"{_ORDER_WHERE} {key}"
        path = settings.source(ORDER_TABLE, key)
        names = _string_array(table[key], where, path)
        order[play_type] = tuple(_resolve(names, key, *valid[key], where, path))
    return order


def _resolve(
    names: list[str],
    key: str,
    valid: Mapping[str, PlayCategory],
    side: Mapping[str, PlayCategory],
    where: str,
    path: Path,
) -> list[PlayCategory]:
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
                    f"{where}: {name!r} is a {kind} category, not a {key} category.",
                    path,
                )
            raise ConfigFileError(
                f"{where}: {name!r} is not a {key} category of this league. "
                f"Valid: {', '.join(sorted(valid))}.",
                path,
            )
        if member in members:
            raise ConfigFileError(f"{where}: {name!r} is listed twice.", path)
        members.append(member)
    return members


def _deleted_plays(settings: Layered) -> frozenset[str]:
    """`deleted_plays`, an array of play names; missing is none."""
    if DELETED_KEY not in settings.values:
        return frozenset()
    where = f"[{SECTION}] {DELETED_KEY}"
    path = settings.source(DELETED_KEY)
    return frozenset(_string_array(settings.values[DELETED_KEY], where, path))


def _bool(settings: Layered, key: str, default: bool) -> bool:
    """`key`, a TOML boolean; a missing key is `default`."""
    value = settings.values.get(key, default)
    if not isinstance(value, bool):
        raise ConfigFileError(
            f"[{SECTION}] {key}: Expected true or false.", settings.source(key)
        )
    return value
