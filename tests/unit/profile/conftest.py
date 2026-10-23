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
    FAKE_FIELD_GOAL_PASS,
    FAKE_FIELD_GOAL_RUN,
    FIELD_GOAL_PAT,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_ANY,
    PASS_LONG_LEFT,
    PASS_LONG_MIDDLE,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_ANY,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_ANY,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RIGHT,
    PercentBound,
    SubstitutionRule,
)

DATA = Path(__file__).resolve().parent / "data"

# Each game category -> the .prf codes it stands for. Offense keeps the pass
# directions; defense has one category per pass length, covering all three.
OFFENSE_CODES_BY_NAME: dict[str, frozenset[int]] = {
    "Goal Line Run": frozenset({GOAL_LINE_RUN}),
    "Razzle Dazzle Run": frozenset({RAZZLE_DAZZLE_RUN}),
    "Run Left": frozenset({RUN_LEFT}),
    "Run Middle": frozenset({RUN_MIDDLE}),
    "Run Right": frozenset({RUN_RIGHT}),
    "Goal Line Pass": frozenset({GOAL_LINE_PASS}),
    "Razzle Dazzle Pass": frozenset({RAZZLE_DAZZLE_PASS}),
    "Pass Long Left": frozenset({PASS_LONG_LEFT}),
    "Pass Long Middle": frozenset({PASS_LONG_MIDDLE}),
    "Pass Long Right": frozenset({PASS_LONG_RIGHT}),
    "Pass Medium Left": frozenset({PASS_MEDIUM_LEFT}),
    "Pass Medium Middle": frozenset({PASS_MEDIUM_MIDDLE}),
    "Pass Medium Right": frozenset({PASS_MEDIUM_RIGHT}),
    "Pass Short Left": frozenset({PASS_SHORT_LEFT}),
    "Pass Short Middle": frozenset({PASS_SHORT_MIDDLE}),
    "Pass Short Right": frozenset({PASS_SHORT_RIGHT}),
}
DEFENSE_CODES_BY_NAME: dict[str, frozenset[int]] = {
    "Goal Line Run": frozenset({GOAL_LINE_RUN}),
    "Razzle Dazzle Run": frozenset({RAZZLE_DAZZLE_RUN}),
    "Run Left": frozenset({RUN_LEFT}),
    "Run Middle": frozenset({RUN_MIDDLE}),
    "Run Right": frozenset({RUN_RIGHT}),
    "Goal Line Pass": frozenset({GOAL_LINE_PASS}),
    "Razzle Dazzle Pass": frozenset({RAZZLE_DAZZLE_PASS}),
    "Pass Long": PASS_LONG_ANY,
    "Pass Medium": PASS_MEDIUM_ANY,
    "Pass Short": PASS_SHORT_ANY,
}


def weights(c1: int, w1: int, c2: int, w2: int, c3: int, w3: int) -> CategoryWeights:
    return CategoryWeights(c1, w1, c2, w2, c3, w3)


def exact_substitution(out: int, in_: int) -> SubstitutionRule:
    """A substitution rule pinning both sides to exact values."""
    return SubstitutionRule(
        out_percent=PercentBound(exact=out), in_percent=PercentBound(exact=in_)
    )


# Every situation/PAT shares one baseline so a diff isolates the change a test makes.
_BASE = weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3)
_PAT_BASE = weights(FIELD_GOAL_PAT, 10, FAKE_FIELD_GOAL_RUN, 0, FAKE_FIELD_GOAL_PASS, 0)


def make_profile(
    profile_type: ProfileType = ProfileType.OFFENSE,
    *,
    field_goal_range: int = 20,
    use_audibles: bool = False,
    substitutions: SubstitutionSettings | None = None,
    category_weights: CategoryWeights | None = None,
) -> Profile:
    """A valid baseline profile: every situation uses the same weights (RM 4,
    PSL 3, PML 3), every PAT the same kick.

    `category_weights` overrides the per-situation weights (e.g. a single-category
    profile for minimum-count tests).
    """
    base = category_weights or _BASE
    return Profile(
        profile_type=profile_type,
        substitutions=substitutions or SubstitutionSettings.default(),
        situations=tuple(
            Situation(stop_clock=False, category_weights=base)
            for _ in range(Profile.NUMBER_SITUATIONS)
        ),
        pat_situations=tuple(
            PatSituation(category_weights=_PAT_BASE)
            for _ in range(Profile.NUMBER_PAT_SITUATIONS)
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
