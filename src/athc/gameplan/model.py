"""Violation types reported by the gameplan validators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RuleName(StrEnum):
    """Identifier for each kind of rule violation. Values are stable strings."""

    DUPLICATE_PLAY = "duplicate_play"
    UNRESOLVED_PLAY = "unresolved_play"
    CATEGORY_REQUIRED = "category_required"
    CATEGORY_DISALLOWED = "category_disallowed"
    CATEGORY_MIN_COUNT = "category_min_count"
    CATEGORY_MAX_COUNT = "category_max_count"
    CATEGORY_MAX_QB_DRAWS = "category_max_qb_draws"
    CATEGORY_MAX_ROLLOUTS = "category_max_rollouts"
    CATEGORY_MAX_TIMED_PERCENT = "category_max_timed_percent"
    CATEGORY_MAX_TWO_DL_PERCENT = "category_max_two_dl_percent"
    SPECIAL_CATEGORY_REQUIRED = "special_category_required"
    CUSTOM_SPECIAL_PLAY_REQUIRED = "custom_special_play_required"


@dataclass(frozen=True, slots=True)
class Violation:
    """One rule violation. `category` is the game category name when the
    violation is tied to one (e.g. "Run Middle"); else None."""

    rule_name: RuleName
    message: str
    category: str | None = None
