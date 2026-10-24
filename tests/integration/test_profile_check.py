"""Integration tests for `athc profile check`."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli import cli
from athc.cli.profile.check import check, check_file
from athc.errors import FILE_NOT_FOUND
from athc.fbpro98_profile import InvalidProfileError
from athc.profile import ProfileRules, load_rules
from tests.conftest import (
    LEAGUE,
    OTHER_LEAGUE,
    PNFL_LABELS,
    athc_toml,
    league_toml,
    no_league_selected,
    no_rules_configured,
    toml_error,
)
from tests.integration.conftest import (
    ATHC,
    DATA,
    DEF1,
    DENVER,
    EXPECTED,
    GP_OFFENSE,
    HINT,
    LAS_VEGAS,
    OFF1,
    RULES_TOML,
    TEAM_REQUIRES_KEY,
    build_teams,
    heads,
    location,
    profile_file,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

# An athc.toml that is not valid TOML.
BROKEN = "[athc\nbroken\n"
Lg2League = Callable[..., Path]

HELP = """\
Usage: athc profile check [OPTIONS] [PATH]...

  Check profiles against the league's rules.

  To check a profile with its game plan, run 'athc check-ppp'.

Positional arguments:
  PATH  .prf files, folders, wildcards or profile keys (default: current
        folder).

Options:
  -r, --recursive  Include subfolders.
  --team NAME      Team the profile keys refer to (default: 'team' in
                   league.toml).
  --league NAME    League to use (default: the one set with 'athc config set
                   league').
  -h, --help       Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile check
    athc profile check off2
    athc profile check drafts\\*OFF*.prf
"""


@pytest.fixture(scope="module")
def rules() -> ProfileRules:
    """The test rules, read with the PNFL labels."""
    return load_rules([RULES_TOML], labels=PNFL_LABELS)


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league, with the test rules as its profile.toml."""
    folder = make_league()
    shutil.copy(RULES_TOML, folder / "profile.toml")
    write_config(athc_toml())
    return folder


# ── check_file ────────────────────────────────────────────────────────────────


def test_check_file_offense_format(rules: ProfileRules) -> None:
    count, line = check_file(OFF1, rules)
    head, *rest = line.splitlines()
    assert count > 0
    assert head.startswith(str(OFF1))
    assert "violation(s)" in head and "offense" in head and "FG range" in head
    assert all(detail.startswith("  ") for detail in rest)


def test_check_file_defense_format(rules: ProfileRules) -> None:
    count, line = check_file(DEF1, rules)
    assert count > 0
    assert "defense" in line.splitlines()[0]


def test_check_file_clean() -> None:
    """No rules: OFF1 is clean."""
    assert check_file(OFF1, ProfileRules()) == (0, f"{OFF1}: offense, FG range 36")


def test_check_file_malformed_raises(tmp_path: Path, rules: ProfileRules) -> None:
    """The reader's error passes through: the loop catches per item."""
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    with pytest.raises(InvalidProfileError) as exc:
        check_file(bad, rules)
    assert exc.value.path == bad


@pytest.mark.parametrize("path", [OFF1, DEF1])
def test_check_file_matches_golden(path: Path, rules: ProfileRules) -> None:
    _, report = check_file(path, rules)
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
    assert "2 file(s) checked" in result.stdout


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
    assert "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_no_path_empty_directory(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to check is a warning, not an error."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.chdir(profiles)
    result = runner.invoke(check, [])
    assert result.exit_code == 0
    assert result.stderr == "WARN .: No .prf files.\n"
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"


def test_cli_rules_option_removed(runner) -> None:
    result = runner.invoke(check, [str(OFF1), "--rules", str(RULES_TOML)])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


@pytest.mark.usefixtures("league")
def test_cli_violations_exit_1(runner) -> None:
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 1
    assert "violation(s)" in result.stdout and "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_multiple_files(runner) -> None:
    result = runner.invoke(check, [str(OFF1), str(DEF1)])
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_directory(runner, tmp_path: Path) -> None:
    shutil.copy2(OFF1, tmp_path / "off.prf")
    shutil.copy2(DEF1, tmp_path / "def.prf")
    result = runner.invoke(check, [str(tmp_path)])
    assert result.exit_code == 1
    assert "2 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_recursive(runner, tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    shutil.copy2(OFF1, sub / "off.prf")
    result = runner.invoke(check, [str(tmp_path), "-r"])
    assert result.exit_code == 1
    assert "1 file(s) checked" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_wildcard_path(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """athc expands the wildcard itself: the two matching profiles only."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copy2(OFF1, profiles / "Off1.prf")
    shutil.copy2(OFF1, profiles / "Off2.prf")
    shutil.copy2(DEF1, profiles / "def.prf")
    monkeypatch.chdir(profiles)
    result = runner.invoke(check, ["Off*.prf"])
    assert result.exit_code == 1
    assert f"{Path('Off1.prf')}: " in result.stdout
    assert f"{Path('Off2.prf')}: " in result.stdout
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_cli_clean_exit_0(runner, league: Path) -> None:
    """An empty rules file: OFF1 passes."""
    (league / "profile.toml").write_text("", encoding="utf-8")
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {OFF1}: offense, FG range 36\n"
        "\n"
        "1 file(s) checked, 0 with violations, 0 failed\n"
    )
    assert result.stderr == ""


@pytest.mark.usefixtures("league")
def test_cli_missing_path(runner) -> None:
    missing = DATA / "nope.prf"
    result = runner.invoke(check, [str(missing)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND}\n"
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 1 failed\n"


@pytest.mark.usefixtures("league")
def test_cli_malformed_prf(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(check, [str(bad)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {bad}: File too small to contain F95 block.\n"


@pytest.mark.usefixtures("league")
def test_cli_bug_in_one_file_keeps_the_batch_going(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    """A bug on one file is reported as unexpected, the other file is still
    checked, and the run still exits 2."""
    doomed = tmp_path / "doomed.prf"
    good = tmp_path / "good.prf"
    shutil.copy2(OFF1, doomed)
    shutil.copy2(OFF1, good)
    from athc.cli.profile import check as check_module

    real_read = check_module.read_profile

    def read(path: str):
        if Path(path) == doomed:
            raise RuntimeError("kaboom")
        return real_read(path)

    monkeypatch.setattr(check_module, "read_profile", read)
    result = runner.invoke(check, [str(doomed), str(good)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {doomed}: Unexpected error. See {log_dir / 'athc.log'} for details.\n"
    )
    assert f"{good}: " in result.stdout
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout


@pytest.mark.usefixtures("league")
def test_cli_continues_past_bad(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.prf"
    bad.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.prf"
    shutil.copy2(OFF1, good)
    result = runner.invoke(check, [str(bad), str(good)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {bad}: File too small to contain F95 block.\n"
    assert f"{good}:" in result.stdout
    assert "2 file(s) checked, 1 with violations, 1 failed" in result.stdout


# ── help ──────────────────────────────────────────────────────────────────────


def test_help_screen(runner) -> None:
    result = runner.invoke(
        cli, ["profile", "check", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == HELP


GROUP_HELP = """\
Usage: athc profile [OPTIONS] COMMAND [ARGS]...

  Check and edit coaching profiles (.prf).

Options:
  -h, --help  Show this message and exit.

Commands:
  check  Check profiles against the league's rules.
  copy   Copy settings from one profile to others.
  diff   Show differences between two profiles.
"""


def test_group_help_screen(runner) -> None:
    result = runner.invoke(
        cli, ["profile", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == GROUP_HELP


def test_bare_group_shows_its_help_on_stderr(runner) -> None:
    result = runner.invoke(cli, ["profile"], prog_name="athc", terminal_width=78)
    assert result.exit_code == 2
    assert result.stderr == GROUP_HELP
    assert result.stdout == ""


# ── profile keys ──────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("work")
def test_cli_key_checks_that_file(runner, lg2_league: Lg2League) -> None:
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    result = runner.invoke(check, ["off2"])
    assert heads(result) == [str(profile_file(folder, DENVER, "off2"))]
    assert "\n1 file(s) checked, " in result.stdout


@pytest.mark.usefixtures("work")
def test_cli_two_keys(runner, lg2_league: Lg2League) -> None:
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    result = runner.invoke(check, ["off1", "def1"])
    assert result.exit_code == 1
    assert heads(result) == [
        str(profile_file(folder, DENVER, "off1")),
        str(profile_file(folder, DENVER, "def1")),
    ]
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.usefixtures("work")
def test_cli_key_keeps_path_order(runner, lg2_league: Lg2League) -> None:
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    result = runner.invoke(check, [str(DEF1), "off1", str(OFF1)])
    assert heads(result) == [
        str(DEF1),
        str(profile_file(folder, DENVER, "off1")),
        str(OFF1),
    ]


@pytest.mark.usefixtures("work")
def test_cli_missing_key_file_counts_failed(runner, lg2_league: Lg2League) -> None:
    """The run goes on past it, and ends with 2."""
    folder = location(build_teams(lg2_league, team="Denver"), DENVER)
    missing = profile_file(folder, DENVER, "off2")
    missing.unlink()
    result = runner.invoke(check, ["off2", "off1"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND} {HINT}\n"
    assert heads(result) == [str(profile_file(folder, DENVER, "off1"))]
    assert "1 file(s) checked, 1 with violations, 1 failed" in result.stdout


def test_cli_no_path_with_team_set(runner, lg2_league: Lg2League, work: Path) -> None:
    """No PATH is still the current folder, `team` or not."""
    build_teams(lg2_league, team="Denver")
    shutil.copy2(OFF1, work / "mine.prf")
    result = runner.invoke(check, [])
    assert heads(result) == ["mine.prf"]


@pytest.mark.usefixtures("work")
def test_cli_team_option_with_a_key(runner, lg2_league: Lg2League) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, ["def1", "--team", "Raiders"])
    assert heads(result) == [
        str(profile_file(location(lg2_dir, LAS_VEGAS), LAS_VEGAS, "def1"))
    ]


def test_cli_team_option_without_path(runner) -> None:
    result = runner.invoke(check, ["--team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr.endswith(TEAM_REQUIRES_KEY)


# ── rules / config resolution ─────────────────────────────────────────────────


def test_cli_no_league(runner, config_dir: Path) -> None:
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)


def test_cli_no_rules_in_league_folder(runner, make_league: MakeLeague) -> None:
    make_league()
    result = runner.invoke(check, [str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")


def test_cli_rules_from_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league()
    shutil.copy(RULES_TOML, folder / "profile.toml")
    write_config(athc_toml())
    assert runner.invoke(check, [str(OFF1)]).exit_code == 1


def test_cli_allowed_lists_use_the_league_labels(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """The allowed lists are read with the labels in the league's league.toml;
    without them `RM` would not load."""
    folder = make_league(LEAGUE, league_toml())
    rules = folder / "profile.toml"
    rules.write_text('allowed_offensive_categories = ["RM"]\n', encoding="utf-8")
    write_config(athc_toml())
    _, report = check_file(OFF1, load_rules([rules], labels=PNFL_LABELS))
    assert "uses banned categories" in report
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 1
    assert result.stdout == (
        f"{report}\n\n1 file(s) checked, 1 with violations, 0 failed\n"
    )


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
    """A profile_rules list layers files in order and the overlay is read
    last: its `min_categories = 4` beats the base's 2."""
    folder = make_league(
        LEAGUE,
        "[league]\nprofile_rules = ['base.toml', 'overlay.toml']\n",
    )
    base, overlay = folder / "base.toml", folder / "overlay.toml"
    shutil.copy(RULES_TOML, base)
    overlay.write_text("min_categories = 4\n", encoding="utf-8")
    _, report = check_file(OFF1, load_rules([base, overlay], labels=PNFL_LABELS))
    assert "requires 4." in report  # the overlay's minimum is in force
    result = runner.invoke(check, [str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 1
    assert result.stdout == (
        f"{report}\n\n1 file(s) checked, 1 with violations, 0 failed\n"
    )


def test_cli_bad_rules_toml(runner, league: Path) -> None:
    (league / "profile.toml").write_text("not = valid = toml", encoding="utf-8")
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'profile.toml'}: {toml_error('not = valid = toml')}\n"
    )


def test_cli_missing_rules(runner, make_league: MakeLeague, tmp_path: Path) -> None:
    missing = tmp_path / "no-such-rules.toml"
    make_league(LEAGUE, f"[league]\nprofile_rules = ['{missing}']\n")
    result = runner.invoke(check, [str(OFF1), "--league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr == (f"FAIL {missing}: {FILE_NOT_FOUND}\n")


def test_cli_malformed_toml(runner, write_config: WriteConfig) -> None:
    toml = write_config(BROKEN)
    result = runner.invoke(check, [str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == (f"FAIL {toml}: {toml_error(BROKEN)}\n")


# ── --gameplan is gone (check-ppp replaces it) ────────────────────────────────


def test_cli_gameplan_option_rejected(runner) -> None:
    result = runner.invoke(check, [str(OFF1), "--gameplan", str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert "No such option '--gameplan'" in result.stderr


# ── packaging check (real subprocess) ─────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_entry_point_subprocess(config_dir: Path, log_dir: Path) -> None:
    env = {
        **os.environ,
        "ATHC_CONFIG_DIR": str(config_dir),
        "ATHC_LOG_DIR": str(log_dir),
    }
    result = subprocess.run(
        [str(ATHC), "profile", "check", str(OFF1)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "violation(s)" in result.stdout
    assert result.stderr == ""
