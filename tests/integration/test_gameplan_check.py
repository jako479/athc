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
from athc.errors import ACCESS_DENIED, FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import InvalidGamePlanError
from athc.gameplan import Rules, load_rules
from athc.playpool import read_play_pool
from tests.conftest import (
    CATEGORIES_TOML,
    LEAGUE,
    PNFL_LABELS,
    athc_toml,
    league_not_found,
    league_toml,
    no_league_selected,
    no_rules_configured,
    toml_error,
)
from tests.integration.conftest import (
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    PLAYS,
    team,
)

RULES = load_rules([str(GP_RULES)], labels=PNFL_LABELS)
POOL = read_play_pool(str(PLAYS), labels=PNFL_LABELS)
WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the test pool and gameplan rules."""
    folder = make_league(LEAGUE, league_toml(PLAYS))
    shutil.copy(GP_RULES, folder / "gameplan.toml")
    write_config(athc_toml())
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
    assert collected.errors == [f"{missing}: {FILE_NOT_FOUND}"]


def test_collect_non_pln(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.touch()
    collected = collect_files([str(bad)], suffix=".pln", recursive=False)
    assert collected.files == []
    assert collected.errors == [f"{bad}: Not a .pln file."]


def test_collect_empty_dir_is_a_warning(tmp_path: Path) -> None:
    collected = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.errors == []
    assert collected.warnings == [f"{tmp_path}: No .pln files."]


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
    assert collected.warnings == ["Off*.pln: No .pln files match."]


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


def test_check_file_clean() -> None:
    """No rules: offense.pln, with no repeat and every play in the pool, is clean."""
    assert check_file(GP_OFFENSE, Rules(), POOL) == (
        0,
        f"{GP_OFFENSE}: offense, 64 normal",
    )


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
    assert result.stderr.endswith("WARN .: No .pln files.\n")
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
def test_cli_wildcard_path(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """athc expands the wildcard itself: the two matching game plans only."""
    plans = tmp_path / "plans"
    plans.mkdir()
    shutil.copy2(GP_OFFENSE, plans / "Off1.pln")
    shutil.copy2(GP_OFFENSE, plans / "Off2.pln")
    shutil.copy2(GP_DEFENSE, plans / "def.pln")
    monkeypatch.chdir(plans)
    result = runner.invoke(check, ["Off*.pln"])
    assert result.exit_code == 1
    assert f"{Path('Off1.pln')}: " in result.stdout
    assert f"{Path('Off2.pln')}: " in result.stdout
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_cli_clean_exit_0(runner, league: Path) -> None:
    """An empty rules file: offense.pln passes."""
    (league / "gameplan.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {GP_OFFENSE}: offense, 64 normal\n"
        "\n"
        "1 file(s) checked, 0 with violations, 0 failed\n"
    )
    assert result.stderr == ""


def test_cli_pool_issue_is_a_warning(runner, league: Path, tmp_path: Path) -> None:
    """A play filed in the wrong folder is a WARN line; the run stays clean."""
    plays = shutil.copytree(PLAYS, tmp_path / "plays")
    shutil.copy2(
        plays / "Offense" / "RL" / "OR45RL01.ply",
        plays / "Offense" / "RM" / "MISFILE.ply",
    )
    (league / "league.toml").write_text(league_toml(plays), encoding="utf-8")
    (league / "gameplan.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert result.stderr == (
        "WARN Offense/RM/MISFILE.ply: Run Left play in a Run Middle folder.\n"
    )
    assert result.stdout.startswith(f"OK   {GP_OFFENSE}: offense, 64 normal\n")


def test_cli_league_that_does_not_exist_fails_first(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    """Before the path, which is missing too."""
    missing = tmp_path / "nope.pln"
    result = runner.invoke(check, [str(missing), "--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE")
    assert result.stdout == ""


@pytest.mark.usefixtures("league")
def test_cli_missing_path(runner) -> None:
    missing = PLAYS / "nope.pln"
    result = runner.invoke(check, [str(missing)])
    assert result.exit_code == 2
    assert f"FAIL {missing}: {FILE_NOT_FOUND}\n" in result.stderr
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 1 failed\n"


@pytest.mark.usefixtures("league")
def test_cli_locked_file_is_access_denied_and_the_batch_goes_on(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file Windows will not open (locked by the game, say) fails in
    Windows' words; the other file is still checked."""
    locked = tmp_path / "locked.pln"
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, locked)
    shutil.copy2(GP_OFFENSE, good)
    from athc.cli.gameplan import check as check_module

    real_read = check_module.read_gameplan

    def read(path: str):
        if Path(path) == locked:
            raise PermissionError(13, "Permission denied", path)
        return real_read(path)

    monkeypatch.setattr(check_module, "read_gameplan", read)
    result = runner.invoke(check, [str(locked), str(good)])
    assert result.exit_code == 2
    assert f"FAIL {locked}: {ACCESS_DENIED}\n" in result.stderr
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout


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
        f"FAIL {doomed}: Unexpected error. See {log_dir / 'athc.log'} for details."
        in result.stderr
    )
    assert f"{good}: " in result.stdout
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout
    log = (log_dir / "athc.log").read_text(encoding="utf-8").splitlines()
    fail = next(i for i, line in enumerate(log) if "Unexpected error" in line)
    assert log[fail].split(" ", 2)[2] == (
        f"ERROR {doomed}: Unexpected error. See {log_dir / 'athc.log'} for details."
    )
    assert log[fail + 1] == "Traceback (most recent call last):"
    assert "RuntimeError: kaboom" in "\n".join(log)


@pytest.mark.usefixtures("league")
def test_cli_malformed_pln(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad)])
    assert result.exit_code == 2
    assert (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
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
    assert result.stderr == (
        f"FAIL {tmp_path / 'nope'}: {PATH_NOT_FOUND} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


def test_cli_play_path_not_set(runner, league: Path) -> None:
    (league / "league.toml").write_text(league_toml(), encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER'.\n"
    )
    assert result.stdout == ""


def test_cli_no_rules_in_league_folder(runner, make_league: MakeLeague) -> None:
    make_league(LEAGUE, league_toml(PLAYS))
    result = runner.invoke(check, [str(GP_OFFENSE), "--league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("gameplan.toml")


def test_cli_rules_file_with_two_problems_is_two_fail_lines(
    runner, league: Path, log_dir: Path
) -> None:
    rules = league / "gameplan.toml"
    rules.write_text(
        "bogus = 1\n[profile_compatibility]\nrequire_all = 3\n", encoding="utf-8"
    )
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    lines = result.stderr.splitlines()
    assert len(lines) == 2
    assert all(line.startswith(f"FAIL {rules}: ") for line in lines)
    assert all(line.endswith(".") for line in lines)
    log = (log_dir / "athc.log").read_text(encoding="utf-8")
    assert log.count(f" ERROR {rules}: ") == 2


def test_cli_bad_rules_toml(runner, league: Path) -> None:
    (league / "gameplan.toml").write_text("not = valid = toml", encoding="utf-8")
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'gameplan.toml'}: {toml_error('not = valid = toml')}\n"
    )


def test_cli_no_league(runner, config_dir: Path) -> None:
    """No config -> the league can't be resolved."""
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)


def test_cli_resolves_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # No flags: league from athc.toml, everything else from its league folder.
    folder = make_league(LEAGUE, league_toml(PLAYS))
    shutil.copy(GP_RULES, folder / "gameplan.toml")
    write_config(athc_toml())
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
    assert result.stderr == f"FAIL {gone}: {FILE_NOT_FOUND}\n"


@pytest.mark.usefixtures("league")
def test_cli_attribute_caps_apply(runner) -> None:
    """The pool reads each play's attributes from its file, so the attribute
    caps (timed, rollout, QB run) are checked."""
    result = runner.invoke(check, [str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert "timed passes" in result.stdout


# ── game plan keys and --team ─────────────────────────────────────────────────


def team_plans(lg2_league, **settings: str) -> Path:
    """A league whose one team (Denver) has its four game plans named after
    their keys: OFF1.pln and DEF1.pln there (copies of the test game plans),
    OFF2.pln and DEF2.pln not. Returns the team's league folder."""
    lg2 = lg2_league(
        team(
            ("o1.prf", "OFF1.pln"),
            ("d1.prf", "DEF1.pln"),
            ("o2.prf", "OFF2.pln"),
            ("d2.prf", "DEF2.pln"),
        ),
        **settings,
    )
    folder = lg2.parent / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    shutil.copy2(GP_OFFENSE, folder / "OFF1.pln")
    shutil.copy2(GP_DEFENSE, folder / "DEF1.pln")
    return folder


def heads(result) -> list[str]:
    """The path of each report's first line, in order."""
    return [
        line.split(": ")[0]
        for line in result.stdout.splitlines()
        if line and not line.startswith(" ") and "file(s) checked" not in line
    ]


def test_cli_key_checks_that_game_plan(runner, lg2_league) -> None:
    folder = team_plans(lg2_league, team="Denver")
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 1
    assert heads(result) == [str(folder / "OFF1.pln")]
    assert "1 file(s) checked, 1 with violations, 0 failed" in result.stdout


def test_cli_key_and_a_path(runner, lg2_league) -> None:
    """Left to right, each file once."""
    folder = team_plans(lg2_league, team="Denver")
    result = runner.invoke(check, ["DEF1", str(GP_OFFENSE), "def1"])
    assert heads(result) == [str(folder / "DEF1.pln"), str(GP_OFFENSE)]
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_cli_key_missing_is_a_failed_item(runner, lg2_league) -> None:
    """At your league location, with the ppp_path hint; the others are
    checked."""
    folder = team_plans(lg2_league, team="Denver")
    result = runner.invoke(check, ["off2", "off1"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        f"FAIL {folder / 'OFF2.pln'}: {FILE_NOT_FOUND} Run 'athc config set "
        "ppp_path FOLDER' or pass a .pln file.\n"
    )
    assert "1 file(s) checked, 1 with violations, 1 failed" in result.stdout


def test_cli_key_team_option(runner, lg2_league) -> None:
    """--team with a key: `team` need not be set."""
    folder = team_plans(lg2_league)
    result = runner.invoke(check, ["off1", "--team", "Broncos"])
    assert heads(result) == [str(folder / "OFF1.pln")]


def test_cli_key_team_not_set(runner, lg2_league, config_dir: Path) -> None:
    team_plans(lg2_league)
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 2
    toml = config_dir / "leagues" / LEAGUE / "league.toml"
    assert result.stderr == (
        f"FAIL {toml}: Team is not set. Run 'athc config set team NAME' or pass "
        "--team or a .pln file.\n"
    )


@pytest.mark.parametrize(
    "args", [[], [str(GP_OFFENSE)], ["."]], ids=["no PATH", "a file", "a folder"]
)
def test_cli_team_without_a_key_is_a_usage_error(runner, args: list[str]) -> None:
    result = runner.invoke(check, [*args, "--team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires a game plan key (off1, def1, off2 or def2).\n"
    )
    assert result.stdout == ""


def test_cli_folder_named_like_a_key_is_searched(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    team_plans(lg2_league, team="Denver")
    (tmp_path / "off1").mkdir()
    shutil.copy2(GP_DEFENSE, tmp_path / "off1" / "draft.pln")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(check, ["off1"])
    assert heads(result) == [str(Path("off1") / "draft.pln")]


def test_cli_file_named_like_a_key_is_that_file(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    team_plans(lg2_league, team="Denver")
    (tmp_path / "off1").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 2
    assert result.stderr.endswith("FAIL off1: Not a .pln file.\n")
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 1 failed\n"


@pytest.mark.parametrize("key", ["def1", "off3"], ids=["a key", "a fifth"])
def test_cli_four_keys_only(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    """The four keys are accepted; any other word is a path like any other."""
    folder = team_plans(lg2_league, team="Denver")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(check, [key])
    if key == "def1":
        assert heads(result) == [str(folder / "DEF1.pln")]
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(f"FAIL off3: {FILE_NOT_FOUND}\n")


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
