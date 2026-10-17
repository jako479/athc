"""The one error family: every expected failure athc reports is an AthcError.

An error carries its `reason` and, when one file is to blame, that file's
`path`, and composes its own text, `<path>: <reason>`, the way `OSError` and
`JSONDecodeError` do; `main()` prints it after `FAIL` and exits 2, and a
batch command prints it per item, so no line names a path twice. The shared
errors live here so the config, league and rules readers raise one class
each, whichever tool is asking.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from os import PathLike, fspath
from pathlib import Path

StrPath = str | PathLike[str]

FILE_NOT_FOUND = "The system cannot find the file specified."
PATH_NOT_FOUND = "The system cannot find the path specified."
ACCESS_DENIED = "Access is denied."
DIRECTORY_INVALID = "The directory name is invalid."
ALREADY_EXISTS = "Cannot create a file when that file already exists."
UNSPECIFIED_ERROR = "Unspecified error."  # Windows' words for an error with no text

# Windows' own words for the problems a user meets, whichever call hit them:
# Python gives one problem two texts (open: "No such file or directory",
# os.stat: "The system cannot find the file specified").
_BY_WINERROR = {
    2: FILE_NOT_FOUND,
    3: PATH_NOT_FOUND,
    5: ACCESS_DENIED,
    183: ALREADY_EXISTS,
    267: DIRECTORY_INVALID,
}
# Python picks the subclass from the error number, so the class covers an
# error made from a number and one raised without any.
_BY_KIND: tuple[tuple[type[OSError], str], ...] = (
    (PermissionError, ACCESS_DENIED),
    (IsADirectoryError, ACCESS_DENIED),  # Windows refuses to open a folder this way
    (NotADirectoryError, DIRECTORY_INVALID),
    (FileExistsError, ALREADY_EXISTS),
)


def _line(reason: str, path: StrPath | None) -> str:
    return reason if path is None else f"{fspath(path)}: {reason}"


def sentence(text: str) -> str:
    """`text` as a sentence: capital first letter, exactly one trailing period."""
    text = text.strip().rstrip(".")
    return f"{text[:1].upper()}{text[1:]}." if text else ""


def _file_name(error: OSError) -> StrPath | None:
    name = error.filename
    return name if isinstance(name, str | PathLike) else None


def missing_reason(path: StrPath) -> str:
    """What Windows says for a missing `path`: the path phrase when the folder
    it should be in is missing too, else the file phrase."""
    return FILE_NOT_FOUND if Path(path).parent.is_dir() else PATH_NOT_FOUND


def reason_of(error: OSError) -> str:
    """An OSError's reason alone, in Windows' words, for a line that names the
    path itself; Python's own text would name the path a second time, with
    its errno."""
    winerror = getattr(error, "winerror", None)
    if winerror in _BY_WINERROR:
        return _BY_WINERROR[winerror]
    # Any other Windows code has its own words (a file in use, a network path,
    # a name too long); only an error without one goes by its kind.
    if winerror is None and isinstance(error, FileNotFoundError):
        name = _file_name(error)
        return FILE_NOT_FOUND if name is None else missing_reason(name)
    if winerror is None:
        for kind, phrase in _BY_KIND:
            if isinstance(error, kind):
                return phrase
    return sentence(error.strerror or str(error)) or UNSPECIFIED_ERROR


def toml_reason(error: tomllib.TOMLDecodeError) -> str:
    """A TOML parse error as one sentence; tomllib's text already names the
    line and column."""
    return sentence(f"Not valid TOML: {error}")


class AthcError(Exception):
    """Base of every expected athc error: a `reason`, and the `path` of the
    file it is about (None when no one file is)."""

    def __init__(self, reason: str, path: StrPath | None = None) -> None:
        super().__init__(*((reason,) if path is None else (reason, path)))
        self.reason = reason
        self.path = path

    def __str__(self) -> str:
        return _line(self.reason, self.path)


class ConfigFileError(AthcError):
    """athc.toml, a league.toml, a tool's TOML file or a league setting cannot
    be read or is invalid: malformed file, wrong value type, bad label, a
    required setting missing."""


class LeagueError(AthcError):
    """No league can be resolved, or the named league has no folder."""


class FileFormatError(AthcError):
    """A game file athc reads is not in the format it expects."""


class RulesFileError(AthcError):
    """A rules TOML file cannot be parsed or validated. Carries one or more
    lines (`errors`), each `<path>: <reason>` when raised with a path; every
    detected problem is reported together."""

    def __init__(
        self, errors: str | Iterable[str], path: StrPath | None = None
    ) -> None:
        reasons = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(reasons), path)
        self.errors: list[str] = [_line(reason, path) for reason in reasons]

    def __str__(self) -> str:
        return "\n".join(self.errors)


def error_line(error: AthcError | OSError, what: str | None = None) -> str:
    """The line a `FAIL` shows: an AthcError's own text, or an OSError as
    `<file>: <reason>`. An error that names no file is put under `what` (the
    item a loop was on), or shown alone without one."""
    if isinstance(error, AthcError):
        text, named = str(error), error.path is not None
    else:
        name = _file_name(error)
        text, named = _line(reason_of(error), name), name is not None
    if named or what is None:
        return text
    return "\n".join(_line(line, what) for line in text.splitlines())
