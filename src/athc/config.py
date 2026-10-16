from __future__ import annotations

import configparser
import os
import re
import tomllib
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from athc.errors import (
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    ConfigFileError,
    LeagueError,
    StrPath,
    ini_reason,
    reason_of,
    toml_reason,
)
from athc.fbpro98_play import CategoryLabels

CONFIG_FILE = "athc.ini"
LEAGUES_DIR = "leagues"
LEAGUE_FILE = "league.toml"
LEAGUE_SECTION = "league"
LEAGUE_PATH_KEY = "path"  # [league] path: the folder holding the league's files
CATEGORIES_SECTION = "categories"

# The settings a command may find unset: what to call each, and the value
# word its `athc config set` form takes.
_NOT_SET: dict[str, tuple[str, str]] = {
    "league": ("League", "NAME"),
    "path": ("League files folder", "FOLDER"),
    "play_path": ("Play pool folder", "FOLDER"),
    "team": ("Team", "NAME"),
}


def not_set_line(key: str, way: str | None = None) -> str:
    """`<Setting> is not set. Run 'athc config set <key> <VALUE>'`, plus
    ` or pass <way>` when the command has a way around it, then the period."""
    what, value = _NOT_SET[key]
    tail = "" if way is None else f" or pass {way}"
    return f"{what} is not set. Run 'athc config set {key} {value}'{tail}."


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
    ConfigFileError, naming the file, when it cannot be opened or parsed."""
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.exists():
        # Opened here: ConfigParser.read skips a file it cannot open, which
        # would read as an empty athc.ini.
        try:
            with path.open(encoding="utf-8") as handle:
                cp.read_file(handle)
        except OSError as e:
            raise ConfigFileError(reason_of(e), path) from e
        except UnicodeDecodeError as e:
            # Saved as ANSI by an editor, an accent in a comment is enough.
            raise ConfigFileError("Not UTF-8 text. Save it as UTF-8.", path) from e
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

    def string(self, key: str) -> str | None:
        """`values[key]` without its outer spaces; None when absent or blank.
        ConfigFileError when the key was written as an array."""
        self._not_an_array(key)
        return self.values.get(key, "").strip() or None

    def path(self, key: str) -> Path | None:
        """`values[key]` as a path; relative values resolve against the league
        folder (the file that names them), like `resolve_path` for `athc.ini`.
        ConfigFileError when the key was written as an array."""
        self._not_an_array(key)
        raw = self.values.get(key)
        if not raw:
            return None
        return self._resolve(raw)

    def _not_an_array(self, key: str) -> None:
        if key in self.lists:
            raise ConfigFileError(
                f"[{LEAGUE_SECTION}] {key}: Expected a string, got an array.",
                self.dir / LEAGUE_FILE,
            )

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
                f"[{LEAGUE_SECTION}] {key}: "
                "Expected an array of strings, got a string.",
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
        raise LeagueError(f"League '{name}' not found. No folder {path}.{_available()}")
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
        raise LeagueError(f"{not_set_line('league', '--league')}{_available()}")
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
        raise ConfigFileError(toml_reason(e), path) from e
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
        raise ConfigFileError(f"[{name or key}]: Must be a table.", path)
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
                f"[{LEAGUE_SECTION}] {key}: Expected a string or an array of strings.",
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


def league_file(league: str | None) -> Path:
    """The resolved league's `league.toml`, whether or not it exists.
    LeagueError when no league is set or its folder is missing."""
    return league_dir(resolve_league(league)) / LEAGUE_FILE


def set_league_value(league: str | None, key: str, value: str) -> Path:
    """Write `key = value` under `[league]` in the league's `league.toml`,
    keeping every comment and other line (tomlkit). Returns the path written.

    A key already there is changed in place. A new key goes on the line after
    its commented example (`# key = ...`) in `[league]`, else after the
    table's last key line, never under the comment that opens the next table.

    A missing file or `[league]` table is Windows' file-not-found
    ConfigFileError and nothing is written: athc does not repair a broken
    install. A malformed file is its parse error, as every reader prints it."""
    import tomlkit  # only this writer needs it

    path = league_file(league)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise ConfigFileError(reason_of(e), path) from e
    try:
        # Parsed by tomllib first so a malformed file gets the readers' wording.
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigFileError(toml_reason(e), path) from e
    document = tomlkit.parse(text)
    table = document.get(LEAGUE_SECTION)
    if not isinstance(table, MutableMapping):
        raise ConfigFileError(FILE_NOT_FOUND, path)
    # A literal string keeps a Windows path's backslashes as typed, like the
    # shipped file's values; one holding a quote needs the escaped form.
    literal = "'" not in value and "\n" not in value
    item = tomlkit.string(value, literal=literal)
    line = f"{tomlkit.key(key).as_string()} = {item.as_string()}"
    if key not in table and (added := _add_league_line(text, key, line)) is not None:
        text = added
    else:
        table[key] = item
        text = tomlkit.dumps(document)
    path.write_text(text, encoding="utf-8")
    return path


# The `[league]` header line, its name bare or quoted, and any table header.
_LEAGUE_HEADER = re.compile(rf"\s*\[\s*([\"']?){LEAGUE_SECTION}\1\s*\]\s*(#.*)?")
_TABLE_HEADER = re.compile(r"\s*\[")


def _add_league_line(text: str, key: str, line: str) -> str | None:
    """`text` with `line`, a new key, added to `[league]`: after its
    commented example (`# key = ...`), else after the table's last key line,
    else after the header. None when no line is the `[league]` header (the
    table written another way): tomlkit adds the key then.

    tomlkit would add it after everything in the table, the comment that
    opens the next table included, so the line is placed by text."""
    lines = text.split("\n")
    header = next(
        (i for i, raw in enumerate(lines) if _LEAGUE_HEADER.fullmatch(raw.rstrip())),
        None,
    )
    if header is None:
        return None
    end = next(
        (i for i in range(header + 1, len(lines)) if _TABLE_HEADER.match(lines[i])),
        len(lines),
    )
    body = range(header + 1, end)
    example = re.compile(rf"\s*#\s*{re.escape(key)}\s*=")
    after = next((i for i in body if example.match(lines[i])), None)
    if after is None:
        # The last line that is neither blank nor a comment ends the last key,
        # a value written over several lines included.
        after = max(
            (i for i in body if lines[i].lstrip()[:1] not in ("", "#")),
            default=header,
        )
    lines.insert(after + 1, line)
    return "\n".join(lines)


def _available() -> str:
    names = available_leagues()
    if names:
        return f" Available: {', '.join(names)}."
    return f" No league folders under {leagues_dir()}."


def play_dir(play_path: StrPath) -> Path:
    """`play_path` when it is a folder; else ConfigFileError in Windows' words,
    with the command that sets it."""
    path = Path(play_path)
    if not path.is_dir():
        reason = DIRECTORY_INVALID if path.exists() else PATH_NOT_FOUND
        raise ConfigFileError(f"{reason} Run 'athc config set play_path FOLDER'.", path)
    return path
