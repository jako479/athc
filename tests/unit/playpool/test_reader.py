"""Tests for read_play_pool: file-driven classification across three layouts,
optional league folder attributes, and folder mismatch warnings."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from athc.errors import ACCESS_DENIED
from athc.fbpro98_play import CategoryLabels, Command, DefensiveFront, LogicBox
from athc.fbpro98_play.schema import (
    COMMAND_MOVE_TO,
    COMMAND_RUN,
    COMMAND_TIMED_PASS,
    POSITION_QB,
    POSITION_T,
)
from athc.playpool import (
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    PlayPool,
    SpecialPlay,
    read_play_pool,
)
from athc.playpool.reader import folder_warnings
from tests.conftest import PNFL_LABELS
from tests.unit.fbpro98_play.conftest import build_ply, build_record
from tests.unit.playpool.conftest import PLAYS, MakePlay

ALL_POOLS = ["league_pool", "flat_pool", "arbitrary_pool"]

# Attributes from the play file — identical in every layout. GBglpH1R and
# JJ9ZXOTR are not rollouts: their QBs stay inside the tackles (131 and 60
# units inside) before they throw.
# (name, category, rollout, qb_run, pass_logic)
OFFENSE = [
    ("AF21rm12", "Run Middle", False, False, None),
    ("AF2AshtZ", "Pass Short Middle", False, False, PassLogic.CHECK_RECEIVERS),
    ("AF6A02T", "Pass Medium Right", False, False, PassLogic.TIMED),
    ("AF6Zscrn", "Pass Medium Right", False, False, PassLogic.CHECK_RECEIVERS),
    ("GBglpH1R", "Goal Line Pass", False, False, PassLogic.TIMED),
    ("JJ9ZXOTR", "Pass Long Right", False, False, PassLogic.TIMED),
    ("WR10GR01", "Goal Line Run", False, True, None),
]

# (name, category, front) — the front comes from the play file, in every
# layout.
DEFENSE = [
    ("AF22PL01", "Pass Long", DefensiveFront.TWO_DL),
    ("AF31rl3H", "Run Left", DefensiveFront.THREE_FOUR),
    ("AF32gp02", "Goal Line Pass", None),
    ("AF41rl2p", "Run Left", DefensiveFront.FOUR_THREE),
]


# ── classification is the same in every layout ────────────────────────────────


@pytest.mark.parametrize("pool_name", ALL_POOLS)
@pytest.mark.parametrize("name,category,rollout,qb_run,logic", OFFENSE)
def test_offensive_file_driven(
    request: pytest.FixtureRequest,
    pool_name: str,
    name: str,
    category: str,
    rollout: bool,
    qb_run: bool,
    logic: PassLogic | None,
) -> None:
    pool: PlayPool = request.getfixturevalue(pool_name)
    play = pool.find_by_name(name)
    assert isinstance(play, OffensivePlay)
    assert play in pool.offensive_plays
    assert play.category.long == category
    assert (play.rollout, play.qb_run, play.pass_logic) == (rollout, qb_run, logic)


@pytest.mark.parametrize("pool_name", ALL_POOLS)
def test_screen_only_from_screens_folder(
    request: pytest.FixtureRequest, pool_name: str
) -> None:
    """Only the play in `Screens/` is a screen, and only in the league layout;
    AF6A02T sits in the folder that holds `Screens/`."""
    pool: PlayPool = request.getfixturevalue(pool_name)
    screens = [play.name for play in pool.offensive_plays if play.screen]
    assert screens == (["AF6Zscrn"] if pool_name == "league_pool" else [])


@pytest.mark.parametrize("pool_name", ALL_POOLS)
@pytest.mark.parametrize("name,category,front", DEFENSE)
def test_defensive_file_driven(
    request: pytest.FixtureRequest,
    pool_name: str,
    name: str,
    category: str,
    front: DefensiveFront | None,
) -> None:
    pool: PlayPool = request.getfixturevalue(pool_name)
    play = pool.find_by_name(name)
    assert isinstance(play, DefensivePlay)
    assert play in pool.defensive_plays
    assert play.category.long == category
    assert play.defensive_front is front


# ── attributes from built plays: the rollout margin and the category gates ────

TIMED = Command(COMMAND_TIMED_PASS, (0,))
RUN = Command(COMMAND_RUN, (2,))


def _write_play(
    folder: Path, name: str, user_category: int, *qb_after_snap: LogicBox
) -> None:
    """An offensive play: tackles at -300 and 300, a QB doing `qb_after_snap`."""
    tackles = [
        build_record(POSITION_T, after_snap=[LogicBox(x, -140, ())])
        for x in (-300, 300)
    ]
    qb = build_record(POSITION_QB, after_snap=qb_after_snap)
    others = [build_record(0x80)] * 8  # WR
    data = build_ply(
        play_category=user_category,
        user_category=user_category,
        player_records=[qb, *tackles, *others],
    )
    (folder / f"{name}.ply").write_bytes(data)


def _copy_play(name: str, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(next(PLAYS.glob(f"**/{name}.ply")), folder / f"{name}.ply")


@pytest.fixture
def reversed_glob(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Path.glob` lists in reverse path order, so only the reader's own sort can
    load the plays in path order (NTFS already lists a folder sorted)."""
    glob = Path.glob

    def _reversed(self: Path, pattern: str, **kwargs: Any) -> Iterator[Path]:
        return iter(sorted(glob(self, pattern, **kwargs), reverse=True))

    monkeypatch.setattr(Path, "glob", _reversed)


@pytest.mark.parametrize(("x", "rollout"), [(400, False), (401, True)])
def test_rollout_is_beyond_100_units_outside_the_line(
    tmp_path: Path, x: int, rollout: bool
) -> None:
    move = Command(COMMAND_MOVE_TO, (x, -300))
    _write_play(tmp_path, "P", 0x03, LogicBox(0, -300, (move, TIMED)))
    play = read_play_pool(tmp_path).find_by_name("P")
    assert isinstance(play, OffensivePlay)
    assert play.rollout is rollout


def test_category_still_gates_the_attributes(tmp_path: Path) -> None:
    """A pass play's QB run is no QB run; a run play's QB pass has no pass logic."""
    move_out = Command(COMMAND_MOVE_TO, (1000, -300))
    _write_play(tmp_path, "PASS", 0x03, LogicBox(0, -300, (RUN,)))  # Pass Short Right
    _write_play(tmp_path, "RUN", 0x09, LogicBox(0, -300, (move_out, TIMED)))
    pool = read_play_pool(tmp_path)
    pass_play, run_play = pool.find_by_name("PASS"), pool.find_by_name("RUN")
    assert isinstance(pass_play, OffensivePlay) and not pass_play.qb_run
    assert isinstance(run_play, OffensivePlay)
    assert (run_play.rollout, run_play.pass_logic) == (False, None)


def test_run_play_in_screens_folder_is_no_screen(tmp_path: Path) -> None:
    """Only a pass play in a `Screens` folder is a screen."""
    _copy_play("AF21rm12", tmp_path / "Offense" / "Screens")  # Run Middle
    play = read_play_pool(tmp_path).find_by_name("AF21rm12")
    assert isinstance(play, OffensivePlay) and not play.screen


@pytest.mark.parametrize("pool_name", ALL_POOLS)
def test_special_file_driven(request: pytest.FixtureRequest, pool_name: str) -> None:
    play = request.getfixturevalue(pool_name).find_by_name("AF-KO")
    assert isinstance(play, SpecialPlay)
    assert play.category.long == "Kickoff"


@pytest.mark.parametrize("tree", ["league", "flat", "arbitrary"])
def test_no_issues_on_consistent_trees(
    request: pytest.FixtureRequest, tree: str
) -> None:
    """League-layout plays match their folders; the others have no recognized folders."""
    root = PLAYS if tree == "league" else request.getfixturevalue(f"{tree}_tree")
    assert read_play_pool(root, labels=PNFL_LABELS).issues == []


# ── file wins over folder; mismatches are issues (end-to-end) ─────────────────


def test_wrong_side_folder_file_wins_and_warns(tmp_path: Path) -> None:
    """A defensive play under an offense folder stays defensive, but is an issue."""
    _copy_play("AF32gp02", tmp_path / "Offense" / "Screens")  # defensive
    pool = read_play_pool(tmp_path, labels=PNFL_LABELS)
    assert isinstance(pool.find_by_name("AF32gp02"), DefensivePlay)  # file wins
    assert pool.issues == [
        "Offense/Screens/AF32gp02.ply: Defensive play in the offense tree."
    ]


def test_wrong_category_folder_warns(tmp_path: Path) -> None:
    """An offense play in the wrong category folder is an issue but classifies
    by file."""
    _copy_play("AF2AshtZ", tmp_path / "Offense" / "PML")  # Pass Short Middle
    pool = read_play_pool(tmp_path, labels=PNFL_LABELS)
    play = pool.find_by_name("AF2AshtZ")
    assert isinstance(play, OffensivePlay)
    assert play.category.long == "Pass Short Middle"
    assert pool.issues == [
        "Offense/PML/AF2AshtZ.ply: Pass Short Middle play in a Pass Medium Left folder."
    ]


def test_side_and_screens_folders_apply_without_labels(tmp_path: Path) -> None:
    """With no labels the side and `Screens` folders still count; `PMR` does not."""
    _copy_play("AF6Zscrn", tmp_path / "Offense" / "PMR" / "Screens")
    _copy_play("AF32gp02", tmp_path / "Offense")  # defensive
    pool = read_play_pool(tmp_path)
    play = pool.find_by_name("AF6Zscrn")
    assert isinstance(play, OffensivePlay) and play.screen
    assert pool.issues == ["Offense/AF32gp02.ply: Defensive play in the offense tree."]


# ── issues: every problem is kept on the pool, word for word ──────────────────


@pytest.mark.usefixtures("reversed_glob")
def test_duplicate_winner_is_last_in_path_order(tmp_path: Path) -> None:
    """Files load in sorted path order, so of two same-named plays the one under
    the later folder wins, whatever order the filesystem lists them in."""
    _copy_play("AF21rm12", tmp_path / "a")  # Run Middle
    (tmp_path / "b").mkdir()
    src = next(PLAYS.glob("**/AF2AshtZ.ply"))  # Pass Short Middle bytes
    shutil.copy(src, tmp_path / "b" / "AF21rm12.ply")
    pool = read_play_pool(tmp_path)
    play = pool.find_by_name("AF21rm12")
    assert play is not None and play.category.long == "Pass Short Middle"
    assert [p.file_path for p in pool.offensive_plays] == [
        tmp_path / "a" / "AF21rm12.ply",
        tmp_path / "b" / "AF21rm12.ply",
    ]
    assert play is pool.offensive_plays[1]
    assert pool.issues == ["Duplicate play name 'AF21rm12'. The last one loaded wins."]


def test_unreadable_file_is_an_issue(tmp_path: Path) -> None:
    """A .ply that cannot be read (here a folder by that name) is skipped with a
    warning like an invalid one; the rest of the pool still loads."""
    (tmp_path / "locked.ply").mkdir()
    _copy_play("AF21rm12", tmp_path)
    pool = read_play_pool(tmp_path)
    assert pool.issues == [f"{tmp_path / 'locked.ply'}: {ACCESS_DENIED} Skipped."]
    assert pool.find_by_name("AF21rm12") is not None


def test_invalid_file_is_an_issue(tmp_path: Path) -> None:
    """An invalid .ply is skipped with its reason; the rest of the pool still
    loads."""
    (tmp_path / "bad.ply").write_bytes(b"\x00\x01\x02")
    _copy_play("AF21rm12", tmp_path)
    pool = read_play_pool(tmp_path)
    assert pool.issues == [
        f"{tmp_path / 'bad.ply'}: The play file is invalid or corrupted. Skipped."
    ]
    assert pool.find_by_name("AF21rm12") is not None


@pytest.mark.usefixtures("reversed_glob")
def test_issues_keep_path_order(tmp_path: Path) -> None:
    """Issues come in the reader's path order (Windows sorts paths without
    regard to case, so `b` precedes `Offense`)."""
    _copy_play("AF2AshtZ", tmp_path / "Offense" / "PML")
    _copy_play("AF21rm12", tmp_path / "a")
    _copy_play("AF21rm12", tmp_path / "b")
    assert read_play_pool(tmp_path, labels=PNFL_LABELS).issues == [
        "Duplicate play name 'AF21rm12'. The last one loaded wins.",
        "Offense/PML/AF2AshtZ.ply: Pass Short Middle play in a Pass Medium Left folder.",
    ]


# ── folder_warnings unit cases (pure; exhaustive over mismatch kinds) ──────────


def test_warn_defensive_play_in_offense_tree(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense
    w = folder_warnings("Offense/PMR/Screens/X.ply", play, PNFL_LABELS)
    assert w == ["Offense/PMR/Screens/X.ply: Defensive play in the offense tree."]


def test_warn_offensive_play_in_defense_tree(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x09)  # offense
    w = folder_warnings("Defense/34RunLeft/X.ply", play, PNFL_LABELS)
    assert w == ["Defense/34RunLeft/X.ply: Offensive play in the defense tree."]


def test_warn_special_play_in_side_tree(make_play: MakePlay) -> None:
    play = make_play("X", special_category=0x02)  # special
    w = folder_warnings("Defense/X.ply", play, PNFL_LABELS)
    assert w == ["Defense/X.ply: Special play in the defense tree."]


def test_warn_offense_category_mismatch(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x07)  # Pass Short Left
    w = folder_warnings("Offense/PML/X.ply", play, PNFL_LABELS)
    assert w == [
        "Offense/PML/X.ply: Pass Short Left play in a Pass Medium Left folder."
    ]


def test_warn_defense_category_mismatch(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x00, user_category=0x22)  # Pass Long
    w = folder_warnings("Defense/RunLeft/X.ply", play, PNFL_LABELS)
    assert w == ["Defense/RunLeft/X.ply: Pass Long play in a Run Left folder."]


def test_warn_user_specific_in_category_folder(make_play: MakePlay) -> None:
    """A User Specific play warns as a plain category mismatch (its category
    never matches a folder)."""
    play = make_play("X", play_category=0x01, user_category=0xFF)  # User Specific
    w = folder_warnings("Offense/PML/X.ply", play, PNFL_LABELS)
    assert w == ["Offense/PML/X.ply: User Specific play in a Pass Medium Left folder."]


@pytest.mark.parametrize(
    ("rel", "play_category", "user_category", "warning"),
    [
        ("Screens/X.ply", 0x00, 0x02, "Defensive play in the offense tree."),
        ("R&SDefs/X.ply", 0x01, 0x09, "Offensive play in the defense tree."),
    ],
)
def test_screens_and_rns_folders_name_their_side(
    make_play: MakePlay, rel: str, play_category: int, user_category: int, warning: str
) -> None:
    """`Screens` is an offense folder and `R&SDefs` a defense one, on their own."""
    play = make_play("X", play_category=play_category, user_category=user_category)
    assert folder_warnings(rel, play, PNFL_LABELS) == [f"{rel}: {warning}"]


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("Offense/PML/PSM/X.ply", []),
        (
            "Offense/PSM/PML/X.ply",
            [
                "Offense/PSM/PML/X.ply: Pass Short Middle play in a Pass Medium "
                "Left folder."
            ],
        ),
    ],
)
def test_deeper_category_folder_wins(
    make_play: MakePlay, rel: str, expected: list[str]
) -> None:
    play = make_play("X", play_category=0x01, user_category=0x0B)  # Pass Short Middle
    assert folder_warnings(rel, play, PNFL_LABELS) == expected


def test_wrong_side_reported_alone(make_play: MakePlay) -> None:
    """Side mismatch suppresses the (cross-side) category mismatch."""
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense, Pass Short
    w = folder_warnings("Offense/PML/X.ply", play, PNFL_LABELS)
    assert w == ["Offense/PML/X.ply: Defensive play in the offense tree."]


def test_no_warn_when_consistent(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x01, user_category=0x17)  # Pass Medium Left
    assert folder_warnings("Offense/PML/X.ply", play, PNFL_LABELS) == []


@pytest.mark.parametrize("rel", ["X.ply", "Offense/X.ply", "alpha/beta/X.ply"])
def test_no_warn_loose_or_unrecognized(make_play: MakePlay, rel: str) -> None:
    """No category folder (loose, side root, or unrecognized) → no warning, even
    for a User Specific play that has no valid category folder anywhere."""
    play = make_play("X", play_category=0x01, user_category=0xFF)  # User Specific
    assert folder_warnings(rel, play, PNFL_LABELS) == []


def test_no_labels_means_no_category_folders(make_play: MakePlay) -> None:
    """Without league labels a PNFL category folder is just a folder."""
    play = make_play("X", play_category=0x01, user_category=0x07)  # Pass Short Left
    assert folder_warnings("Offense/PML/X.ply", play, CategoryLabels()) == []


def test_shared_label_resolves_to_the_plays_side(make_play: MakePlay) -> None:
    """`RR` names Run Right on both sides: each side's Run Right sits in it quietly."""
    labels = CategoryLabels.from_tables({"Run Right": "RR"}, {"Run Right": "RR"})
    offense = make_play("X", play_category=0x01, user_category=0x01)
    defense = make_play("X", play_category=0x00, user_category=0x00)
    assert folder_warnings("RR/X.ply", offense, labels) == []
    assert folder_warnings("RR/X.ply", defense, labels) == []
    pass_play = make_play("X", play_category=0x00, user_category=0x02)  # Pass Short
    assert folder_warnings("RR/X.ply", pass_play, labels) == [
        "RR/X.ply: Pass Short play in a Run Right folder."
    ]


def test_other_sides_label_still_warns_wrong_side(make_play: MakePlay) -> None:
    """A folder named with the other side's label is that side's tree."""
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense
    assert folder_warnings("PML/X.ply", play, PNFL_LABELS) == [
        "PML/X.ply: Defensive play in the offense tree."
    ]


@pytest.mark.parametrize("front", ["34", "43"])
def test_front_prefix_uses_defense_labels(make_play: MakePlay, front: str) -> None:
    play = make_play("X", play_category=0x00, user_category=0x22)  # Pass Long
    assert folder_warnings(f"{front}RunLeft/X.ply", play, PNFL_LABELS) == [
        f"{front}RunLeft/X.ply: Pass Long play in a Run Left folder."
    ]
    # not a defense label
    assert folder_warnings(f"{front}PML/X.ply", play, PNFL_LABELS) == []


@pytest.mark.parametrize("front", ["34", "43"])
def test_front_prefix_needs_a_defense_label(make_play: MakePlay, front: str) -> None:
    """A front folder is a defense folder only when the rest of its name is a
    defense label; otherwise it is unrecognized and never warns."""
    play = make_play("X", play_category=0x01, user_category=0x09)  # offense
    assert folder_warnings(f"{front}PML/X.ply", play, PNFL_LABELS) == []
    assert folder_warnings(f"{front}RunLeft/X.ply", play, CategoryLabels()) == []


# ── the reader never logs: every problem is an issue on the pool ──────────────


def test_reader_never_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    _copy_play("AF2AshtZ", tmp_path / "Offense" / "PML")
    (tmp_path / "bad.ply").write_bytes(b"\x00\x01\x02")
    with caplog.at_level(logging.DEBUG):
        pool = read_play_pool(tmp_path, labels=PNFL_LABELS)
    assert caplog.records == []
    assert len(pool.issues) == 2
