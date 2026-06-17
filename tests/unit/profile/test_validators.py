"""Unit tests for profile validators, against real profiles with crafted rules."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    MinutesRemaining,
    Profile,
    ProfileType,
    SubstitutionPair,
    SubstitutionSettings,
    YardsToGo,
    read_profile,
)
from athc.profile import ProfileRules, RuleName, load_rules, validate_profile
from athc.profile.rules import (
    FIELD_GOAL_PAT,
    PUNT,
    RUN_CLOCK,
    RUN_LEFT,
    RUN_MIDDLE,
    SituationRule,
)
from tests.unit.profile.conftest import DATA, make_profile, weights

OFF1 = read_profile(str(DATA / "TST-OFF1.prf"))  # offense, audibles off, qb 75/80
OFF1_AUD = read_profile(str(DATA / "TST-OFF1-AUD.prf"))  # offense, audibles ON
DEF1 = read_profile(str(DATA / "TST-DEF1.prf"))  # defense
FULL = load_rules([DATA / "profile_rules.toml"])


def make_rules(**over: object) -> ProfileRules:
    """A do-nothing rule set (fields default to neutral) to override one at a time.

    `min_categories` defaults to 1 here so the baseline-count tests have a floor to
    move; everything else relies on the `ProfileRules` defaults.
    """
    base: dict[str, object] = {"min_categories": 1}
    base.update(over)
    return ProfileRules(**base)  # type: ignore[arg-type]


def rule(
    *,
    time: MinutesRemaining | None = None,
    down: Down | None = None,
    yards: YardsToGo | None = None,
    fields: set[FieldPosition] | None = None,
    allowed: frozenset[int] | None = None,
    mandatory: tuple[frozenset[int], ...] = (),
    min_categories: int | None = None,
) -> SituationRule:
    return SituationRule(
        time=time,
        down=down,
        yards=yards,
        fields=frozenset(fields) if fields is not None else None,
        allowed_categories=allowed,
        mandatory_alternatives=mandatory,
        min_categories=min_categories,
    )


def names(profile: Profile, rules: ProfileRules) -> set[RuleName]:
    return {v.rule_name for v in validate_profile(profile, rules)}


# ── audibles ──────────────────────────────────────────────────────────────────


def test_audibles_fires() -> None:
    assert RuleName.AUDIBLES_UNCHECKED in names(
        OFF1_AUD, make_rules(audibles_allowed=False)
    )


def test_audibles_passes_when_off() -> None:
    assert RuleName.AUDIBLES_UNCHECKED not in names(
        OFF1, make_rules(audibles_allowed=False)
    )


def test_audibles_allowed_never_fires() -> None:
    assert RuleName.AUDIBLES_UNCHECKED not in names(
        OFF1_AUD, make_rules(audibles_allowed=True)
    )


def test_audibles_omitted_allows_either_state(tmp_path: Path) -> None:
    """Rules without `audibles_allowed` never flag audibles, on or off."""
    p = tmp_path / "rules.toml"
    p.write_text("min_categories = 2\n", encoding="utf-8")
    rules = load_rules([p])
    assert RuleName.AUDIBLES_UNCHECKED not in names(OFF1, rules)
    assert RuleName.AUDIBLES_UNCHECKED not in names(OFF1_AUD, rules)


# ── substitutions ──────────────────────────────────────────────────────────────

# label -> (SubstitutionSettings attribute, the side that may set it)
_SUB_GROUPS = [
    ("ol", "offensive_linemen", ProfileType.OFFENSE),
    ("qb", "quarterbacks", ProfileType.OFFENSE),
    ("rb", "running_backs", ProfileType.OFFENSE),
    ("wr", "receivers", ProfileType.OFFENSE),
    ("k", "kickers", ProfileType.OFFENSE),
    ("dl", "defensive_linemen", ProfileType.DEFENSE),
    ("lb", "linebackers", ProfileType.DEFENSE),
    ("db", "defensive_backs", ProfileType.DEFENSE),
]


def _profile_with_sub(ptype: ProfileType, attr: str, pair: SubstitutionPair) -> Profile:
    subs = replace(SubstitutionSettings.default(), **{attr: pair})
    return make_profile(ptype, substitutions=subs)


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_fires_when_mismatched(
    label: str, attr: str, ptype: ProfileType
) -> None:
    """Every group is checked on its own side; a differing pair is flagged."""
    profile = _profile_with_sub(ptype, attr, SubstitutionPair(80, 90))
    rules = make_rules(substitutions={label: SubstitutionPair(70, 75)})
    assert RuleName.SUBSTITUTION in names(profile, rules)


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_passes_when_matched(
    label: str, attr: str, ptype: ProfileType
) -> None:
    profile = _profile_with_sub(ptype, attr, SubstitutionPair(70, 75))
    rules = make_rules(substitutions={label: SubstitutionPair(70, 75)})
    assert RuleName.SUBSTITUTION not in names(profile, rules)


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_skipped_on_other_side(
    label: str, attr: str, ptype: ProfileType
) -> None:
    """A group's rule is ignored on the opposite-side profile."""
    other = ProfileType.DEFENSE if ptype == ProfileType.OFFENSE else ProfileType.OFFENSE
    rules = make_rules(substitutions={label: SubstitutionPair(70, 75)})
    assert RuleName.SUBSTITUTION not in names(make_profile(other), rules)


def test_substitution_message_names_group() -> None:
    profile = make_profile(ProfileType.OFFENSE)  # default subs (qb 80/90)
    rules = make_rules(substitutions={"qb": SubstitutionPair(70, 80)})
    msg = next(
        v.message
        for v in validate_profile(profile, rules)
        if v.rule_name == RuleName.SUBSTITUTION
    )
    assert "Quarterbacks" in msg and "70/80" in msg


def test_substitution_multiple_groups_each_fire() -> None:
    profile = make_profile(ProfileType.OFFENSE)  # default subs all 80/90
    rules = make_rules(
        substitutions={"qb": SubstitutionPair(70, 75), "ol": SubstitutionPair(60, 65)}
    )
    fired = [
        v
        for v in validate_profile(profile, rules)
        if v.rule_name == RuleName.SUBSTITUTION
    ]
    assert len(fired) == 2


def test_no_substitutions_no_violation() -> None:
    assert RuleName.SUBSTITUTION not in names(OFF1, make_rules())


# ── min categories ────────────────────────────────────────────────────────────


def _min_category_count(rules: ProfileRules) -> int:
    return sum(
        1
        for v in validate_profile(OFF1, rules)
        if v.rule_name == RuleName.OFFENSE_MIN_CATEGORIES
    )


def test_min_categories_scales_with_threshold() -> None:
    strict = _min_category_count(make_rules(min_categories=3))
    lax = _min_category_count(make_rules(min_categories=1))
    assert strict > lax  # a higher minimum flags more situations


def test_min_categories_rule_raises_baseline() -> None:
    """A matching rule's min_categories overrides the lower baseline."""
    raised = rule(time=MinutesRemaining.OVER_FIVE, min_categories=3)
    n_baseline = _min_category_count(make_rules(min_categories=1))
    n_raised = _min_category_count(
        make_rules(min_categories=1, offense_situations=(raised,))
    )
    assert n_raised > n_baseline  # the >5:00 rule lifts those situations to 3


def test_min_categories_waived_when_all_exempt() -> None:
    exempt = frozenset({FIELD_GOAL_PAT, PUNT, RUN_CLOCK})
    n_exempt = _min_category_count(
        make_rules(min_categories=3, offense_exempt_categories=exempt)
    )
    n_plain = _min_category_count(make_rules(min_categories=3))
    assert n_exempt < n_plain  # exempt-only situations are waived


def test_min_categories_baseline_wins_over_lower_rule() -> None:
    """A matching rule's lower min_categories does not drop the baseline."""
    low = rule(time=MinutesRemaining.OVER_FIVE, min_categories=2)
    n_baseline = _min_category_count(make_rules(min_categories=3))
    n_with_low = _min_category_count(
        make_rules(min_categories=3, offense_situations=(low,))
    )
    assert n_with_low == n_baseline  # baseline 3 still applies; the 2 is ignored


def test_min_categories_not_waived_with_non_exempt_category() -> None:
    """Waiver needs every used category exempt; one real category re-arms the min."""
    mixed = make_profile(
        category_weights=weights(FIELD_GOAL_PAT, 10, RUN_MIDDLE, 4, 0, 0)
    )
    exempt = frozenset({FIELD_GOAL_PAT, PUNT, RUN_CLOCK})
    rules = make_rules(min_categories=3, offense_exempt_categories=exempt)
    assert RuleName.OFFENSE_MIN_CATEGORIES in names(mixed, rules)


def test_min_categories_fires_on_all_zero_weights() -> None:
    """A situation with no weighted category (0 categories) is never waived."""
    empty = make_profile(category_weights=weights(0, 0, 0, 0, 0, 0))
    exempt = frozenset({FIELD_GOAL_PAT, PUNT, RUN_CLOCK})
    rules = make_rules(min_categories=2, offense_exempt_categories=exempt)
    assert RuleName.OFFENSE_MIN_CATEGORIES in names(empty, rules)


def test_no_minimum_passes_single_category() -> None:
    """No baseline (min_categories=0) → a lone non-exempt category never fires."""
    single = make_profile(category_weights=weights(RUN_MIDDLE, 4, 0, 0, 0, 0))
    assert RuleName.OFFENSE_MIN_CATEGORIES not in names(
        single, make_rules(min_categories=0)
    )


def test_rule_minimum_applies_without_baseline() -> None:
    """A rule's min_categories applies even when the baseline is 0."""
    single = make_profile(category_weights=weights(RUN_MIDDLE, 4, 0, 0, 0, 0))
    raised = rule(time=MinutesRemaining.OVER_FIVE, min_categories=2)
    rules = make_rules(min_categories=0, offense_situations=(raised,))
    flagged = {
        v.situation_number
        for v in validate_profile(single, rules)
        if v.rule_name == RuleName.OFFENSE_MIN_CATEGORIES
    }
    assert 1 in flagged  # OVER_FIVE situation lifted to 2 by the rule
    assert 515 not in flagged  # TWO_TO_FIVE — no rule, no baseline


# ── matrix rules across time buckets ──────────────────────────────────────────


def test_matrix_rule_fires_in_non_over_five_bucket() -> None:
    """A situation rule applies to whatever time bucket it filters on.

    The baseline profile uses RUN_MIDDLE + two pass categories everywhere. A rule
    scoped to the TWO_TO_FIVE bucket that allows only RUN_MIDDLE must flag the
    matching situation there, but leave its OVER_FIVE counterpart untouched.
    """
    r = rule(
        time=MinutesRemaining.TWO_TO_FIVE,
        down=Down.FIRST,
        yards=YardsToGo.ZERO_TO_ONE,
        fields={FieldPosition.DEF_5_TO_DEF_35},
        allowed=frozenset({RUN_MIDDLE}),
    )
    rules = make_rules(offense_situations=(r,))
    flagged = {
        v.situation_number
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_ALLOWED_CATEGORIES
    }
    assert 515 in flagged  # TWO_TO_FIVE, 1st-and-0-1, DEF 5-35, tied
    assert 11 not in flagged  # OVER_FIVE counterpart — rule doesn't match


def test_omitted_buckets_match_all() -> None:
    """A rule with no down/yards/field filter matches every situation in its bucket."""
    r = rule(time=MinutesRemaining.OVER_FIVE, allowed=frozenset({RUN_MIDDLE}))
    rules = make_rules(offense_situations=(r,))
    flagged = {
        v.situation_number
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_ALLOWED_CATEGORIES
    }
    assert 1 in flagged  # an OVER_FIVE situation
    assert 515 not in flagged  # a TWO_TO_FIVE situation — outside the time filter


# ── mandatory categories ──────────────────────────────────────────────────────


def test_multiple_mandatory_categories_each_required() -> None:
    """Every category in a `mandatory` list must be used; each is checked alone.

    The baseline profile uses RUN_MIDDLE everywhere but never RUN_LEFT. A rule
    requiring both flags only the missing one (RUN_LEFT, 0x02), not RUN_MIDDLE.
    """
    r = rule(
        time=MinutesRemaining.OVER_FIVE,
        down=Down.FIRST,
        yards=YardsToGo.ZERO_TO_ONE,
        fields={FieldPosition.DEF_5_TO_DEF_35},
        mandatory=(frozenset({RUN_MIDDLE}), frozenset({RUN_LEFT})),
    )
    rules = make_rules(offense_situations=(r,))
    flagged = [
        v
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_MANDATORY_CATEGORY
    ]
    assert flagged  # the cell's seven point-spread situations each fire once
    assert all("0x02" in v.message for v in flagged)  # RUN_LEFT missing
    assert all("0x03" not in v.message for v in flagged)  # RUN_MIDDLE satisfied


# ── disallowed categories ─────────────────────────────────────────────────────


def test_disallowed_category_fires() -> None:
    """A category in the disallowed set is flagged wherever it has weight."""
    rules = make_rules(offense_disallowed_categories=frozenset({RUN_MIDDLE}))
    flagged = [
        v
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_DISALLOWED_CATEGORY
    ]
    assert flagged
    assert all("0x03" in v.message for v in flagged)  # RUN_MIDDLE = 0x03


def test_disallowed_category_clean_when_unused() -> None:
    """A disallowed category the profile never uses fires nothing."""
    rules = make_rules(offense_disallowed_categories=frozenset({RUN_LEFT}))
    assert RuleName.OFFENSE_DISALLOWED_CATEGORY not in names(make_profile(), rules)


def test_all_issues_reported_including_disallowed() -> None:
    """One validate_profile reports every distinct issue, not just the first.

    The baseline profile (RUN_MIDDLE + two passes) is made to trip three rules at
    once: a banned category, a too-restrictive allowed set, and the minimum.
    """
    rules = make_rules(
        min_categories=5,
        offense_disallowed_categories=frozenset({RUN_MIDDLE}),
        offense_situations=(rule(allowed=frozenset({RUN_LEFT})),),
    )
    kinds = {v.rule_name for v in validate_profile(make_profile(), rules)}
    assert {
        RuleName.OFFENSE_DISALLOWED_CATEGORY,
        RuleName.OFFENSE_ALLOWED_CATEGORIES,
        RuleName.OFFENSE_MIN_CATEGORIES,
    } <= kinds


# ── full rule set on real profiles ────────────────────────────────────────────


def test_offense_full_rules() -> None:
    violations = validate_profile(OFF1, FULL)
    assert len(violations) == 18
    pairs = {(v.situation_number, v.rule_name) for v in violations}
    assert (1, RuleName.OFFENSE_ALLOWED_CATEGORIES) in pairs
    assert (300, RuleName.OFFENSE_MANDATORY_CATEGORY) in pairs
    assert (43, RuleName.OFFENSE_MIN_CATEGORIES) in pairs


def test_defense_full_rules() -> None:
    violations = validate_profile(DEF1, FULL)
    assert len(violations) == 7
    assert all(v.rule_name == RuleName.DEFENSE_MIN_CATEGORIES for v in violations)
