"""The profile keys (off1, def1, off2, def2) that `athc profile check`, `diff`
and `copy` share: which operand is a key, which file a key names, and the
setup lines on the way there. The team-name matching limits (one match
accepted, none or two rejected) are check-ppp's tests of the same resolver.

The league helpers (`build_teams` and the rest, in conftest.py) build Denver
and Las Vegas with their profiles where the league file puts them; the
`test_profile_*` modules use them too.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli import cli
from athc.cli.profile.check import check
from athc.cli.profile.diff import diff
from athc.errors import (
    ACCESS_DENIED,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
)
from tests.conftest import LEAGUE, athc_toml, league_not_found
from tests.integration.conftest import (
    DENVER,
    HINT,
    LAS_VEGAS,
    OFF1,
    TEAM_REQUIRES_KEY,
    BuildLeague,
    Lg2League,
    build_teams,
    heads,
    location,
    profile_file,
    put_profiles,
    record,
    team,
)

WriteConfig = Callable[..., Path]

TEAM_NOT_SET = (
    "Team is not set. Run 'athc config set team NAME' or pass --team or a .prf file."
)
PATH_NOT_SET = (
    "League files folder is not set. Run 'athc config set path FOLDER' or pass a "
    ".prf file."
)
TEAMS = "Denver Broncos, Las Vegas Raiders"

# One run of each command with a key among its operands, and one with plain
# files only.
KEY_RUNS = [
    ["check", "off1"],
    ["diff", "off1", str(OFF1)],
    ["copy", str(OFF1), "off1", "--stop-clock"],
]
PLAIN_RUNS = [
    ["check", str(OFF1)],
    ["diff", str(OFF1), str(OFF1)],
    ["copy", str(OFF1), str(OFF1), "--stop-clock"],
]


def league_toml(config_dir: Path) -> Path:
    return config_dir / "leagues" / LEAGUE / "league.toml"


@pytest.fixture(autouse=True)
def work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run from an empty folder, so no word is a file there unless a test
    puts one."""
    folder = tmp_path / "work"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


def run(runner, *args: str) -> Result:
    return runner.invoke(cli, ["profile", *args])


# ── which operand is a key ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("word", "key"),
    [("OFF1", "off1"), ("Def1", "def1"), ("oFF2", "off2"), ("def2", "def2")],
)
def test_each_key_in_any_case(
    runner, lg2_league: Lg2League, word: str, key: str
) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, [word])
    assert heads(result) == [str(profile_file(location(lg2_dir, DENVER), DENVER, key))]
    assert result.stdout.endswith("\n1 file(s) checked, 1 with violations, 0 failed\n")


@pytest.mark.parametrize("word", ["off", "o1", "off0", "off3"])
def test_other_words_are_paths(runner, lg2_league: Lg2League, word: str) -> None:
    build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, [word])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {word}: {FILE_NOT_FOUND}\n"


@pytest.mark.parametrize("word", ["off1.prf", ".\\off1"])
def test_an_extension_or_a_separator_makes_a_path(
    runner, lg2_league: Lg2League, word: str
) -> None:
    build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, [word])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {word}: {FILE_NOT_FOUND}\n"


@pytest.mark.parametrize(
    ("args", "line"),
    [
        (["check", "off1"], "off1: Not a .prf file."),
        (["copy", "x.prf", "off1", "--stop-clock"], "off1: Not a .prf file."),
        (["diff", "off1", "x.prf"], "off1: File too small to contain F95 block."),
        (
            ["copy", "off1", "x.prf", "--stop-clock"],
            "off1: File too small to contain F95 block.",
        ),
    ],
    ids=["check", "copy target", "diff", "copy source"],
)
def test_a_file_named_like_a_key_is_that_file(
    runner, lg2_league: Lg2League, work: Path, args: list[str], line: str
) -> None:
    """On check's PATH and among copy's targets it is not a .prf; on diff and
    as copy's source the reader gives its own line."""
    build_teams(lg2_league, team="Denver")
    (work / "off1").write_bytes(b"\x00\x01\x02")
    shutil.copy2(OFF1, work / "x.prf")
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {line}\n"


def test_check_a_folder_named_like_a_key(
    runner, lg2_league: Lg2League, work: Path
) -> None:
    build_teams(lg2_league, team="Denver")
    (work / "off1").mkdir()
    shutil.copy2(OFF1, work / "off1" / "a.prf")
    result = runner.invoke(check, ["off1"])
    assert heads(result) == [str(Path("off1") / "a.prf")]


def test_check_an_empty_folder_named_like_a_key(
    runner, lg2_league: Lg2League, work: Path
) -> None:
    build_teams(lg2_league, team="Denver")
    (work / "off1").mkdir()
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 0
    assert result.stderr == "WARN off1: No .prf files.\n"


def test_copy_into_a_folder_named_like_a_key(
    runner, lg2_league: Lg2League, work: Path
) -> None:
    build_teams(lg2_league, team="Denver")
    (work / "off1").mkdir()
    shutil.copy2(OFF1, work / "off1" / "a.prf")
    shutil.copy2(OFF1, work / "new.prf")
    result = run(runner, "copy", "new.prf", "off1", "--stop-clock")
    assert result.exit_code == 0
    assert f"OK   {Path('off1') / 'a.prf'}: updated (stop-clock)" in result.stdout
    assert "1 file(s) processed, 1 updated" in result.stdout


@pytest.mark.parametrize(
    "args",
    [["diff", "off1", "x.prf"], ["copy", "off1", "x.prf", "--stop-clock"]],
    ids=["diff", "copy source"],
)
def test_one_profile_from_a_folder_named_like_a_key(
    runner, lg2_league: Lg2League, work: Path, args: list[str]
) -> None:
    build_teams(lg2_league, team="Denver")
    (work / "off1").mkdir()
    shutil.copy2(OFF1, work / "x.prf")
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL off1: {ACCESS_DENIED}\n"


def test_a_key_run_from_another_folder(
    runner, lg2_league: Lg2League, tmp_path: Path
) -> None:
    """Existence is tested against the current folder only."""
    lg2_dir = build_teams(lg2_league, team="Denver")
    (tmp_path / "elsewhere" / "off1").mkdir(parents=True)
    result = runner.invoke(check, ["off1"])
    assert heads(result) == [
        str(profile_file(location(lg2_dir, DENVER), DENVER, "off1"))
    ]


# ── where a key's profile is: ppp_path or the league location ─────────────────


def test_ppp_path_holds_your_profiles(
    runner, lg2_league: Lg2League, tmp_path: Path
) -> None:
    ppp = put_profiles(tmp_path / "mine", DENVER)
    build_teams(lg2_league, team="Denver", ppp_path=ppp)
    result = runner.invoke(check, ["off1", "def2"])
    assert heads(result) == [
        str(profile_file(ppp, DENVER, "off1")),
        str(profile_file(ppp, DENVER, "def2")),
    ]


def test_relative_ppp_path_is_under_the_league_folder(
    runner, lg2_league: Lg2League, config_dir: Path
) -> None:
    build_teams(lg2_league, team="Denver", ppp_path="mine")
    ppp = put_profiles(config_dir / "leagues" / LEAGUE / "mine", DENVER)
    result = runner.invoke(check, ["off1"])
    assert heads(result) == [str(profile_file(ppp, DENVER, "off1"))]


@pytest.mark.parametrize(
    ("setting", "option", "prefix", "in_ppp"),
    [
        ("Denver", "Broncos", DENVER, True),
        ("Denver", "Las Vegas", LAS_VEGAS, False),
        (None, "Denver", DENVER, False),
        ("Denvr", "Denver", DENVER, False),
    ],
    ids=["the team team names", "another team", "team unset", "team unresolvable"],
)
def test_ppp_path_with_team_option(
    runner,
    lg2_league: Lg2League,
    tmp_path: Path,
    setting: str | None,
    option: str,
    prefix: str,
    in_ppp: bool,
) -> None:
    """`ppp_path` holds the files of the team `team` names, however --team
    names it; any other team's are at their league location."""
    ppp = put_profiles(tmp_path / "mine", DENVER)
    settings: dict[str, str | Path] = {"ppp_path": ppp}
    if setting is not None:
        settings["team"] = setting
    lg2_dir = build_teams(lg2_league, **settings)
    result = runner.invoke(check, ["off1", "--team", option])
    folder = ppp if in_ppp else location(lg2_dir, prefix)
    assert heads(result) == [str(profile_file(folder, prefix, "off1"))]


def test_team_option_beats_team(runner, lg2_league: Lg2League) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, ["off1", "--team", "Las Vegas"])
    assert heads(result) == [
        str(profile_file(location(lg2_dir, LAS_VEGAS), LAS_VEGAS, "off1"))
    ]


@pytest.mark.parametrize("kind", ["missing", "a file"])
def test_ppp_path_must_be_a_folder(
    runner, lg2_league: Lg2League, tmp_path: Path, kind: str
) -> None:
    ppp = tmp_path / "mine"
    if kind == "a file":
        ppp.write_text("x", encoding="utf-8")
    build_teams(lg2_league, team="Denver", ppp_path=ppp)
    result = runner.invoke(check, ["off1"])
    reason = DIRECTORY_INVALID if kind == "a file" else PATH_NOT_FOUND
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {ppp}: {reason} Run 'athc config set ppp_path FOLDER'.\n"
    )
    assert result.stdout == ""


# ── a key whose profile is not there ──────────────────────────────────────────


@pytest.mark.parametrize("option", [[], ["--team", "Broncos"]], ids=["team", "--team"])
def test_missing_at_your_league_location_has_the_hint(
    runner, lg2_league: Lg2League, option: list[str]
) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    missing = profile_file(location(lg2_dir, DENVER), DENVER, "off2")
    missing.unlink()
    result = runner.invoke(check, ["off2", *option])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND} {HINT}\n"


def test_missing_folder_is_the_path_phrase(runner, lg2_league: Lg2League) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    shutil.rmtree(location(lg2_dir, DENVER))
    missing = profile_file(location(lg2_dir, DENVER), DENVER, "off2")
    result = runner.invoke(check, ["off2"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {PATH_NOT_FOUND} {HINT}\n"


def test_missing_for_another_team_has_no_hint(runner, lg2_league: Lg2League) -> None:
    lg2_dir = build_teams(lg2_league, team="Denver")
    missing = profile_file(location(lg2_dir, LAS_VEGAS), LAS_VEGAS, "off2")
    missing.unlink()
    result = runner.invoke(check, ["off2", "--team", "Raiders"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND}\n"


def test_missing_in_ppp_path_has_no_hint(
    runner, lg2_league: Lg2League, tmp_path: Path
) -> None:
    ppp = tmp_path / "mine"
    ppp.mkdir()
    build_teams(lg2_league, team="Denver", ppp_path=ppp)
    result = runner.invoke(check, ["off2"])
    assert result.exit_code == 2
    assert (
        result.stderr == f"FAIL {profile_file(ppp, DENVER, 'off2')}: {FILE_NOT_FOUND}\n"
    )


# ── setup: the team, the league files ─────────────────────────────────────────


@pytest.mark.parametrize("args", KEY_RUNS, ids=lambda args: args[0])
def test_team_not_set(
    runner, lg2_league: Lg2League, config_dir: Path, args: list[str]
) -> None:
    build_teams(lg2_league)
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league_toml(config_dir)}: {TEAM_NOT_SET}\n"
    assert result.stdout == ""


def test_team_not_set_shows_before_path(
    runner, build_league: BuildLeague, write_config: WriteConfig, config_dir: Path
) -> None:
    build_league()
    write_config(athc_toml())
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league_toml(config_dir)}: {TEAM_NOT_SET}\n"


def test_team_option_with_team_unset(runner, lg2_league: Lg2League) -> None:
    lg2_dir = build_teams(lg2_league)
    result = runner.invoke(check, ["off1", "--team", "Denver"])
    assert heads(result) == [
        str(profile_file(location(lg2_dir, DENVER), DENVER, "off1"))
    ]


def test_setup_comes_before_the_files(
    runner, lg2_league: Lg2League, config_dir: Path
) -> None:
    """A missing file named outright waits for the team's setup."""
    build_teams(lg2_league)
    result = runner.invoke(diff, ["nope.prf", "off1"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league_toml(config_dir)}: {TEAM_NOT_SET}\n"


@pytest.mark.parametrize("args", KEY_RUNS, ids=lambda args: args[0])
def test_path_not_set(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    config_dir: Path,
    args: list[str],
) -> None:
    build_league(team="Denver")
    write_config(athc_toml())
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league_toml(config_dir)}: {PATH_NOT_SET}\n"


@pytest.mark.parametrize("args", KEY_RUNS, ids=lambda args: args[0])
def test_lge_missing(runner, lg2_league: Lg2League, args: list[str]) -> None:
    lg2 = lg2_league(record(DENVER), team="Denver")
    lg2.with_suffix(".lge").unlink()
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2.with_suffix('.lge')}: {FILE_NOT_FOUND}\n"


@pytest.mark.parametrize("args", KEY_RUNS, ids=lambda args: args[0])
def test_stock_lg2(runner, lg2_league: Lg2League, args: list[str]) -> None:
    lg2 = lg2_league(team(folder=""), team="Denver")
    result = run(runner, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2}: Stock league not supported.\n"


def test_team_matches_no_team(runner, lg2_league: Lg2League, config_dir: Path) -> None:
    build_teams(lg2_league, team="Denvr")
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league_toml(config_dir)}: [league] team: No team named 'Denvr'. "
        f"Teams: {TEAMS}.\n"
    )


def test_team_option_matches_no_team(runner, lg2_league: Lg2League) -> None:
    build_teams(lg2_league, team="Denver")
    result = runner.invoke(check, ["off1", "--team", "Denvr"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        f"Error: Invalid value for '--team': no team named 'Denvr'. Teams: {TEAMS}.\n"
    )


def test_team_array(runner, lg2_league: Lg2League, config_dir: Path) -> None:
    build_teams(lg2_league)
    toml = league_toml(config_dir)
    text = toml.read_text(encoding="utf-8")
    toml.write_text(
        text.replace("[league]\n", "[league]\nteam = ['Denver']\n"), encoding="utf-8"
    )
    result = runner.invoke(check, ["off1"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {toml}: [league] team: Expected a string, got an array.\n"
    )


# ── --team and --league ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "args",
    [
        ["check"],
        ["check", "x.prf"],
        ["check", "*.prf"],
        ["diff", "a.prf", "b.prf"],
        ["copy", "a.prf", "b.prf", "--stop-clock"],
    ],
    ids=["check no PATH", "check a path", "check a wildcard", "diff", "copy"],
)
def test_team_option_needs_a_key(runner, args: list[str]) -> None:
    result = run(runner, *args, "--team", "Denver")
    assert result.exit_code == 2
    assert result.stderr.endswith(TEAM_REQUIRES_KEY)
    assert result.stdout == ""


@pytest.mark.parametrize(
    "args",
    [*PLAIN_RUNS, *KEY_RUNS],
    ids=[f"{args[0]} {kind}" for kind in ("plain", "key") for args in PLAIN_RUNS],
)
def test_unknown_league(
    runner, make_league: Callable[..., Path], config_dir: Path, args: list[str]
) -> None:
    """A named league must exist, whatever the operands."""
    make_league()
    result = run(runner, *args, "--league", "NOPE")
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_plain_files_need_no_league(runner, work: Path) -> None:
    """No athc.toml and no league folder: diff and copy of plain files run."""
    target = shutil.copy2(OFF1, work / "target.prf")
    assert run(runner, "diff", str(OFF1), str(OFF1)).exit_code == 0
    result = run(runner, "copy", str(OFF1), str(target), "--stop-clock")
    assert result.exit_code == 0
    assert "1 file(s) processed, 1 updated" in result.stdout
