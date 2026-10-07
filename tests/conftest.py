"""Shared fixtures for the whole suite.

`config_dir` isolates config lookup (env `ATHC_CONFIG_DIR`) for every test; `write_config`
writes raw INI into that dir. Tests that exercise the platformdirs default must
`monkeypatch.delenv("ATHC_CONFIG_DIR", raising=False)` themselves.
"""

from __future__ import annotations

import functools
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Test league folder names. athc never cares what a league is called; tests that
# need two leagues use both.
LEAGUE = "test_league"
OTHER_LEAGUE = "other_league"


def shipped_files(pattern: str) -> list[Path]:
    """Every shipped `leagues/<pattern>` file, in both `config/dev/` and `config/release/`
    (e.g. `*/rules/gameplan.toml`)."""
    return sorted(
        path
        for folder in ("dev", "release")
        for path in (ROOT / "config" / folder / "leagues").glob(pattern)
    )


def shipped_id(path: Path) -> str:
    """Test id for a shipped league file: `dev/<league>/<file>`."""
    return f"{path.parents[3].name}/{path.parents[1].name}/{path.name}"


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate config lookup to a temp dir so tests never read the real machine config."""
    d = tmp_path / "athc-config"
    d.mkdir()
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(d))
    return d


def write_config_file(config_dir: Path, body: str, name: str = "athc.ini") -> Path:
    """Write raw INI (dedented, leading newline stripped) to `config_dir/name`.
    Plain function so golden `--bless` scripts can use it outside pytest."""
    path = config_dir / name
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return path


def make_league_dir(
    config_dir: Path, name: str = LEAGUE, body: str | None = None
) -> Path:
    """Create `leagues/<name>/` (with `rules/` and `standings/`) under `config_dir`,
    write `league.ini` from `body` when given, and return the folder."""
    folder = config_dir / "leagues" / name
    (folder / "rules").mkdir(parents=True)
    (folder / "standings").mkdir()
    if body is not None:
        write_config_file(folder, body, "league.ini")
    return folder


@pytest.fixture
def write_config(config_dir: Path) -> Callable[..., Path]:
    """`write_config_file` bound to the temp config dir."""
    return functools.partial(write_config_file, config_dir)


@pytest.fixture
def make_league(config_dir: Path) -> Callable[..., Path]:
    """`make_league_dir` bound to the temp config dir."""
    return functools.partial(make_league_dir, config_dir)
