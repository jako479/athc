"""Playpool filename-filter rules — which filename patterns set each
filename-derived play attribute, parsed from a per-league TOML file.

Folder conventions, attributes, and enums are fixed in code (records.py / pool.py);
only these filename filters are league data, so a league with the same folder
layout but different play names just edits the filters.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Final

StrPath = str | PathLike[str]

# Section name -> the attribute it sets.
SECTION_TIMED: Final = "TimedPass"  # a pass play's pass_logic = Timed
SECTION_ROLLOUT: Final = "RolloutPass"  # a pass play's rollout flag
SECTION_QB_RUN: Final = "QBRun"  # a run play's qb_draw flag

_SECTIONS: Final[frozenset[str]] = frozenset(
    {SECTION_TIMED, SECTION_ROLLOUT, SECTION_QB_RUN}
)
_FILTER_KEYS: Final[frozenset[str]] = frozenset(
    {"suffix_any", "suffix_none", "regex_any", "regex_none", "include", "exclude"}
)


class RulesFileError(ValueError):
    """Raised when a playpool rules TOML file cannot be parsed or validated.
    Carries one or more messages (`errors`); every detected problem is reported
    together."""

    def __init__(self, errors: str | Iterable[str]) -> None:
        self.errors: list[str] = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True, slots=True)
class FilenameFilter:
    """Case-sensitive filename match for one attribute.

    A play name matches when it hits ANY of `suffix_any` / `regex_any` /
    `include` and NONE of `suffix_none` / `regex_none` / `exclude` — the vetoes
    win. All comparisons are case-sensitive (use `(?i)` in a regex to opt out).
    """

    suffix_any: tuple[str, ...] = ()
    suffix_none: tuple[str, ...] = ()
    regex_any: tuple[re.Pattern[str], ...] = ()
    regex_none: tuple[re.Pattern[str], ...] = ()
    include: frozenset[str] = frozenset()
    exclude: frozenset[str] = frozenset()

    def matches(self, name: str) -> bool:
        hit = (
            any(name.endswith(s) for s in self.suffix_any)
            or any(p.search(name) for p in self.regex_any)
            or name in self.include
        )
        if not hit:
            return False
        vetoed = (
            any(name.endswith(s) for s in self.suffix_none)
            or any(p.search(name) for p in self.regex_none)
            or name in self.exclude
        )
        return not vetoed


@dataclass(frozen=True, slots=True)
class PlaypoolRules:
    """Filename filters for the three filename-derived attributes."""

    timed: FilenameFilter = field(default_factory=FilenameFilter)
    rollout: FilenameFilter = field(default_factory=FilenameFilter)
    qb_draw: FilenameFilter = field(default_factory=FilenameFilter)


def load_rules(path: StrPath) -> PlaypoolRules:
    """Parse a playpool rules TOML file. Raises RulesFileError on any problem."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise RulesFileError(f"{p}: {e}") from e
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise RulesFileError(f"{p}: TOML parse error: {e}") from e
    return build_rules(data, source=p)


def build_rules(
    data: Mapping[str, Any], *, source: StrPath = "<rules>"
) -> PlaypoolRules:
    """Build a PlaypoolRules from already-parsed TOML data. Collects every
    format/data problem in one pass and raises them all together."""
    errors: list[str] = []
    for key in data:
        if key != "schema_version" and key not in _SECTIONS:
            errors.append(
                f"{source}: unknown section [{key}] (expected {sorted(_SECTIONS)})"
            )
    rules = PlaypoolRules(
        timed=_build_filter(data.get(SECTION_TIMED), source, SECTION_TIMED, errors),
        rollout=_build_filter(
            data.get(SECTION_ROLLOUT), source, SECTION_ROLLOUT, errors
        ),
        qb_draw=_build_filter(data.get(SECTION_QB_RUN), source, SECTION_QB_RUN, errors),
    )
    if errors:
        raise RulesFileError(errors)
    return rules


def _attempt(errors: list[str], fn: Callable[[], Any]) -> Any:
    """Run `fn`, collecting any RulesFileError into `errors`. Returns the value
    on success, else None."""
    try:
        return fn()
    except RulesFileError as e:
        errors.extend(e.errors)
        return None


def _build_filter(
    section: Any, source: StrPath, name: str, errors: list[str]
) -> FilenameFilter:
    if section is None:
        return FilenameFilter()
    if not isinstance(section, dict):
        errors.append(f"{source}: [{name}] must be a table")
        return FilenameFilter()
    unknown = sorted(set(section) - _FILTER_KEYS)
    for key in unknown:
        errors.append(f"{source}: [{name}]: unknown key(s): {key}")
    where = f"{source}: [{name}]"
    return FilenameFilter(
        suffix_any=_attempt(
            errors, lambda: _str_list(section.get("suffix_any"), f"{where}.suffix_any")
        )
        or (),
        suffix_none=_attempt(
            errors,
            lambda: _str_list(section.get("suffix_none"), f"{where}.suffix_none"),
        )
        or (),
        regex_any=_regex_list(section.get("regex_any"), f"{where}.regex_any", errors),
        regex_none=_regex_list(
            section.get("regex_none"), f"{where}.regex_none", errors
        ),
        include=frozenset(
            _attempt(
                errors, lambda: _str_list(section.get("include"), f"{where}.include")
            )
            or ()
        ),
        exclude=frozenset(
            _attempt(
                errors, lambda: _str_list(section.get("exclude"), f"{where}.exclude")
            )
            or ()
        ),
    )


def _str_list(value: object, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise RulesFileError(f"{where}: must be a list of strings")
    return tuple(value)


def _regex_list(
    value: object, where: str, errors: list[str]
) -> tuple[re.Pattern[str], ...]:
    patterns = _attempt(errors, lambda: _str_list(value, where))
    if not patterns:
        return ()
    compiled: list[re.Pattern[str]] = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as e:
            errors.append(f"{where}: invalid regex {pat!r}: {e}")
    return tuple(compiled)


__all__ = [
    "FilenameFilter",
    "PlaypoolRules",
    "RulesFileError",
    "build_rules",
    "load_rules",
]
