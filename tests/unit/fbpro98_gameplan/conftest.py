"""Shared fixtures for fbpro98_gameplan tests.

`OFFENSE_PATH` and `DEFENSE_PATH` are the two game-saved `.pln` files the
valid-parse and round-trip tests read; the reader's error tests mutate a copy of
the offense bytes (`offense_bytes`). `g95_end` and `s98_start` locate a buffer's
J95 and S98 blocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_gameplan.schema import G95_HEADER, J95_HEADER, J95_PLAN_DATA

DATA_DIR = Path(__file__).resolve().parent / "data"
OFFENSE_PATH = DATA_DIR / "offense.pln"
DEFENSE_PATH = DATA_DIR / "defense.pln"

# Runs a test once per fixture file, passed as `pln_path`.
both_sides = pytest.mark.parametrize(
    "pln_path", [OFFENSE_PATH, DEFENSE_PATH], ids=["offense", "defense"]
)


@pytest.fixture
def offense_bytes() -> bytearray:
    """A mutable copy of the offense fixture for the error tests."""
    return bytearray(OFFENSE_PATH.read_bytes())


def g95_end(data: bytes | bytearray) -> int:
    """Absolute offset just past the G95 block, where the J95 block starts."""
    _, g95_size = G95_HEADER.unpack_from(data, 0)
    return G95_HEADER.size + g95_size


def s98_start(data: bytes | bytearray) -> int:
    """Absolute offset of the S98 block header."""
    return g95_end(data) + J95_HEADER.size + J95_PLAN_DATA.size
