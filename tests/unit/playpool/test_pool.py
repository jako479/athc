"""Tests for read_play_pool over the curated play tree (folder/filename rules)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from athc.playpool import (
    DefensiveFront,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassLogic,
    PlayPool,
    SpecialTeamsPlayRecord,
    read_play_pool,
)
from tests.unit.playpool.conftest import PLAYS

# (name, category, screen, rollout, qb_draw, pass_logic) — pinned from fixtures.
# GBglpH1R is timed via the override file; the rest from filename suffixes.
OFFENSE = [
    ("AF21rm12", "Run Middle", False, False, False, None),
    ("AF2AshtZ", "Pass Short Middle", False, False, False, PassLogic.CHECK_RECEIVERS),
    ("AF6A02T", "Pass Medium Right", False, False, False, PassLogic.TIMED),
    ("AF6Zscrn", "Pass Medium Right", True, False, False, PassLogic.CHECK_RECEIVERS),
    ("GBglpH1R", "Goal Line Pass", False, True, False, PassLogic.TIMED),
    ("JJ9ZXOTR", "Pass Long Right", False, True, False, PassLogic.TIMED),
    ("WR10GR01", "Goal Line Run", False, False, True, None),
]

# (name, category, defensive_front)
DEFENSE = [
    ("AF22PL01", "Pass Long", DefensiveFront.TWO_DL),
    ("AF31rl3H", "Run Left", DefensiveFront.THREE_FOUR),
    ("AF32gp02", "Goal Line Pass", None),
    ("AF41rl2p", "Run Left", DefensiveFront.FOUR_THREE),
]


@pytest.mark.parametrize("name,category,screen,rollout,qb_draw,logic", OFFENSE)
def test_offensive_examples(
    pool: PlayPool,
    name: str,
    category: str,
    screen: bool,
    rollout: bool,
    qb_draw: bool,
    logic: PassLogic | None,
) -> None:
    play = pool.find_by_name(name)
    assert isinstance(play, OffensivePlayRecord)
    assert play in pool.offensive_plays
    assert play.category == category
    assert (play.screen, play.rollout, play.qb_draw, play.pass_logic) == (
        screen,
        rollout,
        qb_draw,
        logic,
    )


@pytest.mark.parametrize("name,category,front", DEFENSE)
def test_defensive_examples(
    pool: PlayPool, name: str, category: str, front: DefensiveFront | None
) -> None:
    play = pool.find_by_name(name)
    assert isinstance(play, DefensivePlayRecord)
    assert play in pool.defensive_plays
    assert play.category == category
    assert play.defensive_front == front


def test_special_example(pool: PlayPool) -> None:
    play = pool.find_by_name("AF-KO")
    assert isinstance(play, SpecialTeamsPlayRecord)
    assert play in pool.special_teams_plays
    assert play.category == "Kickoff"


def test_find_across_sides(pool: PlayPool) -> None:
    assert pool.find_by_name("af2ashtz") is not None  # offense, case-insensitive
    assert pool.find_by_name("AF32GP02") is not None  # defense
    assert pool.find_by_name("AF-KO") is not None  # special
    assert pool.find_by_name("DOESNOTEXIST") is None


def test_invalid_skipped(caplog: pytest.LogCaptureFixture) -> None:
    assert (PLAYS / "Offense" / "PML" / "PS7Xmids.ply").is_file()
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        pool = read_play_pool(PLAYS)
    assert "Skipping invalid play file" in caplog.text and "PS7Xmids" in caplog.text
    assert pool.find_by_name("PS7Xmids") is None


def test_side_from_folder_not_filename(tmp_path: Path) -> None:
    """Side comes from the ancestor folder, not a substring of the filename."""
    src = next(PLAYS.glob("**/AF21rm12.ply"))
    dst = tmp_path / "Defense" / "RunLeft"
    dst.mkdir(parents=True)
    shutil.copy(src, dst / "OffenseTrick.ply")  # "Offense" in the name
    play = read_play_pool(tmp_path).find_by_name("OffenseTrick")
    assert isinstance(play, DefensivePlayRecord)  # Defense folder wins


def test_play_outside_side_folders_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    src = next(PLAYS.glob("**/AF21rm12.ply"))
    shutil.copy(src, tmp_path / "loose.ply")  # no Offense/Defense/Special ancestor
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        pool = read_play_pool(tmp_path)
    assert "outside Offense/Defense/Special" in caplog.text
    assert pool.find_by_name("loose") is None
