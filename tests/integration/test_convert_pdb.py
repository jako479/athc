"""Integration tests for `athc convert-pdb`."""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest

from athc.cli.convert_pdb import convert_pdb
from athc.pdbtoexcel import config as pdbtoexcel_config
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.integration.conftest import DATA

PDB = DATA / "2045-2047.pdb"
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(
    make_league: MakeLeague, write_config: Callable[..., Path], tmp_path: Path
) -> Path:
    """The selected league, with no rules; its play_path is an empty folder."""
    plays = tmp_path / "plays"
    plays.mkdir()
    write_config("[athc]\nleague = PNFL\n")
    return make_league("PNFL", f"[league]\nplay_path = {plays}\n")


# ── extension / usage validation (exit 2) ─────────────────────────────────────


def test_requires_both_args(runner) -> None:
    assert runner.invoke(convert_pdb, [str(PDB)]).exit_code == 2


@pytest.mark.parametrize(
    "args",
    [
        ["in.txt", "out.xlsx"],  # bad pdb extension
        [str(PDB), "out.csv"],  # bad output extension
    ],
)
def test_bad_extension_exit_2(runner, args: list[str]) -> None:
    result = runner.invoke(convert_pdb, args)
    assert result.exit_code == 2


def test_bad_pln_extension_exit_2(runner, tmp_path: Path) -> None:
    result = runner.invoke(
        convert_pdb, [str(PDB), str(tmp_path / "o.xlsx"), "-o", "plan.txt"]
    )
    assert result.exit_code == 2


@pytest.mark.parametrize(
    "removed",
    [["--play-path", "plays"], ["--playpool-rules", "r.toml"], ["--skip-totals"]],
)
def test_removed_options_are_rejected(
    runner, tmp_path: Path, removed: list[str]
) -> None:
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx"), *removed])
    assert result.exit_code == 2
    assert "No such option" in result.output


# ── runtime errors (exit 1) ───────────────────────────────────────────────────


def test_missing_pdb_exit_1(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            convert_pdb, [str(tmp_path / "nope.pdb"), str(tmp_path / "o.xlsx")]
        )
    assert result.exit_code == 1
    assert "file not found" in caplog.text


def test_play_path_not_a_directory_exit_1(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    not_a_dir = tmp_path / "notdir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    write_config("[athc]\nleague = PNFL\n")
    make_league("PNFL", f"[league]\nplay_path = {not_a_dir}\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 1
    assert "play path is not a directory" in caplog.text


@pytest.mark.usefixtures("league")
def test_invalid_pdb_content_exit_1(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "bad.pdb"
    bad.write_bytes(bytes([9]) + b"\x00" * ctypes.sizeof(PLAY_DATA))
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(convert_pdb, [str(bad), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 1


# ── end-to-end (exit 0) ───────────────────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_produces_xlsx_with_sheets(runner, tmp_path: Path) -> None:
    out = tmp_path / "out.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    assert out.is_file()
    wb = openpyxl.load_workbook(out)
    assert {"Options", "Run Plays", "Pass Plays", "Def Plays", "Tendencies"} <= set(
        wb.sheetnames
    )
    # Tendencies come straight from the PDB (no pool needed): 23 teams x 16 rows + header.
    assert len(list(wb["Tendencies"].iter_rows(values_only=True))) == 1 + 23 * 16


@pytest.mark.usefixtures("league")
def test_produces_xlsm(runner, tmp_path: Path) -> None:
    out = tmp_path / "out.xlsm"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


@pytest.mark.usefixtures("league")
def test_skip_calcs(runner, tmp_path: Path) -> None:
    out = tmp_path / "out.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out), "--skip-calcs"])
    assert result.exit_code == 0 and out.is_file()


# ── packaging check (real subprocess) ─────────────────────────────────────────


def test_entry_point_subprocess(
    make_league: MakeLeague, config_dir: Path, tmp_path: Path
) -> None:
    make_league("PNFL", f"[league]\nplay_path = {tmp_path}\n")
    env = {**os.environ, "ATHC_CONFIG_DIR": str(config_dir)}
    out = tmp_path / "out.xlsx"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "athc",
            "convert-pdb",
            str(PDB),
            str(out),
            "--league",
            "PNFL",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0 and out.is_file()


# ── league folder / --league ──────────────────────────────────────────────────


def test_config_play_path_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = plays\n")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    cfg = pdbtoexcel_config.load_config("PNFL")
    assert cfg.play_path == str(folder / "plays")
    assert cfg.playpool_rules == folder / "rules" / "playpool.toml"


def test_config_both_overrides_need_no_league() -> None:
    cfg = pdbtoexcel_config.load_config(
        play_path="D:/plays", playpool_rules=Path("E:/r.toml")
    )
    assert cfg.play_path == "D:/plays"
    assert cfg.playpool_rules == Path("E:/r.toml")


def test_config_missing_play_path_is_empty(make_league: MakeLeague) -> None:
    make_league("PNFL")
    assert pdbtoexcel_config.load_config("PNFL").play_path == ""


def test_cli_no_league_is_one_line_error(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pdb = tmp_path / "x.pdb"
    pdb.write_bytes(b"")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(convert_pdb, [str(pdb), str(tmp_path / "out.xlsx")])
    assert result.exit_code == 1
    assert "no league selected" in caplog.text
