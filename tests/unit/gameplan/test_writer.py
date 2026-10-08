"""Unit tests for `gameplan.writer`: cases the real play pool can't produce."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_gameplan import GamePlan, ProfileType, SpecialSlot, StockPlayRef
from athc.fbpro98_play import PlayFile
from athc.gameplan.writer import InvalidPlayInputError, apply_special_plays
from athc.playpool import OffensivePlay, PlayPool


def _pool_with(name: str, *, special_category: int) -> PlayPool:
    """A pool holding one offensive play whose header claims `special_category`."""
    pool = PlayPool("root")
    play_file = PlayFile(
        Path("root") / f"{name}.ply", 0, 0x01, special_category, 0, (), ()
    )
    record = OffensivePlay(name, play_file)
    pool._register(record)
    pool.offensive_plays.append(record)
    return pool


def _offense_gameplan() -> GamePlan:
    slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 0x01, category, 0)
        )
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=(None,) * GamePlan.NUMBER_NORMAL_PLAYS,
        special_plays=tuple(slots),
    )


def test_special_play_without_custom_slot_is_rejected() -> None:
    """A .ply claiming special category 11 has no custom slot to land in."""
    pool = _pool_with("CLOCKPLY", special_category=11)
    with pytest.raises(
        InvalidPlayInputError, match="special category 11, which has no custom slot"
    ):
        apply_special_plays(_offense_gameplan(), ["CLOCKPLY"], pool)


def test_special_play_in_last_custom_category_is_accepted() -> None:
    """Category 10 is the last one with a custom slot."""
    pool = _pool_with("SQUIBPLY", special_category=10)
    updated = apply_special_plays(_offense_gameplan(), ["SQUIBPLY"], pool)
    placed = updated.special_plays[9].custom
    assert placed is not None and placed.name == "SQUIBPLY"
