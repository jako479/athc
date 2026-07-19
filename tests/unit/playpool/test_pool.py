"""Tests for read_play_pool: file-driven classification across three layouts,
optional PNFL folder attributes, and folder mismatch warnings."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from athc.playpool import (
    DefensiveFront,
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    PlayPool,
    SpecialTeamsPlay,
    read_play_pool,
)
from athc.playpool.pool import folder_warnings
from tests.unit.playpool.conftest import PLAYS, MakePlay

ALL_POOLS = ["pnfl_pool", "flat_pool", "nonpnfl_pool"]

# File-driven attributes — identical in every layout.
# (name, category, rollout, qb_draw, pass_logic)
OFFENSE = [
    ("AF21rm12", "Run Middle", False, False, None),
    ("AF2AshtZ", "Pass Short Middle", False, False, PassLogic.CHECK_RECEIVERS),
    ("AF6A02T", "Pass Medium Right", False, False, PassLogic.TIMED),
    ("AF6Zscrn", "Pass Medium Right", False, False, PassLogic.CHECK_RECEIVERS),
    ("GBglpH1R", "Goal Line Pass", True, False, PassLogic.TIMED),
    ("JJ9ZXOTR", "Pass Long Right", True, False, PassLogic.TIMED),
    ("WR10GR01", "Goal Line Run", False, True, None),
]

# (name, category, pnfl_front) — front appears only in the PNFL tree.
DEFENSE = [
    ("AF22PL01", "Pass Long", DefensiveFront.TWO_DL),
    ("AF31rl3H", "Run Left", DefensiveFront.THREE_FOUR),
    ("AF32gp02", "Goal Line Pass", None),
    ("AF41rl2p", "Run Left", DefensiveFront.FOUR_THREE),
]


# ── classification is the same in every layout ────────────────────────────────


@pytest.mark.parametrize("pool_name", ALL_POOLS)
@pytest.mark.parametrize("name,category,rollout,qb_draw,logic", OFFENSE)
def test_offensive_file_driven(
    request: pytest.FixtureRequest,
    pool_name: str,
    name: str,
    category: str,
    rollout: bool,
    qb_draw: bool,
    logic: PassLogic | None,
) -> None:
    pool: PlayPool = request.getfixturevalue(pool_name)
    play = pool.find_by_name(name)
    assert isinstance(play, OffensivePlay)
    assert play in pool.offensive_plays
    assert play.category.long == category
    assert (play.rollout, play.qb_draw, play.pass_logic) == (rollout, qb_draw, logic)


@pytest.mark.parametrize("pool_name", ALL_POOLS)
def test_screen_only_from_pnfl_folder(
    request: pytest.FixtureRequest, pool_name: str
) -> None:
    play = request.getfixturevalue(pool_name).find_by_name("AF6Zscrn")
    assert isinstance(play, OffensivePlay)
    assert play.screen is (pool_name == "pnfl_pool")


@pytest.mark.parametrize("pool_name", ALL_POOLS)
@pytest.mark.parametrize("name,category,pnfl_front", DEFENSE)
def test_defensive_file_driven(
    request: pytest.FixtureRequest,
    pool_name: str,
    name: str,
    category: str,
    pnfl_front: DefensiveFront | None,
) -> None:
    pool: PlayPool = request.getfixturevalue(pool_name)
    play = pool.find_by_name(name)
    assert isinstance(play, DefensivePlay)
    assert play in pool.defensive_plays
    assert play.category.long == category
    expected = pnfl_front if pool_name == "pnfl_pool" else None
    assert play.defensive_front == expected


@pytest.mark.parametrize("pool_name", ALL_POOLS)
def test_special_file_driven(request: pytest.FixtureRequest, pool_name: str) -> None:
    play = request.getfixturevalue(pool_name).find_by_name("AF-KO")
    assert isinstance(play, SpecialTeamsPlay)
    assert play.category.long == "Kickoff"


@pytest.mark.parametrize("pool_name", ALL_POOLS)
def test_find_across_sides(request: pytest.FixtureRequest, pool_name: str) -> None:
    pool: PlayPool = request.getfixturevalue(pool_name)
    assert pool.find_by_name("af2ashtz") is not None  # offense, case-insensitive
    assert pool.find_by_name("AF32GP02") is not None  # defense
    assert pool.find_by_name("AF-KO") is not None  # special
    assert pool.find_by_name("DOESNOTEXIST") is None


@pytest.mark.parametrize("tree", ["pnfl", "flat", "nonpnfl"])
def test_no_warnings_on_consistent_trees(
    request: pytest.FixtureRequest, tree: str, caplog: pytest.LogCaptureFixture
) -> None:
    """PNFL plays match their folders; non-PNFL/flat have no recognized folders."""
    root = PLAYS if tree == "pnfl" else request.getfixturevalue(f"{tree}_tree")
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        read_play_pool(root)
    assert "play in" not in caplog.text  # no side/category mismatch warnings


def test_invalid_skipped(caplog: pytest.LogCaptureFixture) -> None:
    assert (PLAYS / "Offense" / "PML" / "PS7Xmids.ply").is_file()
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        pool = read_play_pool(PLAYS)
    assert "Skipping invalid play file" in caplog.text and "PS7Xmids" in caplog.text
    assert pool.find_by_name("PS7Xmids") is None


def test_flat_play_classified_from_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A loose .ply (no folders) is classified from its file, not skipped."""
    src = next(PLAYS.glob("**/AF21rm12.ply"))  # offensive Run Middle
    shutil.copy(src, tmp_path / "loose.ply")
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        play = read_play_pool(tmp_path).find_by_name("loose")
    assert isinstance(play, OffensivePlay)
    assert play.category.long == "Run Middle"
    assert "play in" not in caplog.text


# ── file wins over folder; mismatches warn (end-to-end) ───────────────────────


def test_wrong_side_folder_file_wins_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A defensive play under an offense folder stays defensive, but warns."""
    src = next(PLAYS.glob("**/AF32gp02.ply"))  # defensive
    dst = tmp_path / "Offense" / "Screens"
    dst.mkdir(parents=True)
    shutil.copy(src, dst / "AF32gp02.ply")
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        play = read_play_pool(tmp_path).find_by_name("AF32gp02")
    assert isinstance(play, DefensivePlay)  # file wins
    assert (
        "Defensive play in the offense tree: Offense/Screens/AF32gp02.ply"
        in caplog.text
    )


def test_wrong_category_folder_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """An offense play in the wrong category folder warns but classifies by file."""
    src = next(PLAYS.glob("**/AF2AshtZ.ply"))  # Pass Short Middle
    dst = tmp_path / "Offense" / "PML"  # folder says Pass Medium Left
    dst.mkdir(parents=True)
    shutil.copy(src, dst / "AF2AshtZ.ply")
    with caplog.at_level(logging.WARNING, logger="athc.playpool.pool"):
        play = read_play_pool(tmp_path).find_by_name("AF2AshtZ")
    assert isinstance(play, OffensivePlay)
    assert play.category.long == "Pass Short Middle"
    assert (
        "Pass Short Middle play in a Pass Medium Left folder: Offense/PML/AF2AshtZ.ply"
        in caplog.text
    )


# ── folder_warnings unit cases (pure; exhaustive over mismatch kinds) ──────────


def test_warn_defensive_play_in_offense_tree(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense
    w = folder_warnings("Offense/PMR/Screens/X.ply", play)
    assert w == ["Defensive play in the offense tree: Offense/PMR/Screens/X.ply"]


def test_warn_offensive_play_in_defense_tree(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x09)  # offense
    w = folder_warnings("Defense/34RunLeft/X.ply", play)
    assert w == ["Offensive play in the defense tree: Defense/34RunLeft/X.ply"]


def test_warn_special_play_in_side_tree(make_play: MakePlay) -> None:
    play = make_play("X", special_category=0x02)  # special teams
    w = folder_warnings("Defense/X.ply", play)
    assert w == ["Special-teams play in the defense tree: Defense/X.ply"]


def test_warn_offense_category_mismatch(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x07)  # Pass Short Left
    w = folder_warnings("Offense/PML/X.ply", play)
    assert w == ["Pass Short Left play in a Pass Medium Left folder: Offense/PML/X.ply"]


def test_warn_defense_category_mismatch(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x00, user_category=0x22)  # Pass Long
    w = folder_warnings("Defense/RunLeft/X.ply", play)
    assert w == ["Pass Long play in a Run Left folder: Defense/RunLeft/X.ply"]


def test_warn_user_specific_in_category_folder(make_play: MakePlay) -> None:
    """A User Specific play warns as a plain category mismatch (its category
    never matches a folder)."""
    play = make_play("X", play_category=0x01, user_category=0xFF)  # User Specific
    w = folder_warnings("Offense/PML/X.ply", play)
    assert w == ["User Specific play in a Pass Medium Left folder: Offense/PML/X.ply"]


def test_wrong_side_reported_alone(make_play: MakePlay) -> None:
    """Side mismatch suppresses the (cross-side) category mismatch."""
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense, Pass Short
    w = folder_warnings("Offense/PML/X.ply", play)
    assert w == ["Defensive play in the offense tree: Offense/PML/X.ply"]


def test_no_warn_when_consistent(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x17)  # Pass Medium Left
    assert folder_warnings("Offense/PML/X.ply", play) == []


@pytest.mark.parametrize("rel", ["X.ply", "Offense/X.ply", "alpha/beta/X.ply"])
def test_no_warn_loose_or_unrecognized(make_play: MakePlay, rel: str) -> None:
    """No category folder (loose, side root, or non-PNFL) → no warning, even for a
    User Specific play that has no valid PNFL folder anywhere."""
    play = make_play("X", play_category=0x01, user_category=0xFF)  # User Specific
    assert folder_warnings(rel, play) == []
