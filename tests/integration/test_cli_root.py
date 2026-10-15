"""`--league NAME`: an option on each league-aware command, not on the root.

Each command that reads league data adds the shared `league_option`, so the
flag goes after the command name like any other option (`athc profile check
--league NAME ...`), the way `aws s3 ls --profile x` and `kubectl get --context
x` take theirs.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import click
import pytest

from athc.cli import cli
from athc.cli.check_ppp import check_ppp
from athc.cli.convert_pdb import convert_pdb
from athc.cli.gameplan.check import check as gameplan_check
from athc.cli.gameplan.find_play import find_play
from athc.cli.gameplan.list_normals import list_normals
from athc.cli.gameplan.list_specials import list_specials
from athc.cli.gameplan.replace_play import replace_play
from athc.cli.gameplan.set_normals import set_normals
from athc.cli.gameplan.set_specials import set_specials
from athc.cli.generate_schedule import generate_schedule
from athc.cli.profile.check import check as profile_check
from athc.cli.profile.copy import copy as profile_copy
from athc.cli.profile.diff import diff as profile_diff
from athc.cli.standings import standings
from tests.conftest import LEAGUE, OTHER_LEAGUE, league_not_found, no_league_selected
from tests.integration.conftest import DATA, GP_OFFENSE, OFF1, RULES_TOML

MakeLeague = Callable[..., Path]

LEAGUE_COMMANDS = [
    gameplan_check,
    find_play,
    list_normals,
    list_specials,
    replace_play,
    set_normals,
    set_specials,
    profile_check,
    profile_diff,
    profile_copy,
    check_ppp,
    convert_pdb,
    generate_schedule,
    standings,
]


def test_root_help_has_no_league(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--league" not in result.stdout


def test_root_rejects_league(runner) -> None:
    result = runner.invoke(cli, ["--league", LEAGUE, "profile", "check", str(OFF1)])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


@pytest.mark.parametrize("command", LEAGUE_COMMANDS)
def test_league_commands_take_league(runner, command: click.Command) -> None:
    """Every one reads the same: `--league NAME` and the shared help text."""
    result = runner.invoke(command, ["--help"])
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())  # the help text wraps
    assert (
        "--league NAME League to use (default: the one set with athc config set "
        "league)." in output
    )


def _unknown_league_args(command: click.Command, tmp_path: Path) -> list[str]:
    """Arguments that get `command` as far as resolving its league."""
    plays = tmp_path / "plays.txt"
    plays.write_text("Some Play\n", encoding="utf-8")
    if command in (gameplan_check, list_normals, list_specials):
        return [str(GP_OFFENSE)]
    if command is find_play:
        return ["Some Play", "--path", str(GP_OFFENSE)]
    if command is replace_play:
        return ["Old Play", "New Play", "--path", str(GP_OFFENSE)]
    if command is set_normals:
        return [str(GP_OFFENSE), str(plays)]
    if command is set_specials:
        return [str(plays), "--path", str(GP_OFFENSE)]
    if command is profile_check:
        return [str(OFF1)]
    if command is profile_diff:
        return [str(OFF1), str(OFF1)]
    if command is profile_copy:
        return [str(OFF1), str(OFF1), "--stop-clock"]
    if command is check_ppp:
        return [str(OFF1), str(GP_OFFENSE)]
    if command is convert_pdb:
        return [str(DATA / "2045-2047.pdb"), str(tmp_path / "out.xlsx")]
    if command is standings:
        return []
    return ["--season", "2048", "--previous", str(tmp_path)]  # generate_schedule


@pytest.mark.parametrize("command", LEAGUE_COMMANDS)
def test_league_flag_reaches_the_command(
    runner,
    make_league: MakeLeague,
    config_dir: Path,
    tmp_path: Path,
    command: click.Command,
) -> None:
    make_league()
    args = [*_unknown_league_args(command, tmp_path), "--league", "NOPE"]
    result = runner.invoke(command, args)
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_league_flag_picks_profile_rules(runner, make_league: MakeLeague) -> None:
    make_league()  # no rules -> would fail
    other = make_league(OTHER_LEAGUE)
    shutil.copy(RULES_TOML, other / "profile.toml")
    result = runner.invoke(
        cli, ["profile", "check", "--league", OTHER_LEAGUE, str(OFF1)]
    )
    assert (
        result.exit_code == 1
    )  # ran against the other league's rules and found violations


def _command_paths(
    group: click.Group, ctx: click.Context, prefix: tuple[str, ...] = ()
) -> Iterator[tuple[str, ...]]:
    """Every command path under `group`, subgroups included."""
    for name in group.list_commands(ctx):
        command = group.get_command(ctx, name)
        path = (*prefix, name)
        yield path
        if isinstance(command, click.Group):
            sub_ctx = click.Context(command, parent=ctx, info_name=name)
            yield from _command_paths(command, sub_ctx, path)


COMMAND_PATHS = [(), *_command_paths(cli, click.Context(cli, info_name="athc"))]


@pytest.mark.parametrize("path", COMMAND_PATHS, ids=lambda p: " ".join(p) or "athc")
def test_short_help_option_on_every_command(runner, path: tuple[str, ...]) -> None:
    result = runner.invoke(cli, [*path, "-h"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    ("path", "shown", "hidden"),
    [
        (
            ("convert-pdb",),
            [
                "PDB_FILE [OUTPUT_FILE]",
                "--pln-off GAME_PLAN",
                "--path FOLDER",
                "--team NAME",
                "--percentages / --no-percentages",
            ],
            ["PDBFILE", "OUTPUTFILE", "pdb_file", "pln_file"],
        ),
        (
            ("gameplan", "check"),
            ["[PATH]...", "--team NAME"],
            ["[path]", "PATHS"],
        ),
        (
            ("gameplan", "find-play"),
            ["PLAY...", "--path PATH", "--team NAME", "--league NAME"],
            ["PLAYS", "[PATH]"],
        ),
        (
            ("gameplan", "replace-play"),
            ["PLAY REPLACEMENT...", "--path PATH", "--team NAME"],
            ["PATH]"],
        ),
        (
            ("gameplan", "list-normals"),
            ["GAME_PLAN [OUTPUT_FILE]", "--team NAME"],
            ["GAMEPLAN", "OUTPUT_PATH", "[output_file]"],
        ),
        (
            ("gameplan", "set-normals"),
            ["GAME_PLAN INPUT_FILE", "--team NAME"],
            ["GAMEPLAN_PATH", "PLAY_LIST", "play_list"],
        ),
        (
            ("gameplan", "set-specials"),
            ["INPUT_FILE", "--path PATH", "--team NAME"],
            ["PATH INPUT_FILE"],
        ),
        (
            ("generate-schedule",),
            [
                "--season YEAR",
                "--previous FILE",
                "--upcoming FILE",
                "--seed NUMBER",
                "--phase2-time-limit LIMIT",
            ],
            ["INTEGER", "--season year"],
        ),
        (("playpool", "check"), ["[FOLDER]"], ["PLAY_DIR", "play_dir"]),
        (
            ("profile", "check"),
            ["[PATH]...", "--team NAME"],
            ["[path]", "PATHS"],
        ),
        (
            ("profile", "copy"),
            ["SOURCE TARGET...", "--team NAME"],
            ["source target"],
        ),
        (
            ("profile", "diff"),
            ["PROFILE1 PROFILE2", "--output FILE", "--team NAME"],
            ["file1", "A.prf", "--output file"],
        ),
        (
            ("check-ppp",),
            ["[PATH]...", "--team NAME"],
            ["path [path]", "PATH [PATH]", "FIRST", "SECOND", "--team name"],
        ),
    ],
    ids=lambda v: " ".join(v) if isinstance(v, tuple) else "",
)
def test_help_uses_uppercase_names(
    runner, path: tuple[str, ...], shown: list[str], hidden: list[str]
) -> None:
    """Placeholders are UPPERCASE with underscores, one name per kind of value."""
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())  # a long usage line wraps
    for text in shown:
        assert text in output
    for text in hidden:
        assert text not in output


USAGE_CASES = [
    ((), "athc [OPTIONS] COMMAND [ARGS]..."),
    (("gameplan",), "athc gameplan [OPTIONS] COMMAND [ARGS]..."),
    (
        ("gameplan", "list-normals"),
        "athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT_FILE]",
    ),
    (("gameplan", "find-play"), "athc gameplan find-play [OPTIONS] PLAY..."),
    (("profile", "diff"), "athc profile diff [OPTIONS] PROFILE1 PROFILE2"),
    (("generate-schedule",), "athc generate-schedule [OPTIONS]"),
    (("autocontinue",), "athc autocontinue [OPTIONS]"),
    (("playpool",), "athc playpool [OPTIONS] COMMAND [ARGS]..."),
    (("playpool", "check"), "athc playpool check [OPTIONS] [FOLDER]"),
    (("check-ppp",), "athc check-ppp [OPTIONS] [PATH]..."),
    (("convert-pdb",), "athc convert-pdb [OPTIONS] PDB_FILE [OUTPUT_FILE]"),
    (("standings",), "athc standings [OPTIONS]"),
]


@pytest.mark.parametrize(
    ("path", "usage"),
    USAGE_CASES,
    ids=[" ".join(path) or "athc" for path, _ in USAGE_CASES],
)
def test_usage_is_clicks_own(runner, path: tuple[str, ...], usage: str) -> None:
    """One `[OPTIONS]`, then the arguments; a group ends in `COMMAND [ARGS]...`."""
    result = runner.invoke(cli, [*path, "-h"], prog_name="athc")
    assert result.exit_code == 0
    block = result.stdout.split("\n\n", 1)[0]  # the usage line, however wrapped
    assert " ".join(block.split()) == f"Usage: {usage}"


# Each leaf command with fixed positionals and a value for each of them: the
# last one is accepted (each command's own tests), one past it is not.
ALL_POSITIONALS = [
    (("convert-pdb",), ["a.pdb", "b.xlsx"]),
    (("gameplan", "list-normals"), ["a.pln", "b.txt"]),
    (("gameplan", "list-specials"), ["a.pln", "b.txt"]),
    (("gameplan", "set-normals"), ["a.pln", "b.txt"]),
    (("gameplan", "set-specials"), ["a.txt"]),
    (("profile", "diff"), ["a.prf", "b.prf"]),
    (("config", "set"), ["team", "Denver"]),
    (("config", "get"), ["team"]),
    (("config", "path"), ["athc.ini"]),
    (("playpool", "check"), ["plays"]),
]


@pytest.mark.parametrize(
    ("path", "positionals"),
    ALL_POSITIONALS,
    ids=[" ".join(path) for path, _ in ALL_POSITIONALS],
)
def test_one_positional_past_the_last_is_rejected(
    runner, path: tuple[str, ...], positionals: list[str]
) -> None:
    result = runner.invoke(cli, [*path, *positionals, "x"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (x).\n")


RECURSIVE_COMMANDS = [
    ("check-ppp",),
    ("gameplan", "check"),
    ("gameplan", "find-play"),
    ("gameplan", "replace-play"),
    ("gameplan", "set-specials"),
    ("profile", "check"),
    ("profile", "copy"),
]


@pytest.mark.parametrize("path", RECURSIVE_COMMANDS, ids=" ".join)
def test_recursive_option_reads_the_same(runner, path: tuple[str, ...]) -> None:
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())  # the help column width varies
    assert "-r, --recursive Include subfolders. " in output


def test_root_ignores_athc_league_env(
    runner,
    make_league: MakeLeague,
    config_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = make_league(OTHER_LEAGUE)
    shutil.copy(RULES_TOML, other / "profile.toml")
    monkeypatch.setenv("ATHC_LEAGUE", OTHER_LEAGUE)
    result = runner.invoke(cli, ["profile", "check", str(OFF1)])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, OTHER_LEAGUE)
