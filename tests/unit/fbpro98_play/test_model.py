"""Tests for athc.fbpro98_play.model — PlayFile properties and category_name.

These build a PlayFile directly (no IO) so every category code can be covered
exhaustively, including the User Specific (0xFF/0xFE) markers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_play import (
    DEFENSIVE_CATEGORIES,
    OFFENSIVE_CATEGORIES,
    SPECIAL_TEAMS_DEFENSIVE_CATEGORIES,
    SPECIAL_TEAMS_OFFENSIVE_CATEGORIES,
    PlayFile,
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


@pytest.mark.parametrize(("code", "name"), sorted(OFFENSIVE_CATEGORIES.items()))
def test_offensive_category_name(code, name):
    assert _play(play_category=0x01, user_category=code).category_name == name


@pytest.mark.parametrize(("code", "name"), sorted(DEFENSIVE_CATEGORIES.items()))
def test_defensive_category_name(code, name):
    assert _play(play_category=0x00, user_category=code).category_name == name


@pytest.mark.parametrize(
    ("code", "name"), sorted(SPECIAL_TEAMS_OFFENSIVE_CATEGORIES.items())
)
def test_offensive_special_teams_names(code, name):
    assert _play(play_category=0x01, special_category=code).category_name == name


@pytest.mark.parametrize(
    ("code", "name"), sorted(SPECIAL_TEAMS_DEFENSIVE_CATEGORIES.items())
)
def test_defensive_special_teams_names(code, name):
    assert _play(play_category=0x00, special_category=code).category_name == name


def test_unknown_normal_code_is_none():
    assert _play(play_category=0x01, user_category=0x3F).category_name is None
    assert _play(play_category=0x00, user_category=0x3F).category_name is None


def test_unknown_special_category_is_none():
    assert _play(play_category=0x01, special_category=0x7F).category_name is None


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
