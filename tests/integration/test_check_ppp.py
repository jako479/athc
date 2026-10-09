"""Integration tests for `athc check-ppp`.

check-ppp prints exactly what `profile check --gameplan` printed and what
`gameplan check` prints, so its reports are compared to their committed goldens.
Every rule, and the league file that pairs a directory's files, comes from the
league folder.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli import cli
from athc.cli.check_ppp import check_ppp
from athc.errors import AthcError
from athc.fbpro98_lg2.schema import FILENAME_SIZE, FOLDER_SIZE, TEAM_TRAILER_SIZE
from tests.conftest import (
    CATEGORIES_TOML,
    LEAGUE,
    OTHER_LEAGUE,
    league_not_found,
    no_league_selected,
    no_rules_configured,
    os_error,
    toml_error,
)
from tests.integration.conftest import (
    COMPAT_OFF_CLEAN,
    DEF1,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    OFF1,
    PLAYS,
    PNFL_LG2,
    POOL_RULES,
    PPP_TREE,
    RULES_TOML,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]
BuildLeague = Callable[..., Path]
PROFILE_FLAG_OFF_TOML = """[gameplan_compatibility]
require_all_profile_categories_in_gameplan = false
"""


@pytest.fixture
def league(make_league: MakeLeague) -> BuildLeague:
    """Build a league folder holding check-ppp's rules; None leaves one out."""

    def _build(
        name: str = LEAGUE,
        *,
        profile_rules: Path | None = RULES_TOML,
        gameplan_rules: Path | None = GP_RULES,
        playpool_rules: Path | None = POOL_RULES,
        play_path: Path | None = PLAYS,
        path: Path | str | None = None,
    ) -> Path:
        settings = [("play_path", play_path), ("path", path)]
        lines = [f"{key} = '{value}'\n" for key, value in settings if value]
        body = "[league]\n" + "".join(lines) + CATEGORIES_TOML if lines else None
        folder = make_league(name, body)
        for source, target in (
            (profile_rules, "profile.toml"),
            (gameplan_rules, "gameplan.toml"),
            (playpool_rules, "playpool.toml"),
        ):
            if source is not None:
                shutil.copy(source, folder / target)
        return folder

    return _build


@pytest.fixture
def full_league(league: BuildLeague, write_config: WriteConfig) -> Path:
    """A league with every rule file, selected by `[athc] league` in athc.ini."""
    folder = league()
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


@pytest.fixture
def lg2_league(
    league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> Callable[..., Path]:
    """A league selected in athc.ini whose `path` folder holds its .lg2
    (named after the league), built from `teams`; keyword arguments go to
    `league`. Returns the .lg2 path."""

    def _build(*teams: bytes, **kwargs) -> Path:
        lg2_dir = tmp_path / "lg2"
        lg2_dir.mkdir()
        lg2 = lg2_dir / f"{LEAGUE}.lg2"
        lg2.write_bytes(b"".join(teams))
        league(path=lg2_dir, **kwargs)
        write_config(f"[athc]\nleague = {LEAGUE}\n")
        return lg2

    return _build


# The TST files under their own names, so the goldens apply.
OFF = ("TST-OFF1.prf", "offense.pln")
DEF = ("TST-DEF1.prf", "defense.pln")


def team(
    off1: tuple[str, str] = ("none-o1.prf", "none-o1.pln"),
    def1: tuple[str, str] = ("none-d1.prf", "none-d1.pln"),
    off2: tuple[str, str] = ("none-o2.prf", "none-o2.pln"),
    def2: tuple[str, str] = ("none-d2.prf", "none-d2.pln"),
    folder: str = "PNFL\\2049\\Plans\\Team",
) -> bytes:
    """One .lg2 team record from its (profile, gameplan) name pairs; a pair not
    given names files that are never on disk."""
    names = (*off1, *def1, *off2, *def2)
    entries = b"".join(
        folder.encode("ascii").ljust(FOLDER_SIZE, b"\x00")
        + name.encode("ascii").ljust(FILENAME_SIZE, b"\x00")
        for name in names
    )
    return entries + bytes(TEAM_TRAILER_SIZE)


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


# ── arguments: a pair of files or one directory ───────────────────────────────


def test_cli_requires_a_path(runner) -> None:
    result = run(runner)
    assert result.exit_code == 2
    assert "Missing argument" in result.stderr


def test_cli_rejects_a_third_path(runner, full_league: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE, DEF1)
    assert result.exit_code == 2
    assert "unexpected extra argument" in result.stderr


@pytest.mark.parametrize("path", [OFF1, GP_OFFENSE])
def test_cli_one_file_is_an_error(runner, full_league: Path, path: Path) -> None:
    """A profile or a gameplan alone is never checked: both are required."""
    result = run(runner, path)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {path}: not a directory; pass one profile and one gameplan, "
        "or a directory\n"
    )
    assert result.stdout == ""


def test_cli_one_missing_path(runner, full_league: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    result = run(runner, missing)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: not found\n"
    assert result.stdout == ""


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
    `[profile_compatibility]`): profile report with its `gameplan:` lines (as
    `profile check --gameplan` printed), then the gameplan report (as
    `gameplan check`), then one summary."""
    result = run(runner, prof, gameplan)
    assert result.exit_code == 1
    assert normalized(result, prof, gameplan) == (
        golden(*stems) + "\n2 file(s) checked, 2 with violations, 0 failed\n"
    )


def test_cli_unused_gameplan_categories_are_info(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """With the gameplan rules' `require_all_gameplan_categories_in_profile`
    off, a gameplan category the profile never uses is only an info line and
    does not count; a profile category the gameplan lacks still fails."""
    league(gameplan_rules=gameplan_rules(tmp_path, reverse=False))
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, DEF1, GP_DEFENSE)
    assert result.exit_code == 1
    situations = golden("TST-DEF1").splitlines(keepends=True)[1:]
    assert normalized(result, DEF1, GP_DEFENSE) == (
        "TST-DEF1.prf: 7 violation(s), 1 gameplan issue(s) (defense, FG range 36)\n"
        + "".join(situations)
        + "  gameplan: special-teams category Field Goal/PAT has no custom special play in the gameplan\n"
        "  gameplan info: gameplan special-teams category Fake FG Run is not used by the profile\n"
        "  gameplan info: gameplan special-teams category Fake FG Pass is not used by the profile\n"
        "  gameplan info: gameplan special-teams category Fake Punt Run is not used by the profile\n"
        "  gameplan info: gameplan special-teams category Fake Punt Pass is not used by the profile\n"
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
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    league(
        profile_rules=write_toml(tmp_path, PROFILE_FLAG_OFF_TOML),
        gameplan_rules=gameplan_rules(tmp_path, reverse=False),
    )
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    monkeypatch.setattr(
        "athc.cli.check_ppp.gameplan_extra_categories", lambda prof, gp: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {COMPAT_OFF_CLEAN}: offense, FG range 20; gameplan compatible\n"
        f"OK   {GP_OFFENSE}: offense, 64 normal\n"
        "\n2 file(s) checked, 0 with violations, 0 failed\n"
    )


def test_cli_unused_gameplan_categories_alone_exit_0(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both files pass their own rules and the gameplan backs every profile
    category; the 10 gameplan categories the profile never uses are only info,
    reported even with the league's flags off."""
    league(
        profile_rules=write_toml(tmp_path, PROFILE_FLAG_OFF_TOML),
        gameplan_rules=gameplan_rules(tmp_path, reverse=False),
    )
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout.startswith(
        f"OK   {COMPAT_OFF_CLEAN}: offense, FG range 20; gameplan compatible\n"
        "  gameplan info: gameplan play category "
    )
    assert result.stdout.count("  gameplan info: ") == 10
    assert (
        "  gameplan info: gameplan play category Run Left is not used by the profile"
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
    league: BuildLeague,
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
    league(
        profile_rules=write_toml(tmp_path, settings),
        gameplan_rules=gameplan_rules(tmp_path, reverse=reverse),
    )
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, DEF1, GP_DEFENSE)
    assert result.exit_code == 1
    assert result.stdout.count("  gameplan: ") == issues
    assert result.stdout.count("  gameplan info: ") == infos
    assert f"2 file(s) checked, {files} with violations, 0 failed" in result.stdout


# ── side mismatch ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prof,gameplan,sides",
    [
        (OFF1, GP_DEFENSE, "profile is offense but gameplan is defense"),
        (DEF1, GP_OFFENSE, "profile is defense but gameplan is offense"),
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
    assert result.stderr == f"FAIL {missing}: not found\n"
    assert result.stdout == ""


def test_cli_reports_every_input_error(
    runner, full_league: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.prf"
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, missing, wrong)
    assert result.exit_code == 2
    assert f"FAIL {missing}: not found" in result.stderr
    assert f"FAIL {wrong}: not a .prf or .pln file" in result.stderr


def test_cli_wrong_extension(runner, full_league: Path, tmp_path: Path) -> None:
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, OFF1, wrong)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {wrong}: not a .prf or .pln file\n"
    assert result.stdout == ""


def test_cli_directory_next_to_a_file_is_not_a_file(
    runner, full_league: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "profiles.prf"
    folder.mkdir()
    result = run(runner, folder, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: not a file\n"
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
        f"FAIL {second}: second {kind} file; pass one profile and one gameplan\n"
    )
    assert result.stdout == ""


def test_cli_bad_input_checks_nothing(
    runner, full_league: Path, tmp_path: Path
) -> None:
    """The good profile is not checked alone: both files are required."""
    wrong = write_bytes(tmp_path, "plan.txt")
    result = run(runner, OFF1, wrong)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {wrong}: not a .prf or .pln file\n"
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
    assert f"FAIL {bad}: File too small to contain F95 block\n" in result.stderr
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
        f"FAIL {bad}: File too small to contain PLN header and offsets table\n"
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


def test_cli_rules_from_league_set_in_athc_ini(runner, full_league: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_cli_no_profile_rules_in_league(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    league(profile_rules=None)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_cli_no_gameplan_rules_in_league(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    league(gameplan_rules=None)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("gameplan.toml")
    assert result.stdout == ""


def test_cli_rules_error_stops_before_the_files(
    runner, league: BuildLeague, write_config: WriteConfig
) -> None:
    """A setup problem stops the run before any file is read: no side-mismatch
    line, no report, no summary."""
    league(profile_rules=None)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
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
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """No rules for either side and no play pool: the first problem found is
    the one reported."""
    league(profile_rules=None, gameplan_rules=None, play_path=tmp_path / "nope")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_cli_no_play_path(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
) -> None:
    folder = league(play_path=None)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL no play_path for the league; set play_path in {folder / 'league.toml'}\n"
    )


def test_cli_play_path_not_a_directory(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
) -> None:
    league(play_path=tmp_path / "nope")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope'}: play path is not a directory\n"


@pytest.mark.parametrize("side", ["profile", "gameplan"])
def test_cli_bad_rules_toml(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    side: str,
) -> None:
    """Bad rules for one side; neither file is checked."""
    bad = write_toml(tmp_path, "not = valid = toml")
    folder = league(**{f"{side}_rules": bad})  # copied in as <side>.toml
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / f'{side}.toml'}: TOML parse error: "
        f"{toml_error('not = valid = toml')}\n"
    )
    assert result.stdout == ""


def test_cli_bad_playpool_rules(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    league(playpool_rules=write_toml(tmp_path, "not = valid = toml"))
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stdout == ""


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
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


@pytest.mark.parametrize("key", ["profile_rules", "gameplan_rules"])
def test_cli_missing_listed_rules_file(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    key: str,
) -> None:
    folder = league()
    (folder / "league.toml").write_text(
        f"[league]\nplay_path = '{PLAYS}'\n{key} = ['gone.toml']\n" + CATEGORIES_TOML,
        encoding="utf-8",
    )
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    gone = folder / "gone.toml"
    assert result.stderr == f"FAIL {gone}: {os_error(gone.read_bytes).strerror}\n"


def test_cli_malformed_ini(
    runner,
    full_league: Path,
    write_config: WriteConfig,
) -> None:
    ini = write_config("[athc\nbroken\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {ini}: line 1: no [section] header above it\n"
    assert result.stdout == ""


# ── a directory: the league file's pairs ──────────────────────────────────────


def test_dir_checks_each_pair_in_league_file_order(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Offense first, as the .lg2 lists it (by name, defense would sort first);
    each pair reads exactly as two-file mode prints it."""
    lg2_league(team(off1=OFF, def1=DEF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, folder)
    assert result.exit_code == 1
    files = [folder / p.name for p in (OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("compat_offense", "offense", "compat_defense", "defense")
        + "\n4 file(s) checked, 4 with violations, 0 failed\n"
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
    result = run(runner, folder)
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {folder / 'compat_off_clean.prf'}: offense, FG range 20; "
        "gameplan compatible\n"
        f"OK   {folder / 'offense.pln'}: offense, 64 normal\n"
        "\n2 file(s) checked, 0 with violations, 0 failed\n"
    )


def test_dir_teams_in_league_file_order(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(def1=DEF), team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, folder)
    files = [folder / p.name for p in (OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("compat_defense", "defense", "compat_offense", "offense")
        + "\n4 file(s) checked, 4 with violations, 0 failed\n"
    )


def test_dir_second_half_pairs(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off2=OFF, def2=DEF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = run(runner, folder)
    assert result.exit_code == 1
    assert "4 file(s) checked, 4 with violations, 0 failed" in result.stdout


def test_dir_names_ignore_case(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=("TST-OFF1.PRF", "OFFENSE.PLN")))
    folder = put(tmp_path / "plans", (OFF1, "tst-off1.prf"), GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 1
    assert result.stdout.startswith(f"{folder / 'tst-off1.prf'}: ")
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_dir_half_a_pair_is_skipped(runner, lg2_league, tmp_path: Path) -> None:
    """TST-OFF1.prf's gameplan is not there, so only the defense pair runs."""
    lg2_league(team(off1=OFF, def1=DEF))
    folder = put(tmp_path / "plans", OFF1, DEF1, GP_DEFENSE)
    result = run(runner, folder)
    assert result.exit_code == 1
    files = [folder / p.name for p in (DEF1, GP_DEFENSE)]
    assert normalized(result, *files) == (
        golden("compat_defense", "defense")
        + "\n2 file(s) checked, 2 with violations, 0 failed\n"
    )


def test_dir_unlisted_files_are_ignored(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, (GP_DEFENSE, "spare.pln"))
    result = run(runner, folder)
    files = [folder / p.name for p in (OFF1, GP_OFFENSE)]
    assert normalized(result, *files) == (
        golden("compat_offense", "offense")
        + "\n2 file(s) checked, 2 with violations, 0 failed\n"
    )


def test_dir_shared_gameplan_is_reported_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    """One gameplan for both halves: its own report prints once, while each
    profile gets its own cross-check against it."""
    lg2_league(team(off1=OFF, off2=("compat_off_clean.prf", "offense.pln")))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, COMPAT_OFF_CLEAN)
    result = run(runner, folder)
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
    result = run(runner, folder)
    assert result.exit_code == 1
    assert result.stdout.count(f"{folder / 'TST-OFF1.prf'}: ") == 2
    assert "4 file(s) checked, 4 with violations, 0 failed" in result.stdout


def test_dir_same_pair_twice_is_checked_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    lg2_league(team(off1=OFF), team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_dir_league_file_folders_are_ignored(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Only the file names count; the folder in each .lg2 entry doesn't."""
    lg2_league(team(off1=OFF, folder="Somewhere\\Else"))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    assert run(runner, folder).exit_code == 1


def test_dir_subfolders_are_not_searched(runner, lg2_league, tmp_path: Path) -> None:
    """No pairs is not an error, since no file has to be there: a warning,
    exit 0."""
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    put(folder / "week1", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 0
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"
    assert result.stderr.endswith(
        f"WARN {folder}: no profile and gameplan pairs from the league file in "
        "directory\n"
    )


def test_dir_empty(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, folder)
    assert result.exit_code == 0
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"
    assert result.stderr.endswith(
        f"WARN {folder}: no profile and gameplan pairs from the league file in "
        "directory\n"
    )


def test_dir_expected_error_in_a_pair_is_its_fail_line(
    runner, lg2_league, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expected error inside one pair's check fails that pair, not the run."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)

    def boom(prof: object, rules: object) -> tuple[()]:
        raise AthcError("rules exploded")

    monkeypatch.setattr("athc.cli.check_ppp.validate_profile", boom)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1] == "FAIL rules exploded"  # after WARNs
    assert "unexpected error" not in result.stderr
    assert result.stdout.endswith("0 file(s) checked, 0 with violations, 1 failed\n")


def test_dir_setup_error_stops_before_the_pairs(
    runner, lg2_league, tmp_path: Path
) -> None:
    """The setup error stops the run before the folder is even looked at."""
    lg2_league(team(off1=OFF), profile_rules=None)
    folder = tmp_path / "plans"
    folder.mkdir()
    result = run(runner, folder)
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
    """Skipped like `os.walk` does, so it reads as a folder with no pairs."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    message = deny(monkeypatch, folder)
    result = run(runner, folder)
    assert result.exit_code == 0
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"
    assert message not in result.stderr
    assert "no profile and gameplan pairs from the league file" in result.stderr


def test_dir_side_mismatch_is_that_pairs_error(
    runner, lg2_league, tmp_path: Path
) -> None:
    """The mismatched pair gets its error line and the rest still run; the
    gameplan it shares with a later pair is reported there."""
    lg2_league(team(off1=("TST-OFF1.prf", "defense.pln"), def1=DEF))
    folder = put(tmp_path / "plans", OFF1, DEF1, GP_DEFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    files = [folder / p.name for p in (OFF1, DEF1, GP_DEFENSE)]
    assert (
        f"FAIL {folder / 'TST-OFF1.prf'}: profile is offense but gameplan is defense"
        in result.stderr
    )
    assert normalized(result, *files) == (
        golden("compat_defense", "defense")
        + "\n3 file(s) checked, 2 with violations, 1 failed\n"
    )


def test_dir_unreadable_file(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=("broken.prf", "offense.pln")))
    folder = put(tmp_path / "plans", GP_OFFENSE)
    bad = write_bytes(folder, "broken.prf")
    result = run(runner, folder)
    assert result.exit_code == 2
    assert f"FAIL {bad}: " in result.stderr
    assert normalized(result, folder / "offense.pln") == (
        golden("offense") + "\n2 file(s) checked, 1 with violations, 1 failed\n"
    )


def test_dir_unreadable_shared_gameplan_is_reported_once(
    runner, lg2_league, tmp_path: Path
) -> None:
    """Each profile still gets its report, with no cross-check."""
    lg2_league(team(off1=("TST-OFF1.prf", "broken.pln"), off2=("x.prf", "broken.pln")))
    folder = put(tmp_path / "plans", OFF1, (OFF1, "x.prf"))
    bad = write_bytes(folder, "broken.pln")
    result = run(runner, folder)
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
    result = run(runner, folder)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")
    assert result.stdout == ""


def test_dir_no_league(runner, config_dir: Path, tmp_path: Path) -> None:
    """Every setup piece needs the league; the error is logged once."""
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir)
    assert result.stdout == ""


def test_dir_no_path(runner, full_league: Path, tmp_path: Path) -> None:
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert (
        "no path for the league; set path in "
        f"{full_league / 'league.toml'}" in result.stderr
    )
    assert result.stdout == ""


def test_dir_first_setup_error_stops_the_run(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    league(profile_rules=None)  # and no `path` either
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert result.stderr == no_rules_configured("profile.toml")


@pytest.mark.parametrize(
    "data,message",
    [
        (b"\x00\x01\x02", "not a whole number"),
        (team(off1=OFF, folder=""), "Old stock league not supported"),
    ],
    ids=["invalid", "stock"],
)
def test_dir_bad_league_file(
    runner,
    lg2_league,
    tmp_path: Path,
    data: bytes,
    message: str,
) -> None:
    lg2 = lg2_league(data)
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert message in result.stderr and str(lg2) in result.stderr
    assert result.stdout == ""


def test_dir_league_file_missing(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
) -> None:
    """`path` is set, but the league's .lg2 isn't in that folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    league(path=lg2_dir)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder)
    assert result.exit_code == 2
    assert f"{LEAGUE}.lg2" in result.stderr
    assert result.stdout == ""


def test_dir_relative_path_is_in_the_league_folder(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    folder = league(path="lg2")
    (folder / "lg2").mkdir()
    (folder / "lg2" / f"{LEAGUE}.lg2").write_bytes(team(off1=OFF))
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    plans = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, plans)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


# ── a tree (-r): each folder on its own ───────────────────────────────────────


def heads(result: Result) -> list[str]:
    """The path of each report's first line, in order."""
    return [
        line.split(": ")[0]
        for line in result.stdout.splitlines()
        if line and not line.startswith(" ") and "file(s) checked" not in line
    ]


def test_tree_finds_pairs_in_subfolders(runner, lg2_league, tmp_path: Path) -> None:
    lg2_league(team(off1=OFF))
    folder = tmp_path / "plans"
    put(folder / "week1", OFF1, GP_OFFENSE)
    result = run(runner, "-r", folder)
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
    result = run(runner, top, "-r")
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
    across folders."""
    lg2_league(team(off1=OFF))
    folder = put(tmp_path / "plans", OFF1)
    put(folder / "week1", GP_OFFENSE)
    result = run(runner, "-r", folder)
    assert result.exit_code == 0
    assert result.stdout == "\n0 file(s) checked, 0 with violations, 0 failed\n"
    assert result.stderr.endswith(
        f"WARN {folder}: no profile and gameplan pairs from the league file in tree\n"
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
    result = run(runner, "-r", folder)
    assert result.exit_code == 1
    assert message not in result.stderr
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "offense.pln")]
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


def test_tree_flag_with_two_files_is_ignored(runner, full_league: Path) -> None:
    result = run(runner, "-r", OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout


# ── real league data: PNFL.lg2 and a copy of its 2049 plans ───────────────────

DENVER = PPP_TREE / "2049" / "Plans" / "Denver (Brian)"
LAS_VEGAS = PPP_TREE / "2049" / "Plans" / "Las Vegas (Neil)"
# Each .lg2 pair in file order: 1st-half offense and defense, then 2nd half.
DENVER_PAIRS = [
    ("DEN-OFF1.prf", "DEN-OGP1.pln"),
    ("DEN-DEF1.prf", "DEN-DGP1.pln"),
    ("DEN-OFF2.prf", "DEN-OGP2.pln"),
    ("DEN-DEF2.prf", "DEN-DGP2.pln"),
]
# Las Vegas uses one gameplan per side for both halves.
LAS_VEGAS_PAIRS = [
    ("LVOFF1.prf", "RAIDEROFF.pln"),
    ("LVDEF1.prf", "RAIDERDEF.pln"),
    ("LVOFF2.prf", "RAIDEROFF.pln"),
    ("LVDEF2.prf", "RAIDERDEF.pln"),
]


@pytest.fixture
def pnfl_league(league: BuildLeague, write_config: WriteConfig, tmp_path: Path) -> Path:
    """The test league, with PNFL.lg2 copied in as its league file."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    shutil.copy2(PNFL_LG2, lg2_dir / f"{LEAGUE}.lg2")
    folder = league(path=lg2_dir)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


def pair_reports(runner, folder: Path, profile: str, gameplan: str) -> list[str]:
    """Two-file mode's report lines for one pair, without the summary."""
    result = run(runner, folder / profile, folder / gameplan)
    return result.stdout.splitlines(keepends=True)[:-2]


def test_real_tree_checks_every_team_folder(runner, pnfl_league: Path) -> None:
    result = run(runner, "-r", PPP_TREE)
    assert "FAIL " not in result.stderr
    assert heads(result) == [
        *(str(DENVER / name) for pair in DENVER_PAIRS for name in pair),
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
    result = run(runner, "-r", PPP_TREE)
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
    result = run(runner, DENVER)
    assert heads(result) == [
        str(DENVER / name) for pair in DENVER_PAIRS for name in pair
    ]


# ── --league, ATHC_LEAGUE, registration ───────────────────────────────────────


def test_league_flag_beats_athc_ini(
    runner, league: BuildLeague, write_config: WriteConfig
) -> None:
    league(LEAGUE, profile_rules=None, gameplan_rules=None)  # would fail
    league(OTHER_LEAGUE)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(
        cli, ["check-ppp", str(OFF1), str(GP_OFFENSE), "--league", OTHER_LEAGUE]
    )
    assert result.exit_code == 1


def test_league_flag_picks_the_league_file(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    """In a directory, `--league` also picks whose `.lg2` pairs the files: both
    leagues share one folder, each file named after its league."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(team(def1=DEF))
    (lg2_dir / f"{OTHER_LEAGUE}.lg2").write_bytes(team(off1=OFF))
    league(LEAGUE, path=lg2_dir)
    league(OTHER_LEAGUE, path=lg2_dir)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = put(tmp_path / "plans", OFF1, GP_OFFENSE, DEF1, GP_DEFENSE)
    result = runner.invoke(cli, ["check-ppp", str(folder), "--league", OTHER_LEAGUE])
    assert heads(result) == [str(folder / "TST-OFF1.prf"), str(folder / "offense.pln")]


def test_athc_league_env_is_ignored(
    runner,
    league: BuildLeague,
    config_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    league(OTHER_LEAGUE)
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
    assert f"FAIL {missing}: not found" in result.stderr
    log = (log_dir / "athc.log").read_text(encoding="utf-8")
    assert f" ERROR FAIL {missing}: not found" in log
    assert log.rstrip().endswith(" INFO exit 2")
