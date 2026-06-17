"""Violation types reported by `validate_profile`."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RuleName(StrEnum):
    """Identifier for each kind of rule violation. Values are stable strings."""

    AUDIBLES_UNCHECKED = "audibles_unchecked"
    SUBSTITUTION = "substitution"
    OFFENSE_ALLOWED_CATEGORIES = "offense_allowed_categories"
    OFFENSE_DISALLOWED_CATEGORY = "offense_disallowed_category"
    OFFENSE_MANDATORY_CATEGORY = "offense_mandatory_category"
    OFFENSE_MIN_CATEGORIES = "offense_min_categories"
    DEFENSE_ALLOWED_CATEGORIES = "defense_allowed_categories"
    DEFENSE_DISALLOWED_CATEGORY = "defense_disallowed_category"
    DEFENSE_MANDATORY_CATEGORY = "defense_mandatory_category"
    DEFENSE_MIN_CATEGORIES = "defense_min_categories"


@dataclass(frozen=True, slots=True)
class Violation:
    """One rule violation. `situation_number` (1..2520) is set for per-situation
    violations; profile-wide ones (audibles, substitution) leave it None."""

    rule_name: RuleName
    message: str
    situation_number: int | None = None
