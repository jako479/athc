"""Play-list writer cases: message forms, and cases the real play pool can't produce."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli.gameplan._common import parse_play_list
from athc.fbpro98_gameplan import GamePlan, ProfileType, SpecialSlot, StockPlayRef
from athc.fbpro98_play import PlayFile
from athc.gameplan.writer import (
    InvalidPlay,
    InvalidPlayListError,
    PlayLine,
    apply_normal_plays,
    apply_special_plays,
)
from athc.playpool import DefensivePlay, OffensivePlay, PlayPool


def _pool_with(
    name: str, *, special_category: int, defensive: bool = False
) -> PlayPool:
    """A pool holding one play whose header claims `special_category`: an
    offensive play, or a defensive one when `defensive`."""
    pool = PlayPool("root")
    play_file = PlayFile(
        Path("root") / f"{name}.ply",
        0,
        0x00 if defensive else 0x01,
        special_category,
        0,
        (),
        (),
    )
    pool.add(
        DefensivePlay(name, play_file) if defensive else OffensivePlay(name, play_file)
    )
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


def _defense_gameplan() -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * GamePlan.NUMBER_NORMAL_PLAYS,
        special_plays=tuple(
            SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)
        ),
    )


def test_special_play_without_custom_slot_is_rejected() -> None:
    """A .ply claiming special category 11 has no custom slot to land in."""
    pool = _pool_with("CLOCKPLY", special_category=11)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), [PlayLine(4, "CLOCKPLY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            4, "'CLOCKPLY' is in special category 11, which has no custom slot."
        )
    ]
    assert str(exc.value) == "1 invalid play(s)."


def test_special_play_in_last_custom_category_is_accepted() -> None:
    """Category 10 is the last one with a custom slot."""
    pool = _pool_with("SQUIBPLY", special_category=10)
    updated = apply_special_plays(_offense_gameplan(), [PlayLine(1, "SQUIBPLY")], pool)
    placed = updated.special_plays[9].custom
    assert placed is not None and placed.name == "SQUIBPLY"


def test_special_teams_play_in_a_normal_slot_is_rejected() -> None:
    pool = _pool_with("KICKPLY", special_category=2)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_offense_gameplan(), [PlayLine(3, "KICKPLY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            3, "'KICKPLY' is a special-teams play and cannot go in a normal slot."
        )
    ]


def test_defensive_play_in_an_offense_game_plan_is_rejected() -> None:
    pool = _pool_with("DEFPLAY", special_category=0, defensive=True)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_offense_gameplan(), [PlayLine(1, "DEFPLAY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(1, "'DEFPLAY' is a defensive play, but the game plan is offensive.")
    ]


def test_offensive_play_in_a_defense_game_plan_is_rejected() -> None:
    pool = _pool_with("OFFPLAY", special_category=0)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_defense_gameplan(), [PlayLine(2, "OFFPLAY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            2, "'OFFPLAY' is an offensive play, but the game plan is defensive."
        )
    ]


def test_normal_play_in_the_specials_list_is_rejected() -> None:
    pool = _pool_with("RUNPLAY", special_category=0)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), [PlayLine(5, "RUNPLAY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(5, "'RUNPLAY' is not a special-teams play.")
    ]


def test_defensive_special_play_in_an_offense_game_plan_is_rejected() -> None:
    pool = _pool_with("DEFKICK", special_category=2, defensive=True)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), [PlayLine(1, "DEFKICK")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            1, "'DEFKICK' is a defensive special play, but the game plan is offensive."
        )
    ]


def test_offensive_special_play_in_a_defense_game_plan_is_rejected() -> None:
    pool = _pool_with("OFFKICK", special_category=2)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_defense_gameplan(), [PlayLine(1, "OFFKICK")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            1, "'OFFKICK' is an offensive special play, but the game plan is defensive."
        )
    ]


def test_play_line_and_invalid_play_are_named_tuples() -> None:
    line, name = PlayLine(3, "Play A")
    assert (line, name) == (3, "Play A")
    invalid = InvalidPlay(4, "Bad.")
    assert invalid == (4, "Bad.")
    assert (invalid.line, invalid.reason) == (4, "Bad.")


def test_parse_play_list_keeps_the_file_line_numbers() -> None:
    text = "\r\n:: comment\r\nPlay A\r\n\r\nPlay B :: note\r\n"
    assert parse_play_list(text) == [PlayLine(3, "Play A"), PlayLine(5, "Play B")]
