"""`athc config set` and the comment-preserving writer behind it: `league`
into athc.ini, the other keys into the league's league.toml."""

from __future__ import annotations

import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli import cli
from athc.cli.config.set import set_
from athc.config import set_config_value
from tests.conftest import (
    LEAGUE,
    OTHER_LEAGUE,
    ROOT,
    league_not_found,
    no_league_selected,
    toml_error,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

COMMENTED = f"""\
; athc settings -- edit to taste
[athc]
; the league the tools use
league = {LEAGUE}

[autocontinue]
; seconds before clicking
continue_pause = 1.0
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
    assert "continue_pause = 1.0" in text


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
    assert result.stdout == f"OK   {ini}: league = {OTHER_LEAGUE}\n"
    assert f"league = {OTHER_LEAGUE}" in ini.read_text(encoding="utf-8")
    assert "; the league the tools use" in ini.read_text(encoding="utf-8")


def test_cli_sets_league_in_its_canonical_spelling(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(OTHER_LEAGUE)
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["League", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {ini}: league = {OTHER_LEAGUE}\n"
    lines = ini.read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if line.casefold().startswith("league")] == [
        f"league = {OTHER_LEAGUE}"
    ]


def test_cli_rejects_unknown_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", OTHER_LEAGUE])
    assert result.exit_code == 2
    # Click's sentence goes on, so athc's part starts lowercase.
    assert f"Error: Invalid value for 'VALUE': league '{OTHER_LEAGUE}' not found. " in (
        result.stderr
    )
    assert result.stderr.endswith(f"Available: {LEAGUE}.\n")
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
    assert result.stderr == (
        f"FAIL {ini}: Not valid INI: No [section] header above it (at line 1).\n"
    )
    assert result.stdout == ""
    assert ini.read_text(encoding="utf-8") == "[athc\nbroken\n"  # left as written


def test_cli_rejects_unknown_key(runner, write_config: WriteConfig) -> None:
    """The five keys are accepted in the writes in this file; one past them
    is not."""
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["colour", "blue"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', "
        "'play_path', 'team', 'ppp_path'.\n"
    )
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


def test_cli_league_needs_a_value(runner, write_config: WriteConfig) -> None:
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'VALUE'.\n")
    assert ini.read_text(encoding="utf-8") == COMMENTED


def test_cli_needs_a_key(runner) -> None:
    result = runner.invoke(set_, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'KEY'.\n")


def test_cli_a_word_too_many(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(OTHER_LEAGUE)
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", OTHER_LEAGUE, "x"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (x).\n")
    assert ini.read_text(encoding="utf-8") == COMMENTED


def test_cli_set_league_refuses_a_named_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    make_league(OTHER_LEAGUE)
    ini = write_config(COMMENTED)
    result = runner.invoke(set_, ["league", OTHER_LEAGUE, "--league", LEAGUE])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: --league cannot be used with set league.\n")
    assert ini.read_text(encoding="utf-8") == COMMENTED


# ── athc config set: the league.toml keys ──

# A league.toml as shipped: comments, the four settings, then other tables.
LEAGUE_TOML = """\
# Open this file with: athc config edit league.toml

[league]
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\\SIERRA\\FBPRO98'
# The folder that holds this league's plays (.ply files).
play_path = 'C:\\SIERRA\\FBPRO98\\PNFL'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\\PNFL\\Denver'

[categories.offense]
"Run Right" = "RR"
"""


def _league_values(toml: Path) -> dict[str, object]:
    return tomllib.loads(toml.read_text(encoding="utf-8"))["league"]


def _kept(before: str, after: str, key: str) -> bool:
    """Every line of `before` but `key`'s own is still in `after`."""
    lines = after.splitlines()
    return all(
        line in lines for line in before.splitlines() if not line.startswith(f"{key} =")
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("path", "E:\\Leagues"),
        ("play_path", "E:\\Leagues\\PNFL"),
        ("team", "Miami"),
        ("ppp_path", "E:\\Coach\\Miami"),
    ],
)
def test_cli_sets_a_league_key(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    key: str,
    value: str,
) -> None:
    toml = make_league(LEAGUE, LEAGUE_TOML) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, [key, value])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {toml}: {key} = {value}\n"
    assert _league_values(toml)[key] == value
    assert _kept(LEAGUE_TOML, toml.read_text(encoding="utf-8"), key)


SHIPPED_LEAGUE_TOML = ROOT / "config" / "release" / "leagues" / "PNFL" / "league.toml"


def test_cli_adds_a_key_after_its_example(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """The shipped league.toml has team and ppp_path as commented examples:
    each new line goes right after its example, and every old line stays."""
    before = SHIPPED_LEAGUE_TOML.read_text(encoding="utf-8").splitlines()
    toml = make_league() / "league.toml"
    shutil.copyfile(SHIPPED_LEAGUE_TOML, toml)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    assert runner.invoke(set_, ["team", "Denver"]).exit_code == 0
    assert runner.invoke(set_, ["ppp_path", "D:\\PNFL\\Denver"]).exit_code == 0
    after = toml.read_text(encoding="utf-8").splitlines()
    team = after.index("team = 'Denver'")
    ppp_path = after.index("ppp_path = 'D:\\PNFL\\Denver'")
    assert after[team - 1] == "# team = 'Denver'"
    assert after[ppp_path - 1] == "# ppp_path = 'D:\\PNFL\\Denver'"
    assert [line for i, line in enumerate(after) if i not in (team, ppp_path)] == (
        before
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "[league]\npath = 'C:\\SIERRA'\n\n# Category names.\n[categories.offense]\n",
            "[league]\npath = 'C:\\SIERRA'\nteam = 'Denver'\n\n# Category names.\n"
            "[categories.offense]\n",
        ),
        (
            "[league]\n# Settings.\n\n# Category names.\n[categories.offense]\n",
            "[league]\nteam = 'Denver'\n# Settings.\n\n# Category names.\n"
            "[categories.offense]\n",
        ),
    ],
    ids=["after the last key", "after the header"],
)
def test_cli_adds_a_key_with_no_example(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    body: str,
    expected: str,
) -> None:
    """No commented example: the new line follows `[league]`'s last key line,
    or its header when it has none, never the comment that opens the next
    table."""
    toml = make_league(LEAGUE, body) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    assert runner.invoke(set_, ["team", "Denver"]).exit_code == 0
    assert toml.read_text(encoding="utf-8") == expected


def test_cli_adds_a_key_to_an_inline_league_table(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """A `[league]` written with no header line takes the key as tomlkit
    adds it."""
    toml = make_league(LEAGUE, "league = { path = 'C:\\SIERRA' }\n") / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    assert runner.invoke(set_, ["team", "Denver"]).exit_code == 0
    assert _league_values(toml) == {"path": "C:\\SIERRA", "team": "Denver"}


def test_cli_writes_the_canonical_key(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    toml = make_league(LEAGUE, LEAGUE_TOML) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["Play_Path", "E:\\Plays"])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {toml}: play_path = E:\\Plays\n"
    assert _league_values(toml)["play_path"] == "E:\\Plays"
    assert "Play_Path" not in toml.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("key", "value"),
    [("ppp_path", "Denver"), ("path", "Z:\\No\\Such\\Folder")],
    ids=["relative", "missing folder"],
)
def test_cli_writes_a_folder_as_supplied(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    key: str,
    value: str,
) -> None:
    toml = make_league(LEAGUE, LEAGUE_TOML) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, [key, value])
    assert result.exit_code == 0
    assert _league_values(toml)[key] == value


def test_cli_league_key_in_the_named_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    mine = make_league(LEAGUE, LEAGUE_TOML) / "league.toml"
    other = make_league(OTHER_LEAGUE, LEAGUE_TOML) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["team", "Miami", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {other}: team = Miami\n"
    assert _league_values(other)["team"] == "Miami"
    assert mine.read_text(encoding="utf-8") == LEAGUE_TOML


def test_cli_league_key_with_no_league_set(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    toml = make_league(LEAGUE, LEAGUE_TOML) / "league.toml"
    result = runner.invoke(set_, ["team", "Miami"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert toml.read_text(encoding="utf-8") == LEAGUE_TOML


def test_cli_league_key_with_an_unknown_league(
    runner, make_league: MakeLeague, write_config: WriteConfig, config_dir: Path
) -> None:
    make_league(LEAGUE, LEAGUE_TOML)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["team", "Miami", "--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_cli_league_key_with_no_league_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    toml = make_league() / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {toml}: The system cannot find the file specified.\n"
    )
    assert result.stdout == ""
    assert not toml.exists()  # nothing created


def test_cli_league_key_with_no_league_section(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    body = '[categories.offense]\n"Run Right" = "RR"\n'
    toml = make_league(LEAGUE, body) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {toml}: The system cannot find the file specified.\n"
    )
    assert toml.read_text(encoding="utf-8") == body  # unchanged


def test_cli_league_key_with_a_malformed_league_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    body = "[league\nteam = 'Denver'\n"
    toml = make_league(LEAGUE, body) / "league.toml"
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = runner.invoke(set_, ["team", "Miami"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {toml}: {toml_error(body)}\n"
    assert toml.read_text(encoding="utf-8") == body  # unchanged


# ── help screen, as an 80-column console shows it ──

SET_HELP = """\
Usage: athc config set [OPTIONS] KEY VALUE

  Set a value in athc.ini or league.toml.

  league goes in athc.ini, the other keys in the league's league.toml.

Positional arguments:
  KEY    Setting to change: league, path, play_path, team or ppp_path.
  VALUE  New value.

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config set league PCFL
    athc config set play_path C:\\SIERRA\\FBPRO98\\PNFL
    athc config set team Denver
"""


def test_help_screen(runner) -> None:
    """KEY lists the five keys; --league NAME shows. Click wraps help 78 wide
    in an 80-column console; CliRunner would force 80."""
    result = runner.invoke(
        cli, ["config", "set", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == SET_HELP
