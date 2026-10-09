"""Integration tests for `athc convert-pdb`.

To regenerate the golden workbook after an intentional change, run this module
as a script: `python -m tests.integration.test_convert_pdb --bless`.
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest
from click.testing import CliRunner

from athc.cli.convert_pdb import convert_pdb
from athc.errors import ConfigFileError
from athc.pdbtoexcel import config as pdbtoexcel_config
from athc.pdbtoexcel.main import convert_pdb as run_conversion
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.conftest import (
    LEAGUE,
    league_toml,
    make_league_dir,
    no_league_selected,
    os_error,
    write_config_file,
    write_pdbtoexcel_toml,
)
from tests.integration.conftest import (
    DATA,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    PLAYS,
    POOL_RULES,
)

PDB = DATA / "2045-2047.pdb"
GOLDEN = EXPECTED / "2045-2047.workbook.json"
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(
    make_league: MakeLeague, write_config: Callable[..., Path], tmp_path: Path
) -> Path:
    """The selected league, with the PNFL labels and order and no playpool
    rules; its play_path is an empty folder."""
    plays = tmp_path / "plays"
    plays.mkdir()
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = make_league(LEAGUE, league_toml(plays))
    write_pdbtoexcel_toml(folder)
    return folder


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
    [["--play-path", "plays"], ["--playpool-rules", "r.toml"]],
)
def test_removed_options_are_rejected(
    runner, tmp_path: Path, removed: list[str]
) -> None:
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx"), *removed])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── runtime errors (exit 1) ───────────────────────────────────────────────────


def test_missing_pdb_exit_2(runner, tmp_path: Path) -> None:
    result = runner.invoke(
        convert_pdb, [str(tmp_path / "nope.pdb"), str(tmp_path / "o.xlsx")]
    )
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.pdb'}: not found\n"


def test_play_path_not_a_directory_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    not_a_dir = tmp_path / "notdir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    write_pdbtoexcel_toml(make_league(LEAGUE, league_toml(not_a_dir)))
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {not_a_dir}: play path is not a directory "
        "(set play_path in the league's league.toml)\n"
    )


@pytest.mark.usefixtures("league")
def test_missing_output_folder_created(runner, tmp_path: Path) -> None:
    out = tmp_path / "reports" / "w1.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


@pytest.mark.usefixtures("league")
def test_missing_output_folders_created_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "reports" / "2049" / "w1.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


@pytest.mark.usefixtures("league")
def test_output_folder_is_a_file_exit_2(runner, tmp_path: Path) -> None:
    (tmp_path / "reports").write_text("x", encoding="utf-8")
    out = tmp_path / "reports" / "w1.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 2
    blocked = os_error(lambda: out.parent.mkdir(parents=True, exist_ok=True))
    assert result.stderr == f"FAIL {blocked}\n"
    assert not out.exists()


def test_missing_pdbtoexcel_toml_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = make_league(LEAGUE, league_toml(tmp_path))
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'pdbtoexcel.toml'}: not found "
        "(convert-pdb needs the league's pdbtoexcel.toml)\n"
    )


@pytest.mark.usefixtures("league")
def test_invalid_pdb_content_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdb"
    bad.write_bytes(bytes([9]) + b"\x00" * ctypes.sizeof(PLAY_DATA))
    result = runner.invoke(convert_pdb, [str(bad), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1] == (
        f"FAIL {bad}: invalid data type {bytes([9])!r} at 0x0"
    )


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
    make_league: MakeLeague, config_dir: Path, log_dir: Path, tmp_path: Path
) -> None:
    write_pdbtoexcel_toml(make_league(LEAGUE, league_toml(tmp_path)))
    env = {
        **os.environ,
        "ATHC_CONFIG_DIR": str(config_dir),
        "ATHC_LOG_DIR": str(log_dir),
    }
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
            LEAGUE,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0 and out.is_file()
    assert result.stdout == f"OK   {out}: 0 play(s)\n"
    lines = result.stderr.splitlines()
    assert lines[0] == f"Creating '{out}'"
    assert lines[1:] and all(line.startswith("WARN ") for line in lines[1:])


# ── league folder / --league ──────────────────────────────────────────────────


def test_config_play_path_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, league_toml("plays"))
    write_pdbtoexcel_toml(folder)
    (folder / "playpool.toml").write_text("", encoding="utf-8")
    cfg = pdbtoexcel_config.load_config(LEAGUE)
    assert cfg.play_path == str(folder / "plays")
    assert cfg.playpool_rules == folder / "playpool.toml"


def test_config_missing_play_path_is_an_error(make_league: MakeLeague) -> None:
    folder = write_pdbtoexcel_toml(make_league(LEAGUE, league_toml())).parent
    with pytest.raises(ConfigFileError) as exc:
        pdbtoexcel_config.load_config(LEAGUE)
    assert str(exc.value) == (
        f"no play_path for the league; set play_path in {folder / 'league.toml'}"
    )


def test_cli_no_league_is_one_line_error(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    pdb = tmp_path / "x.pdb"
    pdb.write_bytes(b"")
    result = runner.invoke(convert_pdb, [str(pdb), str(tmp_path / "out.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir) and result.stdout == ""


def test_no_play_path_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """A league without a play pool converts nothing: an error, not an empty
    workbook."""
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = make_league(LEAGUE, league_toml())
    write_pdbtoexcel_toml(folder)
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL no play_path for the league; set play_path in {folder / 'league.toml'}\n"
    )
    assert result.stdout == "" and not (tmp_path / "o.xlsx").exists()


# ── golden workbook ───────────────────────────────────────────────────────────
# The real .pdb converted against the curated pool (with its playpool rules) and
# both game plans, category worksheets on; every cell compared to the golden JSON.


def _golden_league(config_dir: Path) -> None:
    """Select a league under `config_dir` whose pool is `data/plays/` with its
    playpool rules, the PNFL labels and order, and turn the category worksheets
    on."""
    folder = make_league_dir(config_dir, LEAGUE, league_toml(PLAYS))
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    write_pdbtoexcel_toml(folder)
    write_config_file(
        config_dir,
        f"[athc]\nleague = {LEAGUE}\n[convert-pdb]\ninclude_category_worksheets = true\n",
    )


def _convert_golden(runner: CliRunner, out: Path) -> None:
    result = runner.invoke(
        convert_pdb,
        [str(PDB), str(out), "-o", str(GP_OFFENSE), "-d", str(GP_DEFENSE)],
    )
    assert result.exit_code == 0, result.stderr or repr(result.exception)


def _workbook_cells(path: Path) -> dict[str, list[list[object]]]:
    """Every sheet's cell values; floats rounded so the JSON round-trips exactly."""
    wb = openpyxl.load_workbook(path)
    return {
        ws.title: [
            [round(v, 6) if isinstance(v, float) else v for v in row]
            for row in ws.iter_rows(values_only=True)
        ]
        for ws in wb.worksheets
    }


def _golden_text(cells: dict[str, list[list[object]]]) -> str:
    """The golden JSON, one row per line so a diff shows the changed rows."""
    sheets = ",\n".join(
        f"{json.dumps(name)}: [\n" + ",\n".join(json.dumps(r) for r in rows) + "\n]"
        for name, rows in cells.items()
    )
    return "{\n" + sheets + "\n}\n"


def test_workbook_matches_golden(runner, config_dir: Path, tmp_path: Path) -> None:
    _golden_league(config_dir)
    out = tmp_path / "out.xlsx"
    _convert_golden(runner, out)
    assert _workbook_cells(out) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def _bless() -> None:
    """Regenerate the golden workbook JSON from a fresh conversion."""
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        config_dir = Path(raw) / "config"
        config_dir.mkdir()
        os.environ["ATHC_CONFIG_DIR"] = str(config_dir)
        _golden_league(config_dir)
        out = Path(raw) / "out.xlsx"
        _convert_golden(CliRunner(), out)
        text = _golden_text(_workbook_cells(out))
    GOLDEN.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    print(f"wrote {GOLDEN}")


if __name__ == "__main__":
    if "--bless" in sys.argv:
        _bless()
    else:
        print("Pass --bless to regenerate the golden file.")


# ── progress, warnings and the OK line ────────────────────────────────────────


def _golden_play_rows() -> int:
    """Play rows in the golden workbook: one per (team, play) stat line, the
    Total Stats rows aside."""
    sheets = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return sum(
        1
        for name in ("Run Plays", "Pass Plays", "Def Plays")
        for row in sheets[name][1:]
        if row[0] != "Total Stats"
    )


def test_progress_on_stderr_warnings_and_ok_line(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    _golden_league(config_dir)
    out = tmp_path / "w.xlsx"
    result = runner.invoke(
        convert_pdb, [str(PDB), str(out), "-o", str(GP_OFFENSE), "-d", str(GP_DEFENSE)]
    )
    assert result.exit_code == 0
    lines = result.stderr.splitlines()
    assert lines[0] == f"Creating '{out}'"
    assert lines[1:] and all(line.startswith("WARN ") for line in lines[1:])
    assert result.stdout == f"OK   {out}: {_golden_play_rows()} play(s)\n"


@pytest.mark.usefixtures("league")
def test_empty_pool_warns_per_play_and_writes_no_play_rows(
    runner, tmp_path: Path
) -> None:
    out = tmp_path / "w.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    warnings = result.stderr.splitlines()[1:]
    assert warnings and all(
        line.startswith("WARN Play file not found for play '") for line in warnings
    )
    assert result.stdout == f"OK   {out}: 0 play(s)\n"


def test_play_path_not_a_directory_is_a_config_error(
    make_league: MakeLeague, write_config: Callable[..., Path], tmp_path: Path
) -> None:
    not_a_dir = tmp_path / "notdir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    write_pdbtoexcel_toml(make_league(LEAGUE, league_toml(not_a_dir)))
    with pytest.raises(ConfigFileError) as exc:
        run_conversion(pdb_path=str(PDB), output_path=str(tmp_path / "o.xlsx"))
    assert str(exc.value).startswith(f"{not_a_dir}: play path is not a directory")


@pytest.mark.usefixtures("league")
def test_unwritable_workbook_is_a_fail_line_not_a_bug(runner, tmp_path: Path) -> None:
    """A workbook that cannot be written (here the path is a folder; for a user,
    usually the old workbook still open in Excel) is a one-line failure."""
    out = tmp_path / "w.xlsx"
    out.mkdir()
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1].startswith(f"FAIL {out}: ")
    assert "unexpected error" not in result.stderr
