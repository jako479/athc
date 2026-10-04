"""`athc --league NAME`: one root-level flag for every league-aware command.

The flag lives on the umbrella group (like `aws --profile`, `gcloud
--configuration`, `kubectl --context`), not on each subcommand; subcommands read
it from the Click context via `selected_league`.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

import click
import pytest

from athc.cli import cli, selected_league
from athc.cli.convert_pdb import convert_pdb
from athc.cli.gameplan.check import check as gameplan_check
from athc.cli.generate_schedule import generate_schedule
from athc.cli.profile.check import check as profile_check
from tests.integration.conftest import OFF1, RULES_TOML

MakeLeague = Callable[..., Path]


def test_root_help_lists_league(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--league" in result.output


@pytest.mark.parametrize(
    "command", [gameplan_check, profile_check, convert_pdb, generate_schedule]
)
def test_subcommands_no_longer_take_league(runner, command: click.Command) -> None:
    result = runner.invoke(command, ["--help"])
    assert result.exit_code == 0
    assert "--league" not in result.output


def test_root_league_reaches_profile_check(runner, make_league: MakeLeague) -> None:
    make_league("PNFL")  # no rules -> would fail
    other = make_league("PCFL")
    shutil.copy(RULES_TOML, other / "rules" / "profile.toml")
    result = runner.invoke(cli, ["--league", "PCFL", "profile", "check", str(OFF1)])
    assert result.exit_code == 1  # ran against PCFL's rules and found violations


def test_root_league_unknown_folder(
    runner, make_league: MakeLeague, caplog: pytest.LogCaptureFixture
) -> None:
    make_league("PNFL")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(cli, ["--league", "NOPE", "profile", "check", str(OFF1)])
    assert result.exit_code == 2
    assert "NOPE" in caplog.text and "not found" in caplog.text


def test_root_league_from_env(
    runner, make_league: MakeLeague, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = make_league("PCFL")
    shutil.copy(RULES_TOML, other / "rules" / "profile.toml")
    monkeypatch.setenv("ATHC_LEAGUE", "PCFL")
    result = runner.invoke(cli, ["profile", "check", str(OFF1)])
    assert result.exit_code == 1


def test_selected_league_reads_root_context() -> None:
    ctx = click.Context(click.Command("x"), obj={"league": "PCFL"})
    assert selected_league(ctx) == "PCFL"


def test_selected_league_is_none_without_root() -> None:
    # A subcommand invoked on its own (tests, embedding) has no root object.
    assert selected_league(click.Context(click.Command("x"))) is None
