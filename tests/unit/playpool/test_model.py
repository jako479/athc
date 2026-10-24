"""Unit tests for the play record classes and the PlayPool container."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from athc.fbpro98_play import DefensiveFront, OffensiveCategory
from athc.playpool import (
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    Play,
    PlayPool,
    SpecialPlay,
)
from tests.unit.playpool.conftest import MakePlay


def test_category(make_play: MakePlay) -> None:
    rec = OffensivePlay("AF21rm12", make_play("AF21rm12", user_category=0x09))
    assert rec.category is OffensiveCategory.RUN_MIDDLE
    assert rec.file_path.name == "AF21rm12.ply"


@pytest.mark.parametrize(
    ("user_category", "attributes", "expected"),
    [
        (
            0x03,
            {"screen": True, "rollout": True, "pass_logic": PassLogic.TIMED},
            {
                "category": "Pass Short Right",
                "screen": True,
                "rollout": True,
                "qb_run": False,
                "pass_logic": "Timed",
            },
        ),
        (
            0x09,
            {"qb_run": True},
            {
                "category": "Run Middle",
                "screen": False,
                "rollout": False,
                "qb_run": True,
                "pass_logic": None,
            },
        ),
    ],
)
def test_offensive_to_dict(
    make_play: MakePlay,
    user_category: int,
    attributes: dict[str, Any],
    expected: dict[str, object],
) -> None:
    rec = OffensivePlay("p", make_play("p", user_category=user_category), **attributes)
    assert rec.to_dict() == {
        "name": "p",
        "file_path": "p.ply",
        "play_category": 0x01,
        "special_category": 0,
        "user_category": user_category,
        **expected,
    }


@pytest.mark.parametrize(
    ("front", "expected"), [(DefensiveFront.TWO_DL, "2-DL"), (None, None)]
)
def test_defensive_to_dict(
    make_play: MakePlay, front: DefensiveFront | None, expected: str | None
) -> None:
    rec = DefensivePlay(
        "d",
        make_play("d", play_category=0x00, user_category=0x02),  # Pass Short
        defensive_front=front,
    )
    assert rec.to_dict() == {
        "name": "d",
        "file_path": "d.ply",
        "category": "Pass Short",
        "play_category": 0x00,
        "special_category": 0,
        "user_category": 0x02,
        "defensive_front": expected,
    }


def test_special_to_dict(make_play: MakePlay) -> None:
    rec = SpecialPlay("k", make_play("k", special_category=0x02))
    assert rec.to_dict() == {
        "name": "k",
        "file_path": "k.ply",
        "category": "Kickoff",
        "play_category": 0x01,
        "special_category": 0x02,
        "user_category": 0x03,
    }


@pytest.mark.parametrize(
    ("relative_to", "file_path"),
    [(None, "Offense/p.ply"), (Path("Offense"), "p.ply")],
)
def test_to_dict_file_path(
    make_play: MakePlay, relative_to: Path | None, file_path: str
) -> None:
    rec = OffensivePlay("p", make_play("Offense/p"))
    assert rec.to_dict(relative_to=relative_to)["file_path"] == file_path


def test_find_by_name(make_play: MakePlay) -> None:
    pool = PlayPool("root")
    play = OffensivePlay("AFGZoutX", make_play("AFGZoutX"))
    pool.add(play)
    assert pool.find_by_name("afgzoutx") is play
    assert pool.find_by_name("AFGZOUTX") is play
    assert pool.find_by_name("nope") is None


def test_add_files_by_side(make_play: MakePlay) -> None:
    pool = PlayPool("root")
    offense = OffensivePlay("o", make_play("o"))
    defense = DefensivePlay("d", make_play("d", play_category=0x00, user_category=0x02))
    special = SpecialPlay("k", make_play("k", special_category=0x02))
    for play in (offense, defense, special):
        pool.add(play)
    assert pool.offensive_plays == [offense]
    assert pool.defensive_plays == [defense]
    assert pool.special_plays == [special]


def test_duplicate_name_last_wins(make_play: MakePlay) -> None:
    pool = PlayPool("root")
    first = OffensivePlay("DUP", make_play("DUP", user_category=0x01))
    second = OffensivePlay("DUP", make_play("DUP", user_category=0x09))
    pool.add(first)
    pool.add(second)
    assert pool.find_by_name("DUP") is second
    assert pool.offensive_plays == [first, second]


def test_add_rejects_a_bare_play(make_play: MakePlay) -> None:
    """Only the three sided play types belong in a pool."""
    pool = PlayPool("root")
    with pytest.raises(TypeError):
        pool.add(Play("p", make_play("p")))  # type: ignore[arg-type]
    assert pool.find_by_name("p") is None
