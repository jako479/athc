"""Integration tests for `athc profile diff`."""

from __future__ import annotations

import csv
import io
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from athc.cli.profile.diff import _CSV_COLUMNS, _infer_format, diff, render, render_csv
from athc.fbpro98_profile import ProfileType
from athc.profile import ProfileDiff, SituationChange, SlotChange
from tests.integration.conftest import DATA, DEF1, EXPECTED, OFF1

OFF2 = DATA / "TST-OFF2.prf"
BASE = DATA / "diff_base.prf"
MOD = DATA / "diff_modified.prf"


def _norm(text: str, a: Path, b: Path) -> str:
    return text.replace(str(a), a.name).replace(str(b), b.name)


# ── command (CliRunner) ───────────────────────────────────────────────────────


def test_cli_requires_two_paths(runner) -> None:
    assert runner.invoke(diff, [str(OFF1)]).exit_code == 2


def test_cli_identical_exit_0(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(OFF1)])
    assert result.exit_code == 0
    assert "are identical." in result.output


def test_cli_differs_exit_1(runner) -> None:
    result = runner.invoke(diff, [str(OFF1), str(OFF2)])
    assert result.exit_code == 1
    assert f"{OFF1} -> {OFF2}" in result.output
    assert "[situations]" in result.output
    assert "situation(s)," in result.output  # summary footer


def test_cli_cross_side_exit_2(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(diff, [str(OFF1), str(DEF1)])
    assert result.exit_code == 2
    assert "cannot diff" in caplog.text


def test_cli_missing_path_exit_2(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(diff, [str(DATA / "nope.prf"), str(OFF1)])
    assert result.exit_code == 2


def test_cli_malformed_prf_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(diff, [str(bad), str(OFF1)])
    assert result.exit_code == 2


# ── --output ──────────────────────────────────────────────────────────────────


def test_output_txt_matches_stdout(runner, tmp_path: Path) -> None:
    stdout = runner.invoke(diff, [str(OFF1), str(OFF2)])
    assert stdout.exit_code == 1
    out = tmp_path / "report.txt"
    written = runner.invoke(diff, [str(OFF1), str(OFF2), "-o", str(out)])
    assert written.exit_code == 1
    assert written.output == ""  # nothing to stdout when writing a file
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


def test_output_unknown_extension_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    out = tmp_path / "report.json"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(diff, [str(OFF1), str(OFF1), "-o", str(out)])
    assert result.exit_code == 2
    assert "can't infer format" in caplog.text
    assert not out.exists()


def test_output_write_failure_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    out = tmp_path / "no_such_dir" / "report.csv"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(diff, [str(BASE), str(MOD), "-o", str(out)])
    assert result.exit_code == 2


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


def test_entry_point_subprocess(tmp_path: Path) -> None:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-m", "athc", "profile", "diff", str(OFF1), str(OFF2)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "situation(s)," in result.stdout
