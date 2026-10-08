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

from athc.fbpro98_play import CategoryLabels

ROOT = Path(__file__).resolve().parents[1]

# Test league folder names. athc never cares what a league is called; tests that
# need two leagues use both.
LEAGUE = "test_league"
OTHER_LEAGUE = "other_league"

# The PNFL labels. Real league names are fine in fixtures; they are data, not
# league-aware logic.
PNFL_OFFENSE: dict[str, str] = {
    "Run Right": "RR",
    "Pass Short Right": "PSR",
    "Run Left": "RL",
    "Pass Short Left": "PSL",
    "Run Middle": "RM",
    "Pass Short Middle": "PSM",
    "Razzle Dazzle Pass": "PRD",
    "Pass Medium Right": "PMR",
    "Pass Medium Left": "PML",
    "Pass Medium Middle": "PMM",
    "Pass Long Right": "PLR",
    "Goal Line Run": "GLR",
    "Goal Line Pass": "GLP",
}
PNFL_DEFENSE: dict[str, str] = {
    "Run Right": "RunRight",
    "Pass Short": "PassShort",
    "Run Left": "RunLeft",
    "Run Middle": "RunMiddle",
    "Run Dazzle": "RunDazzle",
    "Pass Dazzle": "PassDazzle",
    "Pass Medium": "PassMedium",
    "Pass Long": "PassLong",
    "Goal Line Run": "GLrun",
    "Goal Line Pass": "GLpass",
}
PNFL_LABELS = CategoryLabels.from_tables(PNFL_OFFENSE, PNFL_DEFENSE)


def _categories_table(side: str, labels: dict[str, str]) -> str:
    lines = "".join(f'"{name}" = "{label}"\n' for name, label in labels.items())
    return f"[categories.{side}]\n{lines}"


# The `[categories.*]` tables of a test league.toml: the PNFL labels.
CATEGORIES_TOML = _categories_table("offense", PNFL_OFFENSE) + _categories_table(
    "defense", PNFL_DEFENSE
)


def league_toml(play_path: Path | str | None = None, *, labels: bool = True) -> str:
    """A league.toml body: `play_path` when given and, by default, the PNFL
    category labels."""
    body = "[league]\n"
    if play_path is not None:
        body += f"play_path = '{play_path}'\n"
    return body + (CATEGORIES_TOML if labels else "")


# A test league's pdbtoexcel.toml: the PNFL category order over the labels above.
PDBTOEXCEL_TOML = (
    "[category_order]\n"
    'run = ["RL", "RM", "RR", "GLR"]\n'
    'pass = ["PSL", "PSM", "PSR", "PML", "PMM", "PMR", "PLR", "PRD", "GLP"]\n'
    'defense = ["RunLeft", "RunMiddle", "RunRight", "RunDazzle", "PassShort", '
    '"PassMedium", "PassLong", "PassDazzle", "GLrun", "GLpass"]\n'
)


def write_pdbtoexcel_toml(folder: Path, body: str = PDBTOEXCEL_TOML) -> Path:
    """Write a league folder's `pdbtoexcel.toml` (the PNFL order by default)."""
    return write_config_file(folder, body, "pdbtoexcel.toml")


def shipped_files(pattern: str) -> list[Path]:
    """Every shipped `leagues/<pattern>` file, in both `config/dev/` and `config/release/`
    (e.g. `*/gameplan.toml`)."""
    return sorted(
        path
        for folder in ("dev", "release")
        for path in (ROOT / "config" / folder / "leagues").glob(pattern)
    )


def shipped_id(path: Path) -> str:
    """Test id for a shipped league file: `dev/<league>/<file>`, whether the file
    sits in the league folder or in `standings\\`."""
    rel = path.relative_to(ROOT / "config")
    return f"{rel.parts[0]}/{rel.parts[2]}/{path.name}"


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate config lookup to a temp dir so tests never read the real machine config."""
    d = tmp_path / "athc-config"
    d.mkdir()
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(d))
    return d


def write_config_file(config_dir: Path, body: str, name: str = "athc.ini") -> Path:
    """Write a raw config file (dedented, leading newline stripped) to `config_dir/name`.
    Plain function so golden `--bless` scripts can use it outside pytest."""
    path = config_dir / name
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return path


def make_league_dir(
    config_dir: Path, name: str = LEAGUE, body: str | None = None
) -> Path:
    """Create `leagues/<name>/` (with `standings/`) under `config_dir`,
    write `league.toml` from `body` when given, and return the folder."""
    folder = config_dir / "leagues" / name
    folder.mkdir(parents=True)
    (folder / "standings").mkdir()
    if body is not None:
        write_config_file(folder, body, "league.toml")
    return folder


@pytest.fixture
def write_config(config_dir: Path) -> Callable[..., Path]:
    """`write_config_file` bound to the temp config dir."""
    return functools.partial(write_config_file, config_dir)


@pytest.fixture
def make_league(config_dir: Path) -> Callable[..., Path]:
    """`make_league_dir` bound to the temp config dir."""
    return functools.partial(make_league_dir, config_dir)
