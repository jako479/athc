"""The one error family: every expected failure athc reports is an AthcError.

An error carries its `reason` and, when one file is to blame, that file's
`path`, and composes its own text, `<path>: <reason>`, the way `OSError` and
`JSONDecodeError` do; `main()` prints it after `FAIL` and exits 2, and a
batch command prints it per item, so no line names a path twice. The shared
errors live here so the config, league and rules readers raise one class
each, whichever tool is asking.
"""

from __future__ import annotations

import configparser
from collections.abc import Iterable
from os import PathLike, fspath

StrPath = str | PathLike[str]


def _line(reason: str, path: StrPath | None) -> str:
    return reason if path is None else f"{fspath(path)}: {reason}"


def reason_of(error: OSError) -> str:
    """An OSError's reason alone (`No such file or directory`), for an
    AthcError that carries the path itself; Python's own text would name the
    path a second time, with its errno."""
    return error.strerror or str(error)


def ini_reason(error: configparser.Error) -> str:
    """A configparser error's reason alone, on one line, for an AthcError that
    carries the path itself; configparser's own text names the file and
    spans lines."""
    match error:
        case configparser.MissingSectionHeaderError():
            return f"line {error.lineno}: no [section] header above it"
        case configparser.ParsingError():
            numbers = [str(lineno) for lineno, _ in error.errors]
            noun = "line" if len(numbers) == 1 else "lines"
            return f"{noun} {', '.join(numbers)}: not a 'key = value' line"
        case configparser.DuplicateSectionError():
            return f"line {error.lineno}: section [{error.section}] repeats"
        case configparser.DuplicateOptionError():
            return (
                f"line {error.lineno}: option '{error.option}' in "
                f"[{error.section}] repeats"
            )
        case _:
            return error.message


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
    """athc.ini, a league.toml, a tool's TOML file or a league setting cannot
    be read or is invalid: malformed file, wrong value type, bad label, a
    required setting missing."""


class LeagueError(AthcError):
    """No league can be resolved, or the named league has no folder."""


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
