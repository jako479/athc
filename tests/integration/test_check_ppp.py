"""Integration tests for `athc check-ppp`.

check-ppp prints exactly what `profile check` (with `--gameplan`) and
`gameplan check` print, so its reports are compared to their committed goldens.
It has no options: every rule comes from the league folder.
"""

from __future__ import annotations

import logging
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
from tests.integration.conftest import (
    COMPAT_OFF_CLEAN,
    DEF1,
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    GP_RULES,
    OFF1,
    PLAYS,
    POOL_RULES,
    RULES_TOML,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]
BuildLeague = Callable[..., Path]
COMPAT_TOML = """[gameplan_compatibility]
profile_categories_in_gameplan = true
gameplan_categories_in_profile = true
"""
FLAGS_OFF_TOML = """[gameplan_compatibility]
profile_categories_in_gameplan = false
gameplan_categories_in_profile = false
"""


@pytest.fixture
def league(make_league: MakeLeague) -> BuildLeague:
    """Build a league folder holding check-ppp's rules; None leaves one out."""

    def _build(
        name: str = "PNFL",
        *,
        profile_rules: Path | None = RULES_TOML,
        gameplan_rules: Path | None = GP_RULES,
        playpool_rules: Path | None = POOL_RULES,
        play_path: Path | None = PLAYS,
    ) -> Path:
        body = f"[league]\nplay_path = {play_path}\n" if play_path else None
        folder = make_league(name, body)
        for source, target in (
            (profile_rules, "profile.toml"),
            (gameplan_rules, "gameplan.toml"),
            (playpool_rules, "playpool.toml"),
        ):
            if source is not None:
                shutil.copy(source, folder / "rules" / target)
        return folder

    return _build


@pytest.fixture
def pnfl(league: BuildLeague, write_config: WriteConfig) -> Path:
    """The full PNFL league, selected by `[athc] league` in athc.ini."""
    folder = league("PNFL")
    write_config("[athc]\nleague = PNFL\n")
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


def write_bytes(tmp_path: Path, name: str, data: bytes = b"\x00\x01\x02") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


# ── arguments: one or two files ───────────────────────────────────────────────


def test_cli_requires_a_file(runner) -> None:
    result = run(runner)
    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_cli_rejects_a_third_file(runner, pnfl: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE, DEF1)
    assert result.exit_code == 2
    assert "unexpected extra argument" in result.output


# ── profile only (as `profile check`) ─────────────────────────────────────────


@pytest.mark.parametrize("prof,count", [(OFF1, 18), (DEF1, 7)])
def test_cli_profile_only_matches_profile_check(
    runner, pnfl: Path, prof: Path, count: int
) -> None:
    result = run(runner, prof)
    assert result.exit_code == 1
    assert normalized(result, prof) == (
        golden(prof.stem)
        + f"\n1 file(s) checked, {count} violation(s) across 1 file(s).\n"
    )


def test_cli_profile_only_clean_exit_0(
    runner, pnfl: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("athc.cli.check_ppp.validate_profile", lambda prof, rules: ())
    result = run(runner, OFF1)
    assert result.exit_code == 0
    assert result.stdout == (
        f"{OFF1}: OK (offense, FG range 36)\n"
        "\n1 file(s) checked, 0 violation(s) across 0 file(s).\n"
    )


def test_cli_profile_only_needs_no_gameplan_config(
    runner, league: BuildLeague, write_config: WriteConfig
) -> None:
    league(gameplan_rules=None, playpool_rules=None, play_path=None)
    write_config("[athc]\nleague = PNFL\n")
    assert run(runner, OFF1).exit_code == 1


# ── gameplan only (as `gameplan check`) ───────────────────────────────────────


@pytest.mark.parametrize("gameplan,count", [(GP_OFFENSE, 3), (GP_DEFENSE, 1)])
def test_cli_gameplan_only_matches_gameplan_check(
    runner, pnfl: Path, gameplan: Path, count: int
) -> None:
    result = run(runner, gameplan)
    assert result.exit_code == 1
    assert normalized(result, gameplan) == (
        golden(gameplan.stem)
        + f"\n1 file(s) checked, {count} violation(s) across 1 file(s).\n"
    )


def test_cli_gameplan_only_clean_exit_0(
    runner, pnfl: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = run(runner, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (
        f"{GP_OFFENSE}: OK (offense, 64 normal)\n"
        "\n1 file(s) checked, 0 violation(s) across 0 file(s).\n"
    )


def test_cli_gameplan_only_needs_no_profile_rules(
    runner, league: BuildLeague, write_config: WriteConfig
) -> None:
    league(profile_rules=None)
    write_config("[athc]\nleague = PNFL\n")
    assert run(runner, GP_OFFENSE).exit_code == 1


# ── both files ────────────────────────────────────────────────────────────────


def test_cli_both_matches_existing_reports(runner, pnfl: Path) -> None:
    """Profile report with its `gameplan:` lines (as `profile check --gameplan`),
    then the gameplan report (as `gameplan check`), then one summary. TST-OFF1
    vs offense.pln has no unused gameplan categories, so the reports match."""
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert normalized(result, OFF1, GP_OFFENSE) == (
        golden("compat_offense", "offense")
        + "\n2 file(s) checked, 22 violation(s) across 2 file(s).\n"
    )


def test_cli_unused_gameplan_categories_are_info(runner, pnfl: Path) -> None:
    """A profile category the gameplan lacks fails, as in `profile check
    --gameplan`; a gameplan category the profile never uses is only an info
    line and does not count."""
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
        + "\n2 file(s) checked, 9 violation(s) across 2 file(s).\n"
    )


def test_cli_file_order_does_not_matter(runner, pnfl: Path) -> None:
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
    league(profile_rules=write_toml(tmp_path, FLAGS_OFF_TOML))
    write_config("[athc]\nleague = PNFL\n")
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    monkeypatch.setattr(
        "athc.cli.check_ppp.gameplan_extra_categories", lambda prof, gp: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (
        f"{COMPAT_OFF_CLEAN}: OK (offense, FG range 20; gameplan compatible)\n"
        f"{GP_OFFENSE}: OK (offense, 64 normal)\n"
        "\n2 file(s) checked, 0 violation(s) across 0 file(s).\n"
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
    league(profile_rules=write_toml(tmp_path, FLAGS_OFF_TOML))
    write_config("[athc]\nleague = PNFL\n")
    monkeypatch.setattr(
        "athc.cli.check_ppp.validate_gameplan", lambda gp, rules, pool: ()
    )
    result = run(runner, COMPAT_OFF_CLEAN, GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout.startswith(
        f"{COMPAT_OFF_CLEAN}: OK (offense, FG range 20; gameplan compatible)\n"
        "  gameplan info: gameplan play category "
    )
    assert result.stdout.count("  gameplan info: ") == 10
    assert (
        "  gameplan info: gameplan play category Run Left is not used by the profile"
        in result.stdout
    )
    assert "2 file(s) checked, 0 violation(s) across 0 file(s)." in result.stdout


@pytest.mark.parametrize(
    "forward,reverse", [(True, True), (True, False), (False, True), (False, False)]
)
def test_cli_cross_check_ignores_league_flags(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    forward: bool,
    reverse: bool,
) -> None:
    """The `[gameplan_compatibility]` flags are for `profile check`; check-ppp
    always reports TST-DEF1 vs defense.pln's 1 missing category (an issue) and
    4 unused ones (info)."""
    flags = (
        "[gameplan_compatibility]\n"
        f"profile_categories_in_gameplan = {str(forward).lower()}\n"
        f"gameplan_categories_in_profile = {str(reverse).lower()}\n"
    )
    league(profile_rules=write_toml(tmp_path, flags))
    write_config("[athc]\nleague = PNFL\n")
    result = run(runner, DEF1, GP_DEFENSE)
    assert result.exit_code == 1
    assert result.stdout.count("  gameplan: ") == 1
    assert result.stdout.count("  gameplan info: ") == 4
    assert "2 file(s) checked, 2 violation(s) across 2 file(s)." in result.stdout


# ── side mismatch ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prof,gameplan,sides",
    [
        (OFF1, GP_DEFENSE, "profile is offense but gameplan is defense"),
        (DEF1, GP_OFFENSE, "profile is defense but gameplan is offense"),
    ],
)
def test_cli_side_mismatch_stops_the_checks(
    runner, pnfl: Path, prof: Path, gameplan: Path, sides: str
) -> None:
    """A mismatch is an error like a setup error: no file is checked and there
    is no summary, only the mismatch line."""
    result = run(runner, prof, gameplan)
    assert result.exit_code == 2
    assert result.stdout == f"{prof}: ERROR: {sides}; sides must match\n"


# ── input errors (logged; every one reported) ─────────────────────────────────


def test_cli_missing_file(
    runner, pnfl: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "nope.prf"
    with caplog.at_level(logging.ERROR):
        result = run(runner, missing)
    assert result.exit_code == 2
    assert f"athc check-ppp: {missing}: path does not exist" in caplog.text
    assert result.stdout == ""


def test_cli_reports_every_input_error(
    runner, pnfl: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "nope.prf"
    wrong = write_bytes(tmp_path, "plan.txt")
    with caplog.at_level(logging.ERROR):
        result = run(runner, missing, wrong)
    assert result.exit_code == 2
    assert f"{missing}: path does not exist" in caplog.text
    assert f"{wrong}: not a .prf or .pln file" in caplog.text


def test_cli_wrong_extension(
    runner, pnfl: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    wrong = write_bytes(tmp_path, "plan.txt")
    with caplog.at_level(logging.ERROR):
        result = run(runner, wrong)
    assert result.exit_code == 2
    assert f"{wrong}: not a .prf or .pln file" in caplog.text


def test_cli_directory_is_not_a_file(
    runner, pnfl: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    folder = tmp_path / "profiles.prf"
    folder.mkdir()
    with caplog.at_level(logging.ERROR):
        result = run(runner, folder)
    assert result.exit_code == 2
    assert f"{folder}: not a file" in caplog.text


def test_cli_extension_is_case_insensitive(runner, pnfl: Path, tmp_path: Path) -> None:
    prof = tmp_path / "OFF.PRF"
    gameplan = tmp_path / "OFF.PLN"
    shutil.copy2(OFF1, prof)
    shutil.copy2(GP_OFFENSE, gameplan)
    result = run(runner, prof, gameplan)
    assert result.exit_code == 1
    assert "2 file(s) checked, 22 violation(s) across 2 file(s)." in result.stdout


@pytest.mark.parametrize(
    "first,second,kind", [(OFF1, DEF1, ".prf"), (GP_OFFENSE, GP_DEFENSE, ".pln")]
)
def test_cli_second_file_of_a_kind_is_an_error(
    runner,
    pnfl: Path,
    caplog: pytest.LogCaptureFixture,
    first: Path,
    second: Path,
    kind: str,
) -> None:
    """The first file is still checked; the second of its kind is an error."""
    with caplog.at_level(logging.ERROR):
        result = run(runner, first, second)
    assert result.exit_code == 2
    assert f"{second}: second {kind} file" in caplog.text
    assert result.stdout.startswith(f"{first}: ")
    assert str(second) not in result.stdout
    assert "1 file(s) checked" in result.stdout


def test_cli_continues_past_bad_input(
    runner, pnfl: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    wrong = write_bytes(tmp_path, "plan.txt")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, wrong)
    assert result.exit_code == 2
    assert f"{wrong}: not a .prf or .pln file" in caplog.text
    assert normalized(result, OFF1) == (
        golden("TST-OFF1") + "\n1 file(s) checked, 18 violation(s) across 1 file(s).\n"
    )


# ── unreadable files (not a profile / not a gameplan) ─────────────────────────


@pytest.mark.parametrize("name", ["broken.prf", "broken.pln"])
def test_cli_malformed_file(runner, pnfl: Path, tmp_path: Path, name: str) -> None:
    bad = write_bytes(tmp_path, name)
    result = run(runner, bad)
    assert result.exit_code == 2
    assert result.stdout.startswith(f"{bad}: ERROR: ")
    assert "1 file(s) checked" in result.stdout


@pytest.mark.parametrize(
    "source,name", [(OFF1, "really_a_profile.pln"), (GP_OFFENSE, "really_a_plan.prf")]
)
def test_cli_file_of_the_other_kind_is_an_error(
    runner, pnfl: Path, tmp_path: Path, source: Path, name: str
) -> None:
    """A .pln that holds a profile is not a gameplan (and the reverse)."""
    fake = tmp_path / name
    shutil.copy2(source, fake)
    result = run(runner, fake)
    assert result.exit_code == 2
    assert result.stdout.startswith(f"{fake}: ERROR: ")


def test_cli_bad_profile_still_checks_gameplan(
    runner, pnfl: Path, tmp_path: Path
) -> None:
    bad = write_bytes(tmp_path, "broken.prf")
    result = run(runner, bad, GP_OFFENSE)
    assert result.exit_code == 2
    lines = normalized(result, GP_OFFENSE).splitlines(keepends=True)
    assert lines[0].startswith(f"{bad}: ERROR: ")
    assert "".join(lines[1:]) == (
        golden("offense") + "\n2 file(s) checked, 3 violation(s) across 1 file(s).\n"
    )


def test_cli_bad_gameplan_still_checks_profile(
    runner, pnfl: Path, tmp_path: Path
) -> None:
    """The profile gets its own report; no cross-check without a gameplan."""
    bad = write_bytes(tmp_path, "broken.pln")
    result = run(runner, OFF1, bad)
    assert result.exit_code == 2
    out = normalized(result, OFF1)
    assert out.startswith(golden("TST-OFF1") + f"{bad}: ERROR: ")
    assert out.endswith("\n2 file(s) checked, 18 violation(s) across 1 file(s).\n")


def test_cli_both_unreadable_reports_both(runner, pnfl: Path, tmp_path: Path) -> None:
    bad_prof = write_bytes(tmp_path, "broken.prf")
    bad_plan = write_bytes(tmp_path, "broken.pln")
    result = run(runner, bad_prof, bad_plan)
    assert result.exit_code == 2
    assert f"{bad_prof}: ERROR: " in result.stdout
    assert f"{bad_plan}: ERROR: " in result.stdout
    assert "2 file(s) checked, 0 violation(s) across 0 file(s)." in result.stdout


# ── league / rules config ─────────────────────────────────────────────────────


def test_cli_no_league(runner, caplog: pytest.LogCaptureFixture) -> None:
    """Both sides need the league; the error is logged once."""
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert caplog.text.count("no league selected") == 1
    assert result.stdout == ""


def test_cli_rules_from_league_set_in_athc_ini(runner, pnfl: Path) -> None:
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 22 violation(s) across 2 file(s)." in result.stdout


def test_cli_no_profile_rules_in_league(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    league(profile_rules=None)
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "rules\\profile.toml" in caplog.text
    assert "--rules" not in caplog.text  # check-ppp has no such option
    assert result.stdout == ""


def test_cli_no_gameplan_rules_in_league(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rules error stops the rule checks for both files, not just its own."""
    league(gameplan_rules=None)
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "no rules configured" in caplog.text
    assert "rules\\gameplan.toml" in caplog.text
    assert "--rules" not in caplog.text  # check-ppp has no such option
    assert result.stdout == ""


def test_cli_rules_error_still_reports_side_mismatch(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The gameplan's rules load, but a profile rules error stops its check
    too; the side mismatch needs no rules and is still reported. No summary
    after a setup error, as in `profile check` / `gameplan check`."""
    league(profile_rules=None)
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_DEFENSE)
    assert result.exit_code == 2
    assert "rules\\profile.toml" in caplog.text
    assert normalized(result, OFF1) == (
        "TST-OFF1.prf: ERROR: profile is offense but gameplan is defense; "
        "sides must match\n"
    )


def test_cli_config_error_still_reports_side_mismatch(
    runner, caplog: pytest.LogCaptureFixture
) -> None:
    """Reading the files and comparing sides need no rules."""
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_DEFENSE)
    assert result.exit_code == 2
    assert "no league selected" in caplog.text
    assert normalized(result, OFF1) == (
        "TST-OFF1.prf: ERROR: profile is offense but gameplan is defense; "
        "sides must match\n"
    )


def test_cli_config_error_still_reports_unreadable_file(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = write_bytes(tmp_path, "broken.pln")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, bad)
    assert result.exit_code == 2
    assert "no league selected" in caplog.text
    assert result.stdout.startswith(f"{bad}: ERROR: ")
    assert result.stdout.count("\n") == 1  # the error line only, no summary


def test_cli_reports_every_config_error(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No rules for either side and no play pool: all three are logged."""
    league(profile_rules=None, gameplan_rules=None, play_path=tmp_path / "nope")
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "rules\\profile.toml" in caplog.text
    assert "rules\\gameplan.toml" in caplog.text
    assert "not a directory" in caplog.text
    assert result.stdout == ""


def test_cli_no_play_path(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    league(play_path=None)
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, GP_OFFENSE)
    assert result.exit_code == 2
    assert "no play_path" in caplog.text
    assert "--play-path" not in caplog.text  # check-ppp has no such option


def test_cli_play_path_not_a_directory(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    league(play_path=tmp_path / "nope")
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, GP_OFFENSE)
    assert result.exit_code == 2
    assert "not a directory" in caplog.text


@pytest.mark.parametrize("side", ["profile", "gameplan"])
def test_cli_bad_rules_toml(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    side: str,
) -> None:
    """Bad rules for one side; neither file is checked."""
    bad = write_toml(tmp_path, "not = valid = toml")
    league(**{f"{side}_rules": bad})
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "TOML parse error" in caplog.text
    assert result.stdout == ""


def test_cli_bad_playpool_rules(
    runner, league: BuildLeague, write_config: WriteConfig, tmp_path: Path
) -> None:
    league(playpool_rules=write_toml(tmp_path, "not = valid = toml"))
    write_config("[athc]\nleague = PNFL\n")
    result = run(runner, GP_OFFENSE)
    assert result.exit_code == 2
    assert result.stdout == ""


def test_cli_rule_lists_in_league_ini(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """`profile_rules` / `gameplan_rules` lists replace the fixed files."""
    folder = make_league(
        "PNFL",
        f"[league]\nplay_path = {PLAYS}\n"
        "profile_rules =\n    rules\\my-profile.toml\n"
        "gameplan_rules =\n    rules\\my-gameplan.toml\n",
    )
    shutil.copy(RULES_TOML, folder / "rules" / "my-profile.toml")
    shutil.copy(GP_RULES, folder / "rules" / "my-gameplan.toml")
    shutil.copy(POOL_RULES, folder / "rules" / "playpool.toml")
    write_config("[athc]\nleague = PNFL\n")
    result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 1
    assert "2 file(s) checked, 22 violation(s) across 2 file(s)." in result.stdout


@pytest.mark.parametrize("key", ["profile_rules", "gameplan_rules"])
def test_cli_missing_listed_rules_file(
    runner,
    league: BuildLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
    key: str,
) -> None:
    folder = league()
    (folder / "league.ini").write_text(
        f"[league]\nplay_path = {PLAYS}\n{key} =\n    rules\\gone.toml\n",
        encoding="utf-8",
    )
    write_config("[athc]\nleague = PNFL\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "gone.toml" in caplog.text


def test_cli_malformed_ini(
    runner, pnfl: Path, write_config: WriteConfig, caplog: pytest.LogCaptureFixture
) -> None:
    write_config("[athc\nbroken\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner, OFF1, GP_OFFENSE)
    assert result.exit_code == 2
    assert "athc.ini" in caplog.text
    assert result.stdout == ""


# ── root group: --league, ATHC_LEAGUE, registration ───────────────────────────


def test_root_league_flag_beats_athc_ini(
    runner, league: BuildLeague, write_config: WriteConfig
) -> None:
    league("PNFL", profile_rules=None, gameplan_rules=None)  # would fail
    league("PCFL")
    write_config("[athc]\nleague = PNFL\n")
    result = runner.invoke(
        cli, ["--league", "PCFL", "check-ppp", str(OFF1), str(GP_OFFENSE)]
    )
    assert result.exit_code == 1


def test_root_league_from_env(
    runner, league: BuildLeague, monkeypatch: pytest.MonkeyPatch
) -> None:
    league("PCFL")
    monkeypatch.setenv("ATHC_LEAGUE", "PCFL")
    result = runner.invoke(cli, ["check-ppp", str(OFF1), str(GP_OFFENSE)])
    assert result.exit_code == 1


def test_root_league_unknown_folder(
    runner, pnfl: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(cli, ["--league", "NOPE", "check-ppp", str(OFF1)])
    assert result.exit_code == 2
    assert "NOPE" in caplog.text and "not found" in caplog.text


def test_root_help_lists_check_ppp(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "check-ppp" in result.output


# ── packaging check (real subprocess) ─────────────────────────────────────────


def _athc(config_dir: Path, *args: Path | str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "ATHC_CONFIG_DIR": str(config_dir)}
    return subprocess.run(
        [sys.executable, "-m", "athc", "check-ppp", *(str(a) for a in args)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_entry_point_subprocess(pnfl: Path, config_dir: Path) -> None:
    result = _athc(config_dir, OFF1, GP_OFFENSE)
    assert result.returncode == 1
    assert "2 file(s) checked, 22 violation(s) across 2 file(s)." in result.stdout


def test_entry_point_errors_go_to_stderr(
    pnfl: Path, config_dir: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.prf"
    result = _athc(config_dir, missing)
    assert result.returncode == 2
    assert result.stdout == ""
    assert f"ERROR: athc check-ppp: {missing}: path does not exist" in result.stderr
