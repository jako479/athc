"""Shared fixtures and paths for integration tests."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from click.testing import CliRunner

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)

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


# ── constructed gameplans ─────────────────────────────────────────────────────


def clock_slot(category: int) -> SpecialSlot:
    """The stock clock play of category 11 or 12; every offense gameplan has both."""
    return SpecialSlot(stock=StockPlayRef(f"CLOCK{category}", 0, 0, 1, category, 0))


def offense_normal(name: str, user_category: int = 0x05) -> CustomPlayRef:
    """Offense normal play; `user_category` 0x05 = Run Left."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=1,
        special_category=0,
        user_category=user_category,
    )


def offense_special(name: str, category: int = 1) -> CustomPlayRef:
    """Offense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=1,
        special_category=category,
        user_category=0,
    )


def defense_normal(name: str, user_category: int = 0x04) -> CustomPlayRef:
    """Defense normal play; `user_category` 0x04 = Run Left."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=0,
        special_category=0,
        user_category=user_category,
    )


def defense_special(name: str, category: int) -> CustomPlayRef:
    """Defense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=0,
        special_category=category,
        user_category=0,
    )


def build_gameplan(
    profile_type: ProfileType,
    normals: Mapping[int, CustomPlayRef] | None = None,
    specials: Mapping[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """A gameplan with the given normal slots (0-based) and custom special slots
    (1-based category) filled; an offense gameplan gets its two stock clock plays."""
    normal_slots: list[CustomPlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    for index, play in (normals or {}).items():
        normal_slots[index] = play
    special_slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category, play in (specials or {}).items():
        special_slots[category - 1] = SpecialSlot(custom=play)
    if profile_type is ProfileType.OFFENSE:
        for category in (11, 12):
            special_slots[category - 1] = clock_slot(category)
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(normal_slots),
        special_plays=tuple(special_slots),
    )
