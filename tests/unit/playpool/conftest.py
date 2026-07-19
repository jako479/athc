"""Shared fixtures for playpool unit tests.

Three pools over the SAME plays exercise the file-driven classifier:
  pnfl_pool    — the curated PNFL tree in data/plays/ (folders add attributes)
  nonpnfl_pool — the same files under arbitrary folder names
  flat_pool    — the same files in one flat directory
Side, category, and filename attributes must match across all three; only the
PNFL tree adds `screen` / `defensive_front`.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.fbpro98_play import PlayFile
from athc.playpool import PlayPool, PlaypoolRules, load_rules, read_play_pool

DATA = Path(__file__).resolve().parent / "data"
PLAYS = DATA / "plays"
RULES_TOML = DATA / "rules.toml"

# arbitrary folder names — none is a recognized PNFL token
NONPNFL_DIRS = ("alpha", "beta/inner", "gamma", "passes", "runs", "misc/deep")

MakePlay = Callable[..., PlayFile]


@pytest.fixture
def make_play() -> MakePlay:
    """Build a PlayFile with just the fields classification reads."""

    def _make(
        name: str,
        *,
        play_category: int = 0x01,  # odd → offense
        user_category: int = 0x03,  # Pass Short Right → pass
        special_category: int = 0,
    ) -> PlayFile:
        return PlayFile(
            Path(f"{name}.ply"),
            0,
            play_category,
            special_category,
            user_category,
            (),
            (),
        )

    return _make


@pytest.fixture(scope="session")
def rules() -> PlaypoolRules:
    return load_rules(RULES_TOML)


def _ply_files() -> list[Path]:
    return sorted(PLAYS.glob("**/*.ply"))


@pytest.fixture(scope="session")
def flat_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Every fixture .ply copied into one flat directory."""
    root = tmp_path_factory.mktemp("flat")
    for src in _ply_files():
        shutil.copy(src, root / src.name)
    return root


@pytest.fixture(scope="session")
def nonpnfl_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Every fixture .ply copied under arbitrary (non-PNFL) folder names."""
    root = tmp_path_factory.mktemp("nonpnfl")
    for i, src in enumerate(_ply_files()):
        sub = root / NONPNFL_DIRS[i % len(NONPNFL_DIRS)]
        sub.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, sub / src.name)
    return root


@pytest.fixture(scope="session")
def pnfl_pool(rules: PlaypoolRules) -> PlayPool:
    return read_play_pool(PLAYS, rules=rules)


@pytest.fixture(scope="session")
def flat_pool(flat_tree: Path, rules: PlaypoolRules) -> PlayPool:
    return read_play_pool(flat_tree, rules=rules)


@pytest.fixture(scope="session")
def nonpnfl_pool(nonpnfl_tree: Path, rules: PlaypoolRules) -> PlayPool:
    return read_play_pool(nonpnfl_tree, rules=rules)
