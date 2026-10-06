"""Shared fixtures and paths for integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

DATA = Path(__file__).resolve().parent / "data"
EXPECTED = Path(__file__).resolve().parent / "expected"
RULES_TOML = DATA / "profile_rules.toml"
OFF1 = DATA / "TST-OFF1.prf"
DEF1 = DATA / "TST-DEF1.prf"

# gameplan check: real gameplans + a curated pool and their rules.
GP_RULES = DATA / "gameplan_rules.toml"
POOL_RULES = DATA / "playpool_rules.toml"
GP_OFFENSE = DATA / "offense.pln"
GP_DEFENSE = DATA / "defense.pln"
PLAYS = DATA / "plays"

# check-ppp: a clean profile that fully matches offense.pln above.
COMPAT_OFF_CLEAN = DATA / "compat_off_clean.prf"

# check-ppp on a tree: the PNFL league file and a copy of its 2049 plans folder
# (Denver's week 6 files, and the same files renamed to Las Vegas's names).
PNFL_LG2 = DATA / "PNFL.lg2"
PPP_TREE = DATA / "ppp"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
