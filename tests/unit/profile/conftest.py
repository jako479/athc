"""Shared paths and profile builders for profile tool-logic unit tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionSettings,
)
from athc.profile.rules import (
    FIELD_GOAL_PAT,
    PASS_MEDIUM_LEFT,
    PASS_SHORT_LEFT,
    RUN_MIDDLE,
)

DATA = Path(__file__).resolve().parent / "data"


def weights(c1: int, w1: int, c2: int, w2: int, c3: int, w3: int) -> CategoryWeights:
    return CategoryWeights(c1, w1, c2, w2, c3, w3)


# Every situation/PAT shares one baseline so a diff isolates the change a test makes.
_BASE = weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3)
_PAT_BASE = weights(FIELD_GOAL_PAT, 10, 0x11, 0, 0x12, 0)


def make_profile(
    profile_type: ProfileType = ProfileType.OFFENSE,
    *,
    field_goal_range: int = 20,
    use_audibles: bool = False,
    substitutions: SubstitutionSettings | None = None,
    category_weights: CategoryWeights | None = None,
) -> Profile:
    """A valid baseline profile (uniform weights); rule-compliance is irrelevant to diffs.

    `category_weights` overrides the per-situation weights (e.g. a single-category
    profile for minimum-count tests).
    """
    base = category_weights or _BASE
    return Profile(
        profile_type=profile_type,
        substitutions=substitutions or SubstitutionSettings.default(),
        situations=tuple(
            Situation.from_situation_number(n, stop_clock=False, category_weights=base)
            for n in range(1, Profile.NUMBER_SITUATIONS + 1)
        ),
        pat_situations=tuple(
            PatSituation.from_situation_number(n, category_weights=_PAT_BASE)
            for n in range(1, Profile.NUMBER_PAT_SITUATIONS + 1)
        ),
        field_goal_range=field_goal_range,
        use_audibles=use_audibles,
    )


def replace_situation(
    profile: Profile, situation_number: int, **changes: object
) -> Profile:
    """Return `profile` with situation `situation_number` replaced via `dataclasses.replace`."""
    idx = situation_number - 1
    new = replace(profile.situations[idx], **changes)
    return replace(
        profile,
        situations=(*profile.situations[:idx], new, *profile.situations[idx + 1 :]),
    )
