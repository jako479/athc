"""Integration tests for `athc gameplan check`."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan._common import collect_files
from athc.cli.gameplan.check import check, check_file
from athc.fbpro98_gameplan import InvalidGamePlanError
from athc.gameplan import load_rules
from athc.playpool import load_rules as load_pool_rules
from athc.playpool import read_play_pool
from tests.conftest import (
    CATEGORIES_TOML,
    LEAGUE,
    PNFL_LABELS,
    league_toml,
    no_league_selected,
    no_rules_configured,
    os_error,
    toml_error,
)
from tests.integration.conftest import (
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    PLAYS,
    POOL_RULES,
)

RULES = load_rules([str(GP_RULES)], labels=PNFL_LABELS)
POOL = read_play_pool(
    str(PLAYS), rules=load_pool_rules(str(POOL_RULES)), labels=PNFL_LABELS
)
WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the test pool, its playpool rules and gameplan rules."""
    folder = make_league(LEAGUE, league_toml(PLAYS))
    shutil.copy(GP_RULES, folder / "gameplan.toml")
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


# ── collect_files ─────────────────────────────────────────────────────────────


def test_collect_single_file(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    collected = collect_files([str(f)], suffix=".pln", recursive=False)
    assert collected.files == [f]
    assert collected.errors == [] and collected.warnings == []


def test_collect_directory_top_level(tmp_path: Path) -> None:
    (tmp_path / "a.pln").touch()
    (tmp_path / "skip.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    files = collect_files([str(tmp_path)], suffix=".pln", recursive=False).files
    assert sorted(f.name for f in files) == ["a.pln"]


def test_collect_directory_recursive(tmp_path: Path) -> None:
    (tmp_path / "top.pln").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    files = collect_files([str(tmp_path)], suffix=".pln", recursive=True).files
    assert sorted(f.name for f in files) == ["deep.pln", "top.pln"]


def test_collect_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    collected = collect_files([str(missing)], suffix=".pln", recursive=False)
    assert collected.files == []
    assert collected.errors == [f"{missing}: not found"]


def test_collect_non_pln(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.touch()
    collected = collect_files([str(bad)], suffix=".pln", recursive=False)
    assert collected.files == []
    assert collected.errors == [f"{bad}: not a .pln file"]


def test_collect_empty_dir_is_a_warning(tmp_path: Path) -> None:
    collected = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.errors == []
    assert collected.warnings == [f"{tmp_path}: no .pln files"]


def test_collect_dedupes(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    files = collect_files([str(f), str(f)], suffix=".pln", recursive=False).files
    assert len(files) == 1


def test_collect_glob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "Off1.pln").touch()
    (tmp_path / "Off2.pln").touch()
    (tmp_path / "skip.txt").touch()
    monkeypatch.chdir(tmp_path)
    collected = collect_files(["Off*.pln"], suffix=".pln", recursive=False)
    assert sorted(f.name for f in collected.files) == ["Off1.pln", "Off2.pln"]
    assert collected.errors == [] and collected.warnings == []


def test_collect_glob_without_a_match_is_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    collected = collect_files(["Off*.pln"], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.errors == []
    assert collected.warnings == ["Off*.pln: no .pln files match"]


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
    assert line.startswith(f"{GP_OFFENSE}: offense, ")


def test_check_file_malformed_raises(tmp_path: Path) -> None:
    """The reader's error passes through: the loop catches per item."""
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    with pytest.raises(InvalidGamePlanError) as exc:
        check_file(bad, RULES, POOL)
    assert exc.value.path == bad


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


@pytest.mark.usefixtures("league")
def test_cli_no_path_checks_current_directory(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plans = tmp_path / "plans"
    plans.mkdir()
    shutil.copy2(GP_OFFENSE, plans / "off.pln")
    shutil.copy2(GP_DEFENSE, plans / "def.pln")
    monkeypatch.chdir(plans)
    result = runner.invoke(check, [])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_no_path_recursive(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plans = tmp_path / "plans"
    (plans / "sub").mkdir(parents=True)
    shutil.copy2(GP_OFFENSE, plans / "sub" / "off.pln")
    monkeypatch.chdir(plans)
    result = runner.invoke(check, ["-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_no_path_empty_directory(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to check is a warning, not an error."""
    plans = tmp_path / "plans"
    plans.mkdir()
    monkeypatch.chdir(plans)
    result = runner.invoke(check, [])
    assert result.exit_code == 0
    assert result.stderr.endswith("WARN .: no .pln files\n")
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"


@pytest.mark.parametrize("option", ["--play-path", "--playpool-rules", "--rules"])
def test_cli_removed_options_are_rejected(runner, option: str) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), option, "x"])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


@pytest.mark.usefixtures("league")
def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.stdout and "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(GP_OFFENSE), str(GP_DEFENSE)])
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_directory(runner, tmp_path: Path) -> None:
    plans = tmp_path / "plans"
    plans.mkdir()
    shutil.copy2(GP_OFFENSE, plans / "off.pln")
    shutil.copy2(GP_DEFENSE, plans / "def.pln")
    result = runner.invoke(check, [str(plans)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "plans" / "sub"
    sub.mkdir(parents=True)
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    result = runner.invoke(check, [str(tmp_path / "plans"), "-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_clean_exit_0(runner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "athc.cli.gameplan.check.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert result.stdout.startswith(f"OK   {GP_OFFENSE}: offense, ")
    assert "1 file(s) checked, 0 with violations, 0 failed" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_missing_path(runner) -> None:
    missing = PLAYS / "nope.pln"
    result = runner.invoke(check, [str(missing)])
    assert result.exit_code == 2
    assert f"FAIL {missing}: not found\n" in result.stderr
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 1 failed\n"


@pytest.mark.usefixtures("league")
def test_cli_bug_in_one_file_keeps_the_batch_going(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    """A bug on one file is reported as unexpected, the other file is still
    checked, and the run still exits 2."""
    doomed = tmp_path / "doomed.pln"
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, doomed)
    shutil.copy2(GP_OFFENSE, good)
    from athc.cli.gameplan import check as check_module

    real_read = check_module.read_gameplan

    def read(path: str):
        if Path(path) == doomed:
            raise RuntimeError("kaboom")
        return real_read(path)

    monkeypatch.setattr(check_module, "read_gameplan", read)
    result = runner.invoke(check, [str(doomed), str(good)])
    assert result.exit_code == 2
    assert (
        f"FAIL {doomed}: unexpected error (see log: {log_dir / 'athc.log'})"
        in result.stderr
    )
    assert f"{good}: " in result.stdout
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout
    assert "RuntimeError: kaboom" in (log_dir / "athc.log").read_text(encoding="utf-8")


@pytest.mark.usefixtures("league")
def test_cli_malformed_pln(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad)])
    assert result.exit_code == 2
    assert (
        f"FAIL {bad}: File too small to contain PLN header and offsets table\n"
        in result.stderr
    )
    assert result.stderr.count(str(bad)) == 1


@pytest.mark.usefixtures("league")
def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, good)
    result = runner.invoke(check, [str(bad), str(good)])
    assert result.exit_code == 2
    assert f"FAIL {bad}: " in result.stderr and f"{good}:" in result.stdout
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout


# ── pool / rules / config resolution ──────────────────────────────────────────


def test_cli_missing_play_path(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "nope"), encoding="utf-8"
    )
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope'}: play path is not a directory\n"


def test_cli_bad_playpool_rules(runner, league: Path) -> None:
    (league / "playpool.toml").write_text("not = valid = toml", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'playpool.toml'}: TOML parse error: "
        f"{toml_error('not = valid = toml')}\n"
    )
    assert result.stdout == ""


def test_cli_no_rules_in_league_folder(runner, make_league: MakeLeague) -> None:
    make_league(LEAGUE, league_toml(PLAYS))
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("gameplan.toml")


def test_cli_bad_rules_toml(runner, league: Path) -> None:
    (league / "gameplan.toml").write_text("not = valid = toml", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'gameplan.toml'}: TOML parse error: "
        f"{toml_error('not = valid = toml')}\n"
    )


def test_cli_no_league(runner, config_dir: Path) -> None:
    """No config -> the league can't be resolved."""
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)


def test_cli_resolves_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # No flags: league from athc.ini, everything else from its league folder.
    folder = make_league(LEAGUE, league_toml(PLAYS))
    shutil.copy(GP_RULES, folder / "gameplan.toml")
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "violation(s)" in result.stdout


def test_cli_gameplan_rules_list_layers_in_order(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    # A gameplan_rules list replaces the fixed file; the overlay is read last.
    folder = make_league(
        LEAGUE,
        f"[league]\nplay_path = '{PLAYS}'\n"
        f"gameplan_rules = ['{GP_RULES}', 'overlay.toml']\n" + CATEGORIES_TOML,
    )
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    (folder / "overlay.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", LEAGUE])
    assert result.exit_code == 1
    assert "violation(s)" in result.stdout


def test_cli_missing_listed_rules_file_is_reported(
    runner, make_league: MakeLeague
) -> None:
    folder = make_league(
        LEAGUE,
        f"[league]\nplay_path = '{PLAYS}'\ngameplan_rules = ['gone.toml']\n"
        + CATEGORIES_TOML,
    )
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", LEAGUE])
    assert result.exit_code == 2
    gone = folder / "gone.toml"
    assert result.stderr == f"FAIL {gone}: {os_error(gone.read_bytes).strerror}\n"


@pytest.mark.usefixtures("league")
def test_cli_league_playpool_rules_apply(runner) -> None:
    """The league's playpool rules are read, so the filename-derived caps (timed,
    rollout, QB draw) are checked."""
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "timed passes" in result.stdout


# ── packaging check (real subprocess) ─────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_entry_point_subprocess(config_dir: Path, log_dir: Path) -> None:
    env = {
        **os.environ,
        "ATHC_CONFIG_DIR": str(config_dir),
        "ATHC_LOG_DIR": str(log_dir),
    }
    result = subprocess.run(
        [sys.executable, "-m", "athc", "gameplan", "check", str(GP_OFFENSE)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
    assert all(line.startswith("WARN ") for line in result.stderr.splitlines())
