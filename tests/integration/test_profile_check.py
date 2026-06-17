"""Integration tests for `athc profile check`."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.profile._common import collect_files
from athc.cli.profile.check import check, check_file
from athc.fbpro98_gameplan import read_gameplan
from athc.profile import ProfileRules, load_rules
from tests.integration.conftest import (
    COMPAT_DEF_CLEAN,
    COMPAT_OFF_CLEAN,
    DATA,
    DEF1,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    OFF1,
    RULES_TOML,
)

RULES = load_rules([RULES_TOML])
WriteConfig = Callable[..., Path]


# ── collect_files ─────────────────────────────────────────────────────────────


def test_collect_single_file(tmp_path: Path) -> None:
    f = tmp_path / "a.prf"
    f.touch()
    files, errors = collect_files([str(f)], suffix=".prf", recursive=False)
    assert files == [f]
    assert errors == []


def test_collect_directory_top_level(tmp_path: Path) -> None:
    (tmp_path / "a.prf").touch()
    (tmp_path / "b.prf").touch()
    (tmp_path / "skip.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.prf").touch()
    files, errors = collect_files([str(tmp_path)], suffix=".prf", recursive=False)
    assert sorted(f.name for f in files) == ["a.prf", "b.prf"]
    assert errors == []


def test_collect_directory_recursive(tmp_path: Path) -> None:
    (tmp_path / "top.prf").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.prf").touch()
    files, errors = collect_files([str(tmp_path)], suffix=".prf", recursive=True)
    assert sorted(f.name for f in files) == ["deep.prf", "top.prf"]
    assert errors == []


def test_collect_missing_path(tmp_path: Path) -> None:
    files, errors = collect_files(
        [str(tmp_path / "nope")], suffix=".prf", recursive=False
    )
    assert files == []
    assert any("does not exist" in e for e in errors)


def test_collect_non_prf(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.touch()
    files, errors = collect_files([str(bad)], suffix=".prf", recursive=False)
    assert files == []
    assert any("not a .prf file" in e for e in errors)


def test_collect_empty_dir(tmp_path: Path) -> None:
    files, errors = collect_files([str(tmp_path)], suffix=".prf", recursive=False)
    assert files == []
    assert any("no .prf files" in e for e in errors)


def test_collect_dedupes(tmp_path: Path) -> None:
    f = tmp_path / "a.prf"
    f.touch()
    files, _ = collect_files([str(f), str(f)], suffix=".prf", recursive=False)
    assert len(files) == 1


@pytest.mark.parametrize(
    "create,pattern,expected,has_error",
    [
        (
            ["Off1.prf", "Off2.prf", "Def.prf", "skip.txt"],
            "Off*.prf",
            ["Off1.prf", "Off2.prf"],
            False,
        ),
        (["a.prf", "b.txt"], "*", ["a.prf"], False),
        (["x.txt"], "*.prf", [], True),
    ],
)
def test_collect_glob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    create: list[str],
    pattern: str,
    expected: list[str],
    has_error: bool,
) -> None:
    for name in create:
        (tmp_path / name).touch()
    monkeypatch.chdir(tmp_path)
    files, errors = collect_files([pattern], suffix=".prf", recursive=False)
    assert sorted(f.name for f in files) == expected
    assert bool(errors) is has_error


# ── check_file ────────────────────────────────────────────────────────────────


def test_check_file_offense_format() -> None:
    count, line = check_file(OFF1, RULES)
    head, *rest = line.splitlines()
    assert count > 0
    assert head.startswith(str(OFF1))
    assert "violation(s)" in head and "offense" in head and "FG range" in head
    assert all(detail.startswith("  ") for detail in rest)


def test_check_file_defense_format() -> None:
    count, line = check_file(DEF1, RULES)
    assert count > 0
    assert "defense" in line.splitlines()[0]


def test_check_file_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.profile.check.validate_profile", lambda prof, rules: ()
    )
    count, line = check_file(OFF1, RULES)
    assert count == 0
    assert line.startswith(f"{OFF1}: OK (offense, FG range ")


def test_check_file_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    count, line = check_file(bad, RULES)
    assert count == -1
    assert line.startswith(f"{bad}: ERROR")


@pytest.mark.parametrize("path,expected", [(OFF1, 18), (DEF1, 7)])
def test_check_file_pinned_counts(path: Path, expected: int) -> None:
    count, _ = check_file(path, RULES)
    assert count == expected


@pytest.mark.parametrize("path", [OFF1, DEF1])
def test_check_file_matches_golden(path: Path) -> None:
    _, report = check_file(path, RULES)
    normalized = report.replace(str(path), path.name)
    golden = (EXPECTED / f"{path.stem}.report.txt").read_text(encoding="utf-8")
    assert normalized + "\n" == golden


# ── command (CliRunner) ───────────────────────────────────────────────────────


def test_cli_requires_path(runner) -> None:
    assert runner.invoke(check, []).exit_code == 2


def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(OFF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output and "1 file(s) checked" in result.output


def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(OFF1), str(DEF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output and "across 2 file(s)" in result.output


def test_cli_directory(runner, tmp_path: Path) -> None:
    shutil.copy2(OFF1, tmp_path / "off.prf")
    shutil.copy2(DEF1, tmp_path / "def.prf")
    result = runner.invoke(check, [str(tmp_path), "--rules", str(RULES_TOML)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output


def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    shutil.copy2(OFF1, sub / "off.prf")
    result = runner.invoke(check, [str(tmp_path), "-r", "--rules", str(RULES_TOML)])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.output


def test_cli_clean_exit_0(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.profile.check.validate_profile", lambda prof, rules: ()
    )
    result = runner.invoke(check, [str(OFF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 0
    assert "OK" in result.output and "0 violation(s) across 0 file(s)" in result.output


def test_cli_missing_path(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(DATA / "nope.prf")])
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


def test_cli_malformed_prf(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad), "--rules", str(RULES_TOML)])
    assert result.exit_code == 2
    assert "ERROR" in result.output


def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.prf"
    shutil.copy2(OFF1, good)
    result = runner.invoke(check, [str(bad), str(good), "--rules", str(RULES_TOML)])
    assert result.exit_code == 2
    assert f"{bad}: ERROR" in result.output and f"{good}:" in result.output
    assert "2 file(s) checked" in result.output


# ── rules / config resolution ─────────────────────────────────────────────────


def test_cli_no_rules(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text


def test_cli_rules_from_ini(runner, write_config: WriteConfig) -> None:
    write_config(f"[profile]\nrule_files =\n    {RULES_TOML}\n")
    assert runner.invoke(check, [str(OFF1)]).exit_code == 1


def test_cli_rules_override_ini(
    runner, write_config: WriteConfig, caplog: pytest.LogCaptureFixture
) -> None:
    write_config("[profile]\nrule_files =\n    bogus.toml\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 1
    assert "bogus.toml" not in caplog.text


def test_cli_rules_layering(runner, tmp_path: Path) -> None:
    overlay = tmp_path / "overlay.toml"
    overlay.write_text("min_categories = 3\n", encoding="utf-8")
    result = runner.invoke(
        check, [str(OFF1), "--rules", str(RULES_TOML), "--rules", str(overlay)]
    )
    assert result.exit_code == 1


def test_cli_bad_rules_toml(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("not = valid = toml", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1), "--rules", str(bad)])
    assert result.exit_code == 2
    assert "TOML parse error" in caplog.text


@pytest.mark.parametrize("via", ["ini", "cli"])
def test_cli_missing_rules(
    runner,
    write_config: WriteConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    via: str,
) -> None:
    missing = tmp_path / "no-such-rules.toml"
    if via == "ini":
        write_config(f"[profile]\nrule_files =\n    {missing}\n")
        args = [str(OFF1)]
    else:
        args = [str(OFF1), "--rules", str(missing)]
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, args)
    assert result.exit_code == 2
    assert str(missing) in caplog.text


def test_cli_malformed_ini(
    runner, write_config: WriteConfig, caplog: pytest.LogCaptureFixture
) -> None:
    write_config("[profile\nbroken\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2


# ── --gameplan compatibility (check_file) ─────────────────────────────────────

EMPTY_RULES = ProfileRules()  # no rules -> validate_profile reports nothing


def test_check_file_gameplan_offense_reports_compat() -> None:
    gp = read_gameplan(str(GP_OFFENSE))
    count, line = check_file(OFF1, RULES, gp)
    head = line.splitlines()[0]
    assert "gameplan issue(s)" in head and "offense" in head
    assert "gameplan: play category GLR (0x00)" in line
    # 18 rule violations + 1 gameplan issue
    assert count == 19


def test_check_file_gameplan_defense_reports_compat() -> None:
    gp = read_gameplan(str(GP_DEFENSE))
    count, line = check_file(DEF1, RULES, gp)
    assert "gameplan: special-teams category Field Goal/PAT" in line
    assert count == 8


def test_check_file_gameplan_clean() -> None:
    gp = read_gameplan(str(GP_OFFENSE))
    count, line = check_file(COMPAT_OFF_CLEAN, EMPTY_RULES, gp)
    assert count == 0
    assert line == f"{COMPAT_OFF_CLEAN}: OK (offense, FG range 20; gameplan compatible)"


def test_check_file_gameplan_side_mismatch() -> None:
    gp = read_gameplan(str(GP_DEFENSE))  # defense gameplan, offense profile
    count, line = check_file(OFF1, RULES, gp)
    assert count == -1
    assert "profile is offense but gameplan is defense" in line


def test_check_file_gameplan_side_mismatch_defense() -> None:
    gp = read_gameplan(str(GP_OFFENSE))  # offense gameplan, defense profile
    count, line = check_file(DEF1, RULES, gp)
    assert count == -1
    assert "profile is defense but gameplan is offense" in line


@pytest.mark.parametrize(
    "prof,gameplan,stem",
    [(OFF1, GP_OFFENSE, "compat_offense"), (DEF1, GP_DEFENSE, "compat_defense")],
)
def test_check_file_gameplan_matches_golden(
    prof: Path, gameplan: Path, stem: str
) -> None:
    gp = read_gameplan(str(gameplan))
    _, report = check_file(prof, RULES, gp)
    normalized = report.replace(str(prof), prof.name)
    golden = (EXPECTED / f"{stem}.report.txt").read_text(encoding="utf-8")
    assert normalized + "\n" == golden


# ── --gameplan compatibility (command) ────────────────────────────────────────


def test_cli_gameplan_offense_exit_1(runner) -> None:
    result = runner.invoke(
        check, [str(OFF1), "--rules", str(RULES_TOML), "--gameplan", str(GP_OFFENSE)]
    )
    assert result.exit_code == 1
    assert "gameplan issue(s)" in result.output
    assert "gameplan: play category GLR (0x00)" in result.output


def test_cli_gameplan_defense_exit_1(runner) -> None:
    result = runner.invoke(
        check, [str(DEF1), "--rules", str(RULES_TOML), "--gameplan", str(GP_DEFENSE)]
    )
    assert result.exit_code == 1
    assert "special-teams category Field Goal/PAT" in result.output


def test_cli_gameplan_clean_exit_0(runner, tmp_path: Path) -> None:
    empty = tmp_path / "empty.toml"
    empty.write_text("", encoding="utf-8")
    result = runner.invoke(
        check,
        [str(COMPAT_DEF_CLEAN), "--rules", str(empty), "--gameplan", str(GP_DEFENSE)],
    )
    assert result.exit_code == 0
    assert "gameplan compatible" in result.output


def test_cli_gameplan_side_mismatch_exit_2(runner) -> None:
    result = runner.invoke(
        check, [str(OFF1), "--rules", str(RULES_TOML), "--gameplan", str(GP_DEFENSE)]
    )
    assert result.exit_code == 2
    assert "profile is offense but gameplan is defense" in result.output


def test_cli_gameplan_mixed_sides_continues(runner) -> None:
    """One gameplan, two profiles: the matching side is checked, the other is a
    per-file side-mismatch error; the run continues and exits 2."""
    result = runner.invoke(
        check,
        [
            str(OFF1),
            str(DEF1),
            "--rules",
            str(RULES_TOML),
            "--gameplan",
            str(GP_OFFENSE),
        ],
    )
    assert result.exit_code == 2
    assert "gameplan issue(s)" in result.output  # OFF1 checked
    assert "profile is defense but gameplan is offense" in result.output  # DEF1
    assert "2 file(s) checked" in result.output


def test_cli_gameplan_missing_file_exit_2(
    runner, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check,
            [str(OFF1), "--rules", str(RULES_TOML), "--gameplan", str(DATA / "no.pln")],
        )
    assert result.exit_code == 2
    assert "no.pln" in caplog.text


def test_cli_gameplan_bad_extension_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "plan.txt"
    bad.write_bytes(b"\x00")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check, [str(OFF1), "--rules", str(RULES_TOML), "--gameplan", str(bad)]
        )
    assert result.exit_code == 2
    assert "not a .pln file" in caplog.text


def test_cli_gameplan_malformed_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            check, [str(OFF1), "--rules", str(RULES_TOML), "--gameplan", str(bad)]
        )
    assert result.exit_code == 2


# ── packaging check (real subprocess) ─────────────────────────────────────────


def test_entry_point_subprocess(tmp_path: Path) -> None:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "athc",
            "profile",
            "check",
            str(OFF1),
            "--rules",
            str(RULES_TOML),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
