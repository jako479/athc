"""Integration tests for `athc profile diff`."""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli import cli
from athc.cli.profile.diff import _CSV_COLUMNS, _infer_format, diff, render, render_csv
from athc.errors import ALREADY_EXISTS, FILE_NOT_FOUND
from athc.fbpro98_profile import ProfileType
from athc.profile import ProfileDiff, SituationChange, SlotChange
from tests.conftest import LEAGUE
from tests.integration.conftest import (
    DATA,
    DEF1,
    DENVER,
    EXPECTED,
    HINT,
    OFF1,
    TEAM_REQUIRES_KEY,
    build_teams,
    location,
    profile_file,
)

OFF2 = DATA / "TST-OFF2.prf"
BASE = DATA / "diff_base.prf"
MOD = DATA / "diff_modified.prf"
Lg2League = Callable[..., Path]

HELP = """\
Usage: athc profile diff [OPTIONS] PROFILE1 PROFILE2

  Show differences between two profiles.

  Shows only what changed; both profiles must be the same side.

Positional arguments:
  PROFILE1  A .prf file or a profile key.
  PROFILE2  The profile to compare it with, named the same way.

Options:
  -o, --output FILE  Write the report to FILE instead of the console (.txt, or
                     .csv for Excel).
  --team NAME        Team the profile keys refer to (default: team in
                     league.toml).
  --league NAME      League to use (default: the one set with athc config set
                     league).
  -h, --help         Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile diff off1 off2
    athc profile diff off1 try.prf -o changes.csv
"""


def _norm(text: str, a: Path, b: Path) -> str:
    return text.replace(str(a), a.name).replace(str(b), b.name)


@pytest.fixture
def work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run from an empty folder, so no key is a file there."""
    folder = tmp_path / "work"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


# ── command (CliRunner) ───────────────────────────────────────────────────────


def test_help_screen(runner) -> None:
    result = runner.invoke(
        cli, ["profile", "diff", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == HELP


def test_cli_requires_two_paths(runner) -> None:
    assert runner.invoke(diff, [str(OFF1)]).exit_code == 2


@pytest.mark.parametrize(
    ("count", "error"),
    [
        (0, "Missing argument 'PROFILE1'."),
        (1, "Missing argument 'PROFILE2'."),
        (2, None),
        (3, f"Got unexpected extra argument ({OFF2})."),
    ],
)
def test_cli_takes_two_operands(runner, count: int, error: str | None) -> None:
    """Two are accepted; one fewer or one more is Click's line, with athc's
    period."""
    result = runner.invoke(diff, [str(OFF1), str(OFF1), str(OFF2)][:count])
    if error is None:
        assert result.exit_code == 0
        assert result.stdout == f"{OFF1} and {OFF1} are identical.\n"
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(f"Error: {error}\n")
        assert result.stdout == ""


@pytest.mark.usefixtures("work")
def test_cli_two_keys(runner, lg2_league: Lg2League) -> None:
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    result = runner.invoke(diff, ["off1", "off2"])
    assert result.exit_code == 1
    first, second = (profile_file(folder, DENVER, key) for key in ("off1", "off2"))
    assert result.stdout.startswith(f"{first} -> {second}\n")


@pytest.mark.usefixtures("work")
def test_cli_key_and_a_file(runner, lg2_league: Lg2League) -> None:
    """The report names the file the key stands for."""
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    result = runner.invoke(diff, ["off1", str(OFF2)])
    assert result.exit_code == 1
    assert result.stdout.startswith(
        f"{profile_file(folder, DENVER, 'off1')} -> {OFF2}\n"
    )


@pytest.mark.usefixtures("work")
def test_cli_missing_key_file(runner, lg2_league: Lg2League) -> None:
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    missing = profile_file(folder, DENVER, "off2")
    missing.unlink()
    result = runner.invoke(diff, ["off1", "off2"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND} {HINT}\n"
    assert result.stdout == ""


def test_cli_team_option_with_two_files(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(OFF2), "--team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr.endswith(TEAM_REQUIRES_KEY)
    assert result.stdout == ""


def test_cli_league_option_with_two_files_reads_nothing_else(
    runner, make_league: Callable[..., Path], write_config: Callable[..., Path]
) -> None:
    """The league is resolved, but neither athc.ini nor its league.toml is
    read: both are broken here."""
    make_league(LEAGUE, "not = valid = toml")
    write_config("[athc\nbroken\n")
    result = runner.invoke(diff, [str(OFF1), str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"{OFF1} and {OFF1} are identical.\n"


def test_cli_identical_exit_0(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(OFF1)])
    assert result.exit_code == 0
    assert result.stdout == f"{OFF1} and {OFF1} are identical.\n"


def test_cli_differs_exit_1(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(OFF2)])
    assert result.exit_code == 1
    assert f"{OFF1} -> {OFF2}" in result.stdout
    assert "[situations]" in result.stdout
    assert "situation(s)," in result.stdout  # summary footer


def test_cli_cross_side_exit_2(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(DEF1)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL Cannot compare {OFF1} (offense) with {DEF1} (defense).\n"
    )
    assert result.stdout == ""


def test_cli_missing_path_exit_2(runner) -> None:
    result = runner.invoke(diff, [str(DATA / "nope.prf"), str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {DATA / 'nope.prf'}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_cli_malformed_prf_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(diff, [str(bad), str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {bad}: File too small to contain F95 block.\n"


# ── --output ──────────────────────────────────────────────────────────────────


def test_output_txt_matches_stdout(runner, tmp_path: Path) -> None:
    stdout = runner.invoke(diff, [str(OFF1), str(OFF2)])
    assert stdout.exit_code == 1
    out = tmp_path / "report.txt"
    written = runner.invoke(diff, [str(OFF1), str(OFF2), "-o", str(out)])
    assert written.exit_code == 1
    assert written.stdout == f"OK   {out}: written\n"  # the report is in the file
    assert out.read_text(encoding="utf-8") == stdout.output


def test_output_txt_identical_exit_0(runner, tmp_path: Path) -> None:
    out = tmp_path / "report.txt"
    assert runner.invoke(diff, [str(OFF1), str(OFF1), "-o", str(out)]).exit_code == 0
    assert "are identical." in out.read_text(encoding="utf-8")


def test_output_csv_rows_and_crlf(runner, tmp_path: Path) -> None:
    out = tmp_path / "report.csv"
    assert runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)]).exit_code == 1
    raw = out.read_bytes()
    assert b"\r\n" in raw  # Excel-friendly line endings
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    assert rows[0] == [f"# {BASE} -> {MOD}"]  # provenance first
    assert list(_CSV_COLUMNS) in rows  # column header present
    data_rows = [r for r in rows if r and r[0] == "1"]
    assert data_rows and " ".join(data_rows[0][1:6]) == ">5 1st 0-1 <DEF5 Ahd8+"


def test_output_unknown_extension_is_a_usage_error(runner, tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(diff, [str(OFF1), str(OFF1), "-o", str(out)])
    assert result.exit_code == 2
    assert "Usage:" in result.stderr
    assert result.stderr.endswith(
        "Error: Invalid value for '-o' / '--output': must have a .txt or .csv "
        "extension.\n"
    )
    assert not out.exists()


def test_output_creates_missing_folder(runner, tmp_path: Path) -> None:
    out = tmp_path / "reports" / "report.csv"
    assert runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)]).exit_code == 1
    assert out.is_file()


def test_output_creates_missing_folders_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "reports" / "2049" / "report.txt"
    assert runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)]).exit_code == 1
    assert out.is_file()


def test_output_write_failure_exit_2(runner, tmp_path: Path) -> None:
    (tmp_path / "reports").write_text("x", encoding="utf-8")
    out = tmp_path / "reports" / "report.csv"
    result = runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {out.parent}: {ALREADY_EXISTS}\n"


# ── golden output (controlled synthetic pair touching every field) ────────────


@pytest.mark.parametrize("ext", ["txt", "csv"])
def test_all_fields_output_matches_golden(runner, tmp_path: Path, ext: str) -> None:
    out = tmp_path / f"report.{ext}"
    assert runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)]).exit_code == 1
    golden = (EXPECTED / f"diff_all_fields.{ext}").read_text(encoding="utf-8")
    assert _norm(out.read_text(encoding="utf-8"), BASE, MOD) == golden


@pytest.mark.parametrize("ext", ["txt", "csv"])
def test_identical_output_matches_golden(runner, tmp_path: Path, ext: str) -> None:
    out = tmp_path / f"report.{ext}"
    assert runner.invoke(diff, [str(BASE), str(BASE), "-o", str(out)]).exit_code == 0
    golden = (EXPECTED / f"diff_identical.{ext}").read_text(encoding="utf-8")
    assert _norm(out.read_text(encoding="utf-8"), BASE, BASE) == golden


# ── render / render_csv (direct) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "name,expected", [("r.txt", "txt"), ("r.csv", "csv"), ("r.json", None), ("r", None)]
)
def test_infer_format(name: str, expected: str | None) -> None:
    assert _infer_format(Path(name)) == expected


def test_render_defense_direction_shows_hex() -> None:
    # PASS_SHORT_LEFT (0x0D) -> PASS_SHORT_RIGHT (0x0F) both collapse to "PassShort"; show hex.
    change = SituationChange(
        100,
        ">5 3rd 6-10 DEF35-OFF35 Tied",
        None,
        (SlotChange(2, (0x0D, 3), (0x0F, 3)),),
    )
    result = ProfileDiff(ProfileType.DEFENSE, (), (change,), ())
    assert "0x0D 3 -> 0x0F 3" in render(result, "a", "b")


def test_render_csv_defense_direction_hex() -> None:
    change = SituationChange(
        100,
        ">5 3rd 6-10 DEF35-OFF35 Tied",
        None,
        (SlotChange(2, (0x0D, 3), (0x0E, 3)),),
    )
    result = ProfileDiff(ProfileType.DEFENSE, (), (change,), ())
    rows = list(csv.reader(io.StringIO(render_csv(result, "a", "b"))))
    data = next(r for r in rows if r and r[0] == "100")
    assert (data[10], data[11]) == ("0x0D:3", "0x0E:3")  # slot2_old, slot2_new


def test_render_csv_slot_cell_formats() -> None:
    weight_only = SituationChange(
        1, ">5 1st 0-1 <DEF5 Tied", None, (SlotChange(1, (0x03, 3), (0x03, 8)),)
    )
    code_change = SituationChange(
        2, ">5 1st 0-1 <DEF5 Tied", None, (SlotChange(1, (0x03, 3), (0x04, 3)),)
    )
    result = ProfileDiff(ProfileType.OFFENSE, (), (weight_only, code_change), ())
    rows = [
        r
        for r in csv.reader(io.StringIO(render_csv(result, "a", "b")))
        if r and r[0] in ("1", "2")
    ]
    assert (rows[0][8], rows[0][9]) == ("RM:3", "RM:8")
    assert (rows[1][8], rows[1][9]) == ("RM:3", "RR:3")


# ── packaging check (real subprocess) ─────────────────────────────────────────


def test_entry_point_subprocess(tmp_path: Path, log_dir: Path) -> None:
    env = {
        **os.environ,
        "ATHC_CONFIG_DIR": str(tmp_path),
        "ATHC_LOG_DIR": str(log_dir),
    }
    result = subprocess.run(
        [sys.executable, "-m", "athc", "profile", "diff", str(OFF1), str(OFF2)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "situation(s)," in result.stdout
    assert result.stderr == ""
