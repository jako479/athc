"""Workbook generation tests: synthetic PDB + injected pool, read back with openpyxl."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
import pytest

from athc.fbpro98_play import OffensiveCategory as O
from athc.pdbtoexcel import Config, PdbWorkbookCreator
from athc.pdbtoexcel.pdb import PDB, PLAY_DATA
from athc.playpool import DefensiveFront
from tests.conftest import PNFL_LABELS
from tests.unit.pdbtoexcel.conftest import (
    PNFL_ORDER,
    make_play_data,
    make_pool,
    make_record,
    make_tendency,
    write_pdb,
)

RUN = PLAY_DATA.PLAY_TYPE.RUN
PASS = PLAY_DATA.PLAY_TYPE.PASS
DEFENSE = PLAY_DATA.PLAY_TYPE.DEFENSE

# user_category codes: Run Left 0x05, Run Middle 0x09, Run Right 0x01.
RUN_LEFT, RUN_MIDDLE = 0x05, 0x09


def _config(**over: object) -> Config:
    base: dict[str, object] = {
        "play_path": "",
        "playpool_rules": None,
        "calculate_percentages": True,
        "include_category_worksheets": False,
        "exclude_sacks_from_pass_attempts": True,
        "category_order": PNFL_ORDER,
        "categories": PNFL_LABELS,
    }
    base.update(over)
    return Config(**base)  # type: ignore[arg-type]


def _convert(
    tmp_path: Path,
    plays,
    records,
    *,
    config=None,
    calculate_totals=False,
    tendencies=(),
    perform_calcs=True,
) -> tuple[openpyxl.Workbook, PdbWorkbookCreator]:
    """Convert and read the workbook back, with the creator for its warnings."""
    pdb = PDB(str(write_pdb(tmp_path / "in.pdb", plays=plays, tendencies=tendencies)))
    out = tmp_path / "out.xlsx"
    creator = PdbWorkbookCreator(config or _config(), make_pool(records), pdb)
    creator.create_workbook(str(out), perform_calcs, calculate_totals)
    return openpyxl.load_workbook(out), creator


def _build(tmp_path: Path, plays, records, **options) -> openpyxl.Workbook:
    return _convert(tmp_path, plays, records, **options)[0]


def _rows(ws):
    return list(ws.iter_rows(values_only=True))


def _run_play(name: str, team: str = "Bears", **stats: int) -> PLAY_DATA:
    return make_play_data(RUN, team, name, **stats)


def test_base_sheets_and_run_row(tmp_path: Path) -> None:
    play = _run_play(
        "RUN1", play_count=10, total_yards=46, fumbles=1, touchdowns_offense=2
    )
    wb = _build(
        tmp_path, [play], [make_record("RUN1", play_category=0x01, user_category=0x09)]
    )  # Run Middle
    assert {"Options", "Run Plays", "Pass Plays", "Def Plays", "Tendencies"} <= set(
        wb.sheetnames
    )
    header, data = _rows(wb["Run Plays"])[0], _rows(wb["Run Plays"])[1]
    assert header[:6] == ("Team", "Category", "Slot 1", "Slot 2", "Play", "Type")
    assert (data[0], data[1], data[4]) == ("Bears", "RM", "RUN1")
    assert not data[5]  # empty Type (no qb_draw) — openpyxl reads "" as None
    assert (data[6], data[7], data[8]) == (10, 46, 4.6)  # rushes, yards, avg


def test_run_row_with_no_attempts_writes_zeros(tmp_path: Path) -> None:
    play = _run_play("RUN0", play_count=0, total_yards=0)
    record = make_record("RUN0", play_category=0x01, user_category=RUN_MIDDLE)
    config = _config(include_category_worksheets=True)
    wb = _build(tmp_path, [play], [record], config=config)
    data = _rows(wb["Run Plays"])[1]
    assert (data[6], data[8], data[10], data[12]) == (0, 0, 0, 0)  # rushes, avg, %, %
    assert _rows(wb["Run Categories"])[1][6] == 0  # Fumble %


def test_pass_row_screen_and_stats(tmp_path: Path) -> None:
    play = make_play_data(
        PASS, "Jets", "PASS1", play_count=10, completions=6, sacks=2, total_yards=70
    )
    record = make_record(
        "PASS1", play_category=0x01, user_category=0x03, screen=True
    )  # Pass Short Right
    data = _rows(_build(tmp_path, [play], [record])["Pass Plays"])[1]
    assert (data[1], data[4], data[5]) == ("PSR", "PASS1", "Screen")
    assert (data[6], data[7]) == (6, 8)  # comp, att (10 - 2 sacks)


def test_defense_row_front_type(tmp_path: Path) -> None:
    play = make_play_data(
        DEFENSE,
        "Vikes",
        "DEF1",
        run_plays_against=5,
        pass_plays_against=5,
        rush_yards_allowed=10,
    )
    record = make_record(
        "DEF1",
        play_category=0x00,
        user_category=0x00,
        defensive_front=DefensiveFront.THREE_FOUR,
    )
    data = _rows(_build(tmp_path, [play], [record])["Def Plays"])[1]
    assert (data[1], data[4], data[5]) == ("RunRight", "DEF1", "3-4")
    assert data[6] == 10  # total calls (run + pass against)


def test_unlabeled_category_shows_its_game_name(tmp_path: Path) -> None:
    order = {**PNFL_ORDER, RUN: (O.RUN_LEFT, O.RAZZLE_DAZZLE_RUN)}
    play = _run_play("RDR", play_count=1, total_yards=1)
    record = make_record("RDR", play_category=0x01, user_category=0x0D)
    wb = _build(tmp_path, [play], [record], config=_config(category_order=order))
    assert _rows(wb["Run Plays"])[1][1] == "Razzle Dazzle Run"


def test_qb_draw_type(tmp_path: Path) -> None:
    play = _run_play("QBD", play_count=3, total_yards=9)
    record = make_record("QBD", play_category=0x01, user_category=0x09, qb_draw=True)
    assert _rows(_build(tmp_path, [play], [record])["Run Plays"])[1][5] == "QB draw"


def test_skip_calcs_omits_percent_columns(tmp_path: Path) -> None:
    play = _run_play("RUN1", play_count=10, total_yards=46)
    record = make_record("RUN1", play_category=0x01, user_category=0x09)
    with_calcs = _rows(_build(tmp_path, [play], [record])["Run Plays"])[0]
    without = _rows(
        _build(tmp_path, [play], [record], perform_calcs=False)["Run Plays"]
    )[0]
    assert "Fumble %" in with_calcs and "Fumble %" not in without


def test_totals_adds_total_stats_team(tmp_path: Path) -> None:
    plays = [
        _run_play("RUN1", play_count=10, total_yards=40),
        _run_play("RUN1", team="Jets", play_count=5, total_yards=30),
    ]
    record = make_record("RUN1", play_category=0x01, user_category=0x09)
    teams = [
        row[0]
        for row in _rows(
            _build(tmp_path, plays, [record], calculate_totals=True)["Run Plays"]
        )[1:]
    ]
    assert "Total Stats" in teams


def test_category_worksheets_when_enabled(tmp_path: Path) -> None:
    play = _run_play("RUN1", play_count=10, total_yards=40)
    record = make_record("RUN1", play_category=0x01, user_category=0x09)
    wb = _build(
        tmp_path, [play], [record], config=_config(include_category_worksheets=True)
    )
    assert "Run Categories" in wb.sheetnames
    assert _rows(wb["Run Categories"])[1][1] == "RM"


def test_special_teams_and_unknown_plays_skipped(tmp_path: Path) -> None:
    plays = [
        _run_play("STPLAY", play_count=1),  # in pool but special teams
        _run_play("GHOST", play_count=1),  # not in pool
    ]
    record = make_record(
        "STPLAY", play_category=0x01, user_category=0x09, special_category=0x02
    )
    wb, creator = _convert(tmp_path, plays, [record])
    assert _rows(wb["Run Plays"]) == [_rows(_build(tmp_path, [], [])["Run Plays"])[0]]
    assert creator.warnings == ["Play file not found for play 'GHOST'"]


def test_tendencies_written(tmp_path: Path) -> None:
    wb = _build(tmp_path, [], [], tendencies=[make_tendency("Bears")])
    rows = _rows(wb["Tendencies"])
    assert len(rows) == 1 + 16  # header + 4 downs x 4 buckets
    assert rows[1][0] == "Bears"


def test_slot_column_from_gameplan(tmp_path: Path) -> None:
    from athc.fbpro98_gameplan import read_gameplan
    from tests.unit.pdbtoexcel.conftest import DATA

    plan = read_gameplan(
        str(DATA / "offense.pln")
    )  # OR45RL01 is at normal slot 0 -> "1-1"
    play = _run_play("OR45RL01", play_count=5, total_yards=20)
    pdb = PDB(str(write_pdb(tmp_path / "in.pdb", plays=[play])))
    pool = make_pool([make_record("OR45RL01", play_category=0x01, user_category=0x09)])
    out = tmp_path / "out.xlsx"
    creator = PdbWorkbookCreator(_config(), pool, pdb, pln_offense=plan)
    creator.create_workbook(str(out), True, False)
    data = _rows(openpyxl.load_workbook(out)["Run Plays"])[1]
    assert data[2] == "1-1"  # Slot 1


# ── category order ────────────────────────────────────────────────────────────


def test_options_sheet_lists_the_order_by_label(tmp_path: Path) -> None:
    ws = _build(tmp_path, [], [])["Options"]
    column = lambda col: [  # noqa: E731
        ws.cell(row=r, column=col).value for r in range(3, 3 + 10)
    ]
    assert column(8)[:4] == ["RL", "RM", "RR", "GLR"] and column(8)[4] is None
    assert column(9)[:9] == [
        "PSL", "PSM", "PSR", "PML", "PMM", "PMR", "PLR", "PRD", "GLP",
    ]  # fmt: skip
    assert column(10) == [
        "RunLeft", "RunMiddle", "RunRight", "RunDazzle", "PassShort",
        "PassMedium", "PassLong", "PassDazzle", "GLrun", "GLpass",
    ]  # fmt: skip


def test_rows_follow_the_category_order(tmp_path: Path) -> None:
    # PDB order and alphabetical order both put RM first; the league order says RL.
    plays = [
        _run_play("A-RM", play_count=1, total_yards=1),
        _run_play("B-RL", play_count=1, total_yards=1),
    ]
    records = [
        make_record("A-RM", play_category=0x01, user_category=RUN_MIDDLE),
        make_record("B-RL", play_category=0x01, user_category=RUN_LEFT),
    ]
    names = [row[4] for row in _rows(_build(tmp_path, plays, records)["Run Plays"])[1:]]
    assert names == ["B-RL", "A-RM"]


def test_unlisted_category_is_left_out(tmp_path: Path) -> None:
    order = {**PNFL_ORDER, RUN: (O.RUN_LEFT,)}
    plays = [
        _run_play("RL1", play_count=1, total_yards=1),
        _run_play("RM1", play_count=1, total_yards=1),
    ]
    records = [
        make_record("RL1", play_category=0x01, user_category=RUN_LEFT),
        make_record("RM1", play_category=0x01, user_category=RUN_MIDDLE),
    ]
    wb = _build(tmp_path, plays, records, config=_config(category_order=order))
    assert [row[4] for row in _rows(wb["Run Plays"])[1:]] == ["RL1"]


# ── deleted plays ─────────────────────────────────────────────────────────────


def test_deleted_play_is_skipped_quietly(tmp_path: Path) -> None:
    config = _config(deleted_plays=frozenset({"GHOST"}))
    plays = [_run_play("ghost", play_count=1), _run_play("ghost", team="Jets")]
    wb, creator = _convert(tmp_path, plays, [], config=config)
    assert len(_rows(wb["Run Plays"])) == 1  # header only
    assert creator.warnings == []


def test_deleted_play_still_in_the_pool_is_skipped_with_a_warning(
    tmp_path: Path,
) -> None:
    # Matched case-insensitively; the warning keeps the spelling from the file.
    config = _config(deleted_plays=frozenset({"run1"}))
    record = make_record("RUN1", play_category=0x01, user_category=RUN_MIDDLE)
    plays = [_run_play("RUN1", play_count=1), _run_play("RUN1", team="Jets")]
    wb, creator = _convert(
        tmp_path, plays, [record], config=config, calculate_totals=True
    )
    assert len(_rows(wb["Run Plays"])) == 1
    assert creator.warnings == [
        "'run1' is listed in [deleted_plays] but is in the play pool; its stats "
        "are skipped"
    ]


# ── warnings and progress come back as values; nothing is logged ──────────────


def test_warnings_are_returned_not_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    plays = [_run_play("RUN1", play_count=1), _run_play("GHOST", play_count=1)]
    record = make_record("RUN1", play_category=0x01, user_category=RUN_MIDDLE)
    pdb = PDB(str(write_pdb(tmp_path / "in.pdb", plays=plays)))
    creator = PdbWorkbookCreator(_config(), make_pool([record]), pdb)
    out = tmp_path / "w.xlsx"
    said: list[str] = []
    with caplog.at_level(logging.DEBUG):
        rows = creator.create_workbook(str(out), True, True, progress=said.append)
    assert caplog.records == []
    assert said == [f"Creating '{out}'"]
    assert creator.warnings == ["Play file not found for play 'GHOST'"]
    assert rows == 1
