# Multi-league config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every league-aware athc tool reads its settings, rules and standings from `leagues\<NAME>\` under the config dir, with the league chosen by `--league`, `ATHC_LEAGUE`, or `[athc] league` in `athc.ini`, which `athc config set league NAME` writes.

**Architecture:** `athc.config` gains one resolver (`load_league_config`) that turns a league name into a `LeagueConfig` (folder + `league.ini` values + helpers for rule files). Each tool's `config.py` asks that object for what it needs instead of reading its own `athc.ini` section. `athc config set` writes `athc.ini` through ConfigUpdater so comments survive. `dev\` and `release\` move to the new layout; the installer copies `leagues\` with per-file ownership rules.

**Tech Stack:** Python 3.12, Click, `configparser`, `configupdater` (new), pytest with `CliRunner`, uv.

**Spec:** `docs/superpowers/specs/2026-09-27-multi-league-config-design.md`

## Global Constraints

- Python 3.12 syntax only (`requires-python = ">=3.12"`, pyright pinned to 3.12).
- Run from the repo root, one command per call, never chained: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`. All four green before a task is done.
- `pytest` fails below 92% coverage; `filterwarnings = ["error"]` (any warning is a failure).
- Never modify expected test results or fixtures to make a failing test pass; tests that assert the old `athc.ini` keys change only because the spec changes the behaviour.
- Every new limit or range gets tests on both sides. This plan introduces none.
- Commit messages: one line, prefixed with the owning tool (`athc:`, `gameplan:`, `profile:`, `scheduler:`, `convert-pdb:`, `build:`, `docs:`). Never mention Claude, Anthropic or any AI tool. No `Co-Authored-By` trailers.
- New CHANGELOG / STATUS entries go at the top of their section. Do not edit `TODO.md`.
- Comments explain why, not what. Ruff at 88 columns, double quotes.
- Public API that athc-admin imports must keep its name, signature and return shape: `athc.config.load_league(league: str | None = None) -> dict[str, str]`, `athc.config.LeagueError`, `athc.cli.league_option`.
- `--league` help text and the `league_option` decorator body stay as they are today except the help string (Task 1).

## Review Focus

1. A league name with path separators or `..` (`athc config set league ..\x`) must be rejected as "not found", never escape `leagues\`. Test pinned in Task 1 (`test_league_dir_rejects_path_segments`).
2. `athc.ini` with `[athc]` present but no `league` key, or `league =` empty, must produce the "no league selected" error, not a folder named "". Test pinned in Task 1 (`test_empty_league_key_is_no_league`).
3. `athc config set league PNFL` on a machine with no `athc.ini` yet must create the file with just `[athc]\nleague = PNFL`. Test pinned in Task 2 (`test_set_creates_missing_file`).
4. A `gameplan_rules` list in `league.ini` that names a file that does not exist must surface that path in the error, not silently run with no rules. Test pinned in Task 3 (`test_cli_missing_listed_rules_file_is_reported`).
5. `generate-schedule` with a configured league whose `standings\` folder lacks the season must name the expected path in the error. Test pinned in Task 6 (`test_find_league_path_errors_when_none_exist`).

---

## File structure

**Create**
- `src/athc/cli/config/set.py` — `athc config set KEY VALUE`.
- `dev/leagues/PNFL/league.ini`, `release/leagues/PNFL/league.ini` — per-league settings.
- `tests/integration/test_config_set.py` — the `set` command and `set_config_value`.

**Modify**
- `src/athc/config.py` — league resolution (`LeagueConfig`, `load_league_config`, `league_dir`, `available_leagues`, `resolve_league`, `set_config_value`, obsolete-key warning). `config_dir`, `config_file`, `resolve_path`, `load_config`, `LeagueError`, `load_league` keep their names.
- `src/athc/cli/__init__.py` — `--league` help text only.
- `src/athc/cli/config/__init__.py` — register `set`.
- `src/athc/gameplan/config.py`, `src/athc/cli/gameplan/_common.py` — read the league folder.
- `src/athc/profile/config.py`, `src/athc/cli/profile/check.py`, `src/athc/cli/profile/_common.py` — league-aware.
- `src/athc/pdbtoexcel/config.py`, `src/athc/pdbtoexcel/main.py`, `src/athc/cli/convert_pdb.py` — league-aware.
- `src/athc/scheduler/config.py`, `src/athc/scheduler/main.py`, `src/athc/cli/generate_schedule.py` — league-aware.
- `dev/athc.ini`, `release/athc.ini`; files moved under `dev/leagues/PNFL/` and `release/leagues/PNFL/`.
- `release/install.bat`, `release/release-build.ps1`.
- Tests: `tests/integration/test_config.py`, `test_gameplan_check.py`, `test_profile_check.py`, `test_generate_schedule.py`, `conftest.py`; `tests/unit/scheduler/test_config.py`.
- Docs listed in Task 9.

**Fixtures already available** (`tests/conftest.py`): `config_dir` (autouse; sets `ATHC_CONFIG_DIR` to a temp dir and returns it) and `write_config(body, name="athc.ini")` (writes dedented INI into that dir). `tests/integration/conftest.py`: `runner` (a `CliRunner`), `DATA`, `RULES_TOML`, `OFF1`, `GP_RULES`, `POOL_RULES`, `GP_OFFENSE`, `PLAYS`.

**League-folder test helper.** Several tasks need a league folder in the temp config dir. Add this fixture to `tests/conftest.py` in Task 1 and use it everywhere after:

```python
@pytest.fixture
def make_league(config_dir: Path) -> Callable[..., Path]:
    """Create `leagues/<name>/` (with `rules/` and `standings/`) under the temp
    config dir, write `league.ini` from `body` when given, and return the folder."""

    def _make(name: str = "PNFL", body: str | None = None) -> Path:
        folder = config_dir / "leagues" / name
        (folder / "rules").mkdir(parents=True)
        (folder / "standings").mkdir()
        if body is not None:
            (folder / "league.ini").write_text(
                textwrap.dedent(body).lstrip("\n"), encoding="utf-8"
            )
        return folder

    return _make
```

---

### Task 1: League resolution in `athc.config`

**Files:**
- Modify: `src/athc/config.py` (whole file)
- Modify: `src/athc/cli/__init__.py:51-58` (help text)
- Modify: `tests/conftest.py` (add `make_league`)
- Modify: `tests/integration/test_config.py:1-143` (league tests) and delete lines 145-189 (release-loader tests; Task 7 re-adds them for the new layout)
- Modify: `pyproject.toml` via `uv add configupdater`

**Interfaces:**
- Consumes: nothing new.
- Produces (all in `athc.config`):
  - `LEAGUES_DIR = "leagues"`, `LEAGUE_FILE = "league.ini"`, `LEAGUE_SECTION = "league"`, `RULES_DIR = "rules"`, `STANDINGS_DIR = "standings"`
  - `class LeagueConfig` (frozen dataclass): `name: str`, `dir: Path`, `values: dict[str, str]`; methods `path(key: str) -> Path | None`, `rules_file(filename: str) -> Path | None`, `rule_files(key: str, default: str) -> tuple[Path, ...]`
  - `leagues_dir() -> Path`
  - `league_dir(name: str) -> Path` (raises `LeagueError` when the folder is missing)
  - `available_leagues() -> list[str]`
  - `configured_league() -> str | None`
  - `resolve_league(league: str | None = None) -> str`
  - `load_league_config(league: str | None = None) -> LeagueConfig`
  - `load_league(league: str | None = None) -> dict[str, str]` (unchanged signature; returns `load_league_config(league).values`)
  - `obsolete_config_entries() -> list[str]`

- [ ] **Step 1: Add the dependency**

Run: `uv add configupdater`
Expected: `pyproject.toml` gains `"configupdater>=3.2"` under `dependencies`; `uv.lock` updated. If `git diff` shows only line-ending noise on other lines, that is the CRLF checkout and is fine.

- [ ] **Step 2: Add the `make_league` fixture to `tests/conftest.py`**

Append the fixture from "File structure" above (it needs `textwrap`, `Callable`, `Path`, already imported there).

- [ ] **Step 3: Replace the league tests in `tests/integration/test_config.py`**

Replace everything from the module docstring through the `[DEFAULT]` cascade test (lines 1-143) with the block below, and delete the release-loader tests (lines 145-189, from `# ── shipped release/athc.ini` through `test_release_convert_pdb_config_loads`). Keep the `athc config` command-group tests at the bottom, but in `test_edit_preserves_existing_file` change both `default_league = PNFL` strings to `league = PNFL`.

```python
"""Direct tests for `athc.config` league resolution — the shared resolver every
`--league` tool calls.

`load_league_config` reads `config_dir()/athc.ini` and `leagues/<NAME>/league.ini`,
so per testing-integration.md these live in the integration tier (unit tests never
read config). Covered once here rather than per command. A league is a folder under
`leagues/`; `[athc] league` in athc.ini names the one used when no flag/env is given.

Also covers the `athc config` command group (path / edit / reveal), with the
editor and Explorer launches mocked.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.config import config as config_group
from athc.cli.config.edit import edit
from athc.cli.config.path import path
from athc.cli.config.reveal import reveal
from athc.config import (
    LeagueError,
    available_leagues,
    league_dir,
    load_league,
    load_league_config,
    obsolete_config_entries,
    resolve_path,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


# ── resolution priority: --league arg → ATHC_LEAGUE → [athc] league ──


def test_resolves_explicit_league_arg(make_league: MakeLeague) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    assert load_league("PNFL")["play_path"] == "D:/p"


def test_resolves_from_env(
    make_league: MakeLeague, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    monkeypatch.setenv("ATHC_LEAGUE", "PNFL")
    assert load_league()["play_path"] == "D:/p"


def test_resolves_from_configured_league(
    make_league: MakeLeague, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    write_config("[athc]\nleague = PNFL\n")
    assert load_league()["play_path"] == "D:/p"


def test_arg_beats_env(make_league: MakeLeague, monkeypatch: pytest.MonkeyPatch) -> None:
    make_league("ARG", "[league]\nk = arg\n")
    make_league("ENV", "[league]\nk = env\n")
    monkeypatch.setenv("ATHC_LEAGUE", "ENV")
    assert load_league("ARG")["k"] == "arg"


def test_env_beats_configured_league(
    make_league: MakeLeague, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_league("ENV", "[league]\nk = env\n")
    make_league("CFG", "[league]\nk = cfg\n")
    write_config("[athc]\nleague = CFG\n")
    monkeypatch.setenv("ATHC_LEAGUE", "ENV")
    assert load_league()["k"] == "env"


# ── LeagueConfig helpers ──


def test_league_config_names_folder(make_league: MakeLeague, config_dir: Path) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    cfg = load_league_config("PNFL")
    assert cfg.name == "PNFL"
    assert cfg.dir == config_dir / "leagues" / "PNFL"
    assert cfg.values == {"play_path": "D:/p"}


def test_missing_league_ini_gives_empty_values(make_league: MakeLeague) -> None:
    make_league("PNFL")  # folder only
    assert load_league_config("PNFL").values == {}


def test_path_resolves_relative_against_league_dir(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = plays\nabs = D:/x\n")
    cfg = load_league_config("PNFL")
    assert cfg.path("play_path") == folder / "plays"
    assert cfg.path("abs") == Path("D:/x")
    assert cfg.path("missing") is None


def test_rules_file_only_when_present(make_league: MakeLeague) -> None:
    folder = make_league("PNFL")
    cfg = load_league_config("PNFL")
    assert cfg.rules_file("gameplan.toml") is None
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    assert cfg.rules_file("gameplan.toml") == folder / "rules" / "gameplan.toml"


def test_rule_files_default_is_the_fixed_file(make_league: MakeLeague) -> None:
    folder = make_league("PNFL")
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config("PNFL")
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "rules" / "gameplan.toml",
    )


def test_rule_files_default_empty_when_fixed_file_missing(
    make_league: MakeLeague,
) -> None:
    make_league("PNFL")
    assert load_league_config("PNFL").rule_files("gameplan_rules", "gameplan.toml") == ()


def test_rule_files_list_replaces_default_in_order(make_league: MakeLeague) -> None:
    folder = make_league(
        "PNFL",
        "[league]\ngameplan_rules =\n    rules\\base.toml\n    D:\\house.toml\n",
    )
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config("PNFL")
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "rules" / "base.toml",
        Path("D:\\house.toml"),
    )


# ── errors ──


def test_no_league_resolvable_lists_available(
    make_league: MakeLeague, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    make_league("PNFL")
    make_league("PCFL")
    with pytest.raises(LeagueError) as exc:
        load_league()
    msg = str(exc.value)
    assert "no league selected" in msg
    assert "athc config set league" in msg
    assert "Available: PCFL, PNFL" in msg


def test_no_league_and_no_folders(monkeypatch: pytest.MonkeyPatch, config_dir: Path) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    with pytest.raises(LeagueError) as exc:
        load_league()
    assert str(config_dir / "leagues") in str(exc.value)


def test_unknown_league_errors(make_league: MakeLeague) -> None:
    make_league("PNFL")
    with pytest.raises(LeagueError) as exc:
        load_league("PCFL")
    msg = str(exc.value)
    assert "PCFL" in msg and "not found" in msg
    assert "Available: PNFL" in msg


def test_empty_league_key_is_no_league(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    write_config("[athc]\nleague =\n")
    with pytest.raises(LeagueError, match="no league selected"):
        load_league()


@pytest.mark.parametrize("name", ["..", "..\\x", "a/b", "a\\b"])
def test_league_dir_rejects_path_segments(name: str, config_dir: Path) -> None:
    (config_dir / "x").mkdir()  # a real sibling folder `..\x` would point at
    with pytest.raises(LeagueError, match="not found"):
        league_dir(name)


def test_malformed_league_ini_errors(make_league: MakeLeague) -> None:
    make_league("PNFL", "[league\nbroken")
    with pytest.raises(LeagueError):
        load_league("PNFL")


def test_available_leagues_lists_folders_only(
    make_league: MakeLeague, config_dir: Path
) -> None:
    make_league("B")
    make_league("A")
    (config_dir / "leagues" / "stray.txt").write_text("", encoding="utf-8")
    assert available_leagues() == ["A", "B"]


def test_available_leagues_without_folder(config_dir: Path) -> None:
    assert available_leagues() == []


# ── obsolete athc.ini keys: one warning, then ignored ──


def test_obsolete_entries_detected(write_config: WriteConfig) -> None:
    write_config(
        "[athc]\ndefault_league = PNFL\nleague = PNFL\n[gameplan]\nrule_files =\n"
        "[profile]\n[convert-pdb]\n[league.PNFL]\nplay_path = x\n[autocontinue]\n"
    )
    assert obsolete_config_entries() == [
        "[athc] default_league",
        "[gameplan]",
        "[profile]",
        "[convert-pdb]",
        "[league.PNFL]",
    ]


def test_obsolete_entries_warned_once_per_load(
    make_league: MakeLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    make_league("PNFL")
    write_config("[athc]\nleague = PNFL\ndefault_league = PNFL\n")
    with caplog.at_level(logging.WARNING, logger="athc.config"):
        load_league_config()
    assert "[athc] default_league" in caplog.text
    assert "leagues" in caplog.text


def test_no_warning_without_obsolete_entries(
    make_league: MakeLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    make_league("PNFL")
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.WARNING, logger="athc.config"):
        load_league_config()
    assert caplog.text == ""


# ── resolve_path: config-relative (ruff/mypy idiom), absolute untouched ──


def test_resolve_path_relative_is_under_config_dir(config_dir: Path) -> None:
    assert resolve_path("rules\\x.toml") == config_dir / "rules" / "x.toml"


def test_resolve_path_absolute_is_unchanged() -> None:
    assert resolve_path("D:\\rules\\x.toml") == Path("D:\\rules\\x.toml")


# ── %(key)s interpolation inside league.ini ──


def test_interpolation_within_league_ini(make_league: MakeLeague) -> None:
    make_league(
        "PNFL",
        "[league]\nleague_root = D:/Leagues/PNFL\nplay_path = %(league_root)s/plays\n",
    )
    assert load_league("PNFL")["play_path"] == "D:/Leagues/PNFL/plays"
```

- [ ] **Step 4: Run the new tests to verify they fail**

Run: `uv run pytest tests/integration/test_config.py -q`
Expected: ImportError on `available_leagues` / `league_dir` / `load_league_config` / `obsolete_config_entries` (collection error).

- [ ] **Step 5: Rewrite `src/athc/config.py`**

```python
from __future__ import annotations

import configparser
import logging
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

# athc.ini entries from the single-league layout. They are ignored; one warning
# tells the user where the values live now.
_OBSOLETE_SECTIONS = ("gameplan", "profile", "convert-pdb")

logger = logging.getLogger(__name__)


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
    `athc.ini` works unchanged in dev (`ATHC_CONFIG_DIR` -> repo `dev/`) and after
    install (`%LOCALAPPDATA%\\athc`); absolute paths are used as-is. This is the
    mainstream config idiom (ruff, mypy): config-relative, not CWD-relative. Paths
    passed on the CLI stay CWD-relative and must not go through here.
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

    def rules_file(self, filename: str) -> Path | None:
        """`rules\\<filename>` in the league folder, or None when absent."""
        candidate = self.dir / RULES_DIR / filename
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
    outside `leagues\\`.
    """
    path = leagues_dir() / name
    if name in (".", "..") or Path(name).name != name or not path.is_dir():
        raise LeagueError(f"league '{name}' not found: no folder {path}.{_available()}")
    return path


def configured_league() -> str | None:
    """`[athc] league` from `athc.ini`, or None when absent or blank."""
    return load_config().get("athc", {}).get("league", "").strip() or None


def resolve_league(league: str | None = None) -> str:
    """The league name to use. Priority: `league` arg -> `ATHC_LEAGUE` env ->
    `[athc] league`. LeagueError when none is set or the folder is missing."""
    name = league or os.environ.get("ATHC_LEAGUE") or configured_league()
    if not name:
        raise LeagueError(
            "no league selected; run 'athc config set league NAME' or pass "
            f"--league.{_available()}"
        )
    league_dir(name)
    return name


def load_league_config(league: str | None = None) -> LeagueConfig:
    """Resolve the league and read `leagues\\<name>\\league.ini`.

    Set `ATHC_CONFIG_DIR` to override the config dir. Logs one warning when
    `athc.ini` still carries entries from the single-league layout.
    """
    obsolete = obsolete_config_entries()
    if obsolete:
        logger.warning(
            "athc.ini: %s no longer read; per-league settings now live in "
            "%s\\<NAME>\\%s (see docs)",
            ", ".join(obsolete),
            LEAGUES_DIR,
            LEAGUE_FILE,
        )
    name = resolve_league(league)
    folder = league_dir(name)
    path = folder / LEAGUE_FILE
    cp = configparser.ConfigParser()  # BasicInterpolation: %(key)s works
    if path.is_file():
        try:
            cp.read(path, encoding="utf-8")
        except configparser.Error as e:
            raise LeagueError(f"{path}: {e}") from e
    values = dict(cp[LEAGUE_SECTION]) if cp.has_section(LEAGUE_SECTION) else {}
    return LeagueConfig(name=name, dir=folder, values=values)


def load_league(league: str | None = None) -> dict[str, str]:
    """The `[league]` values of the resolved league's `league.ini` (with `%(key)s`
    resolved). Kept for callers that only need the raw mapping (athc-admin)."""
    return load_league_config(league).values


def obsolete_config_entries() -> list[str]:
    """Sections/keys in `athc.ini` left over from the single-league layout."""
    raw = load_config()
    found: list[str] = []
    if "default_league" in raw.get("athc", {}):
        found.append("[athc] default_league")
    for section in raw:
        if section in _OBSOLETE_SECTIONS or section.startswith("league."):
            found.append(f"[{section}]")
    return found


def _available() -> str:
    names = available_leagues()
    if names:
        return f" Available: {', '.join(names)}."
    return f" No league folders under {leagues_dir()}."
```

- [ ] **Step 6: Update the `--league` help text in `src/athc/cli/__init__.py`**

Change line 57 to:

```python
        help="League name (a folder under leagues\\ in the config dir).",
```

- [ ] **Step 7: Run the config tests**

Run: `uv run pytest tests/integration/test_config.py -q`
Expected: all pass.

- [ ] **Step 8: Run the whole suite to see what else broke**

Run: `uv run pytest -q`
Expected: failures only in `test_gameplan_check.py` (ini-based tests), `test_profile_check.py` (ini-based tests) and `tests/unit/scheduler/test_config.py` (none yet — scheduler is untouched). Note them; Tasks 3-6 fix them. Coverage may dip below 92% until then; that is expected mid-plan.

- [ ] **Step 9: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml uv.lock src/athc/config.py src/athc/cli/__init__.py tests/conftest.py tests/integration/test_config.py
git commit -m "athc: resolve leagues from leagues\<NAME>\ folders"
```

---

### Task 2: `athc config set KEY VALUE`

**Files:**
- Modify: `src/athc/config.py` (add `set_config_value`)
- Create: `src/athc/cli/config/set.py`
- Modify: `src/athc/cli/config/__init__.py`
- Create: `tests/integration/test_config_set.py`

**Interfaces:**
- Consumes: `athc.config.league_dir`, `LeagueError`, `config_file`.
- Produces: `athc.config.set_config_value(key: str, value: str) -> Path` (returns the file written); Click command `athc.cli.config.set.set_` registered as `athc config set`.

- [ ] **Step 1: Write the failing tests**

```python
"""`athc config set` and the comment-preserving writer behind it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.config.set import set_
from athc.config import set_config_value

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

COMMENTED = """\
; athc settings -- edit to taste
[athc]
; the league the tools use
league = PNFL

[autocontinue]
; seconds before clicking
delay_before_continue = 1.0
"""


# ── set_config_value ──


def test_set_updates_value_and_keeps_comments(write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    set_config_value("league", "PCFL")
    text = ini.read_text(encoding="utf-8")
    assert "league = PCFL" in text
    assert "; athc settings -- edit to taste" in text
    assert "; the league the tools use" in text
    assert "; seconds before clicking" in text
    assert "delay_before_continue = 1.0" in text


def test_set_adds_missing_key(write_config: WriteConfig) -> None:
    ini = write_config("[athc]\n\n[autocontinue]\nhot_corner = true\n")
    set_config_value("league", "PNFL")
    text = ini.read_text(encoding="utf-8")
    assert "league = PNFL" in text
    assert text.index("league = PNFL") < text.index("[autocontinue]")
    assert "hot_corner = true" in text


def test_set_adds_missing_section(write_config: WriteConfig) -> None:
    ini = write_config("[autocontinue]\nhot_corner = true\n")
    set_config_value("league", "PNFL")
    text = ini.read_text(encoding="utf-8")
    assert "[athc]" in text
    assert "league = PNFL" in text
    assert "hot_corner = true" in text


def test_set_creates_missing_file(config_dir: Path) -> None:
    written = set_config_value("league", "PNFL")
    assert written == config_dir / "athc.ini"
    assert written.read_text(encoding="utf-8") == "[athc]\nleague = PNFL\n"


# ── athc config set (CLI) ──


def test_cli_sets_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PCFL")
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", "PCFL"])
    assert result.exit_code == 0
    assert result.output.strip() == "Set league = PCFL"
    assert "league = PCFL" in ini.read_text(encoding="utf-8")
    assert "; the league the tools use" in ini.read_text(encoding="utf-8")


def test_cli_rejects_unknown_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL")
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", "PCFL"])
    assert result.exit_code == 2
    assert "not found" in result.output
    assert "Available: PNFL" in result.output
    assert "league = PNFL" in ini.read_text(encoding="utf-8")  # untouched


def test_cli_rejects_unknown_key(runner, write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["colour", "blue"])
    assert result.exit_code == 2
    assert "unknown key 'colour'" in result.output
    assert "league" in result.output  # names the known keys
    assert "colour" not in ini.read_text(encoding="utf-8")


def test_cli_help_lists_known_keys(runner) -> None:
    result = runner.invoke(set_, ["--help"])
    assert result.exit_code == 0
    assert "league" in result.output


@pytest.mark.usefixtures("config_dir")
def test_group_lists_set(runner) -> None:
    from athc.cli.config import config as config_group

    result = runner.invoke(config_group, ["--help"])
    assert "set" in result.output
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/integration/test_config_set.py -q`
Expected: ImportError (`athc.cli.config.set` / `set_config_value` missing).

- [ ] **Step 3: Add `set_config_value` to `src/athc/config.py`**

Append after `obsolete_config_entries`:

```python
def set_config_value(key: str, value: str) -> Path:
    """Write `[athc] key = value` into `athc.ini`, keeping every comment and the
    file's layout (ConfigUpdater). Creates the file, section or key as needed.
    Returns the path written."""
    from configupdater import ConfigUpdater  # imported here: only this writer needs it

    path = config_file()
    updater = ConfigUpdater()
    if path.is_file():
        updater.read(path, encoding="utf-8")
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
```

ConfigUpdater 3.2 was probed for all four cases while writing this plan: a fresh file writes exactly `[athc]\nleague = PNFL\n`; `add_before.section("athc").space(1)` puts `[athc]` above the first section with one blank line after it; a new key is appended at the end of `[athc]` (after any blank line); an updated value keeps every comment line.

- [ ] **Step 4: Create `src/athc/cli/config/set.py`**

```python
"""`athc config set` -- write one setting into athc.ini, keeping its comments."""

from __future__ import annotations

import click

from athc.cli.config import config
from athc.config import LeagueError, league_dir, set_config_value

KNOWN_KEYS = ("league",)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def set_(key: str, value: str) -> None:
    """Set KEY to VALUE in athc.ini (comments are kept).

    Keys: league -- the league used when --league / ATHC_LEAGUE is not given
    (VALUE must be a folder under leagues\\ in the config dir).
    """
    if key not in KNOWN_KEYS:
        raise click.BadParameter(
            f"unknown key '{key}'; known keys: {', '.join(KNOWN_KEYS)}",
            param_hint="KEY",
        )
    if key == "league":
        try:
            league_dir(value)
        except LeagueError as error:
            raise click.BadParameter(str(error), param_hint="VALUE") from error
    set_config_value(key, value)
    click.echo(f"Set {key} = {value}")
```

- [ ] **Step 5: Register it in `src/athc/cli/config/__init__.py`**

Add after the `reveal` import line:

```python
from athc.cli.config import set as set  # noqa: E402
```

and change the group docstring to:

```python
    """Print the path to athc.ini, edit it, reveal it, or set a value in it."""
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/integration/test_config_set.py tests/integration/test_config.py -q`
Expected: all pass.

- [ ] **Step 7: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add src/athc/config.py src/athc/cli/config/set.py src/athc/cli/config/__init__.py tests/integration/test_config_set.py
git commit -m "athc: config set writes athc.ini without losing comments"
```

---

### Task 3: gameplan reads the league folder

**Files:**
- Modify: `src/athc/gameplan/config.py` (whole file)
- Modify: `src/athc/cli/gameplan/_common.py:136-139` (error text)
- Modify: `tests/integration/test_gameplan_check.py:274-287, 312-330`

**Interfaces:**
- Consumes: `athc.config.load_league_config`, `LeagueConfig`, `LeagueError`.
- Produces: `athc.gameplan.config.load_config(league: str | None = None, *, play_path: Path | None = None, playpool_rules: Path | None = None, rule_files: Sequence[Path] | None = None) -> Config` — unchanged signature; `Config(play_path: Path, playpool_rules: Path | None, rule_files: tuple[Path, ...])` unchanged.

- [ ] **Step 1: Rewrite the two ini-based tests and add three**

In `tests/integration/test_gameplan_check.py` replace `test_cli_no_rules` (lines 274-287) and `test_cli_resolves_from_league_ini` (lines 320-330) with:

```python
def test_cli_no_rules_needs_a_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    # --play-path and --playpool-rules given, --rules not: the rules come from
    # the league folder, so with no league configured that is the error.
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [
                str(GP_OFFENSE),
                "--play-path",
                str(PLAYS),
                "--playpool-rules",
                str(POOL_RULES),
            ],
        )
    assert result.exit_code == 2
    assert "no league selected" in caplog.text


def test_cli_no_rules_in_league_folder(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league("PNFL", f"[league]\nplay_path = {PLAYS}\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "rules\\gameplan.toml" in caplog.text


def test_cli_resolves_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # No flags: league from athc.ini, everything else from leagues/PNFL/.
    folder = make_league("PNFL", f"[league]\nplay_path = {PLAYS}\n")
    shutil.copy(GP_RULES, folder / "rules" / "gameplan.toml")
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    write_config("[athc]\nleague = PNFL\n")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output


def test_cli_gameplan_rules_list_layers_in_order(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    # A gameplan_rules list replaces the fixed file; the overlay is read last.
    folder = make_league(
        "PNFL",
        f"[league]\nplay_path = {PLAYS}\n"
        f"gameplan_rules =\n    {GP_RULES}\n    rules\\overlay.toml\n",
    )
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    (folder / "rules" / "overlay.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 1
    assert "violation(s)" in result.output


def test_cli_missing_listed_rules_file_is_reported(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league(
        "PNFL",
        f"[league]\nplay_path = {PLAYS}\ngameplan_rules =\n    rules\\gone.toml\n",
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 2
    assert "gone.toml" in caplog.text
```

Add to the imports at the top of the file: `import shutil` (if absent) and `MakeLeague = Callable[..., Path]` next to `WriteConfig`.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/integration/test_gameplan_check.py -q -k "league or no_rules"`
Expected: the new tests fail (old `[league.PNFL]` reading, `athc.ini [gameplan]` message).

- [ ] **Step 3: Rewrite `src/athc/gameplan/config.py`**

```python
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
) -> Config:
    """Assemble the gameplan config from the league folder.

    The `play_path` / `playpool_rules` / `rule_files` overrides win and stay
    CWD-relative; the league is resolved only when a value is still needed
    (LeagueError when it can't be). Playpool rules come from the league only when
    the league was resolved for something else, so `--play-path` alone needs none.
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
            raise ConfigFileError(
                "no play_path for the league; set play_path in "
                f"{league_cfg().dir / 'league.ini'} or pass --play-path"
            )
        play_path = resolved

    files = (
        tuple(rule_files)
        if rule_files is not None
        else league_cfg().rule_files(GAMEPLAN_RULES_KEY, GAMEPLAN_RULES_FILE)
    )

    if playpool_rules is None and cfg is not None:
        playpool_rules = cfg.rules_file(PLAYPOOL_RULES_FILE)

    return Config(play_path=play_path, playpool_rules=playpool_rules, rule_files=files)
```

- [ ] **Step 4: Update the "no rules" message in `src/athc/cli/gameplan/_common.py`**

Replace lines 136-139 with:

```python
        logger.error(
            "%s: no rules configured - nothing to check. "
            "Add rules\\gameplan.toml to the league folder or pass --rules.",
            prog,
        )
```

- [ ] **Step 5: Run the gameplan tests**

Run: `uv run pytest tests/integration/test_gameplan_check.py tests/integration/test_gameplan_replace_play.py tests/integration/test_gameplan_set_normals.py tests/integration/test_gameplan_set_specials.py -q`
Expected: all pass.

- [ ] **Step 6: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean. No change is needed in the four gameplan commands' error handling: each already wraps its `load_config(` call in `except (ConfigFileError, ValueError, ...)` (`check.py:82`, `replace_play.py:158`, `set_normals.py:94`, `set_specials.py:179`) and `LeagueError` is a `ValueError`.

- [ ] **Step 7: Commit**

```bash
git add src/athc/gameplan/config.py src/athc/cli/gameplan tests/integration/test_gameplan_check.py
git commit -m "gameplan: read play_path and rules from the league folder"
```

---

### Task 4: profile reads the league folder

**Files:**
- Modify: `src/athc/profile/config.py` (whole file)
- Modify: `src/athc/cli/profile/check.py:10, 26, 55-62, 79-83`
- Modify: `src/athc/cli/profile/_common.py:93-96`
- Modify: `tests/integration/test_profile_check.py:243-268, 300-318`

**Interfaces:**
- Consumes: `athc.config.load_league_config`, `LeagueError`; `athc.cli.league_option`.
- Produces: `athc.profile.config.load_config(league: str | None = None, *, rule_files: Sequence[Path] | None = None) -> Config`; `Config(rule_files: tuple[Path, ...])` unchanged; `athc profile check --league`.

- [ ] **Step 1: Rewrite the ini-based tests**

In `tests/integration/test_profile_check.py`:

Replace `test_cli_no_rules` (the test ending at line 251 whose body invokes `check` with only `OFF1`), `test_cli_rules_from_ini` (254-256), `test_cli_rules_from_ini_relative_to_config_dir` (259-267) and `test_cli_rules_override_ini` (270-277) with:

```python
def test_cli_no_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert "no league selected" in caplog.text


def test_cli_no_rules_in_league_folder(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league("PNFL")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1), "--league", "PNFL"])
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "rules\\profile.toml" in caplog.text


def test_cli_rules_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league("PNFL")
    shutil.copy(RULES_TOML, folder / "rules" / "profile.toml")
    write_config("[athc]\nleague = PNFL\n")
    assert runner.invoke(check, [str(OFF1)]).exit_code == 1


def test_cli_league_flag_picks_folder(runner, make_league: MakeLeague) -> None:
    make_league("PNFL")  # no rules -> would fail
    other = make_league("PCFL")
    shutil.copy(RULES_TOML, other / "rules" / "profile.toml")
    assert runner.invoke(check, [str(OFF1), "--league", "PCFL"]).exit_code == 1


def test_cli_profile_rules_list_relative_to_league_folder(
    runner, make_league: MakeLeague
) -> None:
    folder = make_league("PNFL", "[league]\nprofile_rules =\n    rules\\mine.toml\n")
    shutil.copy(RULES_TOML, folder / "rules" / "mine.toml")
    assert runner.invoke(check, [str(OFF1), "--league", "PNFL"]).exit_code == 1


def test_cli_rules_override_league(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league("PNFL", "[league]\nprofile_rules =\n    bogus.toml\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check, [str(OFF1), "--league", "PNFL", "--rules", str(RULES_TOML)]
        )
    assert result.exit_code == 1
    assert "bogus.toml" not in caplog.text
```

In `test_cli_missing_rules` (parametrized `via`), change the `ini` branch to:

```python
    if via == "ini":
        make_league("PNFL", f"[league]\nprofile_rules =\n    {missing}\n")
        args = [str(OFF1), "--league", "PNFL"]
```

and add `make_league: MakeLeague` to that test's parameters (drop `write_config` if no longer used there). Add `MakeLeague = Callable[..., Path]` near `WriteConfig`; `shutil` is already imported.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/integration/test_profile_check.py -q -k "league or rules"`
Expected: the new tests fail (`--league` is not an option yet; rules still read from `[profile]`).

- [ ] **Step 3: Rewrite `src/athc/profile/config.py`**

```python
"""Profile config: `rules\\profile.toml` (or the `profile_rules` list) from the
league folder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.config import load_league_config

PROFILE_RULES_FILE = "profile.toml"
PROFILE_RULES_KEY = "profile_rules"


class ConfigFileError(ValueError):
    """Raised when the profile config cannot be read."""


@dataclass(frozen=True)
class Config:
    rule_files: tuple[Path, ...] = ()


def load_config(
    league: str | None = None, *, rule_files: Sequence[Path] | None = None
) -> Config:
    """Rule files for `profile check`: the CLI `--rules` list wins; else the
    league folder's `profile_rules` list or fixed `rules\\profile.toml` (missing
    -> no rules). LeagueError when no league can be resolved."""
    if rule_files is not None:
        return Config(rule_files=tuple(rule_files))
    cfg = load_league_config(league)
    return Config(rule_files=cfg.rule_files(PROFILE_RULES_KEY, PROFILE_RULES_FILE))
```

- [ ] **Step 4: Add `--league` to `src/athc/cli/profile/check.py`**

Add `from athc.cli import league_option` and `from athc.config import LeagueError` to the imports. Insert `@league_option` directly above `@click.pass_context` (line 55). Add `league: str | None,` as the last parameter of `check`. Replace lines 79-83 with:

```python
    try:
        config = load_config(league, rule_files=list(rule_overrides) or None)
    except (ConfigFileError, LeagueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)
```

- [ ] **Step 5: Update the "no rules" message in `src/athc/cli/profile/_common.py`**

Replace lines 93-96 with:

```python
        logger.error(
            "%s: no rules configured - nothing to check. "
            "Add rules\\profile.toml to the league folder or pass --rules.",
            prog,
        )
```

- [ ] **Step 6: Run the profile tests**

Run: `uv run pytest tests/integration -q -k profile`
Expected: all pass.

- [ ] **Step 7: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add src/athc/profile/config.py src/athc/cli/profile tests/integration/test_profile_check.py
git commit -m "profile: check takes --league and reads rules from the league folder"
```

---

### Task 5: convert-pdb reads the league folder

**Files:**
- Modify: `src/athc/pdbtoexcel/config.py:1-6, 59-87`
- Modify: `src/athc/pdbtoexcel/main.py:11-33`
- Modify: `src/athc/cli/convert_pdb.py:11, 67-77, 84-97, 118-130`
- Test: `tests/integration/test_convert_pdb.py` (append)

**Interfaces:**
- Consumes: `athc.config.load_league_config`; `athc.cli.league_option`.
- Produces: `athc.pdbtoexcel.config.load_config(league: str | None = None, *, play_path: str | None = None, playpool_rules: Path | None = None) -> Config`; `athc.pdbtoexcel.main.convert_pdb(..., league: str | None = None, ...)`; `athc convert-pdb --league`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_convert_pdb.py` (add the imports it lacks: `from collections.abc import Callable`, `from pathlib import Path`, `from athc.pdbtoexcel import config as pdbtoexcel_config`, `from athc.cli.convert_pdb import convert_pdb`):

```python
MakeLeague = Callable[..., Path]


def test_config_play_path_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = plays\n")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    cfg = pdbtoexcel_config.load_config("PNFL")
    assert cfg.play_path == str(folder / "plays")
    assert cfg.playpool_rules == folder / "rules" / "playpool.toml"


def test_config_play_path_override_needs_no_league(config_dir: Path) -> None:
    cfg = pdbtoexcel_config.load_config(play_path="D:/plays")
    assert cfg.play_path == "D:/plays"
    assert cfg.playpool_rules is None


def test_config_missing_play_path_is_empty(make_league: MakeLeague) -> None:
    make_league("PNFL")
    assert pdbtoexcel_config.load_config("PNFL").play_path == ""


def test_cli_has_league_option(runner) -> None:
    result = runner.invoke(convert_pdb, ["--help"])
    assert result.exit_code == 0
    assert "--league" in result.output


def test_cli_no_league_is_one_line_error(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pdb = tmp_path / "x.pdb"
    pdb.write_bytes(b"")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(convert_pdb, [str(pdb), str(tmp_path / "out.xlsx")])
    assert result.exit_code == 1
    assert "no league selected" in caplog.text
```

(`runner` and `logging`/`pytest` imports: use the ones the file already has; add any missing.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/integration/test_convert_pdb.py -q -k "league or config"`
Expected: fail (`load_config` has no positional `league`; `--league` missing).

- [ ] **Step 3: Rewrite `load_config` in `src/athc/pdbtoexcel/config.py`**

Change the module docstring's first line to: `"""convert-pdb config: play_path and rules\\playpool.toml from the league folder, plus the default category order.` Remove `import configparser` and `from athc.config import CONFIG_FILE, config_dir, resolve_path`; add `from athc.config import load_league_config`. Delete `SECTION = "convert-pdb"` and the `_read` function. Replace `load_config` with:

```python
def load_config(
    league: str | None = None,
    *,
    play_path: str | None = None,
    playpool_rules: Path | None = None,
) -> Config:
    """Locate the play pool. `play_path` / `playpool_rules` (CLI overrides, kept
    CWD-relative) win; otherwise both come from the league folder, resolved only
    when `play_path` is not given (LeagueError when it can't be). A league folder
    without `play_path` yields "" and the caller reports it."""
    if play_path is None:
        cfg = load_league_config(league)
        resolved = cfg.path("play_path")
        play_path = str(resolved) if resolved else ""
        if playpool_rules is None:
            playpool_rules = cfg.rules_file("playpool.toml")
    return Config(play_path=play_path, playpool_rules=playpool_rules)
```

Keep `ConfigFileError`, `Config` (its boolean fields now always take their defaults) and the category-order helpers as they are.

- [ ] **Step 4: Thread `league` through `src/athc/pdbtoexcel/main.py`**

Add `league: str | None = None,` after `output_path: str,` in the signature. Change the `load_config(` call to `load_config(league, play_path=play_path_override, playpool_rules=playpool_rules_override)`. Change the error text to:

```python
            f"(set play_path in the league's league.ini or pass --play-path)"
```

- [ ] **Step 5: Add `--league` to `src/athc/cli/convert_pdb.py`**

Add `from athc.cli import league_option`. Insert `@league_option` directly above `@click.pass_context` (line 84). Add `league: str | None,` after `playpool_rules: Path | None,` in the parameters. Pass `league=league,` to `run_conversion(` right after `output_path=str(outputfile),`. Change the `--play-path` help to `"Play-files directory (overrides the league's play_path)."` and the `--playpool-rules` help to `"Playpool rules TOML for play tags (overrides the league's rules\\playpool.toml)."`. The existing `except (OSError, ValueError, XlsxWriterException)` already catches `LeagueError` (a `ValueError`).

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/integration/test_convert_pdb.py -q`
Expected: all pass.

- [ ] **Step 7: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add src/athc/pdbtoexcel src/athc/cli/convert_pdb.py tests/integration/test_convert_pdb.py
git commit -m "convert-pdb: takes --league and reads the play pool from the league folder"
```

---

### Task 6: scheduler reads the league folder

**Files:**
- Modify: `src/athc/scheduler/config.py:16-17, 132-145, 192-209`
- Modify: `src/athc/scheduler/main.py:29-51`
- Modify: `src/athc/cli/generate_schedule.py:13-18, 43-49, 65-80`
- Modify: `tests/unit/scheduler/test_config.py:18-34, 105-108, 236-250, 366-370, 428-430`
- Modify: `tests/integration/test_generate_schedule.py:67-72, 82-84, 108, 143`

**Interfaces:**
- Consumes: `athc.config.load_league_config`, `LeagueError`, `STANDINGS_DIR`.
- Produces: `scheduler_rules_path(league: str | None = None) -> Path`, `load_scheduler_config(league: str | None = None) -> SchedulerConfig`, `find_config_path(league: str | None = None) -> Path`, `find_league_path(season: int, league: str | None = None) -> Path`; `athc.scheduler.main.generate_schedule(*, season, config_path, league_path, output_dir, seed, time_limit, command_line, league: str | None = None)`; `athc generate-schedule --league`.

- [ ] **Step 1: Update the scheduler unit tests**

In `tests/unit/scheduler/test_config.py`:

Replace lines 18-34 (`RELEASE`, `SEASON`, the comment block, `_write_scheduler_toml`) with:

```python
RELEASE = Path(__file__).resolve().parents[3] / "release"
SEASON = 2048  # shipped standings file is leagues/PNFL/standings/2048.league.ini
LEAGUE = "TST"

# ---------------------------------------------------------------------------
# Scheduler tunables live in leagues/<NAME>/rules/scheduler.toml; league data is a
# separate <season>.league.ini under leagues/<NAME>/standings/: [DivisionStandings]
# (per-division teams in finish order -- this defines division membership) plus
# [OverallStandings] (overall 1-18). Tests derive invalid variants from VALID_LEAGUE.
# ---------------------------------------------------------------------------


def _league_folder(config_dir: Path) -> Path:
    """`leagues/TST/` with `rules/` and `standings/`, and athc.ini naming it."""
    folder = config_dir / "leagues" / LEAGUE
    (folder / "rules").mkdir(parents=True, exist_ok=True)
    (folder / "standings").mkdir(exist_ok=True)
    (config_dir / "athc.ini").write_text(f"[athc]\nleague = {LEAGUE}\n", encoding="utf-8")
    return folder


def _write_scheduler_toml(config_dir: Path, body: str) -> Path:
    path = _league_folder(config_dir) / "rules" / "scheduler.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path
```

Every `load_scheduler_config()` call in tests that first calls `_write_scheduler_toml` keeps working. Two tests call it with no file: change `test_load_scheduler_config_defaults_when_no_file` to:

```python
def test_load_scheduler_config_defaults_when_no_file(config_dir: Path) -> None:
    _league_folder(config_dir)  # league exists, rules/scheduler.toml does not
    cfg = load_scheduler_config()
```

(keep its existing assertions), and add:

```python
def test_load_scheduler_config_needs_a_league(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    with pytest.raises(LeagueError, match="no league selected"):
        load_scheduler_config()
```

with `from athc.config import LeagueError` added to the imports. Any other test in the file that calls `load_scheduler_config()` without first calling `_write_scheduler_toml` (check `test_load_scheduler_config_defaults_when_keys_missing`: it writes a file, fine) must call `_league_folder(config_dir)` first.

Replace lines 238-250 (the three path-resolution tests) with:

```python
def test_find_config_path_returns_scheduler_rules_file(config_dir: Path) -> None:
    # The scheduler config is optional, so this never raises -- it names the path.
    folder = _league_folder(config_dir)
    assert find_config_path() == folder / "rules" / "scheduler.toml"


def test_find_config_path_takes_explicit_league(config_dir: Path) -> None:
    _league_folder(config_dir)
    other = config_dir / "leagues" / "OTHER"
    other.mkdir()
    assert find_config_path("OTHER") == other / "rules" / "scheduler.toml"


def test_find_league_path_errors_when_none_exist(config_dir: Path) -> None:
    folder = _league_folder(config_dir)
    with pytest.raises(ConfigError) as exc:
        find_league_path(SEASON)
    assert str(folder / "standings" / f"{SEASON}.league.ini") in str(exc.value)


def test_find_league_path_resolves_season_file_in_standings(config_dir: Path) -> None:
    folder = _league_folder(config_dir)
    present = _write(folder / "standings" / f"{SEASON}.league.ini", VALID_LEAGUE)
    assert find_league_path(SEASON) == present
```

Change both `load_league(RELEASE / f"{SEASON}.league.ini")` calls (lines 368 and 429) to `load_league(RELEASE / "leagues" / "PNFL" / "standings" / f"{SEASON}.league.ini")`. These two tests fail until Task 7 moves the files; that is expected.

Update `tests/unit/scheduler/test-matrix-config-loading.md` rows: rename `rules/PNFL.scheduler.toml` to `leagues/<NAME>/rules/scheduler.toml`, add a row `| No league resolvable | LeagueError | test_load_scheduler_config_needs_a_league | ☑ |`, and rename the `find_league_path` rows to the new test names.

- [ ] **Step 2: Update the golden integration test**

In `tests/integration/test_generate_schedule.py` replace `_write_config` (lines 67-72) with:

```python
def _write_config(config_dir: Path) -> Path:
    """Install the committed league + scheduler rules as leagues/PNFL/ in an athc
    config dir and name it in athc.ini. Returns the standings file."""
    folder = config_dir / "leagues" / "PNFL"
    (folder / "rules").mkdir(parents=True)
    (folder / "standings").mkdir()
    standings = folder / "standings" / f"{SEASON}.league.ini"
    shutil.copy(LEAGUE, standings)
    shutil.copy(SCHEDULER_RULES, folder / "rules" / "scheduler.toml")
    (config_dir / "athc.ini").write_text("[athc]\nleague = PNFL\n", encoding="utf-8")
    return standings
```

Change line 104 to `standings = _write_config(config_dir)` and line 108 to `league = load_league(standings)`. In `_bless`, change line 139 to `standings = _write_config(config)` and line 143 to `league = load_league(standings)`.

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/unit/scheduler/test_config.py -q`
Expected: the path-resolution and no-league tests fail (paths still `rules/PNFL.scheduler.toml` and `<season>.league.ini` at the config root).

- [ ] **Step 4: Update `src/athc/scheduler/config.py`**

Change the imports to `from athc.config import STANDINGS_DIR, load_league_config`. Replace lines 16-17 with:

```python
LEAGUE_FILE = "league.ini"  # actual file is "standings/<season>.league.ini"
SCHEDULER_RULES_FILE = "scheduler.toml"  # in the league folder's rules/
```

Replace `scheduler_rules_path` (132-137) with:

```python
def scheduler_rules_path(league: str | None = None) -> Path:
    """The scheduler tunables file, `rules/scheduler.toml` in the league folder
    (may not exist; values then default). LeagueError when no league resolves."""
    return load_league_config(league).rules_file_path(SCHEDULER_RULES_FILE)
```

`LeagueConfig.rules_file` returns None when absent, but this path must be named even when missing, so add this method to `LeagueConfig` in `src/athc/config.py` (next to `rules_file`):

```python
    def rules_file_path(self, filename: str) -> Path:
        """`rules\\<filename>` in the league folder, whether or not it exists."""
        return self.dir / RULES_DIR / filename
```

and make `rules_file` use it: `candidate = self.rules_file_path(filename)`.

Change `load_scheduler_config()` to `load_scheduler_config(league: str | None = None)`, its docstring's file name to `rules/scheduler.toml`, and `path = scheduler_rules_path()` to `path = scheduler_rules_path(league)`. Replace lines 192-209 with:

```python
def find_config_path(league: str | None = None) -> Path:
    """Scheduler config path, for report provenance (may not exist)."""
    return scheduler_rules_path(league)


def find_league_path(season: int, league: str | None = None) -> Path:
    """`standings/<season>.league.ini` in the league folder; ConfigError if missing."""
    return _require_season_file(season, LEAGUE_FILE, "league", league)


def _require_season_file(
    season: int, suffix: str, label: str, league: str | None
) -> Path:
    path = load_league_config(league).dir / STANDINGS_DIR / f"{season}.{suffix}"
    if not path.is_file():
        raise ConfigError(
            f"No {label} file for season {season}. Expected:\n  {path}\n"
            f"Run 'athc config path' to find the config dir, then add the file."
        )
    return path
```

- [ ] **Step 5: Thread `league` through `src/athc/scheduler/main.py`**

Add `league: str | None = None,` as the last keyword parameter of `generate_schedule`, and change line 45 to `scheduler_config = load_scheduler_config(league)  # config_path = report provenance`.

- [ ] **Step 6: Add `--league` to `src/athc/cli/generate_schedule.py`**

Add `from athc.cli import league_option` and `from athc.config import LeagueError`. Insert `@league_option` directly above `@click.pass_context`. Add `league: str | None,` as the last parameter. Change the body to:

```python
    try:
        league_path = find_league_path(season, league)
        config = find_config_path(league)
        run_generate(
            season=season,
            config_path=config,
            league_path=league_path,
            output_dir=Path.cwd(),
            seed=chosen_seed,
            time_limit=time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
            league=league,
        )
    except (ConfigError, LeagueError, OSError) as error:
```

Change the docstring's file line to `standings\\<season>.league.ini  in the league folder: [DivisionStandings] ...` (keep the rest of the description).

- [ ] **Step 7: Run the scheduler tests**

Run: `uv run pytest tests/unit/scheduler tests/integration/test_generate_schedule.py -q`
Expected: all pass except the two `test_release_*` tests in `tests/unit/scheduler/test_config.py` (files move in Task 7).

- [ ] **Step 8: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add src/athc/config.py src/athc/scheduler src/athc/cli/generate_schedule.py tests/unit/scheduler tests/integration/test_generate_schedule.py
git commit -m "scheduler: generate-schedule takes --league and reads standings and rules from the league folder"
```

---

### Task 7: `dev\` and `release\` move to the league layout

**Files:**
- Move (git mv): `dev/rules/PNFL.gameplan.toml` → `dev/leagues/PNFL/rules/gameplan.toml`; same for `profile`, `playpool`, `scheduler`; `dev/2045.league.ini` … `dev/2049.league.ini` → `dev/leagues/PNFL/standings/`. Same five+four moves under `release/`.
- Create: `dev/leagues/PNFL/league.ini`, `release/leagues/PNFL/league.ini`
- Modify: `dev/athc.ini`, `release/athc.ini`
- Modify: `tests/integration/conftest.py:17-19`
- Modify: `tests/integration/test_config.py` (re-add release-loader tests)

**Interfaces:**
- Consumes: every loader from Tasks 1-6.
- Produces: the shipped layout the installer (Task 8) and docs (Task 9) describe.

- [ ] **Step 1: Write the release-loader tests**

Append to `tests/integration/test_config.py`:

```python
# ── shipped release/: every loader reads it as installed ──

RELEASE = Path(__file__).resolve().parents[2] / "release"


@pytest.fixture
def release_config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point config lookup at the shipped `release/` folder itself (overriding the
    autouse temp dir). `ATHC_LEAGUE` is cleared so the league comes from athc.ini,
    as on a fresh install."""
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(RELEASE))
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)


@pytest.mark.usefixtures("release_config_dir")
def test_release_league_loads() -> None:
    cfg = load_league_config()  # [athc] league -> leagues/PNFL/
    assert cfg.name == "PNFL"
    assert cfg.values["play_path"]
    assert (cfg.dir / "standings").is_dir()


@pytest.mark.usefixtures("release_config_dir")
def test_release_has_no_obsolete_entries() -> None:
    assert obsolete_config_entries() == []


@pytest.mark.usefixtures("release_config_dir")
def test_release_autocontinue_section_loads() -> None:
    from athc.autocontinue import config as autocontinue_config

    autocontinue_config.load_config()


@pytest.mark.usefixtures("release_config_dir")
def test_release_gameplan_config_loads() -> None:
    from athc.gameplan import config as gameplan_config

    cfg = gameplan_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_profile_config_loads() -> None:
    from athc.profile import config as profile_config

    cfg = profile_config.load_config()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_convert_pdb_config_loads() -> None:
    from athc.pdbtoexcel import config as pdbtoexcel_config

    cfg = pdbtoexcel_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()


@pytest.mark.usefixtures("release_config_dir")
def test_release_scheduler_files_load() -> None:
    from athc.scheduler.config import find_league_path, load_scheduler_config

    load_scheduler_config()
    assert find_league_path(2048).is_file()


def test_dev_mirrors_release_layout() -> None:
    dev = RELEASE.parent / "dev"
    for rel in (
        "athc.ini",
        "leagues/PNFL/league.ini",
        "leagues/PNFL/rules/gameplan.toml",
        "leagues/PNFL/rules/profile.toml",
        "leagues/PNFL/rules/playpool.toml",
        "leagues/PNFL/rules/scheduler.toml",
        "leagues/PNFL/standings/2048.league.ini",
    ):
        assert (dev / rel).is_file(), rel
        assert (RELEASE / rel).is_file(), rel
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/integration/test_config.py -q -k "release or dev_mirrors"`
Expected: fail (no `leagues/` folder yet).

- [ ] **Step 3: Move the files**

From the repo root, one command per call:

```bash
git mv dev/rules/PNFL.gameplan.toml dev/leagues/PNFL/rules/gameplan.toml
```

`git mv` needs the target folder: create `dev/leagues/PNFL/rules` and `dev/leagues/PNFL/standings` first (`mkdir -p`), then repeat for `PNFL.profile.toml` → `profile.toml`, `PNFL.playpool.toml` → `playpool.toml`, `PNFL.scheduler.toml` → `scheduler.toml`, and for each of `2045` … `2049`:

```bash
git mv dev/2045.league.ini dev/leagues/PNFL/standings/2045.league.ini
```

Then the same nine moves under `release/`. Afterwards `dev/rules/` and `release/rules/` must be empty and gone (`git mv` removes them when empty; delete any leftover empty folder).

- [ ] **Step 4: Write the two `league.ini` files**

`dev/leagues/PNFL/league.ini`:

```ini
[league]
play_path = E:\SIERRA\FbPro98\PNFL
db_path = E:\PNFL\Game Log Database\49W4\pnfl_athc.db
```

`release/leagues/PNFL/league.ini`:

```ini
; PNFL league settings. Rules live in rules\ (gameplan.toml, profile.toml,
; playpool.toml, scheduler.toml) and season standings in standings\
; (<season>.league.ini). Reinstalling never overwrites this file.
;
; REQUIRED for gameplan/profile/convert-pdb -- your FbPro98 league plays folder.
[league]
play_path = C:\SIERRA\FBPRO98\PNFL
```

- [ ] **Step 5: Rewrite `dev/athc.ini`**

```ini
; Dev config for running athc from source. Point athc at this folder:
;   $env:ATHC_CONFIG_DIR = "$PWD\dev"
;
; Structural twin of release/athc.ini: same sections/keys. Per-league settings,
; rules and standings live under leagues\<NAME>\ (see leagues\PNFL\league.ini).

[athc]
league = PNFL

[autocontinue]
mouse_move_duration = 0.0
delay_before_continue = 1.0
hot_corner = true
```

- [ ] **Step 6: Rewrite `release/athc.ini`**

```ini
; athc settings -- a ready-to-run PNFL setup. This file is yours: edit values to
; taste; reinstalling never overwrites it (delete it to get a fresh copy).
;
; Each league is a folder under leagues\ next to this file, holding its
; league.ini (play_path), rules\ (gameplan.toml, profile.toml, playpool.toml,
; scheduler.toml) and standings\ (<season>.league.ini). The one thing you must
; set is play_path in leagues\PNFL\league.ini: your FbPro98 league plays folder.
;
; Every section/key is optional and falls back to a sensible default. This file
; itself documents every setting; 'athc <command> --help' covers the rest.

[athc]
; league used when --league / ATHC_LEAGUE is not given; change it with
;   athc config set league NAME
league = PNFL

; autocontinue requires its settings (a clicking watcher shouldn't guess timings).
[autocontinue]
; seconds to move the mouse to the button (0.0 = instant)
mouse_move_duration = 0.0
; seconds before clicking; 0.0 = instant, -1.0 = find but don't click
delay_before_continue = 1.0
; stop the watcher when the mouse hits the top-left corner (default on)
hot_corner = true
```

- [ ] **Step 7: Point the test fixtures at the new paths**

In `tests/integration/conftest.py` replace lines 17-19 with:

```python
_RELEASE_RULES = (
    Path(__file__).resolve().parents[2] / "release" / "leagues" / "PNFL" / "rules"
)
GP_RULES = _RELEASE_RULES / "gameplan.toml"
POOL_RULES = _RELEASE_RULES / "playpool.toml"
```

Search `tests/` for any other `release/rules`, `PNFL.gameplan.toml`, `PNFL.profile.toml`, `PNFL.playpool.toml`, `PNFL.scheduler.toml` or `release / f"{SEASON}` literal (`grep -rn "PNFL\.\(gameplan\|profile\|playpool\|scheduler\)\.toml\|release/rules" tests/`) and update each to the new path.

- [ ] **Step 8: Run the whole suite**

Run: `uv run pytest -q`
Expected: all pass, coverage ≥ 92%.

- [ ] **Step 9: Lint, format, type-check**

Run: `uv run ruff check .`
Run: `uv run ruff format .`
Run: `uv run pyright`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add -A dev release tests
git commit -m "build: dev and release configs move to the leagues\<NAME>\ layout"
```

---

### Task 8: Installer and release build copy `leagues\`

**Files:**
- Modify: `release/install.bat:28-45`
- Modify: `release/release-build.ps1:47-65`

**Interfaces:**
- Consumes: the layout from Task 7.
- Produces: a zip whose root holds `athc.ini`, `install.bat`, the wheel, `docs\` and `leagues\`; an install that deploys them with the ownership rules below.

No automated test covers these scripts (Windows batch/PowerShell, no test harness in the repo). Verify by hand in Step 3.

- [ ] **Step 1: Update `release/install.bat`**

Replace lines 28-45 (from `REM Deploy files to the athc config folder.` through the `for %%f in (*.league.ini)` line) with:

```bat
REM Deploy files to the athc config folder.
REM   - docs\ and each league's rules\ are shipped reference material -> always
REM     overwrite (no guard). Users copy a rule file before editing their own.
REM   - athc.ini, each league's league.ini and standings\ are user-owned ->
REM     guarded with 'if not exist' so edits survive a reinstall. New tool
REM     sections take effect via in-code defaults; the freshly-extracted athc.ini
REM     in this zip is the always-current reference of every setting.
set "DEST=%LOCALAPPDATA%\athc"
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%\docs" mkdir "%DEST%\docs"

copy /Y "docs\*.txt" "%DEST%\docs\" >NUL
if not exist "%DEST%\athc.ini" copy /Y "athc.ini" "%DEST%\athc.ini" >NUL

for /D %%L in (leagues\*) do (
    if not exist "%DEST%\%%L\rules" mkdir "%DEST%\%%L\rules"
    if not exist "%DEST%\%%L\standings" mkdir "%DEST%\%%L\standings"
    copy /Y "%%L\rules\*.toml" "%DEST%\%%L\rules\" >NUL
    if not exist "%DEST%\%%L\league.ini" copy /Y "%%L\league.ini" "%DEST%\%%L\league.ini" >NUL
    for %%f in ("%%L\standings\*.league.ini") do if not exist "%DEST%\%%L\standings\%%~nxf" copy /Y "%%f" "%DEST%\%%L\standings\%%~nxf" >NUL
)
```

- [ ] **Step 2: Update `release/release-build.ps1`**

Replace lines 53-65 (the `*.league.ini` loop and the `"docs", "rules"` loop) with:

```powershell
# Stage the docs\ folder (README + per-command references) and the leagues\
# folder (each league's league.ini, rules\ and standings\).
foreach ($dir in "docs", "leagues") {
    Write-Host "  Staging: $dir\"
    Copy-Item (Join-Path $scriptRoot $dir) $staging -Recurse
}
```

- [ ] **Step 3: Verify by hand**

Run: `powershell -ExecutionPolicy Bypass -File release/release-build.ps1`
Expected: `dist/athc-<ver>/` contains `athc.ini`, `install.bat`, the wheel, `docs\`, `leagues\PNFL\league.ini`, `leagues\PNFL\rules\*.toml` (4 files), `leagues\PNFL\standings\*.league.ini` (5 files), and no `rules\` at the root.

Then, in a scratch copy of that staged folder, run the deploy part only against a temp folder: set `LOCALAPPDATA` to a temp dir for one shell (`cmd /c "set LOCALAPPDATA=<temp>&& install.bat"` would also run `uv tool install`; instead copy lines 34-49 of the new `install.bat` into a scratch `deploy-test.bat`, set `DEST` to a temp folder, run it twice). Expected after run 1: the tree above under `<temp>`. Edit `<temp>\leagues\PNFL\league.ini` and `<temp>\athc.ini`, run again: both edits survive; a change to `<temp>\leagues\PNFL\rules\gameplan.toml` is overwritten. Delete the scratch script; do not commit it.

- [ ] **Step 4: Commit**

```bash
git add release/install.bat release/release-build.ps1
git commit -m "build: installer and release build ship leagues\ instead of rules\ and season files"
```

---

### Task 9: Docs, CHANGELOG, STATUS

**Files:**
- Modify: `docs/design/config.md`, `docs/design/cli.md:155-176`, `docs/design/reference-projects.md:44-72`, `docs/design/installer.md:15-60`, `docs/design/overview.md:63-65`
- Modify: `docs/gameplan/README.md:58-72`, `docs/gameplan/ARCHITECTURE.md:50-57, 93`, `docs/profile/README.md:77-83`, `docs/profile/ARCHITECTURE.md:12, 40, 53`, `docs/playpool/ARCHITECTURE.md:66`, `docs/scheduler/README.md:20, 38-39`, `docs/scheduler/ARCHITECTURE.md:50-51`, `docs/scheduler/phase-2-schedule.md:13`
- Modify: `README.md:21-23`, `release/docs/README.txt:48-58`, `release/docs/COMMANDS.txt:13-36, 148-167` (+ a new section), `release/docs/SCHEDULER-COMMANDS.txt:28, 40`
- Modify: `tests/integration/README.md:45-47, 80, 405, 411-430`, `STATUS.md:14-30, 108, 150`, `CHANGELOG.md:5`

Documentation is very simple, clear and high-level. No test run for this task (docs only).

- [ ] **Step 1: `docs/design/config.md`**

Rewrite the "Section taxonomy", "Example", "Rule-file paths" and "Multi-league selection" sections to:

````markdown
## Layout

One folder per league under the config dir; `athc.ini` holds only app-wide settings.

```
athc.ini                      app-wide settings + the selected league
leagues\
  PNFL\
    league.ini                per-league settings ([league] play_path, …)
    rules\                    gameplan.toml, profile.toml, playpool.toml, scheduler.toml
    standings\                <season>.league.ini
  PCFL\                       same fixed names
```

Fixed, well-known file names inside a league folder; nothing lists them in config. A league is any folder under `leagues\`; its name is the folder name. Per-league values that are not files (`play_path`; athc-admin's `db_path`, `log_dir`) go in `league.ini` under `[league]`; relative paths there resolve against the league folder.

Precedent: OBS Studio (`basic/profiles/<Name>/basic.ini`), Kodi (`profiles/<name>/`), Hugo (`config/_default/` + `config/<env>/`).

## `athc.ini`

```ini
[athc]
league = PNFL

[autocontinue]
mouse_move_duration = 0.0
delay_before_continue = 1.0
hot_corner = true
```

`[athc] league` is edited by hand or with `athc config set league NAME`, which validates the folder and rewrites the file through ConfigUpdater so comments survive (`configparser` drops them on write). Obsolete entries from the single-league layout (`default_league`, `[gameplan]`, `[profile]`, `[convert-pdb]`, `[league.*]`) log one warning and are ignored.

## Rule files

Each tool reads its one fixed file under the league's `rules\`. An optional multi-line list in `league.ini` (`gameplan_rules`, `profile_rules`) replaces it with an ordered set, later files overriding earlier ones. CLI `--rules` still wins and stays CWD-relative.

## Multi-league selection

League-aware commands take `--league NAME` (shared decorator in [cli.md](cli.md)). Priority, highest wins:

1. `--league NAME` (one run, never persisted).
2. `ATHC_LEAGUE`.
3. `[athc] league`.
4. Error naming `athc config set league` and listing the folders under `leagues\`.
````

Update the "Per-tool config code" example to call `load_league_config(league)` and use `cfg.path("play_path")` / `cfg.rule_files("gameplan_rules", "gameplan.toml")`. Delete the sentence "No stateful 'current league' pointer — explicit beats hidden state for non-dev users."

- [ ] **Step 2: `docs/design/cli.md`**

Line 157: replace `(gameplan, profile, playcatalog)` with `(gameplan, profile, convert-pdb, generate-schedule)` and drop `generate-schedule` from the "Non-league tools" list. Line 170 help text → `"League name (a folder under leagues\\ in the config dir)."`. Line 174 → `` Selection priority (highest first): `--league` flag → `ATHC_LEAGUE` env → `[athc] league` in config → error. Full rules in [config.md](config.md). ``

- [ ] **Step 3: `docs/design/reference-projects.md`**

Replace the "Multi-profile config" section (44-72) with:

```markdown
## Multi-profile config (one folder per named profile)

For athc's `leagues\<NAME>\` folders and the stored current league.

- **OBS Studio** — `basic/profiles/<Name>/basic.ini`; the current profile is one key in a global ini. Direct model for the folder-per-league layout with fixed inner file names.
- **Kodi** — `profiles/<name>/` plus a registry naming the last-loaded profile.
- **Calibre** — libraries are folders; the current one is `library_path` in the app-wide prefs. Precedent for keeping the pointer in the main settings file.
- **pip / gcloud / poetry** — `config set KEY VALUE` writes one setting; precedent for `athc config set league NAME`.

**Adaptation for athc**: fixed file names inside each league folder; `[athc] league` in `athc.ini`; `--league` per command; priority `--league` → `ATHC_LEAGUE` → `[athc] league` → error. Full design: [config.md](config.md).
```

In the "Direct design influences" table replace the `Multi-league named sections + [DEFAULT] cascade` row with `| Folder per league, fixed inner file names | OBS Studio, Kodi, Hugo |` and add `| Current league as a key in the main settings file | Calibre |` and `| `config set KEY VALUE` | pip, gcloud, poetry |`.

- [ ] **Step 4: `docs/design/installer.md`**

Replace the table (21-26) with:

```markdown
| File | First install | Reinstall |
|---|---|---|
| `athc.ini` | seeded | **preserved** (user edits survive) |
| `leagues\<NAME>\league.ini` | seeded | **preserved** |
| `leagues\<NAME>\standings\*.league.ini` | seeded | **preserved** (commish edits survive) |
| `leagues\<NAME>\rules\*.toml` | created | overwritten |
| `docs\*.txt` | created | overwritten |
```

Line 28: replace the sentence about config-relative rule paths and `[league.PNFL] play_path` with: "The seeded `athc.ini` selects PNFL; the only value a user must edit is `play_path` in `leagues\PNFL\league.ini` (their FbPro98 plays folder)." Lines 51 and 57: replace "the season config files (`<season>.league.ini`), and the `docs\` + `rules\` folders" with "and the `docs\` + `leagues\` folders".

- [ ] **Step 5: `docs/design/overview.md`**

Line 63 → "- `athc.ini` holds app-wide sections (`[athc]`, `[autocontinue]`); everything per-league lives in `leagues\<NAME>\` (`league.ini`, `rules\`, `standings\`)." Line 65 → "- Tools that operate on league-specific data take a `--league NAME` option; `athc config set league NAME` stores the default."

- [ ] **Step 6: Tool docs**

- `docs/gameplan/README.md` 64-65 → "- `leagues\<NAME>\rules\gameplan.toml` (or a `gameplan_rules` list in `league.ini`) — the rules." and "- `leagues\<NAME>\league.ini` `play_path` (pool dir) and `rules\playpool.toml` (optional filename-filter TOML); league picked by `--league` / `ATHC_LEAGUE` / `[athc] league`." Line 72 link → `release/leagues/PNFL/rules/gameplan.toml`.
- `docs/gameplan/ARCHITECTURE.md` 50 link → `release/leagues/PNFL/rules/gameplan.toml`; 56-57 same two bullets as above.
- `docs/profile/README.md` 77 → `rules\profile.toml` example under `leagues\PNFL\`; 83 link → `release/leagues/PNFL/rules/profile.toml`.
- `docs/profile/ARCHITECTURE.md` 12 → `# rules\profile.toml from the league folder`; 40 link → `release/leagues/PNFL/rules/profile.toml`; 53 → "`leagues\<NAME>\rules\profile.toml`, or a `profile_rules` list in `league.ini` (config found via".
- `docs/playpool/ARCHITECTURE.md` 66 → `release/leagues/PNFL/rules/playpool.toml`.
- `docs/scheduler/README.md` 20 → "`--season` is required and picks `standings\<season>.league.ini` in the league folder (`--league`, else `[athc] league`)"; 38 → `rules/scheduler.toml` in the league folder; 39 → `standings/<season>.league.ini`.
- `docs/scheduler/ARCHITECTURE.md` 50-51 and `docs/scheduler/phase-2-schedule.md` 13: same path renames.

- [ ] **Step 7: End-user docs**

- `README.md` 23 → "`athc` reads `%LOCALAPPDATA%\athc\athc.ini` for app-wide settings and `leagues\<NAME>\` for each league; missing file or section falls back to defaults."
- `release/docs/README.txt` FIRST-TIME SETUP (51-58):

```
athc ships configured for PNFL out of the box. The one thing you must
set is your plays folder: open leagues\PNFL\league.ini in your settings
folder (see below) and set play_path to your FbPro98 league plays
folder, for example:

   [league]
   play_path = D:\SIERRA\FBPRO98\PNFL\plays

Each league is a folder under leagues\ with its league.ini, rules\ and
standings\. To work on another league, copy the PNFL folder, then run:

   athc config set league PCFL
```

- `release/docs/COMMANDS.txt` 13-15 → "Settings live in athc.ini (the file documents every option inline). Each league is a folder under leagues\ next to it: league.ini (play_path), rules\ (gameplan.toml, profile.toml, playpool.toml, scheduler.toml) and standings\ (<season>.league.ini). League-aware tools use [athc] league unless --league is given." Section 1 (21-28): "Rules come from the league's rules\gameplan.toml or --rules (repeatable). The play pool comes from the league's play_path (plus rules\playpool.toml), or --play-path / --playpool-rules." (keep the rest). Example line 36 → `athc gameplan check offense.pln --league PCFL`. Section 8 (151-153): "Rules come from the league's rules\profile.toml or --rules (repeatable)." Example 166 → `athc profile check profiles\ -r --league PCFL`. Add a new numbered section after the last `config` entry (or at the end if none):

```
N) config set  --  store a setting in athc.ini
   ------------------------------------------

   Writes one key under [athc], keeping your comments. Today the only key is
   league: the league used when --league is not given. The value must be a
   folder under leagues\.

   Example terminal calls:
      athc config set league PNFL
```

- `release/docs/SCHEDULER-COMMANDS.txt` 28 → `standings\<season>.league.ini from the league folder`; 40 → `standings\<season>.league.ini (e.g. 2048.league.ini) -- divisions and last season's`.

- [ ] **Step 8: Test READMEs, STATUS, CHANGELOG**

- `tests/integration/README.md`: rows 45-47 → `Rules from the league folder | leagues/PNFL/rules/profile.toml | exit 1 | test_cli_rules_from_league_folder`, `--rules overrides league | list bogus + --rules | exit 1; bogus unused | test_cli_rules_override_league`, add `--league picks folder | two leagues | exit 1 | test_cli_league_flag_picks_folder` and `profile_rules list | relative to league folder | exit 1 | test_cli_profile_rules_list_relative_to_league_folder`; line 80 path → `release/leagues/PNFL/rules/{gameplan,playpool}.toml`; line 405 → `leagues/PNFL/standings/2026.league.ini`; lines 411-430: rename `default_league` → `[athc] league`, `[league.PNFL]` → `leagues/PNFL/league.ini`, and list the new test names from Task 1 (`test_resolves_from_configured_league`, `test_env_beats_configured_league`, `test_no_league_resolvable_lists_available`, `test_unknown_league_errors`, `test_league_dir_rejects_path_segments`, `test_obsolete_entries_warned_once_per_load`) plus a `test_config_set.py` block listing its eight tests.
- `STATUS.md`: add `athc config set                 DONE` after `athc config reveal`; lines 108 and 150 links → `release/leagues/PNFL/rules/gameplan.toml` / `profile.toml`; update the "Updated" date on line 3 to today.
- `CHANGELOG.md`: insert at the top of the `## athc` list:

```markdown
- config: one folder per league under `leagues\`; `[athc] league` picks it; `athc config set league NAME` stores it
- config: `profile check`, `convert-pdb` and `generate-schedule` take `--league`; rules and standings move into the league folder
- build: installer ships `leagues\` and preserves each league's `league.ini` and standings on reinstall
```

- [ ] **Step 9: Commit**

```bash
git add docs README.md release/docs tests/integration/README.md tests/unit/scheduler/test-matrix-config-loading.md STATUS.md CHANGELOG.md
git commit -m "docs: multi-league config layout, --league on every league tool, config set"
```

---

### Task 10: Final verification

- [ ] **Step 1: Full suite**

Run: `uv run pytest -q`
Expected: all pass, coverage ≥ 92%.

- [ ] **Step 2: Lint**

Run: `uv run ruff check .`
Expected: clean.

- [ ] **Step 3: Format**

Run: `uv run ruff format .`
Expected: no files changed (if any change, commit them as `athc: ruff format`).

- [ ] **Step 4: Types**

Run: `uv run pyright`
Expected: 0 errors.

- [ ] **Step 5: Smoke test from source**

Run: `ATHC_CONFIG_DIR=dev uv run athc config set league PNFL`
Expected: `Set league = PNFL`; `dev/athc.ini` unchanged apart from that value, comments intact (`git diff dev/athc.ini` shows nothing when the value was already PNFL).

Run: `ATHC_CONFIG_DIR=dev uv run athc profile check --help`
Expected: `--league` listed.

- [ ] **Step 6: Report**

Leave the worktree and hand off per AGENTS.md: two code blocks, squash-merge first, cleanup second, never chained.
