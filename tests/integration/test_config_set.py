"""`athc config set` and the comment-preserving writer behind it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.config.set import set_
from athc.config import set_config_value

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

COMMENTED = """\
; athc settings -- edit to taste
[athc]
; the league the tools use
league = PNFL

[autocontinue]
; seconds before clicking
delay_before_continue = 1.0
"""


# ── set_config_value ──


def test_set_updates_value_and_keeps_comments(write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    set_config_value("league", "PCFL")
    text = ini.read_text(encoding="utf-8")
    assert "league = PCFL" in text
    assert "; athc settings -- edit to taste" in text
    assert "; the league the tools use" in text
    assert "; seconds before clicking" in text
    assert "delay_before_continue = 1.0" in text


def test_set_adds_missing_key(write_config: WriteConfig) -> None:
    ini = write_config("[athc]\n\n[autocontinue]\nhot_corner = true\n")
    set_config_value("league", "PNFL")
    text = ini.read_text(encoding="utf-8")
    assert "league = PNFL" in text
    assert text.index("league = PNFL") < text.index("[autocontinue]")
    assert "hot_corner = true" in text


def test_set_adds_missing_section(write_config: WriteConfig) -> None:
    ini = write_config("[autocontinue]\nhot_corner = true\n")
    set_config_value("league", "PNFL")
    text = ini.read_text(encoding="utf-8")
    assert "[athc]" in text
    assert "league = PNFL" in text
    assert "hot_corner = true" in text


def test_set_creates_missing_file(config_dir: Path) -> None:
    written = set_config_value("league", "PNFL")
    assert written == config_dir / "athc.ini"
    assert written.read_text(encoding="utf-8") == "[athc]\nleague = PNFL\n"


# ── athc config set (CLI) ──


def test_cli_sets_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PCFL")
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", "PCFL"])
    assert result.exit_code == 0
    assert result.output.strip() == "Set league = PCFL"
    assert "league = PCFL" in ini.read_text(encoding="utf-8")
    assert "; the league the tools use" in ini.read_text(encoding="utf-8")


def test_cli_rejects_unknown_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL")
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", "PCFL"])
    assert result.exit_code == 2
    assert "not found" in result.output
    assert "Available: PNFL" in result.output
    assert "league = PNFL" in ini.read_text(encoding="utf-8")  # untouched


def test_cli_rejects_blank_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL")
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", ""])
    assert result.exit_code == 2
    assert "not found" in result.output
    assert "league = PNFL" in ini.read_text(encoding="utf-8")  # untouched


def test_cli_malformed_ini_is_clean_error(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL")
    ini = write_config("[athc\nbroken\n")
    result = runner.invoke(set_, ["league", "PNFL"])
    assert result.exit_code == 2
    assert "athc.ini" in result.output
    assert "unexpected error" not in result.output
    assert "Traceback" not in result.output
    assert ini.read_text(encoding="utf-8") == "[athc\nbroken\n"  # left as written


def test_cli_rejects_unknown_key(runner, write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["colour", "blue"])
    assert result.exit_code == 2
    assert "unknown key 'colour'" in result.output
    assert "league" in result.output  # names the known keys
    assert "colour" not in ini.read_text(encoding="utf-8")


def test_cli_help_lists_known_keys(runner) -> None:
    result = runner.invoke(set_, ["--help"])
    assert result.exit_code == 0
    assert "league" in result.output


@pytest.mark.usefixtures("config_dir")
def test_group_lists_set(runner) -> None:
    from athc.cli.config import config as config_group

    result = runner.invoke(config_group, ["--help"])
    assert "set" in result.output
