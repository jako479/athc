"""Validate and diff FbPro98 coaching profiles (.prf) against external league rules."""

from athc.profile.compat import (
    CompatIssue,
    CompatKind,
    check_gameplan_compatibility,
)
from athc.profile.diff import (
    ProfileDiff,
    ScalarChange,
    SituationChange,
    SlotChange,
    diff_profiles,
)
from athc.profile.display import category_label, pat_label, situation_label
from athc.profile.model import RuleName, Violation
from athc.profile.rules import (
    DEFENSE_CATEGORIES,
    OFFENSE_CATEGORIES,
    ProfileRules,
    RulesFileError,
    SituationRule,
    load_rules,
)
from athc.profile.validators import validate_profile
from athc.profile.writer import ProfileTypeMismatchError, ProfileWriter

__all__ = [
    "DEFENSE_CATEGORIES",
    "OFFENSE_CATEGORIES",
    "CompatIssue",
    "CompatKind",
    "ProfileDiff",
    "ProfileRules",
    "ProfileTypeMismatchError",
    "ProfileWriter",
    "RuleName",
    "RulesFileError",
    "ScalarChange",
    "SituationChange",
    "SituationRule",
    "SlotChange",
    "Violation",
    "category_label",
    "check_gameplan_compatibility",
    "diff_profiles",
    "load_rules",
    "pat_label",
    "situation_label",
    "validate_profile",
]
