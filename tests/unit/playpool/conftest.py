"""Shared fixtures for playpool unit tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.fbpro98_play import PlayFile
from athc.playpool import PlayPool, PlaypoolRules, load_rules, read_play_pool

DATA = Path(__file__).resolve().parent / "data"
PLAYS = DATA / "plays"
RULES_TOML = DATA / "rules.toml"

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


@pytest.fixture(scope="module")
def rules() -> PlaypoolRules:
    return load_rules(RULES_TOML)


@pytest.fixture(scope="module")
def pool(rules: PlaypoolRules) -> PlayPool:
    return read_play_pool(PLAYS, rules=rules)
