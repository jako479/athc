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
from collections.abc import Callable, Sequence
from pathlib import Path

import openpyxl
import pytest
from click.testing import CliRunner, Result
from openpyxl.worksheet.worksheet import Worksheet

from athc.cli import cli
from athc.cli.convert_pdb import convert_pdb
from athc.config import play_dir
from athc.errors import (
    ACCESS_DENIED,
    ALREADY_EXISTS,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    ConfigFileError,
)
from athc.pdbtoexcel import config as pdbtoexcel_config
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.conftest import (
    CONVERT_PDB_TOML,
    LEAGUE,
    athc_toml,
    league_toml,
    make_league_dir,
    no_league_selected,
    write_config_file,
)
from tests.integration.conftest import (
    DATA,
    DENVER_PLANS,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    PLAYS,
    TEAM_NAMES,
    BuildLeague,
    team,
)
from tests.integration.conftest import DENVER_2049 as DENVER

PDB = DATA / "2045-2047.pdb"
GOLDEN = EXPECTED / "2045-2047.workbook.json"
MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

TEAM_NOT_SET = "Team is not set. Run 'athc config set team NAME' or pass --team."
PATH_NOT_SET = (
    "League files folder is not set. Run 'athc config set path FOLDER' or pass a "
    "game plan with -o, -o2, -d or -d2."
)
HINT = "Run 'athc config set ppp_path FOLDER' or pass --path."


@pytest.fixture
def league(
    make_league: MakeLeague, write_config: Callable[..., Path], tmp_path: Path
) -> Path:
    """The selected league, with the PNFL labels and order; its play_path is an
    empty folder."""
    plays = tmp_path / "plays"
    plays.mkdir()
    write_config(athc_toml() + CONVERT_PDB_TOML)
    return make_league(LEAGUE, league_toml(plays))


def run(runner: CliRunner, *args: Path | str) -> Result:
    return runner.invoke(convert_pdb, [str(arg) for arg in args])


# ── help ──────────────────────────────────────────────────────────────────────

HELP = """\
Usage: athc convert-pdb [OPTIONS] PDB_FILE [OUTPUT]

  Convert a WinLogStats PDB to an Excel workbook.

  Slot columns come from your team's game plans, or from -o, -o2, -d and -d2.

Positional arguments:
  PDB_FILE  WinLogStats .pdb file.
  OUTPUT    .xlsx, or .xlsm to include sorting macros, or a folder (default:
            PDB_FILE with .xlsm, beside it).

Options:
  -o, --pln-off GAME_PLAN         Offense Slot 1.
  -o2, --pln-off-2 GAME_PLAN      Offense Slot 2.
  -d, --pln-def GAME_PLAN         Defense Slot 1.
  -d2, --pln-def-2 GAME_PLAN      Defense Slot 2.
  --path FOLDER                   Folder holding your team's game plans, by
                                  their league-file names (default: ppp_path,
                                  else where the game reads them).
  --team NAME                     Team whose game plans fill the Slot columns
                                  (default: team in league.toml).
  --percentages / --no-percentages
                                  Overrides calculate_percentages in athc.toml
                                  (on by default).
  --league NAME                   League to use (default: the one set with
                                  athc config set league).
  -h, --help                      Show this message and exit.

  Examples:

    athc convert-pdb 49W6.pdb
    athc convert-pdb 49W6.pdb reports\\week6.xlsx -o try3.pln
"""


def test_help_screen(runner) -> None:
    # 78 columns: Click's help in an 80-column console.
    result = runner.invoke(
        cli, ["convert-pdb", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == HELP


# ── extension / usage validation (exit 2) ─────────────────────────────────────


def test_no_arguments_is_missing_pdb_file(runner) -> None:
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'PDB_FILE'.\n")


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


def test_bad_extension_is_a_sentence(runner) -> None:
    result = runner.invoke(convert_pdb, ["in.txt", "out.xlsx"])
    assert result.stderr.endswith(
        "Error: Invalid value for 'PDB_FILE': must have a .pdb extension.\n"
    )


@pytest.mark.parametrize("output", ["-", "week6.pdb"])
def test_output_must_be_a_workbook(runner, tmp_path: Path, output: str) -> None:
    """`-` (the console) and a second PDB are each the extension error, with
    nothing more."""
    target = output if output == "-" else str(tmp_path / output)
    result = runner.invoke(convert_pdb, [str(PDB), target])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "\nError: Invalid value for 'OUTPUT': must have a .xlsx or .xlsm extension.\n"
    )


def test_bad_pln_extension_exit_2(runner, tmp_path: Path) -> None:
    result = runner.invoke(
        convert_pdb, [str(PDB), str(tmp_path / "o.xlsx"), "-o", "plan.txt"]
    )
    assert result.exit_code == 2


@pytest.mark.parametrize(
    ("option", "hint"),
    [("-o2", "'-o2' / '--pln-off-2'"), ("-d2", "'-d2' / '--pln-def-2'")],
)
def test_second_plan_option_takes_a_pln_only(
    runner, tmp_path: Path, option: str, hint: str
) -> None:
    result = run(runner, PDB, tmp_path / "o.xlsx", option, "plan.txt")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        f"Error: Invalid value for {hint}: must have a .pln extension.\n"
    )


def test_plan_option_takes_no_game_plan_key(runner, tmp_path: Path) -> None:
    result = run(runner, PDB, tmp_path / "o.xlsx", "-o", "off1")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for '-o' / '--pln-off': must have a .pln extension.\n"
    )


@pytest.mark.parametrize(
    "removed",
    [["--play-path", "plays"], ["--playpool-rules", "r.toml"], ["--skip-calcs"]],
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
    assert result.stderr == f"FAIL {tmp_path / 'nope.pdb'}: {FILE_NOT_FOUND}\n"


def test_wildcard_that_matches_nothing_is_a_missing_file(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """athc does not expand the PDB: `for %f in (*.pdb)` does, and with no
    match hands the pattern on as it is."""
    monkeypatch.chdir(tmp_path)
    result = run(runner, "*.pdb")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL *.pdb: {FILE_NOT_FOUND}\n"


def test_play_path_not_a_directory_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    not_a_dir = tmp_path / "notdir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    write_config(athc_toml() + CONVERT_PDB_TOML)
    make_league(LEAGUE, league_toml(not_a_dir))
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {not_a_dir}: {DIRECTORY_INVALID} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


def test_play_path_missing_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    missing = tmp_path / "gone"
    write_config(athc_toml() + CONVERT_PDB_TOML)
    make_league(LEAGUE, league_toml(missing))
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {missing}: {PATH_NOT_FOUND} Run 'athc config set play_path FOLDER'.\n"
    )


def test_folder_given_for_the_pdb_exit_2(runner, tmp_path: Path) -> None:
    folder = tmp_path / "x.pdb"
    folder.mkdir()
    result = runner.invoke(convert_pdb, [str(folder), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: {ACCESS_DENIED}\n"


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
    assert result.stderr == f"FAIL {out.parent}: {ALREADY_EXISTS}\n"
    assert not out.exists()


def test_no_category_order_exports_nothing(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """No category_order in athc.toml or league.toml: every list is empty, so
    the pool the golden workbook fills gives no play rows."""
    write_config(athc_toml())
    make_league(LEAGUE, league_toml(PLAYS))
    out = tmp_path / "o.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {out}: 0 play(s)\n"
    workbook = openpyxl.load_workbook(out)
    for name in ("Run Plays", "Pass Plays", "Def Plays"):
        rows = workbook[name].iter_rows(min_row=2, values_only=True)
        assert [row for row in rows if any(v is not None for v in row)] == [], name


def test_league_override_changes_the_order(
    runner,
    make_league: MakeLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """The league's run list replaces athc.toml's: within each team RM rows
    sort before RL, and RR and GLR are left out."""
    write_config(athc_toml() + CONVERT_PDB_TOML)
    body = '[convert-pdb.category_order]\nrun = ["RM", "RL"]\n'
    make_league(LEAGUE, league_toml(PLAYS, convert_pdb=body))
    out = tmp_path / "o.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB), str(out)])
    assert result.exit_code == 0, result.stderr
    sheet = openpyxl.load_workbook(out)["Run Plays"]
    header = next(sheet.iter_rows(values_only=True))
    team, category = header.index("Team"), header.index("Category")
    by_team: dict[object, list[str]] = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[category] is not None:
            by_team.setdefault(row[team], []).append(str(row[category]))
    assert {c for cats in by_team.values() for c in cats} == {"RM", "RL"}
    for cats in by_team.values():
        assert cats == sorted(cats, key=["RM", "RL"].index)


@pytest.mark.usefixtures("league")
def test_invalid_pdb_content_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdb"
    bad.write_bytes(bytes([9]) + b"\x00" * ctypes.sizeof(PLAY_DATA))
    result = runner.invoke(convert_pdb, [str(bad), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1] == (
        f"FAIL {bad}: Invalid data type 0x09 at 0x0."
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


# ── the output: OUTPUT, else <PDB name>.xlsm beside the PDB ───────────────────


def copy_pdb(folder: Path, name: str = "49W6.pdb") -> Path:
    """The fixture PDB copied into `folder` (created), so the default output
    lands there and never in the test data."""
    folder.mkdir(parents=True, exist_ok=True)
    return Path(shutil.copy2(PDB, folder / name))


@pytest.mark.usefixtures("league")
def test_default_output_is_beside_the_pdb(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path / "GameLogs")
    out = tmp_path / "GameLogs" / "49W6.xlsm"
    result = run(runner, pdb)
    assert result.exit_code == 0
    assert out.is_file()
    assert result.stderr.splitlines()[0] == f"Creating {out}"
    assert result.stdout == f"OK   {out}: 0 play(s)\n"


@pytest.mark.usefixtures("league")
def test_default_output_replaces_an_existing_one(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path)
    out = tmp_path / "49W6.xlsm"
    out.write_text("old", encoding="utf-8")
    result = run(runner, pdb)
    assert result.exit_code == 0
    assert "Tendencies" in openpyxl.load_workbook(out).sheetnames


@pytest.mark.usefixtures("league")
def test_bare_pdb_name_writes_into_the_current_folder(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy_pdb(tmp_path / "GameLogs")
    monkeypatch.chdir(tmp_path / "GameLogs")
    result = run(runner, "49W6.pdb")
    assert result.exit_code == 0
    assert (tmp_path / "GameLogs" / "49W6.xlsm").is_file()
    assert result.stdout == "OK   49W6.xlsm: 0 play(s)\n"


@pytest.mark.usefixtures("league")
def test_output_file_given_wins(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path)
    out = tmp_path / "reports" / "week6.xlsx"
    result = run(runner, pdb, out)
    assert result.exit_code == 0
    assert out.is_file()
    assert not (tmp_path / "49W6.xlsm").exists()


@pytest.mark.usefixtures("league")
def test_output_folder_gets_the_default_name(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    result = run(runner, pdb, reports)
    assert result.exit_code == 0
    assert (reports / "49W6.xlsm").is_file()
    assert result.stdout == f"OK   {reports / '49W6.xlsm'}: 0 play(s)\n"


@pytest.mark.usefixtures("league")
def test_output_ending_in_a_backslash_is_a_new_folder(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path)
    reports = tmp_path / "reports"
    result = run(runner, pdb, f"{reports}\\")
    assert result.exit_code == 0
    assert (reports / "49W6.xlsm").is_file()


@pytest.mark.usefixtures("league")
def test_output_without_an_extension_gets_xlsm(runner, tmp_path: Path) -> None:
    pdb = copy_pdb(tmp_path)
    result = run(runner, pdb, tmp_path / "week6")
    assert result.exit_code == 0
    assert (tmp_path / "week6.xlsm").is_file()
    assert not (tmp_path / "week6").exists()


# ── --percentages / --no-percentages over calculate_percentages ───────────────


@pytest.mark.parametrize(
    ("setting", "flag", "shown"),
    [
        ("true", None, True),
        ("true", "--percentages", True),
        ("true", "--no-percentages", False),
        ("false", None, False),
        ("false", "--percentages", True),
        ("false", "--no-percentages", False),
    ],
)
@pytest.mark.usefixtures("league")
def test_percentages_override_the_setting(
    runner,
    write_config: WriteConfig,
    tmp_path: Path,
    setting: str,
    flag: str | None,
    shown: bool,
) -> None:
    """The setting alone decides, and either flag overrides it both ways."""
    write_config(
        athc_toml()
        + CONVERT_PDB_TOML
        + f"[convert-pdb]\ncalculate_percentages = {setting}\n"
    )
    out = tmp_path / "out.xlsx"
    result = run(runner, PDB, out, *([flag] if flag else []))
    assert result.exit_code == 0
    header = next(openpyxl.load_workbook(out)["Run Plays"].iter_rows(values_only=True))
    assert ("Fumble %" in header) is shown


# ── packaging check (real subprocess) ─────────────────────────────────────────


def test_entry_point_subprocess(
    make_league: MakeLeague,
    write_config: WriteConfig,
    config_dir: Path,
    log_dir: Path,
    tmp_path: Path,
) -> None:
    make_league(LEAGUE, league_toml(tmp_path))
    write_config(CONVERT_PDB_TOML)
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
    assert lines[0] == f"Creating {out}"
    assert lines[1:] and all(line.startswith("WARN ") for line in lines[1:])


# ── league folder / --league ──────────────────────────────────────────────────


def test_config_play_path_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, league_toml("plays"))
    cfg = pdbtoexcel_config.load_config(LEAGUE)
    assert cfg.play_path == str(folder / "plays")


def test_config_missing_play_path_is_an_error(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, league_toml())
    with pytest.raises(ConfigFileError) as exc:
        pdbtoexcel_config.load_config(LEAGUE)
    assert str(exc.value) == (
        f"{folder / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER'."
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
    write_config(athc_toml() + CONVERT_PDB_TOML)
    folder = make_league(LEAGUE, league_toml())
    result = runner.invoke(convert_pdb, [str(PDB), str(tmp_path / "o.xlsx")])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER'.\n"
    )
    assert result.stdout == "" and not (tmp_path / "o.xlsx").exists()


# ── golden workbook ───────────────────────────────────────────────────────────
# The real .pdb converted against the curated pool and both game plans, category
# worksheets on; every cell compared to the golden JSON.


def _golden_league(config_dir: Path) -> None:
    """Select a league under `config_dir` whose pool is `data/plays/`, with the
    PNFL labels and order, and turn the category worksheets on."""
    make_league_dir(config_dir, LEAGUE, league_toml(PLAYS))
    write_config_file(
        config_dir,
        athc_toml()
        + CONVERT_PDB_TOML
        + "[convert-pdb]\ninclude_category_worksheets = true\n",
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
    assert lines[0] == f"Creating {out}"
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
        line.startswith("WARN Play '") and line.endswith(" is not in the play pool.")
        for line in warnings
    )
    assert result.stdout == f"OK   {out}: 0 play(s)\n"


def test_play_path_not_a_directory_is_a_config_error(
    make_league: MakeLeague, write_config: Callable[..., Path], tmp_path: Path
) -> None:
    """The command loads the config and checks the pool's folder itself."""
    not_a_dir = tmp_path / "notdir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    write_config(athc_toml() + CONVERT_PDB_TOML)
    make_league(LEAGUE, league_toml(not_a_dir))
    config = pdbtoexcel_config.load_config(LEAGUE)
    with pytest.raises(ConfigFileError) as exc:
        play_dir(config.play_path)
    assert str(exc.value).startswith(f"{not_a_dir}: {DIRECTORY_INVALID} ")


@pytest.mark.usefixtures("league")
def test_unwritable_workbook_is_a_fail_line_not_a_bug(runner, tmp_path: Path) -> None:
    """A workbook that cannot be written (here a folder holds its name; for a
    user, usually the old workbook still open in Excel) is a one-line failure."""
    pdb = copy_pdb(tmp_path)
    blocked = tmp_path / "49W6.xlsm"
    blocked.mkdir()
    result = run(runner, pdb)
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1].startswith(f"FAIL {blocked}: ")
    assert "unexpected error" not in result.stderr


# ── the Slot columns: helpers ─────────────────────────────────────────────────

# The progress line each of Denver's four game plans (DENVER_PLANS, in
# conftest.py) gives.
DENVER_SLOTS = (
    "Denver 1st-half offense, Slot 1",
    "Denver 1st-half defense, Slot 1",
    "Denver 2nd-half offense, Slot 2",
    "Denver 2nd-half defense, Slot 2",
)
NO_DENVER_PLANS = (
    "No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, "
    "DEN-OGP2.pln, DEN-DGP2.pln."
)
SHEETS = ("Run Plays", "Pass Plays", "Def Plays")


def denver() -> bytes:
    """Denver's .lg2 record: its four game plans by their PNFL names, in
    team()'s folder."""
    return team(
        off1=("DEN-OFF1.prf", DENVER_PLANS[0]),
        def1=("DEN-DEF1.prf", DENVER_PLANS[1]),
        off2=("DEN-OFF2.prf", DENVER_PLANS[2]),
        def2=("DEN-DEF2.prf", DENVER_PLANS[3]),
    )


def put_plans(folder: Path, names: Sequence[str] = DENVER_PLANS) -> Path:
    """offense.pln, or defense.pln for a `DGP` name, copied into `folder`
    (created) under each of `names`."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = GP_DEFENSE if "DGP" in name.upper() else GP_OFFENSE
        shutil.copy2(source, folder / name)
    return folder


@pytest.fixture
def denver_league(lg2_league, config_dir: Path, tmp_path: Path) -> Callable[..., Path]:
    """A built league whose one team is Denver (`team = 'Denver'` unless
    `team` is given), with offense.pln and defense.pln as its four game plans
    at their league location. Keyword arguments go to `lg2_league`. Returns
    that league location."""

    def _build(*, plans: bool = True, **settings: object) -> Path:
        settings.setdefault("team", "Denver")
        lg2_league(denver(), **settings)
        write_config_file(config_dir, athc_toml() + CONVERT_PDB_TOML)
        folder = tmp_path / "lg2" / "PNFL" / "2049" / "Plans" / "Team"
        return put_plans(folder) if plans else folder

    return _build


@pytest.fixture
def real_league(pnfl_league: Path, write_config: WriteConfig) -> Path:
    """`pnfl_league` (the real 2049 league file and plans) able to convert."""
    write_config(athc_toml() + CONVERT_PDB_TOML)
    return pnfl_league


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def at_league(tmp_path: Path, team_folder: str) -> Path:
    """A team's league location in `pnfl_league`: where PNFL.lg2 puts its files."""
    return tmp_path / "lg2" / "PNFL" / "2049" / "Plans" / team_folder


def plan_lines(result: Result) -> list[str]:
    """The stderr lines before `Creating <file>`: the game plans' lines."""
    lines = result.stderr.splitlines()
    end = next(i for i, line in enumerate(lines) if line.startswith("Creating "))
    return lines[:end]


def progress(folder: Path, names: tuple[str, ...] = DENVER_PLANS) -> list[str]:
    """The progress line of each of Denver's game plans found in `folder`."""
    return [
        f"{folder / name}: {slot}"
        for name, slot in zip(names, DENVER_SLOTS, strict=True)
    ]


def _hidden(ws: Worksheet, column: int) -> bool:
    # openpyxl keys a column range by its first letter; check every range.
    return any(
        dim.hidden
        and dim.min is not None
        and dim.max is not None
        and dim.min <= column <= dim.max
        for dim in ws.column_dimensions.values()
    )


def shown(out: Path) -> dict[str, tuple[bool, bool]]:
    """Per play sheet, whether Slot 1 and Slot 2 (columns C and D) show."""
    wb = openpyxl.load_workbook(out)
    return {
        name: (not _hidden(wb[name], 3), not _hidden(wb[name], 4)) for name in SHEETS
    }


def slots(offense: tuple[bool, bool], defense: tuple[bool, bool]) -> dict:
    """`shown()`'s answer for these offense and defense Slot columns."""
    return {"Run Plays": offense, "Pass Plays": offense, "Def Plays": defense}


def filled(out: Path, sheet: str, column: int) -> bool:
    """Whether any play row has a slot in the 1-based `column`."""
    ws = openpyxl.load_workbook(out)[sheet]
    return any(row[column - 1] for row in ws.iter_rows(min_row=2, values_only=True))


# ── the game plan options: only the files given ───────────────────────────────


def test_plan_option_fills_its_slot_alone(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    """With `team` set and the team's plans in place, `-o` still uses only the
    file given: offense Slot 1, the other columns hidden, no plan line."""
    denver_league()
    try3 = Path(shutil.copy2(GP_OFFENSE, tmp_path / "try3.pln"))
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, "-o", try3)
    assert result.exit_code == 0
    assert plan_lines(result) == []
    assert shown(out) == slots((True, False), (False, False))
    assert filled(out, "Run Plays", 3)


def test_plan_option_reads_no_league_file(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """`team` set and no `path`: a run with a game plan option still converts."""
    build_league(team="Denver")
    write_config(athc_toml() + CONVERT_PDB_TOML)
    result = run(runner, PDB, tmp_path / "w.xlsx", "-d", GP_DEFENSE)
    assert result.exit_code == 0


def test_second_half_option_alone_shows_slot_2(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league(team=None)
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, "-o2", GP_OFFENSE, "-d2", GP_DEFENSE)
    assert result.exit_code == 0
    assert shown(out) == slots((False, True), (False, True))
    assert filled(out, "Run Plays", 4) and filled(out, "Def Plays", 4)
    assert not filled(out, "Run Plays", 3)


@pytest.mark.parametrize(
    ("option", "plan", "line"),
    [
        ("-o", GP_DEFENSE, "Not an offense game plan."),
        ("-o2", GP_DEFENSE, "Not an offense game plan."),
        ("-d", GP_OFFENSE, "Not a defense game plan."),
        ("-d2", GP_OFFENSE, "Not a defense game plan."),
    ],
)
@pytest.mark.usefixtures("league")
def test_plan_option_on_the_wrong_side_fails(
    runner, tmp_path: Path, option: str, plan: Path, line: str
) -> None:
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, option, plan)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {plan}: {line}\n"
    assert result.stdout == "" and not out.exists()


@pytest.mark.parametrize("plan_option", [None, "-o"], ids=["alone", "with -o"])
@pytest.mark.parametrize("flag", ["--team", "--path"])
def test_team_and_path_never_mix_with_a_plan_option(
    runner,
    denver_league: Callable[..., Path],
    tmp_path: Path,
    flag: str,
    plan_option: str | None,
) -> None:
    """Without a game plan option each flag is accepted; with one, it is a
    usage error."""
    location = denver_league()
    value = "Denver" if flag == "--team" else str(location)
    args = [flag, value, *([plan_option, str(GP_OFFENSE)] if plan_option else [])]
    result = run(runner, PDB, tmp_path / "w.xlsx", *args)
    if plan_option is None:
        assert result.exit_code == 0
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(
            f"Error: {flag} cannot be used with -o, -o2, -d or -d2.\n"
        )


def test_team_is_checked_before_path(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league()
    args = ["--path", location, "--team", "Denver", "-d2", GP_DEFENSE]
    result = run(runner, PDB, tmp_path / "w.xlsx", *args)
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team cannot be used with -o, -o2, -d or -d2.\n"
    )


# ── your team's game plans at their league locations ──────────────────────────


def test_team_plans_fill_every_slot(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league()
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result) == progress(location)
    assert shown(out) == slots((True, True), (True, True))
    assert all(filled(out, sheet, column) for sheet in SHEETS for column in (3, 4))


def test_output_on_a_file_fails_before_the_game_plans_are_read(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league()
    notes = tmp_path / "notes.xlsx"
    notes.write_text("x", encoding="utf-8")
    result = run(runner, PDB, f"{notes}\\")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {notes}: {DIRECTORY_INVALID}\n"


def test_team_plans_from_the_real_league(
    runner, real_league: Path, tmp_path: Path
) -> None:
    set_league(real_league, team="Denver")
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 0
    assert plan_lines(result) == progress(at_league(tmp_path, "Denver (Brian)"))


def test_shared_plan_fills_slot_1_alone(
    runner, real_league: Path, tmp_path: Path
) -> None:
    """Las Vegas uses one game plan per side for both halves."""
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, "--team", "Las Vegas")
    assert result.exit_code == 0
    assert plan_lines(result) == [
        f"{folder / 'RAIDEROFF.pln'}: Las Vegas offense, both halves, Slot 1",
        f"{folder / 'RAIDERDEF.pln'}: Las Vegas defense, both halves, Slot 1",
    ]
    assert shown(out) == slots((True, False), (True, False))


def test_missing_plan_warns_with_the_hint(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league()
    (location / "DEN-OGP2.pln").unlink()
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    lines = progress(location)
    lines[2] = (
        f"WARN {location / 'DEN-OGP2.pln'}: {FILE_NOT_FOUND} Offense Slot 2 is "
        f"hidden. {HINT}"
    )
    assert plan_lines(result) == lines
    assert shown(out) == slots((True, False), (True, True))


def test_missing_first_half_plan_keeps_slot_2(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    """Slot 2 is the 2nd-half plan, whichever plan is there."""
    location = denver_league()
    (location / "DEN-OGP1.pln").unlink()
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert shown(out) == slots((False, True), (True, True))
    assert filled(out, "Run Plays", 4) and not filled(out, "Run Plays", 3)


def test_shared_plan_missing_is_one_warning(
    runner, lg2_league, config_dir: Path, tmp_path: Path
) -> None:
    record = team(
        off1=("O1.prf", "SHARED.pln"),
        def1=("D1.prf", "DEN-DGP1.pln"),
        off2=("O2.prf", "SHARED.pln"),
        def2=("D2.prf", "DEN-DGP2.pln"),
    )
    lg2_league(record, team="Denver")
    write_config_file(config_dir, athc_toml() + CONVERT_PDB_TOML)
    location = put_plans(
        tmp_path / "lg2" / "PNFL" / "2049" / "Plans" / "Team", ["DEN-DGP1.pln"]
    )
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result) == [
        f"WARN {location / 'SHARED.pln'}: {FILE_NOT_FOUND} Offense Slot 1 is "
        f"hidden. {HINT}",
        f"{location / 'DEN-DGP1.pln'}: Denver 1st-half defense, Slot 1",
        f"WARN {location / 'DEN-DGP2.pln'}: {FILE_NOT_FOUND} Defense Slot 2 is "
        f"hidden. {HINT}",
    ]
    assert shown(out) == slots((False, False), (True, False))


def test_team_folder_absent_is_one_warning(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league(plans=False)
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result) == [f"WARN {location}: {PATH_NOT_FOUND} {HINT}"]
    assert shown(out) == slots((False, False), (False, False))


def test_team_folder_with_none_of_the_plans_is_one_warning(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league(plans=False)
    location.mkdir(parents=True)
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result) == [f"WARN {location}: No Denver game plans. {HINT}"]
    assert shown(out) == slots((False, False), (False, False))


def test_plan_on_the_wrong_side_warns(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league()
    shutil.copy2(GP_DEFENSE, location / "DEN-OGP1.pln")
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result)[0] == (
        f"WARN {location / 'DEN-OGP1.pln'}: Not an offense game plan. Offense "
        "Slot 1 is hidden."
    )
    assert shown(out) == slots((False, True), (True, True))


def test_unreadable_plan_warns(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    location = denver_league()
    (location / "DEN-DGP2.pln").write_bytes(b"\x00\x01\x02")
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result)[3] == (
        f"WARN {location / 'DEN-DGP2.pln'}: File too small to contain PLN header "
        "and offsets table. Defense Slot 2 is hidden."
    )
    assert shown(out) == slots((True, True), (True, False))


# ── --path FOLDER ─────────────────────────────────────────────────────────────


def test_path_finds_the_plans_without_case(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league(plans=False)
    lower = tuple(name.lower() for name in DENVER_PLANS)
    folder = put_plans(tmp_path / "wk5", lower)
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, "--path", folder)
    assert result.exit_code == 0
    assert plan_lines(result) == progress(folder, lower)
    assert shown(out) == slots((True, True), (True, True))


def test_path_missing_plan_warns_without_the_hint(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league()
    folder = put_plans(tmp_path / "wk5", DENVER_PLANS[:3])
    result = run(runner, PDB, tmp_path / "w.xlsx", "--path", folder)
    assert result.exit_code == 0
    assert plan_lines(result)[3] == (
        f"WARN {folder / 'DEN-DGP2.pln'}: {FILE_NOT_FOUND} Defense Slot 2 is hidden."
    )


@pytest.mark.parametrize("found", [0, 1], ids=["no plan", "one plan"])
def test_path_with_none_of_the_plans(
    runner, denver_league: Callable[..., Path], tmp_path: Path, found: int
) -> None:
    """None of the plans in the folder is one line naming them; one plan
    there gives a line per missing plan instead."""
    denver_league()
    folder = put_plans(tmp_path / "wk5", DENVER_PLANS[:found])
    if not found:
        (folder / "other.pln").write_bytes(b"")
    result = run(runner, PDB, tmp_path / "w.xlsx", "--path", folder)
    assert result.exit_code == 0
    lines = plan_lines(result)
    if not found:
        assert lines == [f"WARN {folder}: {NO_DENVER_PLANS}"]
    else:
        assert lines[0] == progress(folder)[0]
        assert [line.split(": ", 1)[0] for line in lines[1:]] == [
            f"WARN {folder / name}" for name in DENVER_PLANS[1:]
        ]
        assert all(HINT not in line for line in lines)


def test_path_searches_no_subfolder(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league()
    folder = tmp_path / "wk5"
    put_plans(folder / "sub")
    result = run(runner, PDB, tmp_path / "w.xlsx", "--path", folder)
    assert result.exit_code == 0
    assert plan_lines(result) == [f"WARN {folder}: {NO_DENVER_PLANS}"]


def test_path_wins_over_ppp_path(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    ppp = put_plans(tmp_path / "ppp")
    denver_league(plans=False, ppp_path=ppp)
    folder = put_plans(tmp_path / "wk5")
    result = run(runner, PDB, tmp_path / "w.xlsx", "--path", folder)
    assert plan_lines(result) == progress(folder)


@pytest.mark.parametrize(
    ("make", "reason"),
    [(None, PATH_NOT_FOUND), ("file", DIRECTORY_INVALID)],
    ids=["missing", "a file"],
)
def test_path_must_be_a_folder(
    runner,
    denver_league: Callable[..., Path],
    tmp_path: Path,
    make: str | None,
    reason: str,
) -> None:
    denver_league()
    folder = tmp_path / "wk5"
    if make == "file":
        folder.write_bytes(b"")
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out, "--path", folder)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: {reason}\n"
    assert not out.exists()


# ── ppp_path ──────────────────────────────────────────────────────────────────


def test_ppp_path_finds_the_plans_without_case(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    upper = tuple(name.upper() for name in DENVER_PLANS)
    ppp = put_plans(tmp_path / "ppp", upper)
    denver_league(plans=False, ppp_path=ppp)
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 0
    assert plan_lines(result) == progress(ppp, upper)


def test_ppp_path_relative_to_the_league_folder(
    runner, denver_league: Callable[..., Path], config_dir: Path, tmp_path: Path
) -> None:
    denver_league(plans=False, ppp_path="plans")
    ppp = put_plans(config_dir / "leagues" / LEAGUE / "plans")
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert plan_lines(result) == progress(ppp)


def test_ppp_path_missing_plan_warns_without_the_hint(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    ppp = put_plans(tmp_path / "ppp", DENVER_PLANS[1:])
    denver_league(ppp_path=ppp)
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 0
    assert plan_lines(result)[0] == (
        f"WARN {ppp / 'DEN-OGP1.pln'}: {FILE_NOT_FOUND} Offense Slot 1 is hidden."
    )


def test_ppp_path_is_for_your_team_only(
    runner, real_league: Path, tmp_path: Path
) -> None:
    """`--team` naming another team uses that team's league locations."""
    set_league(real_league, team="Denver", ppp_path=DENVER)
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    result = run(runner, PDB, tmp_path / "w.xlsx", "--team", "Las Vegas")
    assert [line.split(": ")[0] for line in plan_lines(result)] == [
        str(folder / "RAIDEROFF.pln"),
        str(folder / "RAIDERDEF.pln"),
    ]


def test_ppp_path_for_your_team_named_with_the_option(
    runner, real_league: Path, tmp_path: Path
) -> None:
    set_league(real_league, team="Denver", ppp_path=DENVER)
    result = run(runner, PDB, tmp_path / "w.xlsx", "--team", "Broncos")
    assert plan_lines(result) == progress(DENVER)


@pytest.mark.parametrize(
    ("make", "reason"),
    [(None, PATH_NOT_FOUND), ("file", DIRECTORY_INVALID)],
    ids=["missing", "a file"],
)
def test_ppp_path_must_be_a_folder(
    runner,
    denver_league: Callable[..., Path],
    tmp_path: Path,
    make: str | None,
    reason: str,
) -> None:
    ppp = tmp_path / "ppp"
    if make == "file":
        ppp.write_bytes(b"")
    denver_league(ppp_path=ppp)
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {ppp}: {reason} Run 'athc config set ppp_path FOLDER'.\n"
    )


# ── which team: `team`, --team ────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["Denver", "Broncos", "denver broncos"])
def test_team_by_name_nickname_or_both(
    runner, real_league: Path, tmp_path: Path, name: str
) -> None:
    set_league(real_league, team=name)
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert plan_lines(result) == progress(at_league(tmp_path, "Denver (Brian)"))


def test_team_option_beats_team(runner, real_league: Path, tmp_path: Path) -> None:
    set_league(real_league, team="Las Vegas")
    result = run(runner, PDB, tmp_path / "w.xlsx", "--team", "Denver")
    assert plan_lines(result) == progress(at_league(tmp_path, "Denver (Brian)"))


def test_team_option_without_team(runner, real_league: Path, tmp_path: Path) -> None:
    """`team` unset: `--team` still works; the team is not yours, so a missing
    plan carries no ppp_path hint."""
    location = at_league(tmp_path, "Denver (Brian)")
    (location / "DEN-OGP2.pln").unlink()
    result = run(runner, PDB, tmp_path / "w.xlsx", "--team", "Denver")
    assert result.exit_code == 0
    assert plan_lines(result)[2] == (
        f"WARN {location / 'DEN-OGP2.pln'}: {FILE_NOT_FOUND} Offense Slot 2 is hidden."
    )


def test_team_matches_no_team(
    runner, denver_league: Callable[..., Path], config_dir: Path, tmp_path: Path
) -> None:
    denver_league(team="Denvr")
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {config_dir / 'leagues' / LEAGUE / 'league.toml'}: [league] team: "
        "No team named 'Denvr'. Teams: Denver Broncos.\n"
    )


def test_team_option_matches_two_teams(
    runner, lg2_league, config_dir: Path, tmp_path: Path
) -> None:
    """A --team typo shows before the pool's WARN lines, and nothing else."""
    lg2_league(team(), team(), names=[("New York", "Giants"), ("New York", "Jets")])
    write_config_file(config_dir, athc_toml() + CONVERT_PDB_TOML)
    result = run(runner, PDB, tmp_path / "w.xlsx", "--team", "New York")
    assert result.exit_code == 2
    assert "WARN" not in result.stderr
    assert result.stderr.endswith(
        "Error: Invalid value for '--team': 'New York' matches New York Giants and "
        "New York Jets. Use the nickname, or both names in quotes.\n"
    )


def test_no_team_and_nothing_asked_for_is_silent(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league(team=None)
    out = tmp_path / "w.xlsx"
    result = run(runner, PDB, out)
    assert result.exit_code == 0
    assert plan_lines(result) == []
    assert shown(out) == slots((False, False), (False, False))


def test_path_without_a_team_fails(
    runner, denver_league: Callable[..., Path], config_dir: Path, tmp_path: Path
) -> None:
    location = denver_league(team=None)
    result = run(runner, PDB, tmp_path / "w.xlsx", "--path", location)
    assert result.exit_code == 2
    toml = config_dir / "leagues" / LEAGUE / "league.toml"
    assert result.stderr == f"FAIL {toml}: {TEAM_NOT_SET}\n"


@pytest.mark.parametrize(
    ("settings", "args", "line"),
    [
        ({"team": "Denver"}, [], PATH_NOT_SET),
        ({}, ["--team", "Denver"], PATH_NOT_SET),
        ({}, ["--path", "plans"], TEAM_NOT_SET),
    ],
    ids=["team", "--team", "no team before no path"],
)
def test_team_in_play_needs_path(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    settings: dict[str, str],
    args: list[str],
    line: str,
) -> None:
    folder = build_league(**settings)
    write_config(athc_toml() + CONVERT_PDB_TOML)
    (tmp_path / "plans").mkdir()
    result = run(runner, PDB, tmp_path / "w.xlsx", *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'league.toml'}: {line}\n"


def test_league_lge_missing(
    runner, denver_league: Callable[..., Path], tmp_path: Path
) -> None:
    denver_league()
    lge = tmp_path / "lg2" / f"{LEAGUE}.lge"
    lge.unlink()
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lge}: {FILE_NOT_FOUND}\n"


def test_league_team_counts_differ(
    runner, lg2_league, config_dir: Path, tmp_path: Path
) -> None:
    lg2 = lg2_league(denver(), team(), team="Denver", names=TEAM_NAMES[:1])
    write_config_file(config_dir, athc_toml() + CONVERT_PDB_TOML)
    result = run(runner, PDB, tmp_path / "w.xlsx")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2}: Lists 2 team(s), but {LEAGUE}.lge has 1.\n"
