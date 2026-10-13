"""Every expected error is an AthcError; the shared ones live in athc.errors."""

from __future__ import annotations

import configparser
import errno
import tomllib
from pathlib import Path

import pytest

from athc.autocontinue import config as autocontinue_config
from athc.errors import (
    ACCESS_DENIED,
    ALREADY_EXISTS,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    AthcError,
    ConfigFileError,
    FileFormatError,
    LeagueError,
    RulesFileError,
    error_line,
    ini_reason,
    missing_reason,
    reason_of,
    sentence,
    toml_reason,
)
from athc.fbpro98_gameplan import InvalidGamePlanError
from athc.fbpro98_lg2 import InvalidLg2Error
from athc.fbpro98_lge import InvalidLgeError
from athc.fbpro98_play import CategoryLabels, InvalidPlayFileError
from athc.fbpro98_profile import InvalidProfileError, UnsupportedProfileError
from athc.gameplan import RulesFileError as GameplanRulesFileError
from athc.gameplan.writer import InvalidPlayListError
from athc.pdbtoexcel import InvalidPDBError
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
        InvalidLgeError,
        InvalidPlayFileError,
        InvalidProfileError,
        UnsupportedProfileError,
        InvalidPlayListError,
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
    "error", [ConfigFileError, LeagueError, InvalidPDBError, SchedulerError]
)
def test_every_plain_subclass_takes_a_path(error: type[AthcError]) -> None:
    assert str(error("bad block", Path("x"))) == "x: bad block"


@pytest.mark.parametrize(
    "error",
    [
        InvalidGamePlanError,
        InvalidLg2Error,
        InvalidLgeError,
        InvalidPlayFileError,
        InvalidProfileError,
        UnsupportedProfileError,
    ],
)
def test_a_file_format_error_keeps_its_reason_as_written(
    error: type[AthcError],
) -> None:
    """The raise site writes the sentence; the error never rewords it."""
    assert issubclass(error, FileFormatError)
    assert str(error("bad block", Path("x"))) == "x: bad block"
    assert str(error("Bad block.", Path("x"))) == "x: Bad block."


def test_rules_file_error_with_a_path_prefixes_each_line() -> None:
    error = RulesFileError("must be a table", Path("rules.toml"))
    assert error.errors == ["rules.toml: must be a table"]
    assert str(error) == "rules.toml: must be a table"
    assert error.path == Path("rules.toml")


def test_rules_file_error_with_a_path_prefixes_every_line() -> None:
    error = RulesFileError(["a", "b"], Path("rules.toml"))
    assert error.errors == ["rules.toml: a", "rules.toml: b"]
    assert str(error) == "rules.toml: a\nrules.toml: b"


def _win(code: int, text: str, filename: str | None = None) -> OSError:
    error = OSError(errno.EINVAL, text, filename)
    error.winerror = code  # type: ignore[attr-defined]  # set by Windows calls
    return error


@pytest.mark.parametrize(
    ("code", "phrase"),
    [
        (2, FILE_NOT_FOUND),
        (3, PATH_NOT_FOUND),
        (5, ACCESS_DENIED),
        (267, DIRECTORY_INVALID),
        (183, ALREADY_EXISTS),
    ],
)
def test_reason_of_a_windows_code_is_windows_phrase(code: int, phrase: str) -> None:
    assert reason_of(_win(code, "whatever")) == phrase


def test_reason_of_missing_file_in_an_existing_folder(tmp_path: Path) -> None:
    error = FileNotFoundError(
        errno.ENOENT, "No such file or directory", str(tmp_path / "x.pln")
    )
    assert reason_of(error) == FILE_NOT_FOUND


def test_reason_of_missing_folder_on_the_way(tmp_path: Path) -> None:
    error = FileNotFoundError(
        errno.ENOENT, "No such file or directory", str(tmp_path / "gone" / "x.pln")
    )
    assert reason_of(error) == PATH_NOT_FOUND


@pytest.mark.parametrize(
    ("number", "phrase"),
    [
        (errno.EACCES, ACCESS_DENIED),
        (errno.EISDIR, ACCESS_DENIED),
        (errno.ENOTDIR, DIRECTORY_INVALID),
        (errno.EEXIST, ALREADY_EXISTS),
    ],
)
def test_reason_of_an_errno_is_windows_phrase(number: int, phrase: str) -> None:
    assert reason_of(OSError(number, "whatever", "x")) == phrase


@pytest.mark.parametrize(
    ("error", "phrase"),
    [
        (PermissionError("access denied"), ACCESS_DENIED),
        (IsADirectoryError("a folder"), ACCESS_DENIED),
        (NotADirectoryError("a file"), DIRECTORY_INVALID),
        (FileExistsError("taken"), ALREADY_EXISTS),
        (FileNotFoundError("gone"), FILE_NOT_FOUND),
    ],
)
def test_reason_of_a_kind_without_a_number_is_windows_phrase(
    error: OSError, phrase: str
) -> None:
    assert reason_of(error) == phrase


@pytest.mark.parametrize(
    ("code", "text"),
    [
        (53, "The network path was not found"),  # arrives as FileNotFoundError
        (206, "The filename or extension is too long"),
        (80, "The file exists"),  # arrives as FileExistsError
        (
            32,
            "The process cannot access the file because it is being used by "
            "another process",
        ),
        (
            33,
            "The process cannot access the file because another process has "
            "locked a portion of the file",
        ),
    ],
)
def test_reason_of_another_windows_code_keeps_windows_text(
    code: int, text: str
) -> None:
    # A Windows call's own error, as Python builds it: the class comes from the
    # code, so only the code says which problem it is.
    error = OSError(None, text, None, code)
    assert reason_of(error) == f"{text}."


def test_reason_of_without_strerror_uses_the_whole_text() -> None:
    assert reason_of(OSError("disk on fire")) == "Disk on fire."


def test_reason_of_an_error_with_no_text_is_windows_unspecified_error() -> None:
    assert reason_of(OSError()) == "Unspecified error."
    assert error_line(OSError()) == "Unspecified error."


def test_missing_reason(tmp_path: Path) -> None:
    assert missing_reason(tmp_path / "x.pln") == FILE_NOT_FOUND
    assert missing_reason(tmp_path / "gone" / "x.pln") == PATH_NOT_FOUND
    assert missing_reason("x.pln") == FILE_NOT_FOUND  # the current folder exists


def test_error_line_names_the_file() -> None:
    error = PermissionError(errno.EACCES, "Permission denied", "x.pln")
    assert error_line(error) == f"x.pln: {ACCESS_DENIED}"


def test_error_line_without_a_file_name_is_the_phrase_alone() -> None:
    assert error_line(_win(2, "gone")) == FILE_NOT_FOUND


@pytest.mark.parametrize("filename", [b"x.pln", 3])
def test_error_line_ignores_a_bytes_or_number_file_name(filename: object) -> None:
    error = PermissionError(errno.EACCES, "Permission denied")
    error.filename = filename
    assert error_line(error) == ACCESS_DENIED


def test_error_line_of_an_athc_error_is_its_text() -> None:
    assert error_line(AthcError("Bad.", "x.pln")) == "x.pln: Bad."


def test_error_line_names_what_failed_when_the_error_names_no_file() -> None:
    assert error_line(AthcError("Bad."), what="a.prf + b.pln") == "a.prf + b.pln: Bad."
    assert error_line(_win(5, "denied"), what="a.prf + b.pln") == (
        f"a.prf + b.pln: {ACCESS_DENIED}"
    )
    assert error_line(RulesFileError(["One.", "Two."]), what="x") == "x: One.\nx: Two."


def test_error_line_keeps_the_errors_own_file_over_what_failed() -> None:
    assert error_line(AthcError("Bad.", "x.pln"), what="a + b") == "x.pln: Bad."
    error = PermissionError(errno.EACCES, "Permission denied", "x.pln")
    assert error_line(error, what="a + b") == f"x.pln: {ACCESS_DENIED}"


@pytest.mark.parametrize(
    ("text", "result"),
    [
        ("bad thing", "Bad thing."),
        ("Bad thing.", "Bad thing."),
        ("bad thing...", "Bad thing."),
        ("'x' is bad", "'x' is bad."),
        ("  padded  ", "Padded."),
        ("", ""),
    ],
)
def test_sentence(text: str, result: str) -> None:
    assert sentence(text) == result


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
        ("garbage\n", "Not valid INI: No [section] header above it (at line 1)."),
        ("[a]\nbroken\n", "Not valid INI: Not a 'key = value' line (at line 2)."),
        (
            "[a]\nbroken\nworse\n",
            "Not valid INI: Not a 'key = value' line (at lines 2, 3).",
        ),
        ("[a]\n[a]\n", "Not valid INI: Section [a] repeats (at line 2)."),
        (
            "[a]\nx = 1\nx = 2\n",
            "Not valid INI: Option 'x' in [a] repeats (at line 3).",
        ),
    ],
)
def test_ini_reason_is_one_line_without_the_path(text: str, reason: str) -> None:
    assert ini_reason(_ini_error(text)) == reason


def test_toml_reason() -> None:
    with pytest.raises(tomllib.TOMLDecodeError) as exc:
        tomllib.loads("x = \n")
    assert toml_reason(exc.value) == f"Not valid TOML: {exc.value}."


def test_rules_file_error_is_shared() -> None:
    assert GameplanRulesFileError is ProfileRulesFileError


def test_rules_file_error_carries_every_message() -> None:
    error = RulesFileError(["a", "b"])
    assert error.errors == ["a", "b"] and str(error) == "a\nb"
    assert RulesFileError("one").errors == ["one"]


def test_the_two_config_errors_are_gone() -> None:
    assert not hasattr(scheduler_config, "ConfigError")
    assert not hasattr(autocontinue_config, "ConfigError")


def test_category_labels_raise_config_file_error() -> None:
    with pytest.raises(ConfigFileError, match="Not a game category name"):
        CategoryLabels.from_tables({"Nope": "x"}, {})
