from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path

CONFIG_FILE = "athc.ini"
LEAGUES_DIR = "leagues"
LEAGUE_FILE = "league.ini"
LEAGUE_SECTION = "league"
RULES_DIR = "rules"
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
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        cp.read(path, encoding="utf-8")
    return {section: dict(cp[section]) for section in cp.sections()}


class LeagueError(ValueError):
    """Raised when no league can be resolved for a league-specific tool."""


class ConfigFileError(ValueError):
    """athc.ini or a league.ini cannot be read (malformed INI, bad %-interpolation)."""


@dataclass(frozen=True)
class LeagueConfig:
    """One league folder: its name, path and the `[league]` values of its
    `league.ini` (raw strings; missing file -> empty)."""

    name: str
    dir: Path
    values: dict[str, str]

    def path(self, key: str) -> Path | None:
        """`values[key]` as a path; relative values resolve against the league
        folder (the file that names them), like `resolve_path` for `athc.ini`."""
        raw = self.values.get(key)
        if not raw:
            return None
        return self._resolve(raw)

    def rules_file_path(self, filename: str) -> Path:
        """`rules\\<filename>` in the league folder, whether or not it exists."""
        return self.dir / RULES_DIR / filename

    def rules_file(self, filename: str) -> Path | None:
        """`rules\\<filename>` in the league folder, or None when absent."""
        candidate = self.rules_file_path(filename)
        return candidate if candidate.is_file() else None

    def rule_files(self, key: str, default: str) -> tuple[Path, ...]:
        """The ordered rule files for a tool: the multi-line list under `key` in
        `league.ini` when present (later files layer over earlier ones), else the
        fixed `rules\\<default>` file when it exists, else nothing."""
        raw = self.values.get(key)
        if raw:
            return tuple(
                self._resolve(line.strip()) for line in raw.splitlines() if line.strip()
            )
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
    try:
        raw = load_config()
    except configparser.Error as e:
        raise ConfigFileError(f"{config_file()}: {e}") from e
    return raw.get("athc", {}).get("league", "").strip() or None


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
    """Resolve the league and read `leagues\\<name>\\league.ini`.

    Set `ATHC_CONFIG_DIR` to override the config dir.
    """
    name = resolve_league(league)
    folder = league_dir(name)
    path = folder / LEAGUE_FILE
    cp = configparser.ConfigParser()  # BasicInterpolation: %(key)s works
    values: dict[str, str] = {}
    if path.is_file():
        try:
            cp.read(path, encoding="utf-8")
            # Interpolation runs on read of the values, so a stray `%` (as in
            # `%LOCALAPPDATA%`) surfaces here, not in cp.read.
            if cp.has_section(LEAGUE_SECTION):
                values = dict(cp[LEAGUE_SECTION])
        except configparser.Error as e:
            raise ConfigFileError(f"{path}: {e}") from e
    return LeagueConfig(name=name, dir=folder, values=values)


def load_league(league: str | None = None) -> dict[str, str]:
    """The `[league]` values of the resolved league's `league.ini` (with `%(key)s`
    resolved). Kept for callers that only need the raw mapping (athc-admin)."""
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
            raise ConfigFileError(f"{path}: {e}") from e
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
