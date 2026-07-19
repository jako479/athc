"""Coaching-profile validation rules: dataclasses and TOML loader.

Rule data lives in external TOML files — none ship with this package. Use
`load_rules(paths)` to load one or more into a `ProfileRules`. Rule semantics:
docs/profile/RULES_PNFL.md.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    MinutesRemaining,
    SubstitutionPair,
    YardsToGo,
)

# ---------------------------------------------------------------------------
# Play-category codes (.prf category byte values)
# ---------------------------------------------------------------------------

GOAL_LINE_RUN: Final = 0x00
RAZZLE_DAZZLE_RUN: Final = 0x01
RUN_LEFT: Final = 0x02
RUN_MIDDLE: Final = 0x03
RUN_RIGHT: Final = 0x04
GOAL_LINE_PASS: Final = 0x05
RAZZLE_DAZZLE_PASS: Final = 0x06
PASS_LONG_LEFT: Final = 0x07
PASS_LONG_MIDDLE: Final = 0x08
PASS_LONG_RIGHT: Final = 0x09
PASS_MEDIUM_LEFT: Final = 0x0A
PASS_MEDIUM_MIDDLE: Final = 0x0B
PASS_MEDIUM_RIGHT: Final = 0x0C
PASS_SHORT_LEFT: Final = 0x0D
PASS_SHORT_MIDDLE: Final = 0x0E
PASS_SHORT_RIGHT: Final = 0x0F
FIELD_GOAL_PAT: Final = 0x10
FAKE_FIELD_GOAL_RUN: Final = 0x11
FAKE_FIELD_GOAL_PASS: Final = 0x12
PUNT: Final = 0x13
FAKE_PUNT_RUN: Final = 0x14
FAKE_PUNT_PASS: Final = 0x15
RUN_CLOCK: Final = 0x16
RUN_RANDOM: Final = 0x17
PASS_LONG_RANDOM: Final = 0x18
PASS_MEDIUM_RANDOM: Final = 0x19
PASS_SHORT_RANDOM: Final = 0x1A

OFFENSE_CATEGORIES: Final[frozenset[int]] = frozenset(range(0x00, 0x1B))
DEFENSE_CATEGORIES: Final[frozenset[int]] = frozenset(range(0x00, 0x16))

# Defense doesn't distinguish pass direction; the three direction codes share a
# single label.
PASS_LONG_ANY: Final[frozenset[int]] = frozenset(
    {PASS_LONG_LEFT, PASS_LONG_MIDDLE, PASS_LONG_RIGHT}
)
PASS_MEDIUM_ANY: Final[frozenset[int]] = frozenset(
    {PASS_MEDIUM_LEFT, PASS_MEDIUM_MIDDLE, PASS_MEDIUM_RIGHT}
)
PASS_SHORT_ANY: Final[frozenset[int]] = frozenset(
    {PASS_SHORT_LEFT, PASS_SHORT_MIDDLE, PASS_SHORT_RIGHT}
)


# ---------------------------------------------------------------------------
# Substitution position groups (prf spec section 2.2)
# ---------------------------------------------------------------------------

# Label -> (display name, side). The game exposes a side's own groups only; the
# other side's stay at the 80/90 default and aren't user-editable.
SUBSTITUTION_POSITIONS: Final[Mapping[str, tuple[str, str]]] = {
    "OL": ("Offensive linemen", "offense"),
    "QB": ("Quarterbacks", "offense"),
    "RB": ("Running backs", "offense"),
    "WR": ("Receivers", "offense"),
    "K": ("Kickers", "offense"),
    "DL": ("Defensive linemen", "defense"),
    "LB": ("Linebackers", "defense"),
    "DB": ("Defensive backs", "defense"),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SituationRule:
    """One profile rule: game-state filters plus the constraints to apply where
    it matches. Each filter is `None` when omitted, meaning "any value of that
    bucket". PointSpread never filters. A situation gets every rule it matches.

    Constraints (each optional): `allowed_categories` limits which categories may
    have weight > 0; `mandatory_alternatives` holds one set per required category
    (at least one code in each must appear); `min_categories` raises the minimum
    distinct categories for matched situations.
    """

    time: MinutesRemaining | None
    down: Down | None
    yards: YardsToGo | None
    fields: frozenset[FieldPosition] | None
    allowed_categories: frozenset[int] | None
    mandatory_alternatives: tuple[frozenset[int], ...]
    min_categories: int | None

    def matches(
        self,
        minutes: MinutesRemaining,
        down: Down,
        yards: YardsToGo,
        field_position: FieldPosition,
    ) -> bool:
        return (
            (self.time is None or self.time == minutes)
            and (self.down is None or self.down == down)
            and (self.yards is None or self.yards == yards)
            and (self.fields is None or field_position in self.fields)
        )


@dataclass(frozen=True, slots=True)
class ProfileRules:
    """Coaching-profile validation rule set.

    `min_categories` is the baseline minimum distinct categories per situation
    (>= 0); a matching rule's `min_categories` raises it (the strictest wins).
    Omitted in the file, it defaults to 0 — no baseline, only rule-level apply.

    `audibles_allowed` omitted in the file defaults to True — no audibles check.

    Every field is optional; an empty rule set enforces nothing.
    """

    audibles_allowed: bool = True
    substitutions: Mapping[str, SubstitutionPair] = field(default_factory=dict)
    offense_situations: tuple[SituationRule, ...] = ()
    defense_situations: tuple[SituationRule, ...] = ()
    min_categories: int = 0
    offense_disallowed_categories: frozenset[int] = frozenset()
    defense_disallowed_categories: frozenset[int] = frozenset()


# ---------------------------------------------------------------------------
# TOML <-> code name maps
# ---------------------------------------------------------------------------

_DOWN_BY_NAME: Final[Mapping[str, Down]] = {
    "first": Down.FIRST,
    "second": Down.SECOND,
    "third": Down.THIRD,
    "fourth": Down.FOURTH,
}
_YARDS_BY_NAME: Final[Mapping[str, YardsToGo]] = {
    "0-1": YardsToGo.ZERO_TO_ONE,
    "2-5": YardsToGo.TWO_TO_FIVE,
    "6-10": YardsToGo.SIX_TO_TEN,
    ">10": YardsToGo.OVER_TEN,
}
_FIELD_BY_NAME: Final[Mapping[str, FieldPosition]] = {
    "inside_def_5": FieldPosition.INSIDE_DEF_5,
    "def_5_to_def_35": FieldPosition.DEF_5_TO_DEF_35,
    "def_35_to_off_35": FieldPosition.DEF_35_TO_OFF_35,
    "off_35_to_off_5": FieldPosition.OFF_35_TO_OFF_5,
    "inside_off_5": FieldPosition.INSIDE_OFF_5,
}
_TIME_BY_NAME: Final[Mapping[str, MinutesRemaining]] = {
    ">5:00": MinutesRemaining.OVER_FIVE,
    ">2:00-5:00": MinutesRemaining.TWO_TO_FIVE,
    ">1:00-2:00": MinutesRemaining.ONE_TO_TWO,
    ">0:15-1:00": MinutesRemaining.FIFTEEN_SEC_TO_ONE,
    "0:00-0:15": MinutesRemaining.ZERO_TO_FIFTEEN_SEC,
}
# Short labels for offense play categories — single code each.
_OFFENSE_CATEGORY_BY_NAME: Final[Mapping[str, frozenset[int]]] = {
    "GLR": frozenset({GOAL_LINE_RUN}),
    "RL":  frozenset({RUN_LEFT}),
    "RM":  frozenset({RUN_MIDDLE}),
    "RR":  frozenset({RUN_RIGHT}),
    "GLP": frozenset({GOAL_LINE_PASS}),
    "PRD": frozenset({RAZZLE_DAZZLE_PASS}),
    "PLR": frozenset({PASS_LONG_RIGHT}),
    "PML": frozenset({PASS_MEDIUM_LEFT}),
    "PMM": frozenset({PASS_MEDIUM_MIDDLE}),
    "PMR": frozenset({PASS_MEDIUM_RIGHT}),
    "PSL": frozenset({PASS_SHORT_LEFT}),
    "PSM": frozenset({PASS_SHORT_MIDDLE}),
    "PSR": frozenset({PASS_SHORT_RIGHT}),
}  # fmt: skip
# Defense names collapse the three pass directions to a single label.
_DEFENSE_CATEGORY_BY_NAME: Final[Mapping[str, frozenset[int]]] = {
    "GLrun":      frozenset({GOAL_LINE_RUN}),
    "RunDazzle":  frozenset({RAZZLE_DAZZLE_RUN}),
    "RunLeft":    frozenset({RUN_LEFT}),
    "RunMiddle":  frozenset({RUN_MIDDLE}),
    "RunRight":   frozenset({RUN_RIGHT}),
    "GLpass":     frozenset({GOAL_LINE_PASS}),
    "PassDazzle": frozenset({RAZZLE_DAZZLE_PASS}),
    "PassLong":   PASS_LONG_ANY,
    "PassMedium": PASS_MEDIUM_ANY,
    "PassShort":  PASS_SHORT_ANY,
}  # fmt: skip
# Full game-category names (as the game shows them), used by the top-level
# disallowed_categories lists — these categories have no league short labels.
# Each maps to its .prf category byte.
_GAME_CATEGORY_BY_NAME: Final[Mapping[str, int]] = {
    "Goal Line Run": GOAL_LINE_RUN,
    "Razzle Dazzle Run": RAZZLE_DAZZLE_RUN,
    "Run Left": RUN_LEFT,
    "Run Middle": RUN_MIDDLE,
    "Run Right": RUN_RIGHT,
    "Goal Line Pass": GOAL_LINE_PASS,
    "Razzle Dazzle Pass": RAZZLE_DAZZLE_PASS,
    "Pass Long Left": PASS_LONG_LEFT,
    "Pass Long Middle": PASS_LONG_MIDDLE,
    "Pass Long Right": PASS_LONG_RIGHT,
    "Pass Medium Left": PASS_MEDIUM_LEFT,
    "Pass Medium Middle": PASS_MEDIUM_MIDDLE,
    "Pass Medium Right": PASS_MEDIUM_RIGHT,
    "Pass Short Left": PASS_SHORT_LEFT,
    "Pass Short Middle": PASS_SHORT_MIDDLE,
    "Pass Short Right": PASS_SHORT_RIGHT,
    "Field Goal/PAT": FIELD_GOAL_PAT,
    "Fake FG Run": FAKE_FIELD_GOAL_RUN,
    "Fake FG Pass": FAKE_FIELD_GOAL_PASS,
    "Punt": PUNT,
    "Fake Punt Run": FAKE_PUNT_RUN,
    "Fake Punt Pass": FAKE_PUNT_PASS,
    "Run Clock": RUN_CLOCK,
    "Run Random": RUN_RANDOM,
    "Pass Long Random": PASS_LONG_RANDOM,
    "Pass Medium Random": PASS_MEDIUM_RANDOM,
    "Pass Short Random": PASS_SHORT_RANDOM,
}

# Allowed keys at each nesting level. Any other key raises RulesFileError so
# typos like `[my_rule]` (missing `offense.`/`defense.` prefix) are caught early.
_ALLOWED_TOP_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "audibles_allowed",
        "min_categories",
        "substitutions",
        "disallowed_offensive_categories",
        "disallowed_defensive_categories",
        "offense",
        "defense",
    }
)
_ALLOWED_SUB_KEYS: Final[frozenset[str]] = frozenset({"out_percent", "in_percent"})
_ALLOWED_SITUATION_KEYS: Final[frozenset[str]] = frozenset(
    {"time", "down", "yards", "fields", "allowed", "disallowed", "mandatory",
     "min_categories"}
)  # fmt: skip
_CONSTRAINT_KEYS: Final[frozenset[str]] = frozenset(
    {"allowed", "disallowed", "mandatory", "min_categories"}
)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class RulesFileError(ValueError):
    """Raised when rules TOML files cannot be parsed or validated. Carries one or
    more messages (`errors`); every detected problem is reported together."""

    def __init__(self, errors: str | Iterable[str]) -> None:
        self.errors: list[str] = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


@dataclass(slots=True)
class _MergedData:
    """Mutable accumulator for merging multiple rules TOML files."""

    audibles_allowed: bool | None = None
    min_categories: int | None = None
    substitutions: dict[str, SubstitutionPair] = field(default_factory=dict)
    offense_disallowed: frozenset[int] = field(default_factory=frozenset)
    defense_disallowed: frozenset[int] = field(default_factory=frozenset)
    # Keyed by section label so a later file's same-named rule replaces it.
    offense_rules: dict[str, SituationRule] = field(default_factory=dict)
    defense_rules: dict[str, SituationRule] = field(default_factory=dict)


def load_rules(paths: Iterable[Path | str]) -> ProfileRules:
    """Load one or more TOML rules files and merge into a `ProfileRules`.

    Files are merged in order. Top-level scalars and section tables are
    overwritten by later files; per-situation rules are replaced by section label.
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

    if "audibles_allowed" in data:
        val, ok = _attempt(
            errors,
            lambda: _require_bool(data["audibles_allowed"], source, "audibles_allowed"),
        )
        if ok:
            merged.audibles_allowed = val
    if "min_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: _require_nonneg_int(
                data["min_categories"], source, "min_categories"
            ),
        )
        if ok:
            merged.min_categories = val
    if "substitutions" in data:
        _merge_substitutions(merged, data["substitutions"], errors, source=source)
    if "disallowed_offensive_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: frozenset(
                _map_each(
                    data["disallowed_offensive_categories"],
                    _GAME_CATEGORY_BY_NAME,
                    source,
                    "disallowed_offensive_categories",
                )
            ),
        )
        if ok:
            merged.offense_disallowed = val
    if "disallowed_defensive_categories" in data:
        val, ok = _attempt(
            errors,
            lambda: frozenset(
                _map_each(
                    data["disallowed_defensive_categories"],
                    _GAME_CATEGORY_BY_NAME,
                    source,
                    "disallowed_defensive_categories",
                )
            ),
        )
        if ok:
            merged.defense_disallowed = val

    for label, section in data.get("offense", {}).items():
        val, ok = _attempt(
            errors,
            lambda label=label, section=section: _build_situation_rule(
                label, section, _OFFENSE_CATEGORY_BY_NAME, source, side="offense"
            ),
        )
        if ok:
            merged.offense_rules[label] = val
    for label, section in data.get("defense", {}).items():
        val, ok = _attempt(
            errors,
            lambda label=label, section=section: _build_situation_rule(
                label, section, _DEFENSE_CATEGORY_BY_NAME, source, side="defense"
            ),
        )
        if ok:
            merged.defense_rules[label] = val


def _build_situation_rule(
    label: str,
    section: Mapping[str, Any],
    category_map: Mapping[str, frozenset[int]],
    source: Path,
    *,
    side: str,
) -> SituationRule:
    where = f"[{side}.{label}]"
    _reject_unknown_keys(section, _ALLOWED_SITUATION_KEYS, source, where)
    if not (set(section) & _CONSTRAINT_KEYS):
        raise RulesFileError(
            f"{source}: {where}: needs one of "
            f"`allowed`, `disallowed`, `mandatory`, `min_categories`"
        )

    time = _optional_enum(section, "time", _TIME_BY_NAME, source, where)
    down = _optional_enum(section, "down", _DOWN_BY_NAME, source, where)
    yards = _optional_enum(section, "yards", _YARDS_BY_NAME, source, where)
    fields = _optional_fields(section, source, where)

    allowed = _build_allowed(section, category_map, source, where)
    mandatory = _build_mandatory(section, category_map, source, where)
    min_categories = (
        _require_nonneg_int(
            section["min_categories"], source, f"{where}.min_categories"
        )
        if "min_categories" in section
        else None
    )

    return SituationRule(
        time=time,
        down=down,
        yards=yards,
        fields=fields,
        allowed_categories=allowed,
        mandatory_alternatives=mandatory,
        min_categories=min_categories,
    )


def _build_allowed(
    section: Mapping[str, Any],
    category_map: Mapping[str, frozenset[int]],
    source: Path,
    where: str,
) -> frozenset[int] | None:
    has_allowed = "allowed" in section
    has_disallowed = "disallowed" in section
    if has_allowed and has_disallowed:
        raise RulesFileError(
            f"{source}: {where}: `allowed` and `disallowed` are mutually exclusive"
        )
    if has_allowed:
        return _expand_categories(
            section["allowed"], category_map, source, f"{where}.allowed"
        )
    if has_disallowed:
        universe = frozenset().union(*category_map.values())
        bad = _expand_categories(
            section["disallowed"], category_map, source, f"{where}.disallowed"
        )
        return universe - bad
    return None


def _build_mandatory(
    section: Mapping[str, Any],
    category_map: Mapping[str, frozenset[int]],
    source: Path,
    where: str,
) -> tuple[frozenset[int], ...]:
    # Flat list: every category listed must be used. One name per entry; a name
    # that covers several codes (e.g. defensive PassShort) is met by any.
    mandatory_raw = section.get("mandatory", [])
    if not isinstance(mandatory_raw, list):
        raise RulesFileError(f"{source}: {where}: `mandatory` must be a list")
    return tuple(
        _expand_categories([name], category_map, source, f"{where}.mandatory")
        for name in mandatory_raw
    )


def _expand_categories(
    names: object,
    category_map: Mapping[str, frozenset[int]],
    source: Path,
    where: str,
) -> frozenset[int]:
    if not isinstance(names, list):
        raise RulesFileError(f"{source}: {where}: must be a list")
    codes: set[int] = set()
    for name in names:
        if not isinstance(name, str):
            raise RulesFileError(
                f"{source}: {where}: entries must be strings "
                f"(got {type(name).__name__})"
            )
        if name not in category_map:
            raise RulesFileError(f"{source}: {where}: unknown category {name!r}")
        codes.update(category_map[name])
    return frozenset(codes)


def _map_each(
    names: object, name_map: Mapping[str, Any], source: Path, where: str
) -> list[Any]:
    if not isinstance(names, list):
        raise RulesFileError(f"{source}: {where}: must be a list")
    result: list[Any] = []
    for name in names:
        if not isinstance(name, str):
            raise RulesFileError(f"{source}: {where}: entries must be strings")
        if name not in name_map:
            raise RulesFileError(f"{source}: {where}: unknown name {name!r}")
        result.append(name_map[name])
    return result


def _merge_substitutions(
    merged: _MergedData, value: object, errors: list[str], *, source: Path
) -> None:
    """Parse `[substitutions]`: one position label -> out/in pair. Each invalid
    pair is reported; a later file's same position replaces it."""
    if not isinstance(value, Mapping):
        errors.append(f"{source}: [substitutions]: must be a table")
        return
    _attempt(
        errors,
        lambda: _reject_unknown_keys(
            value, frozenset(SUBSTITUTION_POSITIONS), source, "[substitutions]"
        ),
    )
    for position in SUBSTITUTION_POSITIONS:
        if position not in value:
            continue
        pair, ok = _attempt(
            errors,
            lambda position=position: _parse_substitution_pair(
                value[position], source, position
            ),
        )
        if ok:
            merged.substitutions[position] = pair


def _parse_substitution_pair(
    value: object, source: Path, position: str
) -> SubstitutionPair:
    where = f"[substitutions].{position}"
    if not isinstance(value, Mapping):
        raise RulesFileError(f"{source}: {where} must be a table")
    _reject_unknown_keys(value, _ALLOWED_SUB_KEYS, source, where)
    if "out_percent" not in value or "in_percent" not in value:
        raise RulesFileError(
            f"{source}: {where} requires `out_percent` and `in_percent`"
        )
    out = _require_int(value["out_percent"], source, f"{where}.out_percent")
    in_ = _require_int(value["in_percent"], source, f"{where}.in_percent")
    try:
        return SubstitutionPair(out_percent=out, in_percent=in_)  # 0-100, out<=in
    except ValueError as e:
        raise RulesFileError(f"{source}: {where}: {e}") from e


def _reject_unknown_keys(
    section: Mapping[str, Any], allowed: frozenset[str], source: Path, where: str
) -> None:
    """Raise if `section` has any key outside `allowed` — catches typos early."""
    unknown = sorted(set(section) - allowed)
    if unknown:
        names = ", ".join(repr(k) for k in unknown)
        raise RulesFileError(f"{source}: {where}: unknown key(s): {names}")


def _lookup(name_map: Mapping[str, Any], key: str, source: Path, where: str) -> Any:
    if key not in name_map:
        raise RulesFileError(f"{source}: {where}: unknown value {key!r}")
    return name_map[key]


def _optional_enum(
    section: Mapping[str, Any],
    key: str,
    name_map: Mapping[str, Any],
    source: Path,
    where: str,
) -> Any:
    """A single bucket filter; omitted -> None (matches any value)."""
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, str):
        raise RulesFileError(f"{source}: {where}.{key}: must be a string")
    return _lookup(name_map, value, source, f"{where}.{key}")


def _optional_fields(
    section: Mapping[str, Any], source: Path, where: str
) -> frozenset[FieldPosition] | None:
    """`fields` filter; omitted -> None (matches any field position)."""
    if "fields" not in section:
        return None
    fields = section["fields"]
    if not isinstance(fields, list) or not fields:
        raise RulesFileError(f"{source}: {where}: `fields` must be a non-empty list")
    return frozenset(
        _lookup(_FIELD_BY_NAME, f, source, f"{where}.fields") for f in fields
    )


def _require_bool(value: object, source: Path, where: str) -> bool:
    if not isinstance(value, bool):
        raise RulesFileError(f"{source}: {where}: must be a boolean")
    return value


def _require_int(value: object, source: Path, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RulesFileError(f"{source}: {where}: must be an integer")
    return value


def _require_nonneg_int(value: object, source: Path, where: str) -> int:
    n = _require_int(value, source, where)
    if n < 0:
        raise RulesFileError(f"{source}: {where}: must be >= 0")
    return n


def _build_rules(m: _MergedData) -> ProfileRules:
    # Omitted scalars fall back to the ProfileRules defaults (audibles_allowed
    # True = no check; min_categories 0 = no baseline).
    scalars: dict[str, Any] = {}
    if m.audibles_allowed is not None:
        scalars["audibles_allowed"] = m.audibles_allowed
    if m.min_categories is not None:
        scalars["min_categories"] = m.min_categories
    return ProfileRules(
        substitutions=dict(m.substitutions),
        offense_situations=tuple(m.offense_rules.values()),
        defense_situations=tuple(m.defense_rules.values()),
        offense_disallowed_categories=m.offense_disallowed,
        defense_disallowed_categories=m.defense_disallowed,
        **scalars,
    )


__all__ = [
    "DEFENSE_CATEGORIES",
    "OFFENSE_CATEGORIES",
    "PASS_LONG_ANY",
    "PASS_MEDIUM_ANY",
    "PASS_SHORT_ANY",
    "SUBSTITUTION_POSITIONS",
    "ProfileRules",
    "RulesFileError",
    "SituationRule",
    "load_rules",
]
