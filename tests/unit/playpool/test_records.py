"""Unit tests for the play record classes and PlayPool registration."""

from __future__ import annotations

import logging

import pytest

from athc.fbpro98_play import OffensiveCategory
from athc.playpool import (
    DefensiveFront,
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    PlayPool,
    SpecialTeamsPlay,
)
from tests.unit.playpool.conftest import MakePlay


def test_category(make_play: MakePlay) -> None:
    rec = OffensivePlay("AF21rm12", make_play("AF21rm12", user_category=0x09))
    category = rec.category
    assert category is OffensiveCategory.RUN_MIDDLE
    assert category.long == "Run Middle" and category.is_run
    assert rec.file_path.name == "AF21rm12.ply"


def test_offensive_to_dict(make_play: MakePlay) -> None:
    rec = OffensivePlay(
        "p", make_play("p", user_category=0x03), pass_logic=PassLogic.TIMED
    )
    d = rec.to_dict()
    assert d["name"] == "p"
    assert d["category"] == "Pass Short Right"
    assert d["screen"] is False
    assert d["pass_logic"] == "Timed"


def test_defensive_to_dict(make_play: MakePlay) -> None:
    rec = DefensivePlay(
        "d",
        make_play("d", play_category=0x00, user_category=0x02),
        defensive_front=DefensiveFront.TWO_DL,
    )
    d = rec.to_dict()
    assert d["category"] == "Pass Short"
    assert d["defensive_front"] == "2-DL"


def test_special_to_dict(make_play: MakePlay) -> None:
    rec = SpecialTeamsPlay("k", make_play("k", special_category=0x02))
    d = rec.to_dict()
    assert d["name"] == "k"
    assert "screen" not in d and "defensive_front" not in d


def test_find_by_name(make_play: MakePlay) -> None:
    pool = PlayPool("root")
    pool._register(OffensivePlay("AFGZoutX", make_play("AFGZoutX")))
    assert pool.find_by_name("afgzoutx") is not None
    assert pool.find_by_name("AFGZOUTX").name == "AFGZoutX"  # type: ignore[union-attr]
    assert pool.find_by_name("nope") is None


def test_duplicate_name_warns(
    make_play: MakePlay, caplog: pytest.LogCaptureFixture
) -> None:
    pool = PlayPool("root")
    pool._register(OffensivePlay("DUP", make_play("DUP", user_category=0x01)))
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        pool._register(OffensivePlay("DUP", make_play("DUP", user_category=0x09)))
    assert "Duplicate play name 'DUP'" in caplog.text
    dup = pool.find_by_name("DUP")
    assert dup is not None and dup.category is OffensiveCategory.RUN_MIDDLE
