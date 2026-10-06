"""`--league NAME`: an option on each league-aware command, not on the root.

Each command that reads league data adds the shared `league_option`, so the
flag goes after the command name like any other option (`athc profile check
--league NAME ...`), the way `aws s3 ls --profile x` and `kubectl get --context
x` take theirs.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import click
import pytest

from athc.cli import cli
from athc.cli.check_ppp import check_ppp
from athc.cli.convert_pdb import convert_pdb
from athc.cli.gameplan.check import check as gameplan_check
from athc.cli.gameplan.replace_play import replace_play
from athc.cli.gameplan.set_normals import set_normals
from athc.cli.gameplan.set_specials import set_specials
from athc.cli.generate_schedule import generate_schedule
from athc.cli.profile.check import check as profile_check
from tests.conftest import LEAGUE, OTHER_LEAGUE
from tests.integration.conftest import DATA, GP_OFFENSE, OFF1, RULES_TOML

MakeLeague = Callable[..., Path]

LEAGUE_COMMANDS = [
    gameplan_check,
    replace_play,
    set_normals,
    set_specials,
    profile_check,
    check_ppp,
    convert_pdb,
    generate_schedule,
]


def test_root_help_has_no_league(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--league" not in result.output


def test_root_rejects_league(runner) -> None:
    result = runner.invoke(cli, ["--league", LEAGUE, "profile", "check", str(OFF1)])
    assert result.exit_code == 2
    assert "No such option" in result.output


@pytest.mark.parametrize("command", LEAGUE_COMMANDS)
def test_league_commands_take_league(runner, command: click.Command) -> None:
    result = runner.invoke(command, ["--help"])
    assert result.exit_code == 0
    assert "--league name" in result.output


def _unknown_league_args(command: click.Command, tmp_path: Path) -> list[str]:
    """Arguments that get `command` as far as resolving its league."""
    plays = tmp_path / "plays.txt"
    plays.write_text("Some Play\n", encoding="utf-8")
    if command is gameplan_check:
        return [str(GP_OFFENSE)]
    if command is replace_play:
        return ["Old Play", "New Play", str(GP_OFFENSE)]
    if command in (set_normals, set_specials):
        return [str(GP_OFFENSE), str(plays)]
    if command is profile_check:
        return [str(OFF1)]
    if command is check_ppp:
        return [str(OFF1), str(GP_OFFENSE)]
    if command is convert_pdb:
        return [str(DATA / "2045-2047.pdb"), str(tmp_path / "out.xlsx")]
    return ["--season", "2048"]  # generate_schedule


@pytest.mark.parametrize("command", LEAGUE_COMMANDS)
def test_league_flag_reaches_the_command(
    runner,
    make_league: MakeLeague,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    command: click.Command,
) -> None:
    make_league()
    args = [*_unknown_league_args(command, tmp_path), "--league", "NOPE"]
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(command, args)
    assert result.exit_code != 0
    assert "league 'NOPE' not found" in caplog.text


def test_league_flag_picks_profile_rules(runner, make_league: MakeLeague) -> None:
    make_league()  # no rules -> would fail
    other = make_league(OTHER_LEAGUE)
    shutil.copy(RULES_TOML, other / "rules" / "profile.toml")
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
    assert "Usage:" in result.output


@pytest.mark.parametrize(
    ("path", "shown", "hidden"),
    [
        (("config", "set"), ["key value"], ["KEY", "VALUE"]),
        (
            ("convert-pdb",),
            ["pdb_file output_file", "--pln-off pln_file"],
            ["PDBFILE", "OUTPUTFILE", "PATH"],
        ),
        (("gameplan", "check"), ["path..."], ["PATH"]),
        (("gameplan", "find-play"), ["play... path"], ["PLAY", "PATH"]),
        (
            ("gameplan", "replace-play"),
            ["play replacement path"],
            ["PLAY", "REPLACEMENT", "PATH"],
        ),
        (
            ("gameplan", "set-normals"),
            ["gameplan input_file"],
            ["GAMEPLAN_PATH", "INPUT_PATH"],
        ),
        (
            ("gameplan", "set-specials"),
            ["path input_file"],
            ["TARGET", "INPUT_PATH"],
        ),
        (
            ("generate-schedule",),
            ["--season year", "--seed number", "--time-limit number"],
            ["INTEGER"],
        ),
        (("profile", "check"), ["path...", "--gameplan pln_file"], ["PATH"]),
        (
            ("profile", "diff"),
            ["file1 file2", "--output file"],
            ["A.prf", "B.prf", "FILE"],
        ),
        (("check-ppp",), ["path [path]"], ["PATH", "FIRST", "SECOND"]),
    ],
    ids=lambda v: " ".join(v) if isinstance(v, tuple) else "",
)
def test_help_uses_lowercase_names(
    runner, path: tuple[str, ...], shown: list[str], hidden: list[str]
) -> None:
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    output = " ".join(result.output.split())  # a long usage line wraps
    for text in shown:
        assert text in output
    for text in hidden:
        assert text not in output


USAGE_CASES = [
    ((), "athc [-h] [--version] command [args]..."),
    (("gameplan",), "athc gameplan [-h] command [args]..."),
    (
        ("gameplan", "list-normals"),
        "athc gameplan list-normals [-h] [--sort slot|name] gameplan [output_file]",
    ),
    (("gameplan", "find-play"), "athc gameplan find-play [-h] [-r] play... path"),
    (("profile", "diff"), "athc profile diff [-h] [-o file] file1 file2"),
    (
        ("generate-schedule",),
        "athc generate-schedule [-h] --season year [--seed number] "
        "[--time-limit number] [--league name]",
    ),
    (("autocontinue",), "athc autocontinue [-h] [--hot-corner | --no-hot-corner]"),
    (("check-playpool",), "athc check-playpool [-h] [--league name] [play_dir]"),
    (("check-ppp",), "athc check-ppp [-h] [-r] [--league name] path [path]"),
    (
        ("convert-pdb",),
        "athc convert-pdb [-h] [-o pln_file] [-o2 pln_file] [-d pln_file] "
        "[-d2 pln_file] [--skip-calcs] [--league name] pdb_file output_file",
    ),
]


@pytest.mark.parametrize(
    ("path", "usage"),
    USAGE_CASES,
    ids=[" ".join(path) or "athc" for path, _ in USAGE_CASES],
)
def test_usage_lists_each_option(runner, path: tuple[str, ...], usage: str) -> None:
    result = runner.invoke(cli, [*path, "-h"], prog_name="athc")
    assert result.exit_code == 0
    block = result.output.split("\n\n", 1)[0]  # the usage line, however wrapped
    assert " ".join(block.split()) == f"Usage: {usage}"


def test_long_usage_wraps_between_options(runner) -> None:
    result = runner.invoke(cli, ["convert-pdb", "-h"], prog_name="athc")
    usage = result.output.split("\n\n", 1)[0].splitlines()
    assert len(usage) > 1  # long enough to wrap
    for line in usage:
        assert line.count("[") == line.count("]"), line  # no option split


def test_root_ignores_athc_league_env(
    runner,
    make_league: MakeLeague,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    other = make_league(OTHER_LEAGUE)
    shutil.copy(RULES_TOML, other / "rules" / "profile.toml")
    monkeypatch.setenv("ATHC_LEAGUE", OTHER_LEAGUE)
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(cli, ["profile", "check", str(OFF1)])
    assert result.exit_code == 2
    assert "no league selected" in caplog.text
