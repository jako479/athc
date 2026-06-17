"""Unit tests for the play record classes and PlayPool registration."""

from __future__ import annotations

import logging

import pytest

from athc.playpool import (
    DefensiveFront,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassLogic,
    PlayPool,
    SpecialTeamsPlayRecord,
)
from athc.playpool.records import play_type
from tests.unit.playpool.conftest import MakePlay


def test_play_type_function() -> None:
    assert play_type("Run Middle") == "run"
    assert play_type("Pass Short") == "pass"
    assert play_type("Field Goal/PAT") is None
    assert play_type(None) is None


def test_category_and_play_type(make_play: MakePlay) -> None:
    rec = OffensivePlayRecord(
        "AF21rm12", make_play("AF21rm12", user_category=0x09), pool_category="RM"
    )
    assert rec.category == "Run Middle"
    assert rec.play_type == "run"
    assert rec.file_path.name == "AF21rm12.ply"
    assert rec.is_run and not rec.is_pass


def test_offensive_to_dict(make_play: MakePlay) -> None:
    rec = OffensivePlayRecord(
        "p",
        make_play("p", user_category=0x03),
        pool_category="PSR",
        pass_logic=PassLogic.TIMED,
    )
    d = rec.to_dict()
    assert d["name"] == "p"
    assert d["category"] == "Pass Short Right"
    assert d["pool_category"] == "PSR"
    assert d["screen"] is False
    assert d["pass_logic"] == "Timed"


def test_defensive_to_dict(make_play: MakePlay) -> None:
    rec = DefensivePlayRecord(
        "d",
        make_play("d", play_category=0x00, user_category=0x02),
        pool_category="PassShort",
        defensive_front=DefensiveFront.TWO_DL,
    )
    d = rec.to_dict()
    assert d["pool_category"] == "PassShort"
    assert d["defensive_front"] == "2-DL"


def test_special_to_dict(make_play: MakePlay) -> None:
    rec = SpecialTeamsPlayRecord("k", make_play("k", special_category=0x02))
    d = rec.to_dict()
    assert d["name"] == "k"
    assert "pool_category" not in d


def test_find_by_name(make_play: MakePlay) -> None:
    pool = PlayPool("root")
    pool._register(
        OffensivePlayRecord("AFGZoutX", make_play("AFGZoutX"), pool_category="PSR")
    )
    assert pool.find_by_name("afgzoutx") is not None
    assert pool.find_by_name("AFGZOUTX").name == "AFGZoutX"  # type: ignore[union-attr]
    assert pool.find_by_name("nope") is None


def test_duplicate_name_warns(
    make_play: MakePlay, caplog: pytest.LogCaptureFixture
) -> None:
    pool = PlayPool("root")
    pool._register(
        OffensivePlayRecord(
            "DUP", make_play("DUP", user_category=0x01), pool_category="RR"
        )
    )
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        pool._register(
            OffensivePlayRecord(
                "DUP", make_play("DUP", user_category=0x09), pool_category="RM"
            )
        )
    assert "Duplicate play name 'DUP'" in caplog.text
    assert pool.find_by_name("DUP").category == "Run Middle"  # type: ignore[union-attr]
