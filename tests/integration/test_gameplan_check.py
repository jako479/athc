"""Integration tests for `athc gameplan check`."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan._common import collect_files
from athc.cli.gameplan.check import check, check_file
from athc.gameplan import load_rules
from athc.playpool import load_rules as load_pool_rules
from athc.playpool import read_play_pool
from tests.integration.conftest import (
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    PLAYS,
    POOL_RULES,
)

RULES = load_rules([str(GP_RULES)])
POOL = read_play_pool(str(PLAYS), rules=load_pool_rules(str(POOL_RULES)))
# Flags that skip league resolution (play-path + playpool-rules + rules).
FLAGS = [
    "--play-path",
    str(PLAYS),
    "--playpool-rules",
    str(POOL_RULES),
    "--rules",
    str(GP_RULES),
]
WriteConfig = Callable[..., Path]


# ── collect_files ─────────────────────────────────────────────────────────────


def test_collect_single_file(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    files, errors = collect_files([str(f)], suffix=".pln", recursive=False)
    assert files == [f]
    assert errors == []


def test_collect_directory_top_level(tmp_path: Path) -> None:
    (tmp_path / "a.pln").touch()
    (tmp_path / "skip.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    files, _ = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert sorted(f.name for f in files) == ["a.pln"]


def test_collect_directory_recursive(tmp_path: Path) -> None:
    (tmp_path / "top.pln").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    files, _ = collect_files([str(tmp_path)], suffix=".pln", recursive=True)
    assert sorted(f.name for f in files) == ["deep.pln", "top.pln"]


def test_collect_missing_path(tmp_path: Path) -> None:
    files, errors = collect_files(
        [str(tmp_path / "nope")], suffix=".pln", recursive=False
    )
    assert files == []
    assert any("does not exist" in e for e in errors)


def test_collect_non_pln(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.touch()
    files, errors = collect_files([str(bad)], suffix=".pln", recursive=False)
    assert files == []
    assert any("not a .pln file" in e for e in errors)


def test_collect_empty_dir(tmp_path: Path) -> None:
    files, errors = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert files == []
    assert any("no .pln files" in e for e in errors)


def test_collect_dedupes(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    files, _ = collect_files([str(f), str(f)], suffix=".pln", recursive=False)
    assert len(files) == 1


def test_collect_glob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "Off1.pln").touch()
    (tmp_path / "Off2.pln").touch()
    (tmp_path / "skip.txt").touch()
    monkeypatch.chdir(tmp_path)
    files, errors = collect_files(["Off*.pln"], suffix=".pln", recursive=False)
    assert sorted(f.name for f in files) == ["Off1.pln", "Off2.pln"]
    assert errors == []


# ── check_file ────────────────────────────────────────────────────────────────


def test_check_file_offense_format() -> None:
    count, line = check_file(GP_OFFENSE, RULES, POOL)
    head, *rest = line.splitlines()
    assert count > 0
    assert head.startswith(str(GP_OFFENSE))
    assert "violation(s)" in head and "offense" in head and "normal" in head
    assert all(detail.startswith("  ") for detail in rest)


def test_check_file_defense_format() -> None:
    count, line = check_file(GP_DEFENSE, RULES, POOL)
    assert count > 0
    assert "defense" in line.splitlines()[0]


def test_check_file_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.gameplan.check.validate_gameplan", lambda gp, rules, pool: ()
    )
    count, line = check_file(GP_OFFENSE, RULES, POOL)
    assert count == 0
    assert line.startswith(f"{GP_OFFENSE}: OK (offense, ")


def test_check_file_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    count, line = check_file(bad, RULES, POOL)
    assert count == -1
    assert line.startswith(f"{bad}: ERROR")


@pytest.mark.parametrize("path,expected", [(GP_OFFENSE, 3), (GP_DEFENSE, 1)])
def test_check_file_pinned_counts(path: Path, expected: int) -> None:
    count, _ = check_file(path, RULES, POOL)
    assert count == expected


@pytest.mark.parametrize("path", [GP_OFFENSE, GP_DEFENSE])
def test_check_file_matches_golden(path: Path) -> None:
    _, report = check_file(path, RULES, POOL)
    normalized = report.replace(str(path), path.name)
    golden = (EXPECTED / f"{path.stem}.report.txt").read_text(encoding="utf-8")
    assert normalized + "\n" == golden


# ── command (CliRunner) ───────────────────────────────────────────────────────


def test_cli_requires_path(runner) -> None:
    assert runner.invoke(check, []).exit_code == 2


def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), *FLAGS])
    assert result.exit_code == 1
    assert "violation(s)" in result.output and "1 file(s) checked" in result.output


def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), str(GP_DEFENSE), *FLAGS])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output and "across 2 file(s)" in result.output


def test_cli_directory(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    shutil.copy2(GP_DEFENSE, tmp_path / "def.pln")
    result = runner.invoke(check, [str(tmp_path), *FLAGS])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output


def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    result = runner.invoke(check, [str(tmp_path), "-r", *FLAGS])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.output


def test_cli_clean_exit_0(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.gameplan.check.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = runner.invoke(check, [str(GP_OFFENSE), *FLAGS])
    assert result.exit_code == 0
    assert "OK" in result.output and "0 violation(s) across 0 file(s)" in result.output


def test_cli_missing_path(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(PLAYS / "nope.pln"), *FLAGS])
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


def test_cli_malformed_pln(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad), *FLAGS])
    assert result.exit_code == 2
    assert "ERROR" in result.output


def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, good)
    result = runner.invoke(check, [str(bad), str(good), *FLAGS])
    assert result.exit_code == 2
    assert f"{bad}: ERROR" in result.output and f"{good}:" in result.output
    assert "2 file(s) checked" in result.output


# ── pool / rules / config resolution ──────────────────────────────────────────


def test_cli_missing_play_path(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [
                str(GP_OFFENSE),
                "--play-path",
                str(tmp_path / "nope"),
                "--playpool-rules",
                str(POOL_RULES),
                "--rules",
                str(GP_RULES),
            ],
        )
    assert result.exit_code == 2
    assert "not a directory" in caplog.text


def test_cli_bad_playpool_rules(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("not = valid = toml", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [
                str(GP_OFFENSE),
                "--play-path",
                str(PLAYS),
                "--playpool-rules",
                str(bad),
                "--rules",
                str(GP_RULES),
            ],
        )
    assert result.exit_code == 2


def test_cli_no_rules(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [
                str(GP_OFFENSE),
                "--play-path",
                str(PLAYS),
                "--playpool-rules",
                str(POOL_RULES),
            ],
        )
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text


def test_cli_bad_rules_toml(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("not = valid = toml", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [
                str(GP_OFFENSE),
                "--play-path",
                str(PLAYS),
                "--playpool-rules",
                str(POOL_RULES),
                "--rules",
                str(bad),
            ],
        )
    assert result.exit_code == 2
    assert "TOML parse error" in caplog.text


def test_cli_no_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    """No path overrides and no config -> the league can't be resolved."""
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "league" in caplog.text.lower()


def test_cli_resolves_from_league_ini(runner, write_config: WriteConfig) -> None:
    # No flags: everything resolves from config_dir()/athc.ini (ATHC_CONFIG_DIR).
    write_config(
        f"[athc]\ndefault_league = PNFL\n"
        f"[gameplan]\nrule_files =\n    {GP_RULES}\n"
        f"[league.PNFL]\nPlayPath = {PLAYS}\nPlayPoolRules = {POOL_RULES}\n",
    )
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output


# ── packaging check (real subprocess) ─────────────────────────────────────────


def test_entry_point_subprocess(tmp_path: Path) -> None:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-m", "athc", "gameplan", "check", str(GP_OFFENSE), *FLAGS],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
