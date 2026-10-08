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
from athc.profile import load_rules
from tests.conftest import LEAGUE, OTHER_LEAGUE
from tests.integration.conftest import (
    DATA,
    DEF1,
    EXPECTED,
    GP_OFFENSE,
    OFF1,
    RULES_TOML,
)

RULES = load_rules([RULES_TOML])
WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league, with the test rules as its profile.toml."""
    folder = make_league()
    shutil.copy(RULES_TOML, folder / "profile.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


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


@pytest.mark.usefixtures("league")
def test_cli_no_path_checks_current_directory(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copy2(OFF1, profiles / "off.prf")
    shutil.copy2(DEF1, profiles / "def.prf")
    monkeypatch.chdir(profiles)
    result = runner.invoke(check, [])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_no_path_recursive(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profiles = tmp_path / "profiles"
    (profiles / "sub").mkdir(parents=True)
    shutil.copy2(OFF1, profiles / "sub" / "off.prf")
    monkeypatch.chdir(profiles)
    result = runner.invoke(check, ["-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.output


def test_cli_no_path_empty_directory(
    runner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.chdir(profiles)
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [])
    assert result.exit_code == 2
    assert ".: no .prf files in directory" in caplog.text


def test_cli_rules_option_removed(runner) -> None:
    result = runner.invoke(check, [str(OFF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 2
    assert "No such option" in result.output


@pytest.mark.usefixtures("league")
def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output and "1 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(OFF1), str(DEF1)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output and "across 2 file(s)" in result.output


@pytest.mark.usefixtures("league")
def test_cli_directory(runner, tmp_path: Path) -> None:
    shutil.copy2(OFF1, tmp_path / "off.prf")
    shutil.copy2(DEF1, tmp_path / "def.prf")
    result = runner.invoke(check, [str(tmp_path)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    shutil.copy2(OFF1, sub / "off.prf")
    result = runner.invoke(check, [str(tmp_path), "-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_clean_exit_0(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.profile.check.validate_profile", lambda prof, rules: ()
    )
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 0
    assert "OK" in result.output and "0 violation(s) across 0 file(s)" in result.output


def test_cli_missing_path(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(DATA / "nope.prf")])
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


@pytest.mark.usefixtures("league")
def test_cli_malformed_prf(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad)])
    assert result.exit_code == 2
    assert "ERROR" in result.output


@pytest.mark.usefixtures("league")
def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.prf"
    shutil.copy2(OFF1, good)
    result = runner.invoke(check, [str(bad), str(good)])
    assert result.exit_code == 2
    assert f"{bad}: ERROR" in result.output and f"{good}:" in result.output
    assert "2 file(s) checked" in result.output


# ── rules / config resolution ─────────────────────────────────────────────────


def test_cli_no_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert "no league selected" in caplog.text


def test_cli_no_rules_in_league_folder(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league()
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "profile.toml" in caplog.text


def test_cli_rules_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league()
    shutil.copy(RULES_TOML, folder / "profile.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    assert runner.invoke(check, [str(OFF1)]).exit_code == 1


def test_cli_league_flag_picks_folder(runner, make_league: MakeLeague) -> None:
    make_league()  # no rules -> would fail
    other = make_league(OTHER_LEAGUE)
    shutil.copy(RULES_TOML, other / "profile.toml")
    assert runner.invoke(check, [str(OFF1), "--league", OTHER_LEAGUE]).exit_code == 1


def test_cli_profile_rules_list_relative_to_league_folder(
    runner, make_league: MakeLeague
) -> None:
    folder = make_league(LEAGUE, "[league]\nprofile_rules = ['mine.toml']\n")
    shutil.copy(RULES_TOML, folder / "mine.toml")
    assert runner.invoke(check, [str(OFF1), "--league", LEAGUE]).exit_code == 1


def test_cli_rules_layering(runner, make_league: MakeLeague) -> None:
    # A profile_rules list layers files in order; the overlay is read last.
    folder = make_league(
        LEAGUE,
        "[league]\nprofile_rules = ['base.toml', 'overlay.toml']\n",
    )
    shutil.copy(RULES_TOML, folder / "base.toml")
    (folder / "overlay.toml").write_text("min_categories = 3\n", encoding="utf-8")
    assert runner.invoke(check, [str(OFF1), "--league", LEAGUE]).exit_code == 1


def test_cli_bad_rules_toml(
    runner, league: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (league / "profile.toml").write_text("not = valid = toml", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert "TOML parse error" in caplog.text


def test_cli_missing_rules(
    runner, make_league: MakeLeague, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "no-such-rules.toml"
    make_league(LEAGUE, f"[league]\nprofile_rules = ['{missing}']\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 2
    assert str(missing) in caplog.text


def test_cli_malformed_ini(
    runner, write_config: WriteConfig, caplog: pytest.LogCaptureFixture
) -> None:
    write_config("[profile\nbroken\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2


# ── --gameplan is gone (check-ppp replaces it) ────────────────────────────────


def test_cli_gameplan_option_rejected(runner) -> None:
    result = runner.invoke(check, [str(OFF1), "--gameplan", str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "No such option '--gameplan'" in result.output


# ── packaging check (real subprocess) ─────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_entry_point_subprocess(config_dir: Path) -> None:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(config_dir)}
    result = subprocess.run(
        [sys.executable, "-m", "athc", "profile", "check", str(OFF1)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
