from __future__ import annotations

import configparser
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from athc.errors import ConfigFileError, LeagueError, ini_reason, reason_of
from athc.fbpro98_play import CategoryLabels

CONFIG_FILE = "athc.ini"
LEAGUES_DIR = "leagues"
LEAGUE_FILE = "league.toml"
LEAGUE_SECTION = "league"
CATEGORIES_SECTION = "categories"
STANDINGS_DIR = "standings"


def config_dir() -> Path:
    if override := os.environ.get("ATHC_CONFIG_DIR"):
        return Path(override)
    return user_config_path("athc", appauthor=False, ensure_exists=False)


def config_file() -> Path:
    """Path to the athc settings file (it need not exist)."""
    return config_dir() / CONFIG_FILE


def resolve_path(value: str | os.PathLike[str]) -> Path:
    """Resolve a path read from `athc.ini` against the config file's directory.

    Relative paths are taken under `config_dir()` (where `athc.ini` lives), so one
    `athc.ini` works unchanged in dev (`ATHC_CONFIG_DIR` -> repo `config/dev/`) and
    after install (`%LOCALAPPDATA%\\athc`); absolute paths are used as-is. This is
    the mainstream config idiom (ruff, mypy): config-relative, not CWD-relative.
    Paths passed on the CLI stay CWD-relative and must not go through here.
    """
    p = Path(value)
    return p if p.is_absolute() else config_dir() / p


def load_config() -> dict[str, dict[str, str]]:
    """`athc.ini` as `{section: {key: value}}`; `{}` when the file is absent.
    ConfigFileError, naming the file, when it cannot be parsed."""
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        try:
            cp.read(path, encoding="utf-8")
        except configparser.Error as e:
            raise ConfigFileError(ini_reason(e), path) from e
    return {section: dict(cp[section]) for section in cp.sections()}


@dataclass(frozen=True, slots=True)
class LeagueConfig:
    """One league folder: its name, path and the `[league]` table of its
    `league.toml` — string values in `values`, arrays of strings in `lists`
    (missing file -> empty) — plus the league's category labels."""

    name: str
    dir: Path
    values: dict[str, str]
    lists: dict[str, tuple[str, ...]] = field(default_factory=dict)
    categories: CategoryLabels = field(default_factory=CategoryLabels)

    def path(self, key: str) -> Path | None:
        """`values[key]` as a path; relative values resolve against the league
        folder (the file that names them), like `resolve_path` for `athc.ini`.
        ConfigFileError when the key was written as an array."""
        if key in self.lists:
            raise ConfigFileError(
                f"[{LEAGUE_SECTION}] {key}: expected a string, got an array",
                self.dir / LEAGUE_FILE,
            )
        raw = self.values.get(key)
        if not raw:
            return None
        return self._resolve(raw)

    def rules_file_path(self, filename: str) -> Path:
        """`<filename>` in the league folder, whether or not it exists."""
        return self.dir / filename

    def rules_file(self, filename: str) -> Path | None:
        """`<filename>` in the league folder, or None when absent."""
        candidate = self.rules_file_path(filename)
        return candidate if candidate.is_file() else None

    def rule_files(self, key: str, default: str) -> tuple[Path, ...]:
        """The ordered rule files for a tool: the array under `key` in
        `league.toml` when present (later files layer over earlier ones), else the
        fixed `<default>` file in the league folder when it exists, else nothing.
        ConfigFileError when the key was written as a single string."""
        if key in self.values:
            raise ConfigFileError(
                f"[{LEAGUE_SECTION}] {key}: expected an array of strings, got a string",
                self.dir / LEAGUE_FILE,
            )
        names = self.lists.get(key)
        if names:
            return tuple(self._resolve(name) for name in names)
        fixed = self.rules_file(default)
        return (fixed,) if fixed else ()

    def _resolve(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else self.dir / p


def leagues_dir() -> Path:
    return config_dir() / LEAGUES_DIR


def available_leagues() -> list[str]:
    """Folder names under `leagues\\`, sorted; empty when the folder is absent."""
    root = leagues_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def league_dir(name: str) -> Path:
    """`leagues\\<name>`; LeagueError unless it is an existing direct subfolder.

    The name must be a single path segment so `..` or `a\\b` can never reach
    outside `leagues\\`; a blank name is refused too, since `leagues\\` joined
    with "" (or with spaces, which Windows trims) is the `leagues\\` folder.
    """
    path = leagues_dir() / name
    if (
        not name.strip()
        or name in (".", "..")
        or Path(name).name != name
        or not path.is_dir()
    ):
        raise LeagueError(f"league '{name}' not found: no folder {path}.{_available()}")
    return path


def configured_league() -> str | None:
    """`[athc] league` from `athc.ini`, or None when absent or blank.
    ConfigFileError when `athc.ini` cannot be parsed."""
    return load_config().get("athc", {}).get("league", "").strip() or None


def resolve_league(league: str | None = None) -> str:
    """The league name to use. Priority: `league` arg -> `[athc] league`; a blank
    arg counts as not given. LeagueError when none is set or the folder is
    missing."""
    league = (league or "").strip() or None
    name = league or configured_league()
    if not name:
        raise LeagueError(
            "no league selected; run 'athc config set league NAME' or pass "
            f"--league.{_available()}"
        )
    league_dir(name)
    return name


def load_league_config(league: str | None = None) -> LeagueConfig:
    """Resolve the league and read `leagues\\<name>\\league.toml`.

    Set `ATHC_CONFIG_DIR` to override the config dir.
    """
    name = resolve_league(league)
    folder = league_dir(name)
    path = folder / LEAGUE_FILE
    if not path.is_file():
        return LeagueConfig(name=name, dir=folder, values={})
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as e:
        raise ConfigFileError(reason_of(e), path) from e
    except tomllib.TOMLDecodeError as e:
        raise ConfigFileError(str(e), path) from e
    values, lists = _league_values(_table(data, LEAGUE_SECTION, path), path)
    categories = _category_labels(_table(data, CATEGORIES_SECTION, path), path)
    return LeagueConfig(
        name=name, dir=folder, values=values, lists=lists, categories=categories
    )


def _table(
    data: Mapping[str, Any], key: str, path: Path, name: str | None = None
) -> Mapping[str, Any]:
    """`data[key]` as a TOML table (`{}` when absent); ConfigFileError otherwise.
    `name` is the table's full dotted name for the message."""
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ConfigFileError(f"[{name or key}] must be a table", path)
    return value


def _league_values(
    table: Mapping[str, Any], path: Path
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """Split `[league]` into string values and string arrays; anything else is a
    ConfigFileError."""
    values: dict[str, str] = {}
    lists: dict[str, tuple[str, ...]] = {}
    for key, value in table.items():
        if isinstance(value, str):
            values[key] = value
        elif isinstance(value, list) and all(isinstance(v, str) for v in value):
            lists[key] = tuple(value)
        else:
            raise ConfigFileError(
                f"[{LEAGUE_SECTION}] {key}: expected a string or an array of strings",
                path,
            )
    return values, lists


def _category_labels(table: Mapping[str, Any], path: Path) -> CategoryLabels:
    """`[categories.offense]` / `[categories.defense]` as the league's labels."""
    offense = _table(table, "offense", path, f"{CATEGORIES_SECTION}.offense")
    defense = _table(table, "defense", path, f"{CATEGORIES_SECTION}.defense")
    return CategoryLabels.from_tables(offense, defense, path)


def load_league(league: str | None = None) -> dict[str, str]:
    """The `[league]` string values of the resolved league's `league.toml`. Kept
    for callers that only need the raw mapping (athc-admin)."""
    return load_league_config(league).values


def set_config_value(key: str, value: str) -> Path:
    """Write `[athc] key = value` into `athc.ini`, keeping every comment and the
    file's layout (ConfigUpdater). Creates the file, section or key as needed.
    Returns the path written; ConfigFileError when the file cannot be parsed."""
    # Imported here: only this writer needs it. The submodule path is used because
    # pyright cannot see the package's star re-export.
    from configupdater.configupdater import ConfigUpdater

    path = config_file()
    updater = ConfigUpdater()
    if path.is_file():
        try:
            updater.read(path, encoding="utf-8")
        except configparser.Error as e:  # ConfigUpdater raises configparser's classes
            raise ConfigFileError(ini_reason(e), path) from e
    if not updater.has_section("athc"):
        if updater.sections():
            updater[updater.sections()[0]].add_before.section("athc").space(1)
        else:
            updater.add_section("athc")
    updater["athc"][key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        updater.write(handle)
    return path


def _available() -> str:
    names = available_leagues()
    if names:
        return f" Available: {', '.join(names)}."
    return f" No league folders under {leagues_dir()}."
