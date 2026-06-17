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

# gameplan check: real gameplans + a curated pool; the canonical PNFL release rules.
_RELEASE_RULES = Path(__file__).resolve().parents[2] / "release" / "rules"
GP_RULES = _RELEASE_RULES / "PNFL.gameplan.toml"
POOL_RULES = _RELEASE_RULES / "PNFL.playpool.toml"
GP_OFFENSE = DATA / "offense.pln"
GP_DEFENSE = DATA / "defense.pln"
PLAYS = DATA / "plays"

# profile check --gameplan: clean profiles that fully match the gameplans above.
COMPAT_OFF_CLEAN = DATA / "compat_off_clean.prf"
COMPAT_DEF_CLEAN = DATA / "compat_def_clean.prf"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
