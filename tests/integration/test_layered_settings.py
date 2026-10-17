"""`layered_settings`: a tool's `athc.toml` table with the league's
`league.toml` table laid over it key by key, and the file that set each key.

Shown on a throwaway `[tool]` table; convert-pdb's own keys are tested in
tests/unit/pdbtoexcel/test_config.py. Integration tier: both files are read
from the config dir.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import (
    ConfigFileError,
    LeagueConfig,
    config_file,
    layered_settings,
    load_league_config,
)
from tests.conftest import LEAGUE

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


@pytest.fixture
def league_file(make_league: MakeLeague) -> Callable[[str | None], Path]:
    """Make the test league, with `body` as its league.toml when given (none
    otherwise); returns the league.toml path."""

    def _make(body: str | None = None) -> Path:
        return make_league(LEAGUE, body) / "league.toml"

    return _make


def _league() -> LeagueConfig:
    return load_league_config(LEAGUE)


# ── one file alone ──


def test_base_alone(write_config: WriteConfig, league_file) -> None:
    write_config("[tool]\na = 1\n")
    league_file()
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": 1}
    assert settings.source("a") == config_file()


def test_league_alone(league_file) -> None:
    toml = league_file("[tool]\na = 2\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": 2}
    assert settings.source("a") == toml


def test_no_file_anywhere_is_empty(league_file) -> None:
    league_file()
    settings = layered_settings("tool", _league())
    assert settings.values == {}
    assert settings.sources == {}


def test_neither_file_has_the_table(write_config: WriteConfig, league_file) -> None:
    write_config("[other]\na = 1\n")
    league_file("[league]\n")
    assert layered_settings("tool", _league()).values == {}


# ── key by key ──


def test_league_key_replaces_base_key(write_config: WriteConfig, league_file) -> None:
    write_config("[tool]\na = 1\n")
    toml = league_file("[tool]\na = 2\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": 2}
    assert settings.source("a") == toml


def test_base_key_kept_when_league_leaves_it_out(
    write_config: WriteConfig, league_file
) -> None:
    write_config("[tool]\na = 1\n")
    toml = league_file("[tool]\nb = 2\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": 1, "b": 2}
    assert settings.source("a") == config_file()
    assert settings.source("b") == toml


def test_nested_table_merges_key_by_key(write_config: WriteConfig, league_file) -> None:
    write_config("[tool.t]\nx = 1\ny = 2\n")
    toml = league_file("[tool.t]\nx = 3\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"t": {"x": 3, "y": 2}}
    assert settings.source("t", "x") == toml
    assert settings.source("t", "y") == config_file()
    assert settings.source("t") == toml  # set last by the league


def test_tables_merge_at_every_depth(write_config: WriteConfig, league_file) -> None:
    write_config("[tool.t.u]\np = 1\nq = 2\n")
    toml = league_file("[tool.t.u]\np = 3\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"t": {"u": {"p": 3, "q": 2}}}
    assert settings.source("t", "u", "p") == toml
    assert settings.source("t", "u", "q") == config_file()


def test_inline_table_merges_like_a_table(
    write_config: WriteConfig, league_file
) -> None:
    write_config("[tool.t]\nx = 1\ny = 2\n")
    league_file("[tool]\nt = { x = 3 }\n")
    assert layered_settings("tool", _league()).values == {"t": {"x": 3, "y": 2}}


def test_array_replaces_whole(write_config: WriteConfig, league_file) -> None:
    write_config("[tool]\na = [1, 2]\n")
    toml = league_file("[tool]\na = [3]\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": [3]}
    assert settings.source("a") == toml


def test_empty_array_replaces_too(write_config: WriteConfig, league_file) -> None:
    write_config("[tool]\na = [1, 2]\n")
    league_file("[tool]\na = []\n")
    assert layered_settings("tool", _league()).values == {"a": []}


def test_scalar_replaces_table(write_config: WriteConfig, league_file) -> None:
    write_config("[tool.t]\nx = 1\n")
    toml = league_file("[tool]\nt = 5\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"t": 5}
    assert settings.source("t") == toml
    with pytest.raises(KeyError):
        settings.source("t", "x")  # went with the base's table


def test_table_replaces_scalar(write_config: WriteConfig, league_file) -> None:
    write_config("[tool]\nt = 5\n")
    toml = league_file("[tool.t]\nx = 1\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"t": {"x": 1}}
    assert settings.source("t") == toml
    assert settings.source("t", "x") == toml


def test_empty_league_table_changes_nothing(
    write_config: WriteConfig, league_file
) -> None:
    write_config("[tool]\na = 1\n[tool.t]\nx = 1\n")
    league_file("[tool]\n[tool.t]\n")
    settings = layered_settings("tool", _league())
    assert settings.values == {"a": 1, "t": {"x": 1}}
    assert settings.source("a") == config_file()
    assert settings.source("t", "x") == config_file()


def test_source_of_an_unset_key_is_key_error(
    write_config: WriteConfig, league_file
) -> None:
    write_config("[tool]\na = 1\n")
    league_file()
    with pytest.raises(KeyError):
        layered_settings("tool", _league()).source("b")


def test_values_are_the_toml_types(write_config: WriteConfig, league_file) -> None:
    write_config('[tool]\nb = true\ni = 1\nf = 1.5\ns = "x"\n')
    league_file('[tool]\na = ["y"]\n')
    assert layered_settings("tool", _league()).values == {
        "b": True,
        "i": 1,
        "f": 1.5,
        "s": "x",
        "a": ["y"],
    }
    values = layered_settings("tool", _league()).values
    assert [type(values[k]) for k in ("b", "i", "f", "s", "a")] == [
        bool,
        int,
        float,
        str,
        list,
    ]


def test_the_files_are_left_as_read(write_config: WriteConfig, league_file) -> None:
    """The merge builds its own tables: reading twice gives the same result."""
    write_config("[tool.t]\nx = 1\ny = 2\n")
    league_file("[tool.t]\nx = 3\n")
    league = _league()
    first = layered_settings("tool", league)
    assert layered_settings("tool", league).values == first.values
    assert league.table("tool") == {"t": {"x": 3}}


# ── a table written as a value names its file ──


def test_league_table_written_as_a_value_is_an_error(
    write_config: WriteConfig, league_file
) -> None:
    write_config("[tool]\na = 1\n")
    toml = league_file("tool = 1\n")
    with pytest.raises(ConfigFileError) as exc:
        layered_settings("tool", _league())
    assert str(exc.value) == f"{toml}: [tool]: Must be a table."


def test_base_table_written_as_a_value_is_an_error(
    write_config: WriteConfig, league_file
) -> None:
    base = write_config("tool = 1\n")
    league_file("[tool]\na = 1\n")
    with pytest.raises(ConfigFileError) as exc:
        layered_settings("tool", _league())
    assert str(exc.value) == f"{base}: [tool]: Must be a table."


# ── LeagueConfig.tables / table ──


def test_league_tables_hold_the_whole_file(league_file) -> None:
    league_file("[league]\nteam = 'Denver'\n[tool]\na = 1\n")
    league = _league()
    assert league.tables == {"league": {"team": "Denver"}, "tool": {"a": 1}}
    assert league.table("tool") == {"a": 1}
    assert league.table("absent") == {}


def test_league_tables_empty_without_a_file(league_file) -> None:
    league_file()
    assert _league().tables == {}
