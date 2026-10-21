"""Play-list writer cases: message forms, and cases the real play pool can't produce."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from athc.cli.gameplan._common import parse_play_list
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)
from athc.fbpro98_play import PlayFile
from athc.gameplan.writer import (
    InvalidPlay,
    InvalidPlayListError,
    PlayLine,
    apply_normal_plays,
    apply_special_plays,
)
from athc.playpool import DefensivePlay, OffensivePlay, PlayPool


def _pool_with(*names: str, special_category: int, defensive: bool = False) -> PlayPool:
    """A pool holding one play per name, each header claiming `special_category`:
    offensive plays, or defensive ones when `defensive`."""
    pool = PlayPool("root")
    for name in names:
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
            DefensivePlay(name, play_file)
            if defensive
            else OffensivePlay(name, play_file)
        )
    return pool


def _ref(name: str, special_category: int) -> CustomPlayRef:
    """The slot entry a `_pool_with` offensive play is written as."""
    return CustomPlayRef(
        filename=f"root\\{name}.ply",
        play_category=0x01,
        special_category=special_category,
        user_category=0,
    )


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
    gp = _offense_gameplan()
    updated = apply_special_plays(gp, [PlayLine(1, "SQUIBPLY")], pool)
    placed = updated.special_plays[9].custom
    assert placed is not None and placed.name == "SQUIBPLY"
    assert updated == replace(
        gp,
        special_plays=(
            *gp.special_plays[:9],
            SpecialSlot(custom=_ref("SQUIBPLY", 10)),
            *gp.special_plays[10:],
        ),
    )


def test_normal_plays_fill_slots_in_order_with_blanks_empty() -> None:
    pool = _pool_with("RUNA", "RUNB", special_category=0)
    gp = _offense_gameplan()
    updated = apply_normal_plays(
        gp, [PlayLine(1, "RUNA"), PlayLine(2, ""), PlayLine(3, "RUNB")], pool
    )
    assert updated == replace(
        gp, normal_plays=(_ref("RUNA", 0), None, _ref("RUNB", 0), *(None,) * 61)
    )


def test_special_plays_merge_keeps_unlisted_categories() -> None:
    """A listed play fills its own category; category 4's custom, the blank
    line and the clock stocks are left as they were."""
    base = _offense_gameplan()
    gp = replace(
        base,
        special_plays=(
            *base.special_plays[:3],
            SpecialSlot(custom=_ref("OLDPUNT", 4)),
            *base.special_plays[4:],
        ),
    )
    pool = _pool_with("KICKPLY", special_category=2)
    updated = apply_special_plays(gp, [PlayLine(1, ""), PlayLine(2, "KICKPLY")], pool)
    assert updated == replace(
        gp,
        special_plays=(
            *gp.special_plays[:1],
            SpecialSlot(custom=_ref("KICKPLY", 2)),
            *gp.special_plays[2:],
        ),
    )


def test_special_play_in_a_normal_slot_is_rejected() -> None:
    pool = _pool_with("KICKPLY", special_category=2)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_offense_gameplan(), [PlayLine(3, "KICKPLY")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(3, "'KICKPLY' is a special play and cannot go in a normal slot.")
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
        InvalidPlay(5, "'RUNPLAY' is not a special play.")
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


def test_normal_play_name_matches_any_case() -> None:
    """A list name finds its pool play in any case; the slot gets the pool's file."""
    pool = _pool_with("RUNA", special_category=0)
    gp = _offense_gameplan()
    updated = apply_normal_plays(gp, [PlayLine(1, "runa")], pool)
    assert updated.normal_plays[0] == _ref("RUNA", 0)


def test_every_bad_normal_line_is_reported_at_once() -> None:
    pool = _pool_with("RUNA", special_category=0)
    lines = [PlayLine(1, "GHOST"), PlayLine(2, "RUNA"), PlayLine(4, "GHOST2")]
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_offense_gameplan(), lines, pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(1, "'GHOST' is not in the play pool (slot 1-1)."),
        InvalidPlay(4, "'GHOST2' is not in the play pool (slot 1-3)."),
    ]
    assert str(exc.value) == "2 invalid play(s)."


def test_normal_plays_fill_all_64_slots() -> None:
    """The 64th line is read: a bad play there is reported."""
    pool = _pool_with("RUNA", special_category=0)
    lines = [PlayLine(n, "RUNA") for n in range(1, 64)] + [PlayLine(64, "GHOST")]
    with pytest.raises(InvalidPlayListError) as exc:
        apply_normal_plays(_offense_gameplan(), lines, pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(64, "'GHOST' is not in the play pool (slot 16-4).")
    ]


def test_normal_plays_past_64_are_dropped() -> None:
    """A 65th line has no slot, so it is never read."""
    pool = _pool_with("RUNA", special_category=0)
    lines = [PlayLine(n, "RUNA") for n in range(1, 65)] + [PlayLine(65, "GHOST")]
    gp = _offense_gameplan()
    updated = apply_normal_plays(gp, lines, pool)
    assert updated == replace(gp, normal_plays=(_ref("RUNA", 0),) * 64)


def test_duplicate_special_play_is_rejected_any_case() -> None:
    pool = _pool_with("KICKPLY", special_category=2)
    lines = [PlayLine(1, "KICKPLY"), PlayLine(2, "kickply")]
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), lines, pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            2, "Duplicate special play 'kickply', already used for special category 2."
        )
    ]


def test_two_special_plays_for_one_category_are_rejected() -> None:
    pool = _pool_with("KICKA", "KICKB", special_category=2)
    lines = [PlayLine(1, "KICKA"), PlayLine(3, "KICKB")]
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), lines, pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(
            3, "'KICKB' targets special category 2, already filled by another play."
        )
    ]


def test_special_play_not_in_the_pool_is_rejected() -> None:
    pool = _pool_with("KICKPLY", special_category=2)
    with pytest.raises(InvalidPlayListError) as exc:
        apply_special_plays(_offense_gameplan(), [PlayLine(2, "GHOST")], pool)
    assert exc.value.invalid_plays == [
        InvalidPlay(2, "'GHOST' is not in the play pool.")
    ]


def test_play_line_and_invalid_play_are_named_tuples() -> None:
    line, name = PlayLine(3, "Play A")
    assert (line, name) == (3, "Play A")
    invalid = InvalidPlay(4, "Bad.")
    assert invalid == (4, "Bad.")
    assert (invalid.line, invalid.reason) == (4, "Bad.")


def test_parse_play_list_keeps_the_file_line_numbers() -> None:
    text = "\r\n:: comment\r\nPlay A\r\n\r\nPlay B :: note\r\n"
    assert parse_play_list(text) == [
        PlayLine(1, ""),
        PlayLine(3, "Play A"),
        PlayLine(4, ""),
        PlayLine(5, "Play B"),
    ]


def test_parse_play_list_keeps_blank_lines_as_empty_entries() -> None:
    text = "Play A\n   \n\t\nPlay B\n"
    assert parse_play_list(text) == [
        PlayLine(1, "Play A"),
        PlayLine(2, ""),
        PlayLine(3, ""),
        PlayLine(4, "Play B"),
    ]


def test_parse_play_list_drops_blank_lines_after_the_last_play() -> None:
    assert parse_play_list("Play A\n\n:: end\n  \n\n") == [PlayLine(1, "Play A")]


def test_parse_play_list_of_only_blank_lines_is_empty() -> None:
    assert parse_play_list("\n  \n:: only a comment\n") == []
