"""Integration tests for `athc gameplan list-normals` / `list-specials`."""

from __future__ import annotations

import logging
from pathlib import Path

from athc.cli.gameplan.list_normals import list_normals
from athc.cli.gameplan.list_specials import list_specials
from tests.integration.conftest import EXPECTED, GP_DEFENSE, GP_OFFENSE


def _expected(name: str) -> list[str]:
    return (EXPECTED / name).read_text(encoding="utf-8").splitlines()


# ── list-normals ──────────────────────────────────────────────────────────────


def test_normals_requires_path(runner) -> None:
    assert runner.invoke(list_normals, []).exit_code == 2


def test_normals_rejects_invalid_sort(runner) -> None:
    assert (
        runner.invoke(list_normals, [str(GP_OFFENSE), "--sort", "bogus"]).exit_code == 2
    )


def test_normals_stdout_offense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_normals_slot.txt")


def test_normals_stdout_defense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_DEFENSE)])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("defense_normals_slot.txt")


def test_normals_stdout_sort_name(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "--sort", "name"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_normals_name.txt")


def test_normals_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_normals_slot.txt")


def test_normals_file_sort_name(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out), "--sort", "name"])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_name.txt"
    )


def test_normals_refuses_overwrite_without_force(
    runner, tmp_path: Path, caplog
) -> None:
    out = tmp_path / "plays.txt"
    out.write_text("existing\n", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 1
    assert out.read_text(encoding="utf-8") == "existing\n"
    assert "already exists" in caplog.text


def test_normals_overwrites_with_force(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out), "--force"])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_slot.txt"
    )


def test_normals_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert f"Wrote 64 normal play(s) to {out}" in result.output


def test_normals_missing_gameplan(runner, tmp_path: Path, caplog) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(tmp_path / "nope.pln")])
    assert result.exit_code == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_normals_malformed_file_mode_no_output(runner, tmp_path: Path, caplog) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "plays.txt"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(bad), str(out)])
    assert result.exit_code == 1
    assert not out.exists()


# ── list-specials ─────────────────────────────────────────────────────────────


def test_specials_requires_path(runner) -> None:
    assert runner.invoke(list_specials, []).exit_code == 2


def test_specials_stdout_offense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_specials.txt")


def test_specials_stdout_defense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_DEFENSE)])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("defense_specials.txt")


def test_specials_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_specials.txt")


def test_specials_refuses_overwrite_without_force(
    runner, tmp_path: Path, caplog
) -> None:
    out = tmp_path / "spec.txt"
    out.write_text("existing\n", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 1
    assert out.read_text(encoding="utf-8") == "existing\n"
    assert "already exists" in caplog.text


def test_specials_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert f"Wrote 6 special play(s) to {out}" in result.output


def test_specials_malformed_file_mode_no_output(runner, tmp_path: Path, caplog) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "spec.txt"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_specials, [str(bad), str(out)])
    assert result.exit_code == 1
    assert not out.exists()
