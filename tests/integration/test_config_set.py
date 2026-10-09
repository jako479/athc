"""`athc config set` and the comment-preserving writer behind it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.config.set import set_
from athc.config import set_config_value
from tests.conftest import LEAGUE, OTHER_LEAGUE

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

COMMENTED = f"""\
; athc settings -- edit to taste
[athc]
; the league the tools use
league = {LEAGUE}

[autocontinue]
; seconds before clicking
delay_before_continue = 1.0
"""


# ── set_config_value ──


def test_set_updates_value_and_keeps_comments(write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    set_config_value("league", OTHER_LEAGUE)
    text = ini.read_text(encoding="utf-8")
    assert f"league = {OTHER_LEAGUE}" in text
    assert "; athc settings -- edit to taste" in text
    assert "; the league the tools use" in text
    assert "; seconds before clicking" in text
    assert "delay_before_continue = 1.0" in text


def test_set_adds_missing_key(write_config: WriteConfig) -> None:
    ini = write_config("[athc]\n\n[autocontinue]\nhot_corner = true\n")
    set_config_value("league", LEAGUE)
    text = ini.read_text(encoding="utf-8")
    assert f"league = {LEAGUE}" in text
    assert text.index(f"league = {LEAGUE}") < text.index("[autocontinue]")
    assert "hot_corner = true" in text


def test_set_adds_missing_section(write_config: WriteConfig) -> None:
    ini = write_config("[autocontinue]\nhot_corner = true\n")
    set_config_value("league", LEAGUE)
    text = ini.read_text(encoding="utf-8")
    assert "[athc]" in text
    assert f"league = {LEAGUE}" in text
    assert "hot_corner = true" in text


def test_set_creates_missing_file(config_dir: Path) -> None:
    written = set_config_value("league", LEAGUE)
    assert written == config_dir / "athc.ini"
    assert written.read_text(encoding="utf-8") == f"[athc]\nleague = {LEAGUE}\n"


# ── athc config set (CLI) ──


def test_cli_sets_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(OTHER_LEAGUE)
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"Set league = {OTHER_LEAGUE}\n"
    assert f"league = {OTHER_LEAGUE}" in ini.read_text(encoding="utf-8")
    assert "; the league the tools use" in ini.read_text(encoding="utf-8")


def test_cli_rejects_unknown_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", OTHER_LEAGUE])
    assert result.exit_code == 2
    assert "not found" in result.stderr
    assert f"Available: {LEAGUE}" in result.stderr
    assert f"league = {LEAGUE}" in ini.read_text(encoding="utf-8")  # untouched


def test_cli_rejects_blank_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", ""])
    assert result.exit_code == 2
    assert "not found" in result.stderr
    assert f"league = {LEAGUE}" in ini.read_text(encoding="utf-8")  # untouched


def test_cli_malformed_ini_is_clean_error(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    ini = write_config("[athc\nbroken\n")
    result = runner.invoke(set_, ["league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {ini}: line 1: no [section] header above it\n"
    assert result.stdout == ""
    assert ini.read_text(encoding="utf-8") == "[athc\nbroken\n"  # left as written


def test_cli_rejects_unknown_key(runner, write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["colour", "blue"])
    assert result.exit_code == 2
    assert "unknown key 'colour'" in result.stderr
    assert "league" in result.stderr  # names the known keys
    assert "colour" not in ini.read_text(encoding="utf-8")


def test_cli_help_lists_known_keys(runner) -> None:
    result = runner.invoke(set_, ["--help"])
    assert result.exit_code == 0
    assert "league" in result.stdout


@pytest.mark.usefixtures("config_dir")
def test_group_lists_set(runner) -> None:
    from athc.cli.config import config as config_group

    result = runner.invoke(config_group, ["--help"])
    assert "set" in result.stdout
