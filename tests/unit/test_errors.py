"""Every expected error is an AthcError; the shared ones live in athc.errors."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from athc.autocontinue import config as autocontinue_config
from athc.errors import (
    AthcError,
    ConfigFileError,
    LeagueError,
    RulesFileError,
    ini_reason,
    reason_of,
)
from athc.fbpro98_gameplan import InvalidGamePlanError
from athc.fbpro98_lg2 import InvalidLg2Error, UnsupportedLg2Error
from athc.fbpro98_play import CategoryLabels, InvalidPlayFileError
from athc.fbpro98_profile import InvalidProfileError, UnsupportedProfileError
from athc.gameplan import RulesFileError as GameplanRulesFileError
from athc.gameplan.writer import InvalidPlayInputError
from athc.pdbtoexcel import InvalidPDBError
from athc.playpool import RulesFileError as PoolRulesFileError
from athc.profile import ProfileTypeMismatchError
from athc.profile import RulesFileError as ProfileRulesFileError
from athc.scheduler import config as scheduler_config
from athc.scheduler.schedulers.errors import SchedulerError


@pytest.mark.parametrize(
    "error",
    [
        ConfigFileError,
        LeagueError,
        RulesFileError,
        InvalidGamePlanError,
        InvalidLg2Error,
        UnsupportedLg2Error,
        InvalidPlayFileError,
        InvalidProfileError,
        UnsupportedProfileError,
        InvalidPlayInputError,
        InvalidPDBError,
        ProfileTypeMismatchError,
        SchedulerError,
    ],
)
def test_every_library_error_is_an_athc_error(error: type) -> None:
    assert issubclass(error, AthcError)


def test_athc_error_without_a_path_is_its_reason() -> None:
    error = AthcError("league 'NOPE' not found")
    assert str(error) == "league 'NOPE' not found"
    assert error.reason == "league 'NOPE' not found" and error.path is None


def test_athc_error_with_a_path_composes_path_colon_reason() -> None:
    error = AthcError("not found", Path("x.pln"))
    assert str(error) == "x.pln: not found"
    assert error.reason == "not found" and error.path == Path("x.pln")


def test_athc_error_takes_a_str_path() -> None:
    assert str(AthcError("not found", "x.pln")) == "x.pln: not found"


@pytest.mark.parametrize(
    "error",
    [
        ConfigFileError,
        LeagueError,
        InvalidGamePlanError,
        InvalidLg2Error,
        UnsupportedLg2Error,
        InvalidPlayFileError,
        InvalidProfileError,
        UnsupportedProfileError,
        InvalidPDBError,
        SchedulerError,
    ],
)
def test_every_plain_subclass_takes_a_path(error: type[AthcError]) -> None:
    assert str(error("bad block", Path("x"))) == "x: bad block"


def test_rules_file_error_with_a_path_prefixes_each_line() -> None:
    error = RulesFileError("must be a table", Path("rules.toml"))
    assert error.errors == ["rules.toml: must be a table"]
    assert str(error) == "rules.toml: must be a table"
    assert error.path == Path("rules.toml")


def test_rules_file_error_with_a_path_prefixes_every_line() -> None:
    error = RulesFileError(["a", "b"], Path("rules.toml"))
    assert error.errors == ["rules.toml: a", "rules.toml: b"]
    assert str(error) == "rules.toml: a\nrules.toml: b"


def test_reason_of_keeps_only_the_system_wording() -> None:
    error = FileNotFoundError(2, "No such file or directory", "x.pln")
    assert reason_of(error) == "No such file or directory"


def test_reason_of_falls_back_to_the_whole_text() -> None:
    assert reason_of(OSError("disk on fire")) == "disk on fire"


def test_athc_error_takes_any_path_like() -> None:
    class Location:
        def __fspath__(self) -> str:
            return "x.pln"

    assert str(AthcError("bad", Location())) == "x.pln: bad"


def _ini_error(text: str) -> configparser.Error:
    with pytest.raises(configparser.Error) as exc:
        configparser.ConfigParser(interpolation=None).read_string(text)
    return exc.value


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("garbage\n", "line 1: no [section] header above it"),
        ("[a]\nbroken\n", "line 2: not a 'key = value' line"),
        ("[a]\nbroken\nworse\n", "lines 2, 3: not a 'key = value' line"),
        ("[a]\n[a]\n", "line 2: section [a] repeats"),
        ("[a]\nx = 1\nx = 2\n", "line 3: option 'x' in [a] repeats"),
    ],
)
def test_ini_reason_is_one_line_without_the_path(text: str, reason: str) -> None:
    assert ini_reason(_ini_error(text)) == reason


def test_rules_file_error_is_shared() -> None:
    assert GameplanRulesFileError is ProfileRulesFileError is PoolRulesFileError


def test_rules_file_error_carries_every_message() -> None:
    error = RulesFileError(["a", "b"])
    assert error.errors == ["a", "b"] and str(error) == "a\nb"
    assert RulesFileError("one").errors == ["one"]


def test_the_two_config_errors_are_gone() -> None:
    assert not hasattr(scheduler_config, "ConfigError")
    assert not hasattr(autocontinue_config, "ConfigError")


def test_category_labels_raise_config_file_error() -> None:
    with pytest.raises(ConfigFileError, match="not a game category name"):
        CategoryLabels.from_tables({"Nope": "x"}, {})
