"""Unit tests for profile validators, against real profiles with crafted rules."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from functools import partial
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
from athc.profile import (
    PercentBound,
    ProfileRules,
    RuleName,
    RuleViolation,
    SubstitutionRule,
    validate_profile,
)
from athc.profile import load_rules as _load_rules
from athc.profile.rules import (
    FAKE_FIELD_GOAL_PASS,
    FAKE_FIELD_GOAL_RUN,
    FAKE_PUNT_PASS,
    FAKE_PUNT_RUN,
    FIELD_GOAL_PAT,
    PASS_LONG_LEFT,
    PASS_LONG_RANDOM,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_RANDOM,
    PASS_SHORT_LEFT,
    PASS_SHORT_RANDOM,
    PUNT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_CLOCK,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RANDOM,
    SituationRule,
)
from tests.conftest import PNFL_LABELS
from tests.unit.profile.conftest import (
    DATA,
    exact_substitution,
    make_profile,
    weights,
)

load_rules = partial(_load_rules, labels=PNFL_LABELS)

OFF1 = read_profile(str(DATA / "TST-OFF1.prf"))  # offense, audibles off, qb 75/80
OFF1_AUD = read_profile(str(DATA / "TST-OFF1-AUD.prf"))  # offense, audibles ON
DEF1 = read_profile(str(DATA / "TST-DEF1.prf"))  # defense, DL/LB/DB 96/98
FULL = load_rules([DATA / "profile_rules.toml"])

ALL_SITUATIONS = range(1, Profile.NUMBER_SITUATIONS + 1)
# The first 504 slots are the >5:00 bucket (prf.md 2.3.4).
OVER_FIVE_SITUATIONS = range(1, 505)


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
    disallowed: frozenset[int] = frozenset(),
    mandatory: tuple[frozenset[int], ...] = (),
    min_categories: int | None = None,
) -> SituationRule:
    return SituationRule(
        time=time,
        down=down,
        yards=yards,
        fields=frozenset(fields) if fields is not None else None,
        allowed_categories=allowed,
        disallowed_categories=disallowed,
        mandatory_alternatives=mandatory,
        min_categories=min_categories,
    )


def names(profile: Profile, rules: ProfileRules) -> set[RuleName]:
    return {v.rule_name for v in validate_profile(profile, rules)}


# ── audibles ──────────────────────────────────────────────────────────────────


def test_audibles_fires() -> None:
    assert validate_profile(OFF1_AUD, make_rules(audibles_allowed=False)) == (
        RuleViolation(RuleName.AUDIBLES_UNCHECKED, "Audibles must be unchecked."),
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
    ("OL", "offensive_linemen", ProfileType.OFFENSE),
    ("QB", "quarterbacks", ProfileType.OFFENSE),
    ("RB", "running_backs", ProfileType.OFFENSE),
    ("WR", "receivers", ProfileType.OFFENSE),
    ("K", "kickers", ProfileType.OFFENSE),
    ("DL", "defensive_linemen", ProfileType.DEFENSE),
    ("LB", "linebackers", ProfileType.DEFENSE),
    ("DB", "defensive_backs", ProfileType.DEFENSE),
]


def _profile_with_sub(ptype: ProfileType, attr: str, pair: SubstitutionPair) -> Profile:
    subs = replace(SubstitutionSettings.default(), **{attr: pair})
    return make_profile(ptype, substitutions=subs)


def _qb_profile(out: int, in_: int) -> Profile:
    return _profile_with_sub(
        ProfileType.OFFENSE, "quarterbacks", SubstitutionPair(out, in_)
    )


def _sub_messages(profile: Profile, rules: ProfileRules) -> list[str]:
    return [
        v.message
        for v in validate_profile(profile, rules)
        if v.rule_name == RuleName.SUBSTITUTION
    ]


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_fires_when_mismatched(
    label: str, attr: str, ptype: ProfileType
) -> None:
    """Every group is checked on its own side; a differing pair is flagged."""
    profile = _profile_with_sub(ptype, attr, SubstitutionPair(80, 90))
    rules = make_rules(substitutions={label: exact_substitution(70, 75)})
    assert RuleName.SUBSTITUTION in names(profile, rules)


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_passes_when_matched(
    label: str, attr: str, ptype: ProfileType
) -> None:
    profile = _profile_with_sub(ptype, attr, SubstitutionPair(70, 75))
    rules = make_rules(substitutions={label: exact_substitution(70, 75)})
    assert RuleName.SUBSTITUTION not in names(profile, rules)


@pytest.mark.parametrize("label,attr,ptype", _SUB_GROUPS)
def test_substitution_skipped_on_other_side(
    label: str, attr: str, ptype: ProfileType
) -> None:
    """A group's rule is ignored on the opposite-side profile."""
    other = ProfileType.DEFENSE if ptype == ProfileType.OFFENSE else ProfileType.OFFENSE
    rules = make_rules(substitutions={label: exact_substitution(70, 75)})
    assert RuleName.SUBSTITUTION not in names(make_profile(other), rules)


def test_substitution_exact_reports_each_side() -> None:
    """Each mismatched side is its own violation: group, side, bound, actual."""
    rules = make_rules(substitutions={"QB": exact_substitution(70, 80)})
    assert _sub_messages(_qb_profile(80, 90), rules) == [
        "Quarterbacks out_percent must be 70, got 80.",
        "Quarterbacks in_percent must be 80, got 90.",
    ]


def test_substitution_exact_matched_side_is_silent() -> None:
    rules = make_rules(substitutions={"QB": exact_substitution(70, 80)})
    assert _sub_messages(_qb_profile(70, 90), rules) == [
        "Quarterbacks in_percent must be 80, got 90."
    ]


@pytest.mark.parametrize(
    "actual,expected",
    [
        (69, ["Quarterbacks out_percent must be >= 70, got 69."]),
        (70, []),  # at min
        (80, []),  # at max
        (81, ["Quarterbacks out_percent must be <= 80, got 81."]),
    ],
)
def test_substitution_range_bounds_inclusive(actual: int, expected: list[str]) -> None:
    """min/max are inclusive; a value outside names the bound it breaks."""
    rules = make_rules(
        substitutions={
            "QB": SubstitutionRule(out_percent=PercentBound(minimum=70, maximum=80))
        }
    )
    assert _sub_messages(_qb_profile(actual, 90), rules) == expected


def test_substitution_min_only() -> None:
    rules = make_rules(
        substitutions={"QB": SubstitutionRule(in_percent=PercentBound(minimum=85))}
    )
    assert _sub_messages(_qb_profile(80, 84), rules) == [
        "Quarterbacks in_percent must be >= 85, got 84."
    ]
    assert _sub_messages(_qb_profile(80, 85), rules) == []


def test_substitution_max_only() -> None:
    rules = make_rules(
        substitutions={"QB": SubstitutionRule(in_percent=PercentBound(maximum=85))}
    )
    assert _sub_messages(_qb_profile(80, 86), rules) == [
        "Quarterbacks in_percent must be <= 85, got 86."
    ]
    assert _sub_messages(_qb_profile(80, 85), rules) == []


def test_substitution_unchecked_side_accepts_any_value() -> None:
    rules = make_rules(
        substitutions={"QB": SubstitutionRule(out_percent=PercentBound(exact=75))}
    )
    assert _sub_messages(_qb_profile(75, 75), rules) == []
    assert _sub_messages(_qb_profile(75, 100), rules) == []


def test_substitution_exact_and_range_mixed() -> None:
    rules = make_rules(
        substitutions={
            "QB": SubstitutionRule(
                out_percent=PercentBound(exact=75), in_percent=PercentBound(minimum=80)
            )
        }
    )
    assert _sub_messages(_qb_profile(75, 80), rules) == []
    assert _sub_messages(_qb_profile(70, 79), rules) == [
        "Quarterbacks out_percent must be 75, got 70.",
        "Quarterbacks in_percent must be >= 80, got 79.",
    ]


def test_substitution_bound_on_defense_group() -> None:
    """Bounds apply to defense groups on defense profiles and are skipped on offense."""
    rules = make_rules(
        substitutions={"DL": SubstitutionRule(out_percent=PercentBound(maximum=70))}
    )
    dl = _profile_with_sub(
        ProfileType.DEFENSE, "defensive_linemen", SubstitutionPair(80, 90)
    )
    assert _sub_messages(dl, rules) == [
        "Defensive linemen out_percent must be <= 70, got 80."
    ]
    assert _sub_messages(make_profile(ProfileType.OFFENSE), rules) == []


def test_substitution_multiple_groups_each_fire() -> None:
    profile = make_profile(ProfileType.OFFENSE)  # default subs all 80/90
    rules = make_rules(
        substitutions={
            "QB": SubstitutionRule(out_percent=PercentBound(exact=70)),
            "OL": SubstitutionRule(out_percent=PercentBound(exact=60)),
        }
    )
    fired = _sub_messages(profile, rules)
    assert len(fired) == 2
    assert any("Quarterbacks" in m for m in fired)
    assert any("Offensive linemen" in m for m in fired)


def test_no_substitutions_no_violation() -> None:
    assert RuleName.SUBSTITUTION not in names(OFF1, make_rules())


# ── min categories ────────────────────────────────────────────────────────────


_TWO_CATEGORIES = weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, 0, 0)


def _min_violations(profile: Profile, rules: ProfileRules) -> list[RuleViolation]:
    return [
        v
        for v in validate_profile(profile, rules)
        if v.rule_name
        in (RuleName.OFFENSE_MIN_CATEGORIES, RuleName.DEFENSE_MIN_CATEGORIES)
    ]


def _too_few(
    numbers: Iterable[int],
    used: int,
    required: int,
    rule_name: RuleName = RuleName.OFFENSE_MIN_CATEGORIES,
) -> list[RuleViolation]:
    """The min-categories violation each situation in `numbers` gets."""
    return [
        RuleViolation(
            rule_name,
            f"Situation {n} has {used} category(ies) with non-zero weight; "
            f"requires {required}.",
            situation_number=n,
        )
        for n in numbers
    ]


@pytest.mark.parametrize(("minimum", "flagged"), [(2, False), (3, True)])
def test_min_categories_at_the_limit_and_one_past(minimum: int, flagged: bool) -> None:
    """A situation with exactly the minimum passes; one short is flagged."""
    profile = make_profile(category_weights=_TWO_CATEGORIES)
    expected = _too_few(ALL_SITUATIONS, 2, minimum) if flagged else []
    assert _min_violations(profile, make_rules(min_categories=minimum)) == expected


@pytest.mark.parametrize(("weight", "flagged"), [(0, True), (1, False)])
def test_weight_one_counts_a_category_and_weight_zero_does_not(
    weight: int, flagged: bool
) -> None:
    profile = make_profile(
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, weight, 0, 0)
    )
    expected = _too_few(ALL_SITUATIONS, 1, 2) if flagged else []
    assert _min_violations(profile, make_rules(min_categories=2)) == expected


@pytest.mark.parametrize("baseline", [0, 2])
def test_rule_min_categories_raises_the_baseline_where_it_matches(
    baseline: int,
) -> None:
    """A matching rule's higher minimum applies in its bucket only, with or
    without a baseline; elsewhere the baseline holds."""
    raised = rule(time=MinutesRemaining.OVER_FIVE, min_categories=3)
    rules = make_rules(min_categories=baseline, offense_situations=(raised,))
    profile = make_profile(category_weights=_TWO_CATEGORIES)
    assert _min_violations(profile, rules) == _too_few(OVER_FIVE_SITUATIONS, 2, 3)


def test_min_categories_baseline_wins_over_lower_rule() -> None:
    """A matching rule's lower min_categories does not drop the baseline."""
    low = rule(time=MinutesRemaining.OVER_FIVE, min_categories=2)
    rules = make_rules(min_categories=3, offense_situations=(low,))
    profile = make_profile(category_weights=_TWO_CATEGORIES)
    assert _min_violations(profile, rules) == _too_few(ALL_SITUATIONS, 2, 3)


def test_min_categories_strictest_matching_rule_wins() -> None:
    """Of several matching rules the highest minimum applies; it is neither the
    first nor the last here."""
    rules = make_rules(
        offense_situations=(
            rule(min_categories=2),
            rule(min_categories=4),
            rule(min_categories=3),
        )
    )
    assert _min_violations(make_profile(), rules) == _too_few(ALL_SITUATIONS, 3, 4)


# Each code alone at a minimum of 3: only kick and punt (plus run clock on
# offense) are waived; the fakes and the randoms are not.
@pytest.mark.parametrize(
    ("ptype", "code", "waived"),
    [
        (ProfileType.OFFENSE, RUN_MIDDLE, False),
        (ProfileType.OFFENSE, FIELD_GOAL_PAT, True),
        (ProfileType.OFFENSE, FAKE_FIELD_GOAL_RUN, False),
        (ProfileType.OFFENSE, FAKE_FIELD_GOAL_PASS, False),
        (ProfileType.OFFENSE, PUNT, True),
        (ProfileType.OFFENSE, FAKE_PUNT_RUN, False),
        (ProfileType.OFFENSE, FAKE_PUNT_PASS, False),
        (ProfileType.OFFENSE, RUN_CLOCK, True),
        (ProfileType.OFFENSE, RUN_RANDOM, False),
        (ProfileType.OFFENSE, PASS_LONG_RANDOM, False),
        (ProfileType.OFFENSE, PASS_MEDIUM_RANDOM, False),
        (ProfileType.OFFENSE, PASS_SHORT_RANDOM, False),
        (ProfileType.DEFENSE, RUN_MIDDLE, False),
        (ProfileType.DEFENSE, FIELD_GOAL_PAT, True),
        (ProfileType.DEFENSE, FAKE_FIELD_GOAL_RUN, False),
        (ProfileType.DEFENSE, FAKE_FIELD_GOAL_PASS, False),
        (ProfileType.DEFENSE, PUNT, True),
        (ProfileType.DEFENSE, FAKE_PUNT_RUN, False),
        (ProfileType.DEFENSE, FAKE_PUNT_PASS, False),
    ],
)
def test_min_categories_waived_only_for_exempt_categories(
    ptype: ProfileType, code: int, waived: bool
) -> None:
    profile = make_profile(ptype, category_weights=weights(code, 4, 0, 0, 0, 0))
    rule_name = (
        RuleName.OFFENSE_MIN_CATEGORIES
        if ptype == ProfileType.OFFENSE
        else RuleName.DEFENSE_MIN_CATEGORIES
    )
    expected = [] if waived else _too_few(ALL_SITUATIONS, 1, 3, rule_name)
    assert _min_violations(profile, make_rules(min_categories=3)) == expected


def test_exempt_combination_waived() -> None:
    """Any mix of exempt categories (e.g. punt + punt + kick) is still waived."""
    profile = make_profile(
        category_weights=weights(PUNT, 4, PUNT, 4, FIELD_GOAL_PAT, 2)
    )
    assert RuleName.OFFENSE_MIN_CATEGORIES not in names(
        profile, make_rules(min_categories=3)
    )


def test_exempt_plus_non_exempt_obeys_minimum() -> None:
    """punt + punt + PSL = 2 distinct categories: flagged when min is 3, allowed at 2."""
    profile = make_profile(
        category_weights=weights(PUNT, 4, PUNT, 4, PASS_SHORT_LEFT, 2)
    )
    assert RuleName.OFFENSE_MIN_CATEGORIES in names(
        profile, make_rules(min_categories=3)
    )
    assert RuleName.OFFENSE_MIN_CATEGORIES not in names(
        profile, make_rules(min_categories=2)
    )


def test_min_categories_not_waived_with_non_exempt_category() -> None:
    """Waiver needs every used category exempt; one real category re-arms the min."""
    mixed = make_profile(
        category_weights=weights(FIELD_GOAL_PAT, 10, RUN_MIDDLE, 4, 0, 0)
    )
    assert RuleName.OFFENSE_MIN_CATEGORIES in names(mixed, make_rules(min_categories=3))


def test_min_categories_fires_on_all_zero_weights() -> None:
    """A situation with no weighted category (0 categories) is never waived."""
    empty = make_profile(category_weights=weights(0, 0, 0, 0, 0, 0))
    assert RuleName.OFFENSE_MIN_CATEGORIES in names(empty, make_rules(min_categories=2))


def test_no_minimum_passes_single_category() -> None:
    """No baseline (min_categories=0) → a lone non-exempt category never fires."""
    single = make_profile(category_weights=weights(RUN_MIDDLE, 4, 0, 0, 0, 0))
    assert RuleName.OFFENSE_MIN_CATEGORIES not in names(
        single, make_rules(min_categories=0)
    )


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
    # The cell is situations 8-14, one per point spread (prf.md 2.3.4); each
    # fires once, for RUN_LEFT only.
    assert [(v.situation_number, v.message) for v in flagged] == [
        (n, f"Situation {n} is missing a mandatory category (one of: 0x02)")
        for n in range(8, 15)
    ]


def test_mandatory_category_of_two_matching_rules_reported_once() -> None:
    needs_run_left = (frozenset({RUN_LEFT}),)
    rules = make_rules(
        offense_situations=(
            rule(mandatory=needs_run_left),
            rule(mandatory=needs_run_left),
        )
    )
    assert validate_profile(make_profile(), rules) == tuple(
        RuleViolation(
            RuleName.OFFENSE_MANDATORY_CATEGORY,
            f"Situation {n} is missing a mandatory category (one of: 0x02)",
            situation_number=n,
        )
        for n in ALL_SITUATIONS
    )


# ── allowed categories ────────────────────────────────────────────────────────


def test_two_matching_rules_allowed_intersect() -> None:
    """Each matching rule's `allowed` narrows the others: RM+PSL and RM+PML
    leave only RM, so the baseline's PSL (0x0D) and PML (0x0A) are flagged."""
    rules = make_rules(
        offense_situations=(
            rule(allowed=frozenset({RUN_MIDDLE, PASS_SHORT_LEFT})),
            rule(allowed=frozenset({RUN_MIDDLE, PASS_MEDIUM_LEFT})),
        )
    )
    assert validate_profile(make_profile(), rules) == tuple(
        RuleViolation(
            RuleName.OFFENSE_ALLOWED_CATEGORIES,
            f"Situation {n} uses disallowed categories: 0x0A, 0x0D",
            situation_number=n,
        )
        for n in ALL_SITUATIONS
    )


# ── disallowed categories ─────────────────────────────────────────────────────


def _banned_messages(profile: Profile, rules: ProfileRules) -> list[str]:
    return [
        v.message
        for v in validate_profile(profile, rules)
        if v.rule_name
        in (RuleName.OFFENSE_DISALLOWED_CATEGORY, RuleName.DEFENSE_DISALLOWED_CATEGORY)
    ]


def test_category_outside_allowed_list_is_banned() -> None:
    """A used category the allowed list leaves out is banned in every situation
    that uses it. The baseline profile uses RUN_MIDDLE (0x03), PSL and PML."""
    rules = make_rules(
        offense_allowed_categories=frozenset({PASS_SHORT_LEFT, PASS_MEDIUM_LEFT})
    )
    assert _banned_messages(make_profile(), rules) == [
        f"Situation {n} uses banned categories: 0x03"
        for n in range(1, Profile.NUMBER_SITUATIONS + 1)
    ]


def test_allowed_list_clean_when_every_used_category_is_listed() -> None:
    rules = make_rules(
        offense_allowed_categories=frozenset(
            {RUN_MIDDLE, PASS_SHORT_LEFT, PASS_MEDIUM_LEFT}
        )
    )
    assert _banned_messages(make_profile(), rules) == []


@pytest.mark.parametrize("ptype", [ProfileType.OFFENSE, ProfileType.DEFENSE])
def test_empty_allowed_list_enforces_nothing(ptype: ProfileType) -> None:
    profile = make_profile(
        ptype, category_weights=weights(RUN_RANDOM, 4, RAZZLE_DAZZLE_RUN, 3, 0, 0)
    )
    assert _banned_messages(profile, make_rules()) == []


# Every code of each side against a list naming only RUN_MIDDLE. The lists
# limit offense 0x00-0x0F and the randoms 0x17-0x1A (no league label), and
# defense 0x00-0x0F; the special categories (offense 0x10-0x16, defense
# 0x10-0x15) are never limited.
_OFFENSE_LIMITED = frozenset(range(0x00, 0x10)) | frozenset(range(0x17, 0x1B))
_DEFENSE_LIMITED = frozenset(range(0x00, 0x10))


@pytest.mark.parametrize(
    ("ptype", "code"),
    [(ProfileType.OFFENSE, code) for code in range(0x00, 0x1B)]
    + [(ProfileType.DEFENSE, code) for code in range(0x00, 0x16)],
)
def test_allowed_list_scope(ptype: ProfileType, code: int) -> None:
    profile = make_profile(ptype, category_weights=weights(code, 4, 0, 0, 0, 0))
    listed = frozenset({RUN_MIDDLE})
    rules = make_rules(
        offense_allowed_categories=listed, defense_allowed_categories=listed
    )
    if ptype == ProfileType.OFFENSE:
        limited, rule_name = _OFFENSE_LIMITED, RuleName.OFFENSE_DISALLOWED_CATEGORY
    else:
        limited, rule_name = _DEFENSE_LIMITED, RuleName.DEFENSE_DISALLOWED_CATEGORY
    banned = code in limited - listed
    expected = tuple(
        RuleViolation(
            rule_name,
            f"Situation {n} uses banned categories: 0x{code:02X}",
            situation_number=n,
        )
        for n in ALL_SITUATIONS
        if banned
    )
    assert validate_profile(profile, rules) == expected


def test_rule_disallowed_fires_only_where_the_rule_matches() -> None:
    """A rule's `disallowed` flags a matching situation that uses the category;
    the same profile is clean where the rule does not match."""
    r = rule(
        time=MinutesRemaining.OVER_FIVE,
        down=Down.FIRST,
        yards=YardsToGo.ZERO_TO_ONE,
        fields={FieldPosition.DEF_5_TO_DEF_35},
        disallowed=frozenset({RUN_MIDDLE}),
    )
    rules = make_rules(offense_situations=(r,))
    flagged = {
        v.situation_number
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_DISALLOWED_CATEGORY
    }
    assert 11 in flagged  # OVER_FIVE, 1st-and-0-1, DEF 5-35, tied
    assert 515 not in flagged  # TWO_TO_FIVE counterpart — rule doesn't match


def test_rule_disallowed_leaves_unlabeled_categories_alone() -> None:
    """A category the league gives no label (Pass Long Left) is not flagged by
    a rule that disallows something else."""
    profile = make_profile(
        category_weights=weights(PASS_LONG_LEFT, 4, RUN_MIDDLE, 3, 0, 0)
    )
    r = rule(disallowed=frozenset({RAZZLE_DAZZLE_PASS}))
    got = names(profile, make_rules(offense_situations=(r,)))
    assert RuleName.OFFENSE_DISALLOWED_CATEGORY not in got
    assert RuleName.OFFENSE_ALLOWED_CATEGORIES not in got


def test_rule_disallowed_combines_with_allowed_list() -> None:
    """A category the allowed list leaves out and a matching rule's `disallowed`
    give one violation per situation, listing every code."""
    r = rule(disallowed=frozenset({PASS_SHORT_LEFT}))
    rules = make_rules(
        offense_allowed_categories=frozenset({PASS_SHORT_LEFT, PASS_MEDIUM_LEFT}),
        offense_situations=(r,),
    )
    hits = [
        v
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_DISALLOWED_CATEGORY
        and v.situation_number == 11
    ]
    assert [v.message for v in hits] == [
        "Situation 11 uses banned categories: 0x03, 0x0D"
    ]


def test_two_matching_rules_disallowed_union() -> None:
    rules = make_rules(
        offense_situations=(
            rule(disallowed=frozenset({RUN_MIDDLE})),
            rule(disallowed=frozenset({PASS_SHORT_LEFT})),
        )
    )
    hits = [
        v
        for v in validate_profile(make_profile(), rules)
        if v.rule_name == RuleName.OFFENSE_DISALLOWED_CATEGORY
        and v.situation_number == 11
    ]
    assert [v.message for v in hits] == [
        "Situation 11 uses banned categories: 0x03, 0x0D"
    ]


@pytest.mark.parametrize(
    ("ptype", "expected"),
    [
        (
            ProfileType.OFFENSE,
            {
                RuleName.OFFENSE_DISALLOWED_CATEGORY,
                RuleName.OFFENSE_ALLOWED_CATEGORIES,
                RuleName.OFFENSE_MANDATORY_CATEGORY,
                RuleName.OFFENSE_MIN_CATEGORIES,
            },
        ),
        (
            ProfileType.DEFENSE,
            {
                RuleName.DEFENSE_DISALLOWED_CATEGORY,
                RuleName.DEFENSE_ALLOWED_CATEGORIES,
                RuleName.DEFENSE_MANDATORY_CATEGORY,
                RuleName.DEFENSE_MIN_CATEGORIES,
            },
        ),
    ],
)
def test_all_issues_reported_under_the_profiles_side(
    ptype: ProfileType, expected: set[RuleName]
) -> None:
    """One validate_profile reports every distinct issue, not just the first,
    each under the profile's side.

    The baseline profile (RUN_MIDDLE + two passes) trips all four at once: a
    category the allowed list leaves out, a too-restrictive allowed set, a
    missing mandatory category and the minimum.
    """
    listed = frozenset({PASS_SHORT_LEFT, PASS_MEDIUM_LEFT})
    r = rule(allowed=frozenset({RUN_LEFT}), mandatory=(frozenset({RUN_LEFT}),))
    rules = make_rules(
        min_categories=5,
        offense_allowed_categories=listed,
        defense_allowed_categories=listed,
        offense_situations=(r,),
        defense_situations=(r,),
    )
    assert names(make_profile(ptype), rules) == expected


# ── full rule set on real profiles ────────────────────────────────────────────


def test_offense_full_rules() -> None:
    allowed = RuleName.OFFENSE_ALLOWED_CATEGORIES
    mandatory = RuleName.OFFENSE_MANDATORY_CATEGORY
    minimum = RuleName.OFFENSE_MIN_CATEGORIES
    assert [
        (v.situation_number, v.rule_name) for v in validate_profile(OFF1, FULL)
    ] == [
        (1, allowed),
        (37, allowed),
        (43, minimum),
        (162, allowed),
        (164, allowed),
        (204, allowed),
        *((n, mandatory) for n in (300, 301, 303, 305, 306, 309, 313, 314, 315)),
        (327, mandatory),
        (342, mandatory),
        (414, minimum),
    ]


def test_defense_full_rules() -> None:
    """DL, LB and DB sub out at 96, past the rules' maximum of 95."""
    violations = validate_profile(DEF1, FULL)
    assert [v.message for v in violations[:3]] == [
        "Defensive linemen out_percent must be <= 95, got 96.",
        "Linebackers out_percent must be <= 95, got 96.",
        "Defensive backs out_percent must be <= 95, got 96.",
    ]
    assert [(v.situation_number, v.rule_name) for v in violations] == [
        *((None, RuleName.SUBSTITUTION) for _ in range(3)),
        *((n, RuleName.DEFENSE_MIN_CATEGORIES) for n in range(246, 253)),
    ]
