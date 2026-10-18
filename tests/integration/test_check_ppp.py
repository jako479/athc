"""Integration tests for `athc check-ppp`.

check-ppp prints exactly what `profile check --gameplan` printed and what
`gameplan check` prints, so its reports are compared to their committed goldens.
Every rule, the league files that name each team's files, and your team come
from the league folder.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli import cli
from athc.cli.check_ppp import check_ppp
from athc.errors import (
    ACCESS_DENIED,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    AthcError,
)
from athc.fbpro98_lge import read_lge
from athc.fbpro98_profile import read_profile
from athc.profile import RuleName, load_rules, validate_profile
from tests.conftest import (
    CATEGORIES_TOML,
    LEAGUE,
    OTHER_LEAGUE,
    PNFL_LABELS,
    athc_toml,
    league_not_found,
    no_league_selected,
    no_rules_configured,
    toml_error,
)
from tests.integration.conftest import (
    COMPAT_OFF_CLEAN,
    DEF1,
    DENVER_PAIRS,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    OFF1,
    PLAYS,
    PNFL_LGE,
    PPP_TREE,
    RULES_TOML,
    TEAM_NAMES,
    BuildLeague,
    lge,
    team,
)
from tests.integration.conftest import DENVER_2049 as DENVER
from tests.integration.conftest import LAS_VEGAS_2049 as LAS_VEGAS

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

# An athc.toml that is not valid TOML.
BROKEN = "[athc\nbroken\n"
PROFILE_FLAG_OFF_TOML = """[gameplan_compatibility]
require_all_profile_categories_in_gameplan = false
"""
TEAM_NOT_SET = (
    "Team is not set. Run 'athc config set team NAME' or pass --team or --all-teams."
)
LEAGUE_LOCATION_HINT = "Run 'athc config set ppp_path FOLDER' or pass the folder."


@pytest.fixture
def full_league(build_league: BuildLeague, write_config: WriteConfig) -> Path:
    """A league with every rule file, selected by `[athc] league` in athc.toml."""
    folder = build_league()
    write_config(athc_toml())
    return folder


# The TST files under their own names, so the goldens apply.
OFF = ("TST-OFF1.prf", "offense.pln")
DEF = ("TST-DEF1.prf", "defense.pln")


def put(folder: Path, *files: Path | tuple[Path, str]) -> Path:
    """Copy each file into `folder` (created), under its own name or the given
    one; return the folder."""
    folder.mkdir(parents=True, exist_ok=True)
    for item in files:
        source, name = item if isinstance(item, tuple) else (item, item.name)
        shutil.copy2(source, folder / name)
    return folder


def run(runner, *paths: Path | str, **kwargs) -> Result:
    return runner.invoke(check_ppp, [str(p) for p in paths], **kwargs)


def golden(*stems: str) -> str:
    """The committed `profile check` / `gameplan check` reports, in order."""
    return "".join(
        (EXPECTED / f"{stem}.report.txt").read_text(encoding="utf-8") for stem in stems
    )


def normalized(result: Result, *paths: Path) -> str:
    """stdout with each full path shortened to its file name, as in the goldens."""
    out = result.stdout
    for path in paths:
        out = out.replace(str(path), path.name)
    return out


def write_toml(tmp_path: Path, text: str, name: str = "rules.toml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def gameplan_rules(tmp_path: Path, *, reverse: bool) -> Path:
    """GP_RULES with `require_all_gameplan_categories_in_profile` set to `reverse`."""
    text = GP_RULES.read_text(encoding="utf-8").replace(
        "require_all_gameplan_categories_in_profile = true",
        f"require_all_gameplan_categories_in_profile = {str(reverse).lower()}",
    )
    return write_toml(tmp_path, text, "gameplan.toml")


def write_bytes(tmp_path: Path, name: str, data: bytes = b"\x00\x01\x02") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def heads(result: Result) -> list[str]:
    """The path of each report's first line, in order."""
    return [
        line.split(": ")[0]
        for line in result.stdout.splitlines()
        if line and not line.startswith(" ") and "file(s) checked" not in line
    ]


def tally(result: Result) -> str:
    """The tally, the last line on stdout."""
    return result.stdout.splitlines()[-1]


# ── arguments: a pair of files, one folder, or none ───────────────────────────


def test_cli_requires_a_path(runner, full_league: Path) -> None:
    """With no path, the run needs a team: no `team`, no team flag."""
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {full_league / 'league.toml'}: {TEAM_NOT_SET}\n"
    assert result.stdout == ""


def test_cli_rejects_a_third_path(runner, full_league: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE, DEF1)
    assert result.exit_code == 2
    assert "unexpected extra argument" in result.stderr


@pytest.mark.parametrize(
    ("extra", "line"),
    [
        ((), None),
        ((DEF1,), f"Got unexpected extra argument ({DEF1})."),
        ((DEF1, GP_DEFENSE), f"Got unexpected extra arguments ({DEF1} {GP_DEFENSE})."),
    ],
    ids=["two", "three", "four"],
)
def test_cli_path_count(
    runner, full_league: Path, extra: tuple[Path, ...], line: str | None
) -> None:
    """Two paths are a pair; a third is Click's own line, with the period."""
    result = run(runner, OFF1, GP_OFFENSE, *extra)
    if line is None:
        assert result.exit_code == 1
        assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(f"Error: {line}\n")


@pytest.mark.parametrize(
    ("path", "line"),
    [
        (
            OFF1,
            "No game plan given. Run 'athc profile check' to check a profile alone.",
        ),
        (
            GP_OFFENSE,
            "No profile given. Run 'athc gameplan check' to check a game plan alone.",
        ),
    ],
    ids=["profile", "game plan"],
)
def test_cli_one_file_is_an_error(
    runner, full_league: Path, path: Path, line: str
) -> None:
    """A profile or a gameplan alone is never checked: the line names the
    command that checks it alone."""
    result = run(runner, path)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {path}: {line}\n"
    assert result.stdout == ""


def test_cli_one_file_of_another_kind_is_an_error(
    runner, full_league: Path, tmp_path: Path
) -> None:
    """One path is a folder argument; a file that is neither a profile nor a game
    plan is not a folder."""
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, wrong)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {wrong}: {DIRECTORY_INVALID} "
        "Pass one profile and one game plan, or a folder.\n"
    )
    assert result.stdout == ""


def test_cli_one_missing_path(runner, full_league: Path, tmp_path: Path) -> None:
    """One path is a folder argument, so a missing one is a missing path."""
    missing = tmp_path / "nope"
    result = run(runner, missing)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {PATH_NOT_FOUND}\n"
    assert result.stdout == ""


def test_cli_team_and_all_teams_together(runner, full_league: Path) -> None:
    result = run(runner, "--team", "Denver", "--all-teams")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team and --all-teams cannot be used together.\n"
    )


@pytest.mark.parametrize(
    "flag", [("--team", "Denver"), ("--all-teams",)], ids=["--team", "--all-teams"]
)
def test_cli_team_flag_with_two_files(
    runner, full_league: Path, flag: tuple[str, ...]
) -> None:
    result = run(runner, *flag, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team and --all-teams cannot be used with files.\n"
    )
    assert result.stdout == ""


def test_help_shows_the_team_options(runner) -> None:
    result = run(runner, "--help")
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())  # the help text wraps
    assert "Usage: check-ppp [OPTIONS] [PATH]..." in output
    assert "--team NAME Team to check (default: team in league.toml)." in output
    assert "-a, --all-teams Every team in the league." in output


# ── both files ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prof,gameplan,stems",
    [
        (OFF1, GP_OFFENSE, ("compat_offense", "offense")),
        (DEF1, GP_DEFENSE, ("compat_defense", "defense")),
    ],
)
def test_cli_both_matches_existing_reports(
    runner,
    full_league: Path,
    prof: Path,
    gameplan: Path,
    stems: tuple[str, str],
) -> None:
    """With both compatibility settings on, as in the test rules (the profile
    rules' `[gameplan_compatibility]` and the gameplan rules'
    `[profile_compatibility]`): profile report with its `game plan:` lines (as
    `profile check --gameplan` printed), then the gameplan report (as
    `gameplan check`), then one summary."""
    result = run(runner, prof, gameplan)
    assert result.exit_code == 1
    assert normalized(result, prof, gameplan) == (
        golden(*stems) + "\n2 file(s) checked, 2 with violations, 0 failed\n"
    )


def test_cli_unused_gameplan_categories_are_info(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """With the gameplan rules' `require_all_gameplan_categories_in_profile`
    off, a gameplan category the profile never uses is only an info line and
    does not count; a profile category the gameplan lacks still fails."""
    build_league(gameplan_rules=gameplan_rules(tmp_path, reverse=False))
    write_config(athc_toml())
    result = run(runner, DEF1, GP_DEFENSE)
    assert result.exit_code == 1
    situations = golden("TST-DEF1").splitlines(keepends=True)[1:]
    assert normalized(result, DEF1, GP_DEFENSE) == (
        "TST-DEF1.prf: 7 violation(s), 1 game plan issue(s) (defense, FG range 36)\n"
        + "".join(situations)
        + "  game plan: special-teams category Field Goal/PAT has no custom special play in the game plan\n"
        "  game plan info: special-teams category Fake FG Run is in the game plan but not used by the profile\n"
        "  game plan info: special-teams category Fake FG Pass is in the game plan but not used by the profile\n"
        "  game plan info: special-teams category Fake Punt Run is in the game plan but not used by the profile\n"
        "  game plan info: special-teams category Fake Punt Pass is in the game plan but not used by the profile\n"
        + golden("defense")
        + "\n2 file(s) checked, 2 with violations, 0 failed\n"
    )


def test_cli_file_order_does_not_matter(runner, full_league: Path) -> None:
    profile_first = run(runner, OFF1, GP_OFFENSE)
    gameplan_first = run(runner, GP_OFFENSE, OFF1)
    assert gameplan_first.exit_code == profile_first.exit_code == 1
    assert gameplan_first.stdout == profile_first.stdout


def test_cli_both_clean_exit_0(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_league(
        profile_rules=write_toml(tmp_path, PROFILE_FLAG_OFF_TOML),
        gameplan_rules=gameplan_rules(tmp_path, reverse=False),
    )
    write_config(athc_toml())
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    monkeypatch.setattr(
        "athc.cli.check_ppp.gameplan_extra_categories", lambda prof, gp: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {COMPAT_OFF_CLEAN}: offense, FG range 20; game plan compatible\n"
        f"OK   {GP_OFFENSE}: offense, 64 normal\n"
        "\n2 file(s) checked, 0 with violations, 0 failed\n"
    )


def test_cli_unused_gameplan_categories_alone_exit_0(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both files pass their own rules and the gameplan backs every profile
    category; the 10 gameplan categories the profile never uses are only info,
    reported even with the league's flags off."""
    build_league(
        profile_rules=write_toml(tmp_path, PROFILE_FLAG_OFF_TOML),
        gameplan_rules=gameplan_rules(tmp_path, reverse=False),
    )
    write_config(athc_toml())
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout.startswith(
        f"OK   {COMPAT_OFF_CLEAN}: offense, FG range 20; game plan compatible\n"
        "  game plan info: play category "
    )
    assert result.stdout.count("  game plan info: ") == 10
    assert (
        "  game plan info: play category Run Left is in the game plan but not used by the profile"
        in result.stdout
    )
    assert "2 file(s) checked, 0 with violations, 0 failed" in result.stdout


@pytest.mark.parametrize(
    "forward,reverse,issues,infos,files",
    [
        (True, True, 5, 0, 2),
        (True, False, 1, 4, 2),
        (False, True, 4, 0, 2),
        (False, False, 0, 4, 1),
    ],
)
def test_cli_cross_check_follows_league_settings(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    forward: bool,
    reverse: bool,
    issues: int,
    infos: int,
    files: int,
) -> None:
    """TST-DEF1 vs defense.pln: 1 profile category the gameplan lacks, 4 gameplan
    categories the profile never uses. The first counts only when the profile
    rules' `require_all_profile_categories_in_gameplan` is on; the others count
    when the gameplan rules' `require_all_gameplan_categories_in_profile` is
    on, else they are info lines. `files` is how many files have findings
    (defense.pln always has its own violation)."""
    settings = (
        "[gameplan_compatibility]\n"
        f"require_all_profile_categories_in_gameplan = {str(forward).lower()}\n"
    )
    build_league(
        profile_rules=write_toml(tmp_path, settings),
        gameplan_rules=gameplan_rules(tmp_path, reverse=reverse),
    )
    write_config(athc_toml())
    result = run(runner, DEF1, GP_DEFENSE)
    assert result.exit_code == 1
    assert result.stdout.count("  game plan: ") == issues
    assert result.stdout.count("  game plan info: ") == infos
    assert f"2 file(s) checked, {files} with violations, 0 failed" in result.stdout


# ── side mismatch ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prof,gameplan,sides",
    [
        (OFF1, GP_DEFENSE, "Profile is offense but game plan is defense."),
        (DEF1, GP_OFFENSE, "Profile is defense but game plan is offense."),
    ],
)
def test_cli_side_mismatch_stops_the_checks(
    runner, full_league: Path, prof: Path, gameplan: Path, sides: str
) -> None:
    """A mismatch is an error like a setup error: no file is checked and there
    is no summary, only the mismatch line."""
    result = run(runner, prof, gameplan)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.endswith(f"FAIL {prof}: {sides}\n")


# ── input errors (logged; every one reported; nothing checked) ────────────────


def test_cli_missing_file(runner, full_league: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nope.prf"
    result = run(runner, missing, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_cli_reports_every_input_error(
    runner, full_league: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.prf"
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, missing, wrong)
    assert result.exit_code == 2
    assert f"FAIL {missing}: {FILE_NOT_FOUND}" in result.stderr
    assert f"FAIL {wrong}: Not a .prf or .pln file." in result.stderr


def test_cli_wrong_extension(runner, full_league: Path, tmp_path: Path) -> None:
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, OFF1, wrong)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {wrong}: Not a .prf or .pln file.\n"
    assert result.stdout == ""


def test_cli_directory_next_to_a_file_is_not_a_file(
    runner, full_league: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "profiles.prf"
    folder.mkdir()
    result = run(runner, folder, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: {ACCESS_DENIED}\n"
    assert result.stdout == ""


def test_cli_extension_is_case_insensitive(
    runner, full_league: Path, tmp_path: Path
) -> None:
    prof = tmp_path / "OFF.PRF"
    gameplan = tmp_path / "OFF.PLN"
    shutil.copy2(OFF1, prof)
    shutil.copy2(GP_OFFENSE, gameplan)
    result = run(runner, prof, gameplan)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.parametrize(
    "first,second,kind", [(OFF1, DEF1, ".prf"), (GP_OFFENSE, GP_DEFENSE, ".pln")]
)
def test_cli_second_file_of_a_kind_is_an_error(
    runner,
    full_league: Path,
    first: Path,
    second: Path,
    kind: str,
) -> None:
    """Both are required, so neither file is checked."""
    result = run(runner, first, second)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {second}: Second {kind} file. Pass one profile and one game plan.\n"
    )
    assert result.stdout == ""


def test_cli_bad_input_checks_nothing(
    runner, full_league: Path, tmp_path: Path
) -> None:
    """The good profile is not checked alone: both files are required."""
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, OFF1, wrong)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {wrong}: Not a .prf or .pln file.\n"
    assert result.stdout == ""


# ── unreadable files (not a profile / not a gameplan) ─────────────────────────


@pytest.mark.parametrize(
    "source,name,partner",
    [
        (OFF1, "really_a_profile.pln", OFF1),
        (GP_OFFENSE, "really_a_plan.prf", GP_OFFENSE),
    ],
)
def test_cli_file_of_the_other_kind_is_an_error(
    runner, full_league: Path, tmp_path: Path, source: Path, name: str, partner: Path
) -> None:
    """A .pln that holds a profile is not a gameplan (and the reverse)."""
    fake = tmp_path / name
    shutil.copy2(source, fake)
    result = run(runner, fake, partner)
    assert result.exit_code == 2
    assert f"FAIL {fake}: " in result.stderr


def test_cli_bad_profile_still_checks_gameplan(
    runner, full_league: Path, tmp_path: Path
) -> None:
    bad = write_bytes(tmp_path, "broken.prf")
    result = run(runner, bad, GP_OFFENSE)
    assert result.exit_code == 2
    assert f"FAIL {bad}: File too small to contain F95 block.\n" in result.stderr
    assert result.stderr.count(str(bad)) == 1
    assert normalized(result, GP_OFFENSE) == (
        golden("offense") + "\n2 file(s) checked, 1 with violations, 1 failed\n"
    )


def test_cli_bad_gameplan_still_checks_profile(
    runner, full_league: Path, tmp_path: Path
) -> None:
    """The profile gets its own report; no cross-check without a gameplan."""
    bad = write_bytes(tmp_path, "broken.pln")
    result = run(runner, OFF1, bad)
    assert result.exit_code == 2
    assert (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
        in result.stderr
    )
    assert result.stderr.count(str(bad)) == 1
    assert normalized(result, OFF1) == (
        golden("TST-OFF1") + "\n2 file(s) checked, 1 with violations, 1 failed\n"
    )


def test_cli_bad_gameplan_clean_profile_is_ok(
    runner, full_league: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no gameplan to cross-check, a clean profile reads as plain OK."""
    monkeypatch.setattr("athc.cli.check_ppp.validate_profile", lambda prof, rules: ())
    bad = write_bytes(tmp_path, "broken.pln")
    result = run(runner, OFF1, bad)
    assert result.exit_code == 2
    assert result.stdout.splitlines()[0] == f"OK   {OFF1}: offense, FG range 36"
    assert f"FAIL {bad}: " in result.stderr


def test_cli_both_unreadable_reports_both(
    runner, full_league: Path, tmp_path: Path
) -> None:
    bad_prof = write_bytes(tmp_path, "broken.prf")
    bad_plan = write_bytes(tmp_path, "broken.pln")
    result = run(runner, bad_prof, bad_plan)
    assert result.exit_code == 2
    assert f"FAIL {bad_prof}: " in result.stderr
    assert f"FAIL {bad_plan}: " in result.stderr
    assert "2 file(s) checked, 0 with violations, 2 failed" in result.stdout


# ── league / rules config ─────────────────────────────────────────────────────


def test_cli_no_league(runner, config_dir: Path) -> None:
    """Both sides need the league; the error is logged once."""
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)
    assert result.stdout == ""


def test_cli_rules_from_league_set_in_athc_toml(runner, full_league: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_cli_no_profile_rules_in_league(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    build_league(profile_rules=None)
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_cli_no_gameplan_rules_in_league(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    build_league(gameplan_rules=None)
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("gameplan.toml")
    assert result.stdout == ""


def test_cli_rules_error_stops_before_the_files(
    runner, build_league: BuildLeague, write_config: WriteConfig
) -> None:
    """A setup problem stops the run before any file is read: no side-mismatch
    line, no report, no summary."""
    build_league(profile_rules=None)
    write_config(athc_toml())
    result = run(runner, OFF1, GP_DEFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_cli_config_error_stops_before_the_files(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    bad = write_bytes(tmp_path, "broken.pln")
    result = run(runner, OFF1, bad)
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)
    assert result.stdout == ""


def test_cli_first_config_error_stops_the_run(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """No rules for either side and no play pool: the first problem found is
    the one reported."""
    build_league(profile_rules=None, gameplan_rules=None, play_path=tmp_path / "nope")
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_cli_no_play_path(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    folder = build_league(play_path=None)
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER'.\n"
    )


def test_cli_play_path_not_a_directory(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
) -> None:
    build_league(play_path=tmp_path / "nope")
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'nope'}: {PATH_NOT_FOUND} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


@pytest.mark.parametrize("side", ["profile", "gameplan"])
def test_cli_bad_rules_toml(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    side: str,
) -> None:
    """Bad rules for one side; neither file is checked."""
    bad = write_toml(tmp_path, "not = valid = toml")
    folder = build_league(**{f"{side}_rules": bad})  # copied in as <side>.toml
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / f'{side}.toml'}: {toml_error('not = valid = toml')}\n"
    )
    assert result.stdout == ""


def test_cli_profile_allowed_lists_use_the_league_labels(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """The profile rules' allowed lists are read with the labels in the
    league's league.toml; without them `RM` would not load."""
    rules = write_toml(tmp_path, 'allowed_offensive_categories = ["RM"]\n')
    build_league(profile_rules=rules)
    write_config(athc_toml())
    banned = [
        f"  [situation {v.situation_number}] {v.message}"
        for v in validate_profile(
            read_profile(OFF1), load_rules([rules], labels=PNFL_LABELS)
        )
        if v.rule_name is RuleName.OFFENSE_DISALLOWED_CATEGORY
    ]
    assert banned
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert [line for line in lines if "uses banned categories" in line] == banned


def test_cli_rule_lists_in_league_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """`profile_rules` / `gameplan_rules` lists replace the fixed files."""
    folder = make_league(
        LEAGUE,
        f"[league]\nplay_path = '{PLAYS}'\n"
        "profile_rules = ['my-profile.toml']\n"
        "gameplan_rules = ['my-gameplan.toml']\n" + CATEGORIES_TOML,
    )
    shutil.copy(RULES_TOML, folder / "my-profile.toml")
    shutil.copy(GP_RULES, folder / "my-gameplan.toml")
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.parametrize("key", ["profile_rules", "gameplan_rules"])
def test_cli_missing_listed_rules_file(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    key: str,
) -> None:
    folder = build_league()
    (folder / "league.toml").write_text(
        f"[league]\nplay_path = '{PLAYS}'\n{key} = ['gone.toml']\n" + CATEGORIES_TOML,
        encoding="utf-8",
    )
    write_config(athc_toml())
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    gone = folder / "gone.toml"
    assert result.stderr == f"FAIL {gone}: {FILE_NOT_FOUND}\n"


def test_cli_malformed_toml(
    runner,
    full_league: Path,
    write_config: WriteConfig,
) -> None:
    toml = write_config(BROKEN)
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (f"FAIL {toml}: {toml_error(BROKEN)}\n")
    assert result.stdout == ""


# ── a directory: the league file's pairs ──────────────────────────────────────


def test_dir_checks_each_pair_in_league_file_order(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Offense first, as the .lg2 lists it (by name, defense would sort first);
    each pair reads exactly as two-file mode prints it."""
    lg2_league(team(off1=OFF, def1=DEF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    files = [folder / p.name for p in (OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("compat_offense", "offense", "compat_defense", "defense")
        + "\n4 file(s) checked, 4 with violations, 0 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_clean_exit_0(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lg2_league(team(off1=("compat_off_clean.prf", "offense.pln")))
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    monkeypatch.setattr("athc.cli.check_ppp.validate_profile", lambda prof, rules: ())
    monkeypatch.setattr(
        "athc.cli.check_ppp.gameplan_extra_categories", lambda prof, gp: ()
    )
    folder = put(tmp_path / "plans", COMPAT_OFF_CLEAN, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {folder / 'compat_off_clean.prf'}: offense, FG range 20; "
        "game plan compatible\n"
        f"OK   {folder / 'offense.pln'}: offense, 64 normal\n"
        "\n2 file(s) checked, 0 with violations, 0 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_teams_in_league_file_order(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(def1=DEF), team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    files = [folder / p.name for p in (OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("compat_defense", "defense", "compat_offense", "offense")
        + "\n4 file(s) checked, 4 with violations, 0 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_second_half_pairs(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off2=OFF, def2=DEF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert "4 file(s) checked, 4 with violations, 0 failed" in result.stdout


def test_dir_names_ignore_case(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=("TST-OFF1.PRF", "OFFENSE.PLN")))
    folder = put(tmp_path / "plans", (OFF1, "tst-off1.prf"), GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert result.stdout.startswith(f"{folder / 'tst-off1.prf'}: ")
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_dir_half_a_pair_is_skipped(runner, lg2_league, tmp_path: Path) -> None:
    """TST-OFF1.prf's gameplan is not there: the profile is checked alone, its
    gameplan a `WARN` where its report would be, counted as missing."""
    lg2_league(team(off1=OFF, def1=DEF))
    folder = put(tmp_path / "plans", OFF1, DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert f"WARN {folder / 'offense.pln'}: {FILE_NOT_FOUND}\n" in result.stderr
    files = [folder / p.name for p in (OFF1, DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("TST-OFF1", "compat_defense", "defense")
        + "\n3 file(s) checked, 3 with violations, 0 failed, 1 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_unlisted_files_are_ignored(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, (GP_DEFENSE, "spare.pln"))
    result = run(runner, "--all-teams", folder)
    files = [folder / p.name for p in (OFF1, GP_OFFENSE)]
    assert normalized(result, *files) == (
        golden("compat_offense", "offense")
        + "\n2 file(s) checked, 2 with violations, 0 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_shared_gameplan_is_reported_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    """One gameplan for both halves: its own report prints once, while each
    profile gets its own cross-check against it."""
    lg2_league(team(off1=OFF, off2=("compat_off_clean.prf", "offense.pln")))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, COMPAT_OFF_CLEAN)
    result = run(runner, "--all-teams", folder)
    files = [folder / p.name for p in (OFF1, GP_OFFENSE, COMPAT_OFF_CLEAN)]
    pair = normalized(
        run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE), COMPAT_OFF_CLEAN, GP_OFFENSE
    )
    clean_report = pair[: pair.index("\noffense.pln: ") + 1]
    assert normalized(result, *files).startswith(
        golden("compat_offense", "offense") + clean_report + "\n3 file(s) checked, "
    )


def test_dir_profile_in_two_pairs_is_reported_twice(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Each report holds its own cross-check, so a profile listed with two
    gameplans is reported with each."""
    lg2_league(team(off1=OFF, off2=("TST-OFF1.prf", "other.pln")))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, (GP_OFFENSE, "other.pln"))
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert result.stdout.count(f"{folder / 'TST-OFF1.prf'}: ") == 2
    assert "4 file(s) checked, 4 with violations, 0 failed" in result.stdout


def test_dir_same_pair_twice_is_checked_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    lg2_league(team(off1=OFF), team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_dir_league_file_folders_are_ignored(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Only the file names count; the folder in each .lg2 entry doesn't."""
    lg2_league(team(off1=OFF, folder="Somewhere\\Else"))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    assert run(runner, "--all-teams", folder).exit_code == 1


def test_dir_subfolders_are_not_searched(runner, lg2_league, tmp_path: Path) -> None:
    """No file has to be there, so a team with none is a warning, exit 0."""
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    put(folder / "week1", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 0
    assert result.stdout == (
        "\n0 file(s) checked, 0 with violations, 0 failed, 0 missing, "
        "1 team(s) with no files\n"
    )
    assert result.stderr.endswith(f"WARN {folder}: No files for 1 team(s): Denver.\n")


def test_dir_empty(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 0
    assert result.stdout == (
        "\n0 file(s) checked, 0 with violations, 0 failed, 0 missing, "
        "1 team(s) with no files\n"
    )
    assert result.stderr.endswith(f"WARN {folder}: No files for 1 team(s): Denver.\n")


def test_dir_locked_gameplan_is_access_denied(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gameplan Windows will not open fails in Windows' words."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)

    def locked(path: str) -> None:
        raise PermissionError(13, "Permission denied", path)

    monkeypatch.setattr("athc.cli.check_ppp.read_gameplan", locked)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert f"FAIL {folder / GP_OFFENSE.name}: {ACCESS_DENIED}\n" in result.stderr


def test_dir_expected_error_in_a_pair_is_its_fail_line(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expected error inside one pair's check fails that pair, not the run;
    naming no file of its own, its line names the pair."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)

    def boom(prof: object, rules: object) -> tuple[()]:
        raise AthcError("Rules exploded.")

    monkeypatch.setattr("athc.cli.check_ppp.validate_profile", boom)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    pair = f"{folder / OFF1.name} + {folder / GP_OFFENSE.name}"
    assert result.stderr.splitlines()[-1] == f"FAIL {pair}: Rules exploded."
    assert "unexpected error" not in result.stderr
    assert result.stdout.endswith(
        "0 file(s) checked, 0 with violations, 1 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_setup_error_stops_before_the_pairs(
    runner, lg2_league, tmp_path: Path
) -> None:
    """The setup error stops the run before the folder is even looked at."""
    lg2_league(team(off1=OFF), profile_rules=None)
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def deny(monkeypatch: pytest.MonkeyPatch, locked: Path) -> str:
    """Make `Path.walk` unable to read `locked`, as `os.scandir` would fail on
    it: the error goes to `on_error` when given, and the folder is never
    yielded. Returns the error text."""
    message = f"[WinError 5] Access is denied: '{locked}'"
    real_walk = Path.walk

    def walk(self: Path, top_down=True, on_error=None, follow_symlinks=False):
        for folder, subfolders, filenames in real_walk(
            self, top_down, on_error, follow_symlinks
        ):
            if folder == locked:
                if on_error is not None:
                    on_error(PermissionError(message))
                subfolders.clear()
                continue
            yield folder, subfolders, filenames

    monkeypatch.setattr(Path, "walk", walk)
    return message


def test_dir_unreadable_directory_has_no_pairs(
    runner,
    lg2_league,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipped like `os.walk` does, so it reads as a folder with no files."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    message = deny(monkeypatch, folder)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 0
    assert result.stdout == (
        "\n0 file(s) checked, 0 with violations, 0 failed, 0 missing, "
        "1 team(s) with no files\n"
    )
    assert message not in result.stderr
    assert f"WARN {folder}: No files for 1 team(s): Denver.\n" in result.stderr


def test_dir_side_mismatch_is_that_pairs_error(
    runner, lg2_league, tmp_path: Path
) -> None:
    """The mismatched pair gets its error line and the rest still run; the
    gameplan it shares with a later pair is reported there."""
    lg2_league(team(off1=("TST-OFF1.prf", "defense.pln"), def1=DEF))
    folder = put(tmp_path / "plans", OFF1, DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    files = [folder / p.name for p in (OFF1, DEF1, GP_DEFENSE)]
    assert (
        f"FAIL {folder / 'TST-OFF1.prf'}: Profile is offense but game plan is defense."
        in result.stderr
    )
    assert normalized(result, *files) == (
        golden("compat_defense", "defense")
        + "\n3 file(s) checked, 2 with violations, 1 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_unreadable_file(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=("broken.prf", "offense.pln")))
    folder = put(tmp_path / "plans", GP_OFFENSE)
    bad = write_bytes(folder, "broken.prf")
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert f"FAIL {bad}: " in result.stderr
    assert normalized(result, folder / "offense.pln") == (
        golden("offense")
        + "\n2 file(s) checked, 1 with violations, 1 failed, 0 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_unreadable_shared_gameplan_is_reported_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Each profile still gets its report, with no cross-check."""
    lg2_league(team(off1=("TST-OFF1.prf", "broken.pln"), off2=("x.prf", "broken.pln")))
    folder = put(tmp_path / "plans", OFF1, (OFF1, "x.prf"))
    bad = write_bytes(folder, "broken.pln")
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert result.stderr.count(f"FAIL {bad}: ") == 1
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "x.prf")]
    assert "3 file(s) checked, 2 with violations, 1 failed" in result.stdout


def test_dir_setup_error_stops_before_the_files(
    runner, lg2_league, tmp_path: Path
) -> None:
    """No profile rules: the run stops there; neither the mismatch nor the
    unreadable file is looked at."""
    lg2_league(
        team(off1=("TST-OFF1.prf", "defense.pln"), def1=("broken.prf", "defense.pln")),
        profile_rules=None,
    )
    folder = put(tmp_path / "plans", OFF1, GP_DEFENSE)
    write_bytes(folder, "broken.prf")
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_dir_no_league(runner, config_dir: Path, tmp_path: Path) -> None:
    """Every setup piece needs the league; the error is logged once."""
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)
    assert result.stdout == ""


def test_dir_no_path(runner, full_league: Path, tmp_path: Path) -> None:
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert (
        f"FAIL {full_league / 'league.toml'}: League files folder is not set. "
        "Run 'athc config set path FOLDER' or pass the folder." in result.stderr
    )
    assert result.stdout == ""


def test_dir_first_setup_error_stops_the_run(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """No team, no `path` and no profile rules: `team` is read first."""
    folder = build_league(profile_rules=None)  # and no `path` or `team` either
    write_config(athc_toml())
    plans = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, plans)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'league.toml'}: {TEAM_NOT_SET}\n"


def test_dir_bad_league_file(runner, lg2_league, tmp_path: Path) -> None:
    lg2 = lg2_league(b"\x00\x01\x02")
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert "not a whole number" in result.stderr and str(lg2) in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "lg2_folder", ["", "STOCK\x00A\\FBPRO97\\STOCK"], ids=["old", "modern"]
)
def test_dir_stock_league_file(
    runner, lg2_league, tmp_path: Path, lg2_folder: str
) -> None:
    """Every kind of stock league gets the same one line."""
    lg2 = lg2_league(team(off1=OFF, folder=lg2_folder))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert f"FAIL {lg2}: Stock league not supported.\n" in result.stderr
    assert result.stdout == ""


def test_dir_league_file_missing(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
) -> None:
    """`path` is set, but the league's .lg2 isn't in that folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    build_league(path=lg2_dir)
    write_config(athc_toml())
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 2
    assert f"{LEAGUE}.lg2" in result.stderr
    assert result.stdout == ""


def test_dir_relative_path_is_in_the_league_folder(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    folder = build_league(path="lg2")
    (folder / "lg2").mkdir()
    (folder / "lg2" / f"{LEAGUE}.lg2").write_bytes(team(off1=OFF))
    (folder / "lg2" / f"{LEAGUE}.lge").write_bytes(lge(TEAM_NAMES[0]))
    write_config(athc_toml())
    plans = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", plans)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


# ── a folder: missing files and teams with none ───────────────────────────────


def test_dir_missing_partner_keeps_the_code(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `WARN` never changes the exit code: the game plan alone is clean."""
    lg2_league(team(off1=("compat_off_clean.prf", "offense.pln")))
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    folder = put(tmp_path / "plans", GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 0
    assert (
        f"WARN {folder / 'compat_off_clean.prf'}: {FILE_NOT_FOUND}\n" in result.stderr
    )
    assert result.stdout == (
        f"OK   {folder / 'offense.pln'}: offense, 64 normal\n"
        "\n1 file(s) checked, 0 with violations, 0 failed, 1 missing, "
        "0 team(s) with no files\n"
    )


def test_dir_shared_gameplan_missing_once(runner, lg2_league, tmp_path: Path) -> None:
    """A game plan two pairs share is noted missing once; each profile is
    checked alone."""
    lg2_league(team(off1=OFF, off2=("x.prf", "offense.pln")))
    folder = put(tmp_path / "plans", OFF1, (OFF1, "x.prf"))
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert result.stderr.count(f"WARN {folder / 'offense.pln'}: ") == 1
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "x.prf")]
    assert tally(result) == (
        "2 file(s) checked, 2 with violations, 0 failed, 1 missing, "
        "0 team(s) with no files"
    )


def test_dir_whole_pair_missing_prints_nothing(
    runner, lg2_league, tmp_path: Path
) -> None:
    lg2_league(team(off1=OFF, def1=DEF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert "TST-DEF1.prf" not in result.stderr + result.stdout
    assert "defense.pln" not in result.stderr + result.stdout
    assert tally(result) == (
        "2 file(s) checked, 2 with violations, 0 failed, 0 missing, "
        "0 team(s) with no files"
    )


def test_dir_missing_file_in_league_file_spelling(
    runner, lg2_league, tmp_path: Path
) -> None:
    """A found file prints its on-disk name; a missing one the league file's."""
    lg2_league(team(off1=("TST-OFF1.PRF", "OFFENSE.PLN")))
    folder = put(tmp_path / "plans", GP_OFFENSE)
    result = run(runner, "--all-teams", folder)
    assert f"WARN {folder / 'TST-OFF1.PRF'}: {FILE_NOT_FOUND}\n" in result.stderr
    assert heads(result) == [str(folder / "offense.pln")]


@pytest.mark.parametrize("others", [True, False], ids=["others' files", "empty"])
def test_dir_your_team_with_no_files(
    runner, lg2_league, tmp_path: Path, others: bool
) -> None:
    """One team with no file in the folder: one `WARN` with the names the
    league file gives its files, whether other teams' files are there or not."""
    lg2_league(team(off1=OFF), team(def1=DEF), team="Las Vegas")
    folder = tmp_path / "plans"
    folder.mkdir()
    if others:
        put(folder, OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 0
    assert result.stderr.endswith(
        f"WARN {folder}: No Las Vegas files. The league file names none-o1.prf, "
        "none-o1.pln, TST-DEF1.prf, defense.pln, none-o2.prf, none-o2.pln, "
        "none-d2.prf, none-d2.pln.\n"
    )
    assert (
        result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed, 0 missing\n"
    )


def test_dir_no_files_names_each_file_once(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    """Las Vegas uses one game plan per side for both halves."""
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, "--team", "Las Vegas", folder)
    assert result.stderr.endswith(
        f"WARN {folder}: No Las Vegas files. The league file names LVOFF1.prf, "
        "RAIDEROFF.pln, LVDEF1.prf, RAIDERDEF.pln, LVOFF2.prf, LVDEF2.prf.\n"
    )


def test_dir_all_teams_with_no_files_on_one_line(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Every team with no file, in `.lge` order, on one line."""
    lg2_league(team(), team(def1=DEF), team())
    folder = put(tmp_path / "plans", DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", folder)
    assert result.exit_code == 1
    assert result.stderr.endswith(
        f"WARN {folder}: No files for 2 team(s): Denver, Jacksonville.\n"
    )
    assert tally(result) == (
        "2 file(s) checked, 2 with violations, 0 failed, 0 missing, "
        "2 team(s) with no files"
    )


def test_dir_all_teams_real_league(runner, pnfl_league: Path) -> None:
    lge_teams = read_lge("PNFL", PNFL_LGE.parent).teams
    others = ", ".join(t.name for t in lge_teams if t.name != "Denver")
    result = run(runner, "--all-teams", DENVER)
    assert result.stderr.endswith(
        f"WARN {DENVER}: No files for 17 team(s): {others}.\n"
    )
    assert tally(result).endswith(", 0 missing, 17 team(s) with no files")


def test_tree_is_the_scope_for_no_files(runner, lg2_league, tmp_path: Path) -> None:
    """With `-r` the team's files anywhere in the tree count; with none in it,
    the one `WARN` names the top folder."""
    lg2_league(team(off1=OFF), team(), team="Denver")
    folder = tmp_path / "plans"
    week1 = put(folder / "week1", OFF1, GP_OFFENSE)
    found = run(runner, "-r", folder)
    assert "No Denver files" not in found.stderr
    assert heads(found) == [str(week1 / "TST-OFF1.prf"), str(week1 / "offense.pln")]
    other = run(runner, "-r", "--team", "Las Vegas", folder)
    assert other.stderr.count("No Las Vegas files.") == 1
    assert f"WARN {folder}: No Las Vegas files." in other.stderr


# ── a tree (-r): each folder on its own ───────────────────────────────────────


def test_tree_finds_pairs_in_subfolders(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    put(folder / "week1", OFF1, GP_OFFENSE)
    result = run(runner, "--all-teams", "-r", folder)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_tree_folder_order(runner, lg2_league, tmp_path: Path) -> None:
    """The top folder first, then each subfolder (and its own subfolders) by
    name, ignoring case. `_x` sorts first by name, though Windows lists it
    after the letters, so the order is athc's, not the file system's."""
    lg2_league(team(off1=OFF, def1=DEF))
    top = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    upper = put(top / "B week", DEF1, GP_DEFENSE)
    lower = put(top / "a week", OFF1, GP_OFFENSE)
    nested = put(lower / "z", DEF1, GP_DEFENSE)
    underscore = put(top / "_x", DEF1, GP_DEFENSE)
    result = run(runner, "--all-teams", top, "-r")
    assert heads(result) == [
        str(top / "TST-OFF1.prf"),
        str(top / "offense.pln"),
        str(underscore / "TST-DEF1.prf"),
        str(underscore / "defense.pln"),
        str(lower / "TST-OFF1.prf"),
        str(lower / "offense.pln"),
        str(nested / "TST-DEF1.prf"),
        str(nested / "defense.pln"),
        str(upper / "TST-DEF1.prf"),
        str(upper / "defense.pln"),
    ]
    assert "10 file(s) checked, 10 with violations, 0 failed" in result.stdout


def test_tree_pair_split_across_folders_is_not_found(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Weeks and seasons reuse the same names, so a pair is never matched
    across folders: each half is checked alone in its own folder, its partner
    a `WARN`."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1)
    week1 = put(folder / "week1", GP_OFFENSE)
    result = run(runner, "--all-teams", "-r", folder)
    assert result.exit_code == 1
    assert f"WARN {folder / 'offense.pln'}: {FILE_NOT_FOUND}\n" in result.stderr
    assert f"WARN {week1 / 'TST-OFF1.prf'}: {FILE_NOT_FOUND}\n" in result.stderr
    assert normalized(result, folder / OFF1.name, week1 / GP_OFFENSE.name) == (
        golden("TST-OFF1", "offense")
        + "\n2 file(s) checked, 2 with violations, 0 failed, 2 missing, "
        "0 team(s) with no files\n"
    )


def test_tree_unreadable_folder_is_skipped(
    runner,
    lg2_league,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Like `os.walk`: no message, and the rest of the tree is checked."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    locked = put(folder / "locked", OFF1, GP_OFFENSE)
    message = deny(monkeypatch, locked)
    result = run(runner, "--all-teams", "-r", folder)
    assert result.exit_code == 1
    assert message not in result.stderr
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "offense.pln")]
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_tree_flag_with_two_files_is_ignored(runner, full_league: Path) -> None:
    result = run(runner, "-r", OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


# ── league files: the .lg2 and the .lge ───────────────────────────────────────


def test_league_lge_missing(runner, lg2_league, tmp_path: Path) -> None:
    lg2 = lg2_league(team(off1=OFF))
    lg2.with_suffix(".lge").unlink()
    result = run(runner, "--all-teams", tmp_path)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2.with_suffix('.lge')}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("record", "line"),
    [
        (b"\x00\x01\x02", "is not a whole number"),
        (team(folder=""), "Stock league not supported."),
    ],
    ids=["bad", "stock"],
)
def test_league_lg2_errors_come_first(
    runner, lg2_league, tmp_path: Path, record: bytes, line: str
) -> None:
    """The .lg2 is read, and judged, before the .lge."""
    lg2 = lg2_league(record)
    lg2.with_suffix(".lge").unlink()
    result = run(runner, "--all-teams", tmp_path)
    assert result.exit_code == 2
    assert result.stderr.startswith(f"FAIL {lg2}: ")
    assert line in result.stderr
    assert ".lge" not in result.stderr


@pytest.mark.parametrize(
    ("lg2_teams", "line"),
    [
        (2, None),
        (1, f"Lists 1 team(s), but {LEAGUE}.lge has 2."),
        (3, f"Lists 3 team(s), but {LEAGUE}.lge has 2."),
    ],
    ids=["equal", "one fewer", "one more"],
)
def test_league_team_counts(
    runner, lg2_league, tmp_path: Path, lg2_teams: int, line: str | None
) -> None:
    """The two league files must list the same teams."""
    lg2 = lg2_league(*(team() for _ in range(lg2_teams)), names=TEAM_NAMES[:2])
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, "--all-teams", folder)
    if line is None:
        assert result.exit_code == 0
        assert tally(result).endswith(", 2 team(s) with no files")
    else:
        assert result.exit_code == 2
        assert result.stderr == f"FAIL {lg2}: {line}\n"


# ── the team: `team`, --team, --all-teams ─────────────────────────────────────

# Denver's files in .lg2 order (DENVER_PAIRS, in conftest.py), pair by pair.
DENVER_FILES = [name for pair in DENVER_PAIRS for name in pair]
# Las Vegas uses one gameplan per side for both halves.
LAS_VEGAS_PAIRS = [
    ("LVOFF1.prf", "RAIDEROFF.pln"),
    ("LVDEF1.prf", "RAIDERDEF.pln"),
    ("LVOFF2.prf", "RAIDEROFF.pln"),
    ("LVDEF2.prf", "RAIDERDEF.pln"),
]
LAS_VEGAS_HEADS = [
    "LVOFF1.prf",
    "RAIDEROFF.pln",
    "LVDEF1.prf",
    "RAIDERDEF.pln",
    "LVOFF2.prf",
    "LVDEF2.prf",
]


def at_league(tmp_path: Path, team_folder: str) -> Path:
    """A team's league location in `pnfl_league`: where PNFL.lg2 puts its files."""
    return tmp_path / "lg2" / "PNFL" / "2049" / "Plans" / team_folder


def denver_heads(folder: Path) -> list[str]:
    return [str(folder / name) for name in DENVER_FILES]


def lge_names() -> str:
    """Every team of PNFL.lge by both names, as the no-match lines list them."""
    teams = read_lge("PNFL", PNFL_LGE.parent).teams
    return ", ".join(t.official_name for t in teams)


@pytest.mark.parametrize("source", ["team", "--team"])
@pytest.mark.parametrize(
    "name", ["Denver", "Broncos", "Denver Broncos", "dENVER bRONCOS"]
)
def test_team_by_name_nickname_or_both(
    runner, pnfl_league: Path, tmp_path: Path, source: str, name: str
) -> None:
    """The team name, the nickname or both, without case."""
    if source == "team":
        set_league(pnfl_league, team=name)
        result = run(runner)
    else:
        result = run(runner, "--team", name)
    assert heads(result) == denver_heads(at_league(tmp_path, "Denver (Brian)"))


def test_team_matches_no_team(runner, pnfl_league: Path) -> None:
    set_league(pnfl_league, team="Denvr")
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {pnfl_league / 'league.toml'}: [league] team: No team named "
        f"'Denvr'. Teams: {lge_names()}.\n"
    )
    assert result.stdout == ""


def test_team_option_matches_no_team(runner, pnfl_league: Path) -> None:
    result = run(runner, "--team", "Denvr")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for '--team': no team named 'Denvr'. Teams: "
        f"{lge_names()}.\n"
    )
    assert result.stdout == ""


NEW_YORK = [("New York", "Giants"), ("New York", "Jets")]


def test_team_matches_two_teams(runner, lg2_league, config_dir: Path) -> None:
    lg2_league(team(), team(), names=NEW_YORK, team="New York")
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {config_dir / 'leagues' / LEAGUE / 'league.toml'}: [league] team: "
        "'New York' matches New York Giants and New York Jets. Use the nickname, "
        "or both names in quotes.\n"
    )


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("Giants", None),
        ("Raiders", "no team named 'Raiders'. Teams: New York Giants, New York Jets."),
        (
            "New York",
            "'New York' matches New York Giants and New York Jets. Use the "
            "nickname, or both names in quotes.",
        ),
    ],
    ids=["one", "none", "two"],
)
def test_team_option_match_count(
    runner, lg2_league, tmp_path: Path, name: str, error: str | None
) -> None:
    """Exactly one team must match: one is accepted, none or two rejected."""
    lg2_league(team(), team(), names=NEW_YORK)
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, "--team", name, folder)
    if error is None:
        assert result.exit_code == 0
        assert f"WARN {folder}: No New York files." in result.stderr
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(f"Error: Invalid value for '--team': {error}\n")


def test_team_blank_is_not_set(runner, lg2_league, config_dir: Path) -> None:
    lg2_league(team(), team="  ")
    result = run(runner)
    assert result.exit_code == 2
    toml = config_dir / "leagues" / LEAGUE / "league.toml"
    assert result.stderr == f"FAIL {toml}: {TEAM_NOT_SET}\n"


def test_team_array(runner, pnfl_league: Path) -> None:
    toml = pnfl_league / "league.toml"
    text = toml.read_text(encoding="utf-8")
    text = text.replace("[league]\n", "[league]\nteam = ['Denver']\n")
    toml.write_text(text, encoding="utf-8")
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {toml}: [league] team: Expected a string, got an array.\n"
    )


def test_team_option_beats_team(runner, pnfl_league: Path, tmp_path: Path) -> None:
    set_league(pnfl_league, team="Denver")
    result = run(runner, "--team", "Las Vegas")
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    assert heads(result) == [str(folder / name) for name in LAS_VEGAS_HEADS]


@pytest.mark.parametrize("setting", [None, "Denvr"], ids=["unset", "no match"])
def test_team_option_without_your_team(
    runner, pnfl_league: Path, tmp_path: Path, setting: str | None
) -> None:
    """`team` unset or naming no team: `--team` still works, at the league
    locations."""
    if setting is not None:
        set_league(pnfl_league, team=setting)
    result = run(runner, "--team", "Denver")
    assert "FAIL " not in result.stderr
    assert heads(result) == denver_heads(at_league(tmp_path, "Denver (Brian)"))


# ── where the files come from: PATH, ppp_path, the league locations ──────────


def test_source_ppp_path(runner, pnfl_league: Path) -> None:
    set_league(pnfl_league, team="Denver", ppp_path=DENVER)
    result = run(runner)
    assert heads(result) == denver_heads(DENVER)
    assert tally(result).endswith(", 0 missing")


def test_source_league_locations_without_ppp_path(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    set_league(pnfl_league, team="Denver")
    result = run(runner)
    assert heads(result) == denver_heads(at_league(tmp_path, "Denver (Brian)"))
    assert re.fullmatch(
        r"8 file\(s\) checked, \d+ with violations, 0 failed", tally(result)
    )


def test_source_current_folder(
    runner, pnfl_league: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`.` is the current folder, even with `ppp_path` set."""
    set_league(pnfl_league, team="Denver", ppp_path=LAS_VEGAS)
    monkeypatch.chdir(DENVER)
    result = run(runner, ".")
    assert heads(result) == DENVER_FILES


def test_source_folder(runner, pnfl_league: Path) -> None:
    set_league(pnfl_league, team="Denver", ppp_path=LAS_VEGAS)
    result = run(runner, DENVER)
    assert heads(result) == denver_heads(DENVER)


@pytest.mark.parametrize(
    ("flags", "heads_in"),
    [
        (("--team", "Broncos"), "ppp_path"),
        (("--team", "Las Vegas"), "league"),
        (("--all-teams",), "league"),
    ],
    ids=["your team", "another team", "all teams"],
)
def test_source_ppp_path_is_for_your_team(
    runner,
    pnfl_league: Path,
    tmp_path: Path,
    flags: tuple[str, ...],
    heads_in: str,
) -> None:
    set_league(pnfl_league, team="Denver", ppp_path=DENVER)
    result = run(runner, *flags)
    shown = heads(result)
    if heads_in == "ppp_path":
        assert shown == denver_heads(DENVER)
    else:
        assert all(head.startswith(str(tmp_path / "lg2")) for head in shown)
        assert shown


def test_source_relative_ppp_path(runner, pnfl_league: Path) -> None:
    mine = put(pnfl_league / "mine", *(DENVER / name for name in DENVER_FILES))
    set_league(pnfl_league, team="Denver", ppp_path="mine")
    result = run(runner)
    assert heads(result) == denver_heads(mine)


@pytest.mark.parametrize("exists", [False, True], ids=["missing", "a file"])
def test_source_ppp_path_not_a_folder(
    runner, pnfl_league: Path, tmp_path: Path, exists: bool
) -> None:
    ppp_path = tmp_path / "mine"
    if exists:
        ppp_path.write_text("x", encoding="utf-8")
    set_league(pnfl_league, team="Denver", ppp_path=ppp_path)
    result = run(runner)
    reason = DIRECTORY_INVALID if exists else PATH_NOT_FOUND
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {ppp_path}: {reason} Run 'athc config set ppp_path FOLDER'.\n"
    )
    assert result.stdout == ""


# ── the league locations: where the league file puts each file ───────────────


def test_league_one_file_missing(runner, pnfl_league: Path, tmp_path: Path) -> None:
    """A `FAIL`, counted as failed; its partner is checked alone."""
    set_league(pnfl_league, team="Denver")
    folder = at_league(tmp_path, "Denver (Brian)")
    (folder / "DEN-OGP2.pln").unlink()
    result = run(runner)
    assert result.exit_code == 2
    assert f"FAIL {folder / 'DEN-OGP2.pln'}: {FILE_NOT_FOUND}\n" in result.stderr
    assert heads(result) == [
        h for h in denver_heads(folder) if not h.endswith("DEN-OGP2.pln")
    ]
    alone = next(
        line for line in result.stdout.splitlines() if "DEN-OFF2.prf: " in line
    )
    assert "game plan" not in alone
    assert re.fullmatch(
        r"8 file\(s\) checked, \d+ with violations, 1 failed", tally(result)
    )


def test_league_shared_gameplan_missing_once(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    (folder / "RAIDEROFF.pln").unlink()
    result = run(runner, "--team", "Las Vegas")
    assert result.exit_code == 2
    assert result.stderr.count(f"FAIL {folder / 'RAIDEROFF.pln'}: ") == 1
    assert re.fullmatch(
        r"6 file\(s\) checked, \d+ with violations, 1 failed", tally(result)
    )


def test_league_recursive_is_ignored(runner, pnfl_league: Path) -> None:
    set_league(pnfl_league, team="Denver")
    assert heads(run(runner, "-r")) == heads(run(runner))


@pytest.mark.parametrize("present", [False, True], ids=["absent", "empty"])
def test_league_no_files_for_your_team(runner, lg2_league, present: bool) -> None:
    """One line for the team's folder, with the `ppp_path` hint: the run
    checks your team alone."""
    lg2 = lg2_league(team(off1=OFF), team="Denver")
    folder = lg2.parent / "PNFL" / "2049" / "Plans" / "Team"
    if present:
        folder.mkdir(parents=True)
    reason = "No Denver files." if present else PATH_NOT_FOUND
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr.endswith(f"FAIL {folder}: {reason} {LEAGUE_LOCATION_HINT}\n")
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 1 failed\n"


@pytest.mark.parametrize(
    ("teams", "flags", "label", "tail"),
    [
        (1, ("--all-teams",), "Denver", ", 1 team(s) with no files"),
        (2, ("--team", "Las Vegas"), "Las Vegas", ""),
    ],
    ids=["all teams", "another team"],
)
def test_league_no_files_without_the_hint(
    runner, lg2_league, teams: int, flags: tuple[str, ...], label: str, tail: str
) -> None:
    """The hint is for your team alone: not with `--all-teams` or another
    team."""
    lg2 = lg2_league(*(team() for _ in range(teams)), team="Denver")
    folder = lg2.parent / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    result = run(runner, *flags)
    assert result.exit_code == 2
    assert result.stderr.endswith(f"FAIL {folder}: No {label} files.\n")
    assert tally(result) == f"0 file(s) checked, 0 with violations, 1 failed{tail}"


# ── real league data: PNFL.lg2 and a copy of its 2049 plans ───────────────────


def pair_reports(runner, folder: Path, profile: str, gameplan: str) -> list[str]:
    """Two-file mode's report lines for one pair, without the summary."""
    result = run(runner, folder / profile, folder / gameplan)
    return result.stdout.splitlines(keepends=True)[:-2]


def test_real_tree_checks_every_team_folder(runner, pnfl_league: Path) -> None:
    result = run(runner, "--all-teams", "-r", PPP_TREE)
    assert "FAIL " not in result.stderr
    assert heads(result) == [
        *denver_heads(DENVER),
        str(LAS_VEGAS / "LVOFF1.prf"),
        str(LAS_VEGAS / "RAIDEROFF.pln"),
        str(LAS_VEGAS / "LVDEF1.prf"),
        str(LAS_VEGAS / "RAIDERDEF.pln"),
        str(LAS_VEGAS / "LVOFF2.prf"),
        str(LAS_VEGAS / "LVDEF2.prf"),
    ]
    assert "\n14 file(s) checked, " in result.stdout


def test_real_tree_reads_as_two_file_mode(runner, pnfl_league: Path) -> None:
    """Each pair reads exactly as two-file mode prints it; a shared gameplan's
    own report only the first time."""
    result = run(runner, "--all-teams", "-r", PPP_TREE)
    expected: list[str] = []
    for folder, pairs in ((DENVER, DENVER_PAIRS), (LAS_VEGAS, LAS_VEGAS_PAIRS)):
        seen: set[str] = set()
        for profile, gameplan in pairs:
            lines = pair_reports(runner, folder, profile, gameplan)
            if gameplan in seen:  # keep the profile report only
                head = f"{folder / gameplan}: "
                lines = lines[
                    : next(i for i, s in enumerate(lines) if s.startswith(head))
                ]
            seen.add(gameplan)
            expected.extend(lines)
    assert result.stdout.splitlines(keepends=True)[:-2] == expected


def test_real_team_folder_alone(runner, pnfl_league: Path) -> None:
    result = run(runner, "--team", "Denver", DENVER)
    assert heads(result) == denver_heads(DENVER)


# ── --league, ATHC_LEAGUE, registration ───────────────────────────────────────


def test_league_flag_beats_athc_toml(
    runner, build_league: BuildLeague, write_config: WriteConfig
) -> None:
    build_league(LEAGUE, profile_rules=None, gameplan_rules=None)  # would fail
    build_league(OTHER_LEAGUE)
    write_config(athc_toml())
    result = runner.invoke(
        cli, ["check-ppp", str(OFF1), str(GP_OFFENSE), "--league", OTHER_LEAGUE]
    )
    assert result.exit_code == 1


def test_league_flag_picks_the_league_file(
    runner, build_league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """In a folder, `--league` also picks whose league files pair the files:
    both leagues share one folder, each file named after its league."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(team(def1=DEF))
    (lg2_dir / f"{OTHER_LEAGUE}.lg2").write_bytes(team(off1=OFF))
    for name in (LEAGUE, OTHER_LEAGUE):
        (lg2_dir / f"{name}.lge").write_bytes(lge(TEAM_NAMES[0]))
    build_league(LEAGUE, path=lg2_dir)
    build_league(OTHER_LEAGUE, path=lg2_dir)
    write_config(athc_toml())
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = runner.invoke(
        cli, ["check-ppp", str(folder), "--all-teams", "--league", OTHER_LEAGUE]
    )
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "offense.pln")]


def test_athc_league_env_is_ignored(
    runner,
    build_league: BuildLeague,
    config_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_league(OTHER_LEAGUE)
    monkeypatch.setenv("ATHC_LEAGUE", OTHER_LEAGUE)
    result = runner.invoke(cli, ["check-ppp", str(OFF1), str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, OTHER_LEAGUE)


def test_league_flag_unknown_folder(
    runner, full_league: Path, config_dir: Path
) -> None:
    result = runner.invoke(
        cli, ["check-ppp", str(OFF1), str(GP_OFFENSE), "--league", "NOPE"]
    )
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_root_help_lists_check_ppp(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "check-ppp" in result.stdout


# ── packaging check (real subprocess) ─────────────────────────────────────────


def _athc(
    config_dir: Path, log_dir: Path, *args: Path | str
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "ATHC_CONFIG_DIR": str(config_dir),
        "ATHC_LOG_DIR": str(log_dir),
    }
    return subprocess.run(
        [sys.executable, "-m", "athc", "check-ppp", *(str(a) for a in args)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_entry_point_subprocess(
    full_league: Path, config_dir: Path, log_dir: Path
) -> None:
    result = _athc(config_dir, log_dir, OFF1, GP_OFFENSE)
    assert result.returncode == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout
    assert all(line.startswith("WARN ") for line in result.stderr.splitlines())


def test_entry_point_errors_go_to_stderr(
    full_league: Path, config_dir: Path, log_dir: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.prf"
    result = _athc(config_dir, log_dir, missing, GP_OFFENSE)
    assert result.returncode == 2
    assert result.stdout == ""
    assert f"FAIL {missing}: {FILE_NOT_FOUND}" in result.stderr
    log = (log_dir / "athc.log").read_text(encoding="utf-8")
    assert f" ERROR {missing}: {FILE_NOT_FOUND}" in log
    assert log.rstrip().endswith(" INFO exit 2")
