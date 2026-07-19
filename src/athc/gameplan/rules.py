"""Gameplan validation rules and their TOML loader.

No rules ship with the package. `load_rules(paths)` parses one or more external
TOML files into a `Rules` value; later files layer over earlier ones (per-category
replace, scalar overwrite). Categories are keyed by short label — offense uses
codes (`[offense.PSL]`), defense uses words (`[defense.RunDazzle]`).
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Final

from athc.fbpro98_play import (
    DefensiveCategory,
    OffensiveCategory,
    SpecialOffensiveCategory,
    category_by_short,
)


@dataclass(frozen=True, slots=True)
class OffenseCategoryRule:
    """Constraints on one offensive game category. Every field is optional.

    `required` (default False) True means the category must appear with at least
    `min_count` plays; False is optional but still enforces the caps if used.
    `min_count` defaults to 0. `max_count` caps the play count when set. Other
    caps apply only when set: `max_qb_draws` for run categories, `max_rollouts`
    and `max_timed_percent` for pass categories. Counts are >= 0;
    `max_timed_percent` is a fraction in [0, 1].
    """

    required: bool = False
    min_count: int = 0
    max_count: int | None = None
    max_qb_draws: int | None = None
    max_rollouts: int | None = None
    max_timed_percent: Fraction | None = None


@dataclass(frozen=True, slots=True)
class DefenseCategoryRule:
    """Constraints on one defensive game category. Every field is optional:
    `required` defaults False, `min_count` 0. `max_count` caps the play count;
    `max_two_dl_percent` caps the fraction of plays using the 2-DL (Run-and-Shoot)
    defensive front. Counts are >= 0; `max_two_dl_percent` is a fraction in [0, 1]."""

    required: bool = False
    min_count: int = 0
    max_count: int | None = None
    max_two_dl_percent: Fraction | None = None


@dataclass(frozen=True, slots=True)
class Rules:
    """A gameplan validation rule set, loaded from external TOML. Every field is
    optional; an empty rule set enforces nothing."""

    offense_categories: Mapping[str, OffenseCategoryRule] = field(default_factory=dict)
    defense_categories: Mapping[str, DefenseCategoryRule] = field(default_factory=dict)
    required_special_categories: frozenset[int] = frozenset()
    disallowed_offensive_categories: frozenset[str] = frozenset()
    disallowed_defensive_categories: frozenset[str] = frozenset()
    custom_special_play_required: bool = False


_OFFENSE_CATEGORIES: Final[frozenset[str]] = frozenset(
    c.long for c in OffensiveCategory
)
_DEFENSE_CATEGORIES: Final[frozenset[str]] = frozenset(
    c.long for c in DefensiveCategory
)

# Valid [offense.X] / [defense.X] section labels (the league short labels).
_OFFENSE_LABELS: Final[list[str]] = sorted(
    c.short for c in OffensiveCategory if c.short != c.long
)
_DEFENSE_LABELS: Final[list[str]] = sorted(
    c.short for c in DefensiveCategory if c.short != c.long
)

# Special-category name -> code byte.
_SPECIAL_CATEGORY_BY_NAME: Final[Mapping[str, int]] = {
    c.long: c.code for c in SpecialOffensiveCategory
}

_RUN_SUBKEYS: Final[frozenset[str]] = frozenset(
    {"required", "min_count", "max_count", "max_qb_draws"}
)
_PASS_SUBKEYS: Final[frozenset[str]] = frozenset(
    {"required", "min_count", "max_count", "max_rollouts", "max_timed_percent"}
)
_DEFENSE_SUBKEYS: Final[frozenset[str]] = frozenset(
    {"required", "min_count", "max_count", "max_two_dl_percent"}
)
_ALLOWED_TOP_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "required_special_categories",
        "custom_special_play_required",
        "disallowed_offensive_categories",
        "disallowed_defensive_categories",
        "offense",
        "defense",
    }
)


class RulesFileError(ValueError):
    """Raised when gameplan rules TOML files cannot be parsed or validated. Carries
    one or more messages (`errors`); every detected problem is reported together."""

    def __init__(self, errors: str | Iterable[str]) -> None:
        self.errors: list[str] = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


@dataclass(slots=True)
class _MergedData:
    required_special_categories: frozenset[int] | None = None
    custom_special_play_required: bool | None = None
    disallowed_offensive: frozenset[str] | None = None
    disallowed_defensive: frozenset[str] | None = None
    offense: dict[str, OffenseCategoryRule] = field(default_factory=dict)
    defense: dict[str, DefenseCategoryRule] = field(default_factory=dict)


def load_rules(paths: Iterable[Path | str]) -> Rules:
    """Load one or more TOML rules files and merge them into a `Rules`.

    Files merge in order: top-level scalars/lists overwrite; per-category rules
    overwrite per category key.
    """
    path_list = [Path(p) for p in paths]
    if not path_list:
        raise RulesFileError("at least one rules file is required")

    merged = _MergedData()
    errors: list[str] = []
    for path in path_list:
        try:
            data = _read_toml(path)
        except RulesFileError as e:
            errors.extend(e.errors)
            continue
        _merge_file(merged, data, errors, source=path)

    if errors:
        raise RulesFileError(errors)
    return _build_rules(merged)


def _read_toml(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise RulesFileError(f"{path}: {e}") from e
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise RulesFileError(f"{path}: TOML parse error: {e}") from e


def _attempt(errors: list[str], fn: Callable[[], Any]) -> tuple[Any, bool]:
    """Run `fn`, collecting any RulesFileError into `errors`. Returns
    `(value, ok)` so the caller applies the result only on success."""
    try:
        return fn(), True
    except RulesFileError as e:
        errors.extend(e.errors)
        return None, False


def _merge_file(
    merged: _MergedData, data: Mapping[str, Any], errors: list[str], *, source: Path
) -> None:
    """Apply one parsed TOML document onto `merged`, collecting every problem."""
    _attempt(
        errors, lambda: _reject_unknown_keys(data, _ALLOWED_TOP_KEYS, source, "(top)")
    )

    if "required_special_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: frozenset(
                _map_each(
                    data["required_special_categories"],
                    _SPECIAL_CATEGORY_BY_NAME,
                    source,
                    "required_special_categories",
                )
            ),
        )
        if ok:
            merged.required_special_categories = val

    if "custom_special_play_required" in data:
        val, ok = _attempt(
            errors,
            lambda: _require_bool(
                data["custom_special_play_required"],
                source,
                "custom_special_play_required",
            ),
        )
        if ok:
            merged.custom_special_play_required = val

    if "disallowed_offensive_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: _category_name_set(
                data["disallowed_offensive_categories"],
                _OFFENSE_CATEGORIES,
                source,
                "disallowed_offensive_categories",
            ),
        )
        if ok:
            merged.disallowed_offensive = val
    if "disallowed_defensive_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: _category_name_set(
                data["disallowed_defensive_categories"],
                _DEFENSE_CATEGORIES,
                source,
                "disallowed_defensive_categories",
            ),
        )
        if ok:
            merged.disallowed_defensive = val

    for label, section in data.get("offense", {}).items():
        val, ok = _attempt(
            errors,
            lambda label=label, section=section: _build_offense_section(
                label, section, source
            ),
        )
        if ok:
            name, rule = val
            merged.offense[name] = rule
    for label, section in data.get("defense", {}).items():
        val, ok = _attempt(
            errors,
            lambda label=label, section=section: _build_defense_section(
                label, section, source
            ),
        )
        if ok:
            name, rule = val
            merged.defense[name] = rule


def _build_offense_section(
    label: str, section: Mapping[str, Any], source: Path
) -> tuple[str, OffenseCategoryRule]:
    member = category_by_short(label)
    if not isinstance(member, OffensiveCategory):
        raise RulesFileError(
            f"{source}: [offense.{label}]: not an offense category label. "
            f"Valid: {_OFFENSE_LABELS}"
        )
    return member.long, _build_offense_rule(label, member, section, source)


def _build_defense_section(
    label: str, section: Mapping[str, Any], source: Path
) -> tuple[str, DefenseCategoryRule]:
    member = category_by_short(label)
    if not isinstance(member, DefensiveCategory):
        raise RulesFileError(
            f"{source}: [defense.{label}]: not a defense category label. "
            f"Valid: {_DEFENSE_LABELS}"
        )
    return member.long, _build_defense_rule(label, section, source)


def _build_offense_rule(
    label: str, member: OffensiveCategory, section: Mapping[str, Any], source: Path
) -> OffenseCategoryRule:
    where = f"[offense.{label}]"
    is_run = member.is_run
    _reject_unknown_keys(
        section, _RUN_SUBKEYS if is_run else _PASS_SUBKEYS, source, where
    )
    _require_nonempty(section, source, where)
    return OffenseCategoryRule(
        required=_bool_or_false(section.get("required"), source, f"{where}.required"),
        min_count=_int_or_zero(section.get("min_count"), source, f"{where}.min_count"),
        max_count=_optional_int(section.get("max_count"), source, f"{where}.max_count"),
        max_qb_draws=(
            _optional_int(section.get("max_qb_draws"), source, f"{where}.max_qb_draws")
            if is_run
            else None
        ),
        max_rollouts=(
            _optional_int(section.get("max_rollouts"), source, f"{where}.max_rollouts")
            if not is_run
            else None
        ),
        max_timed_percent=(
            _optional_fraction(
                section.get("max_timed_percent"), source, f"{where}.max_timed_percent"
            )
            if not is_run
            else None
        ),
    )


def _build_defense_rule(
    label: str, section: Mapping[str, Any], source: Path
) -> DefenseCategoryRule:
    where = f"[defense.{label}]"
    _reject_unknown_keys(section, _DEFENSE_SUBKEYS, source, where)
    _require_nonempty(section, source, where)
    return DefenseCategoryRule(
        required=_bool_or_false(section.get("required"), source, f"{where}.required"),
        min_count=_int_or_zero(section.get("min_count"), source, f"{where}.min_count"),
        max_count=_optional_int(section.get("max_count"), source, f"{where}.max_count"),
        max_two_dl_percent=_optional_fraction(
            section.get("max_two_dl_percent"), source, f"{where}.max_two_dl_percent"
        ),
    )


def _build_rules(m: _MergedData) -> Rules:
    return Rules(
        offense_categories=dict(m.offense),
        defense_categories=dict(m.defense),
        required_special_categories=m.required_special_categories or frozenset(),
        disallowed_offensive_categories=m.disallowed_offensive or frozenset(),
        disallowed_defensive_categories=m.disallowed_defensive or frozenset(),
        custom_special_play_required=bool(m.custom_special_play_required),
    )


def _reject_unknown_keys(
    section: Mapping[str, Any], allowed: frozenset[str], source: Path, where: str
) -> None:
    unknown = sorted(set(section) - allowed)
    if unknown:
        names = ", ".join(repr(k) for k in unknown)
        raise RulesFileError(f"{source}: {where}: unknown key(s): {names}")


def _require_nonempty(section: Mapping[str, Any], source: Path, where: str) -> None:
    if not section:
        raise RulesFileError(f"{source}: {where}: empty rule; set at least one key")


def _require_bool(value: object, source: Path, where: str) -> bool:
    if not isinstance(value, bool):
        raise RulesFileError(f"{source}: {where}: must be a boolean")
    return value


def _require_int(value: object, source: Path, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RulesFileError(f"{source}: {where}: must be an integer")
    return value


def _bool_or_false(value: object | None, source: Path, where: str) -> bool:
    return False if value is None else _require_bool(value, source, where)


def _int_or_zero(value: object | None, source: Path, where: str) -> int:
    if value is None:
        return 0
    n = _require_int(value, source, where)
    if n < 0:
        raise RulesFileError(f"{source}: {where}: must be >= 0")
    return n


def _optional_int(value: object | None, source: Path, where: str) -> int | None:
    """Optional count; must be >= 0 when present."""
    if value is None:
        return None
    n = _require_int(value, source, where)
    if n < 0:
        raise RulesFileError(f"{source}: {where}: must be >= 0")
    return n


def _optional_fraction(
    value: object | None, source: Path, where: str
) -> Fraction | None:
    """Parse `"n/m"` -> Fraction in [0, 1]. Reject any other shape or range."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RulesFileError(f'{source}: {where}: must be a string like "1/2"')
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError) as e:
        raise RulesFileError(
            f"{source}: {where}: invalid fraction {value!r}: {e}"
        ) from e
    if not 0 <= fraction <= 1:
        raise RulesFileError(f"{source}: {where}: must be in [0, 1]")
    return fraction


def _category_name_set(
    value: object, valid: frozenset[str], source: Path, where: str
) -> frozenset[str]:
    """A list of full game-category names, each validated against `valid`."""
    if not isinstance(value, list):
        raise RulesFileError(f"{source}: {where}: must be a list")
    out: set[str] = set()
    for name in value:
        if not isinstance(name, str):
            raise RulesFileError(f"{source}: {where}: entries must be strings")
        if name not in valid:
            raise RulesFileError(f"{source}: {where}: unknown category {name!r}")
        out.add(name)
    return frozenset(out)


def _map_each(
    names: object, name_map: Mapping[str, Any], source: Path, where: str
) -> list[Any]:
    if not isinstance(names, list):
        raise RulesFileError(f"{source}: {where}: must be a list")
    out: list[Any] = []
    for name in names:
        if not isinstance(name, str):
            raise RulesFileError(f"{source}: {where}: entries must be strings")
        if name not in name_map:
            raise RulesFileError(f"{source}: {where}: unknown name {name!r}")
        out.append(name_map[name])
    return out


__all__ = [
    "DefenseCategoryRule",
    "OffenseCategoryRule",
    "Rules",
    "RulesFileError",
    "load_rules",
]
