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
from athc.gameplan.config import load_config
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
WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the test pool, its playpool rules and gameplan rules."""
    folder = make_league("PNFL", f"[league]\nplay_path = {PLAYS}\n")
    shutil.copy(GP_RULES, folder / "rules" / "gameplan.toml")
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    write_config("[athc]\nleague = PNFL\n")
    return folder


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


@pytest.mark.parametrize("option", ["--play-path", "--playpool-rules", "--rules"])
def test_cli_removed_options_are_rejected(runner, option: str) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), option, "x"])
    assert result.exit_code == 2
    assert "No such option" in result.output


@pytest.mark.usefixtures("league")
def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output and "1 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), str(GP_DEFENSE)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output and "across 2 file(s)" in result.output


@pytest.mark.usefixtures("league")
def test_cli_directory(runner, tmp_path: Path) -> None:
    plans = tmp_path / "plans"
    plans.mkdir()
    shutil.copy2(GP_OFFENSE, plans / "off.pln")
    shutil.copy2(GP_DEFENSE, plans / "def.pln")
    result = runner.invoke(check, [str(plans)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "plans" / "sub"
    sub.mkdir(parents=True)
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    result = runner.invoke(check, [str(tmp_path / "plans"), "-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.output


@pytest.mark.usefixtures("league")
def test_cli_clean_exit_0(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.gameplan.check.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert "OK" in result.output and "0 violation(s) across 0 file(s)" in result.output


@pytest.mark.usefixtures("league")
def test_cli_missing_path(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(PLAYS / "nope.pln")])
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


@pytest.mark.usefixtures("league")
def test_cli_malformed_pln(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad)])
    assert result.exit_code == 2
    assert "ERROR" in result.output


@pytest.mark.usefixtures("league")
def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, good)
    result = runner.invoke(check, [str(bad), str(good)])
    assert result.exit_code == 2
    assert f"{bad}: ERROR" in result.output and f"{good}:" in result.output
    assert "2 file(s) checked" in result.output


# ── pool / rules / config resolution ──────────────────────────────────────────


def test_cli_missing_play_path(
    runner, league: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (league / "league.ini").write_text(
        f"[league]\nplay_path = {tmp_path / 'nope'}\n", encoding="utf-8"
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "not a directory" in caplog.text


def test_cli_bad_playpool_rules(
    runner, league: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (league / "rules" / "playpool.toml").write_text(
        "not = valid = toml", encoding="utf-8"
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2


def test_cli_no_rules_in_league_folder(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league("PNFL", f"[league]\nplay_path = {PLAYS}\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "rules\\gameplan.toml" in caplog.text


def test_cli_bad_rules_toml(
    runner, league: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (league / "rules" / "gameplan.toml").write_text(
        "not = valid = toml", encoding="utf-8"
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "TOML parse error" in caplog.text


def test_cli_no_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    """No config -> the league can't be resolved."""
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "league" in caplog.text.lower()


def test_cli_resolves_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # No flags: league from athc.ini, everything else from leagues/PNFL/.
    folder = make_league("PNFL", f"[league]\nplay_path = {PLAYS}\n")
    shutil.copy(GP_RULES, folder / "rules" / "gameplan.toml")
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    write_config("[athc]\nleague = PNFL\n")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.output


def test_cli_gameplan_rules_list_layers_in_order(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    # A gameplan_rules list replaces the fixed file; the overlay is read last.
    folder = make_league(
        "PNFL",
        f"[league]\nplay_path = {PLAYS}\n"
        f"gameplan_rules =\n    {GP_RULES}\n    rules\\overlay.toml\n",
    )
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    (folder / "rules" / "overlay.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 1
    assert "violation(s)" in result.output


def test_cli_missing_listed_rules_file_is_reported(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league(
        "PNFL",
        f"[league]\nplay_path = {PLAYS}\ngameplan_rules =\n    rules\\gone.toml\n",
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(check, [str(GP_OFFENSE), "--league", "PNFL"])
    assert result.exit_code == 2
    assert "gone.toml" in caplog.text


def test_load_config_play_path_alone_reads_league_playpool_rules(
    tmp_path: Path, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """A `play_path` override replaces only `play_path`; the playpool rules still
    come from the league folder."""
    folder = make_league("PNFL", f"[league]\nplay_path = {tmp_path / 'league-pool'}\n")
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    write_config("[athc]\nleague = PNFL\n")
    cfg = load_config(play_path=PLAYS)
    assert cfg.play_path == PLAYS
    assert cfg.playpool_rules == folder / "rules" / "playpool.toml"


@pytest.mark.usefixtures("league")
def test_cli_league_playpool_rules_apply(runner) -> None:
    """The league's playpool rules are read, so the filename-derived caps (timed,
    rollout, QB draw) are checked."""
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "timed passes" in result.output


# ── packaging check (real subprocess) ─────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_entry_point_subprocess(config_dir: Path) -> None:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(config_dir)}
    result = subprocess.run(
        [sys.executable, "-m", "athc", "gameplan", "check", str(GP_OFFENSE)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
