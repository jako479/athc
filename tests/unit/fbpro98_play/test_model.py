"""Tests for athc.fbpro98_play.model — PlayFile properties and category_name.

These build a PlayFile directly (no IO) so every category code can be covered
exhaustively, including the User Specific (0xFF/0xFE) markers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_play import (
    UNKNOWN_CATEGORY,
    DefensiveCategory,
    OffensiveCategory,
    PlayFile,
    SpecialDefensiveCategory,
    SpecialOffensiveCategory,
    category_by_short,
    resolve_category,
)


def _play(
    *,
    play_category: int = 0x01,
    special_category: int = 0x00,
    user_category: int = 0x01,
) -> PlayFile:
    """PlayFile carrying only the fields the side/category properties read."""
    return PlayFile(
        file_path=Path("<test>"),
        stream_length=0,
        play_category=play_category,
        special_category=special_category,
        user_category=user_category,
        player_offsets=(),
        player_headers=(),
    )


@pytest.mark.parametrize("play_category", [0x01, 0x03, 0x9B, 0xFF])
def test_odd_play_category_is_offensive(play_category):
    play = _play(play_category=play_category)
    assert play.is_offensive
    assert not play.is_defensive


@pytest.mark.parametrize("play_category", [0x00, 0x02, 0x82, 0xFE])
def test_even_play_category_is_defensive(play_category):
    play = _play(play_category=play_category)
    assert play.is_defensive
    assert not play.is_offensive


def test_is_special_teams():
    assert _play(special_category=0x02).is_special_teams
    assert not _play(special_category=0x00).is_special_teams


@pytest.mark.parametrize("category", list(OffensiveCategory))
def test_offensive_category_name(category):
    play = _play(play_category=0x01, user_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(DefensiveCategory))
def test_defensive_category_name(category):
    play = _play(play_category=0x00, user_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(SpecialOffensiveCategory))
def test_offensive_special_teams_names(category):
    play = _play(play_category=0x01, special_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(SpecialDefensiveCategory))
def test_defensive_special_teams_names(category):
    play = _play(play_category=0x00, special_category=category.code)
    assert play.category_name == category.long


def test_unknown_normal_code_is_unknown():
    off = _play(play_category=0x01, user_category=0x3F)
    assert off.category is UNKNOWN_CATEGORY and off.category_name == "Unknown"
    assert _play(play_category=0x00, user_category=0x3F).category is UNKNOWN_CATEGORY


def test_unknown_special_category_is_unknown():
    assert _play(play_category=0x01, special_category=0x7F).category is UNKNOWN_CATEGORY


def test_high_bits_are_masked():
    # bits 7-6 vary across plays in the same category; the lookup ignores them
    plain = _play(play_category=0x01, user_category=0x09).category_name
    high = _play(
        play_category=0x01, user_category=0xC9
    ).category_name  # 0xC9 & 0x3F == 0x09
    assert plain == high == "Run Middle"


def test_user_specific_resolves():
    # full-byte 0xFF/0xFE markers resolve despite the 0x3F mask
    assert (
        _play(play_category=0x01, user_category=0xFF).category_name == "User Specific"
    )
    assert (
        _play(play_category=0x00, user_category=0xFE).category_name == "User Specific"
    )


# ── category enum + resolve_category ──────────────────────────────────────────


def test_category_returns_enum_member():
    play = _play(play_category=0x01, user_category=0x03)
    assert play.category is OffensiveCategory.PASS_SHORT_RIGHT
    assert play.category_name == play.category.long == "Pass Short Right"


def test_short_and_long_names():
    assert OffensiveCategory.PASS_SHORT_RIGHT.short == "PSR"
    assert OffensiveCategory.PASS_SHORT_RIGHT.long == "Pass Short Right"
    assert DefensiveCategory.RUN_LEFT.short == "RunLeft"
    assert DefensiveCategory.RUN_LEFT.long == "Run Left"


def test_short_falls_back_to_long_without_league_name():
    for c in (
        OffensiveCategory.PASS_LONG_LEFT,
        OffensiveCategory.PASS_LONG_MIDDLE,
        OffensiveCategory.RAZZLE_DAZZLE_RUN,
        OffensiveCategory.USER_SPECIFIC,
    ):
        assert c.short == c.long
    for special in SpecialOffensiveCategory:  # special teams have no short labels
        assert special.short == special.long


def test_is_run_is_pass():
    assert OffensiveCategory.RUN_LEFT.is_run and not OffensiveCategory.RUN_LEFT.is_pass
    psr = OffensiveCategory.PASS_SHORT_RIGHT
    assert psr.is_pass and not psr.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_pass


def test_resolve_category_picks_side_and_special():
    assert resolve_category(0x01, 0x00, 0x03) is OffensiveCategory.PASS_SHORT_RIGHT
    assert resolve_category(0x00, 0x00, 0x02) is DefensiveCategory.PASS_SHORT
    assert resolve_category(0x01, 0x02, 0x00) is SpecialOffensiveCategory.KICKOFF
    assert resolve_category(0x00, 0x02, 0x00) is SpecialDefensiveCategory.KICK_RETURN


def test_resolve_category_mask_and_unknown():
    # 0xC9 & 0x3F == 0x09 (Run Middle); 0xFF is the full-byte User Specific marker
    assert resolve_category(0x01, 0x00, 0xC9) is OffensiveCategory.RUN_MIDDLE
    assert resolve_category(0x01, 0x00, 0xFF) is OffensiveCategory.USER_SPECIFIC
    assert resolve_category(0x01, 0x00, 0x3F) is UNKNOWN_CATEGORY


def test_category_by_short():
    assert category_by_short("PSR") is OffensiveCategory.PASS_SHORT_RIGHT
    assert category_by_short("RunLeft") is DefensiveCategory.RUN_LEFT
    assert category_by_short("Pass Long Left") is None  # no league abbreviation
    assert category_by_short("nope") is None
