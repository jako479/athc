"""Validators that surface rule violations in a `Profile`.

Each validator returns a list of `Violation`; `validate_profile` is the public
entry point. All thresholds come from the supplied `ProfileRules` — nothing is
hardcoded here. A situation is checked against every rule it matches: `allowed`
sets intersect, `mandatory` requirements accumulate, and `min_categories` takes
the strictest (highest) value, falling back to the rule set's baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from athc.fbpro98_profile import CategoryWeights, Profile, Situation
from athc.profile.model import RuleName, Violation
from athc.profile.rules import SUBSTITUTION_POSITIONS, ProfileRules, SituationRule


def validate_profile(profile: Profile, rules: ProfileRules) -> tuple[Violation, ...]:
    """Run every validator against `profile` and return the combined report."""
    violations: list[Violation] = []
    violations.extend(_validate_audibles(profile, rules))
    violations.extend(_validate_substitutions(profile, rules))
    violations.extend(_validate_situations(profile, rules))
    return tuple(violations)


# ---------------------------------------------------------------------------
# Profile-wide validators
# ---------------------------------------------------------------------------


def _validate_audibles(profile: Profile, rules: ProfileRules) -> list[Violation]:
    if rules.audibles_allowed or not profile.use_audibles:
        return []
    return [Violation(RuleName.AUDIBLES_UNCHECKED, "Audibles must be unchecked.")]


# Substitution position label -> the SubstitutionSettings attribute it checks.
_SUBSTITUTION_ATTR = {
    "ol": "offensive_linemen",
    "qb": "quarterbacks",
    "rb": "running_backs",
    "wr": "receivers",
    "k": "kickers",
    "dl": "defensive_linemen",
    "lb": "linebackers",
    "db": "defensive_backs",
}


def _validate_substitutions(profile: Profile, rules: ProfileRules) -> list[Violation]:
    """Check each configured position group against the profile, for the profile's
    side only (the other side's groups aren't user-editable)."""
    side = "offense" if profile.is_offense else "defense"
    violations: list[Violation] = []
    for position, required in rules.substitutions.items():
        display, pos_side = SUBSTITUTION_POSITIONS[position]
        if pos_side != side:
            continue
        actual = getattr(profile.substitutions, _SUBSTITUTION_ATTR[position])
        if actual != required:
            violations.append(
                Violation(
                    RuleName.SUBSTITUTION,
                    f"{display} substitution must be "
                    f"{required.out_percent}/{required.in_percent}, "
                    f"got {actual.out_percent}/{actual.in_percent}.",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Per-situation validators
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _SideRuleNames:
    allowed: RuleName
    disallowed: RuleName
    mandatory: RuleName
    min_categories: RuleName


_OFFENSE_NAMES = _SideRuleNames(
    allowed=RuleName.OFFENSE_ALLOWED_CATEGORIES,
    disallowed=RuleName.OFFENSE_DISALLOWED_CATEGORY,
    mandatory=RuleName.OFFENSE_MANDATORY_CATEGORY,
    min_categories=RuleName.OFFENSE_MIN_CATEGORIES,
)
_DEFENSE_NAMES = _SideRuleNames(
    allowed=RuleName.DEFENSE_ALLOWED_CATEGORIES,
    disallowed=RuleName.DEFENSE_DISALLOWED_CATEGORY,
    mandatory=RuleName.DEFENSE_MANDATORY_CATEGORY,
    min_categories=RuleName.DEFENSE_MIN_CATEGORIES,
)


def _validate_situations(profile: Profile, rules: ProfileRules) -> list[Violation]:
    if profile.is_offense:
        side_rules = rules.offense_situations
        exempt = rules.offense_exempt_categories
        disallowed = rules.offense_disallowed_categories
        names = _OFFENSE_NAMES
    else:
        side_rules = rules.defense_situations
        exempt = rules.defense_exempt_categories
        disallowed = rules.defense_disallowed_categories
        names = _DEFENSE_NAMES

    violations: list[Violation] = []
    for situation in profile.situations:
        cats = _categories_with_weight(situation.category_weights)
        matching = [
            rule
            for rule in side_rules
            if rule.matches(
                situation.minutes_remaining,
                situation.down,
                situation.yards_to_go,
                situation.field_position,
            )
        ]
        violations.extend(
            _check_situation(
                situation, cats, matching, disallowed, exempt, names, rules
            )
        )
    return violations


def _check_situation(
    situation: Situation,
    cats: frozenset[int],
    matching: list[SituationRule],
    disallowed: frozenset[int],
    exempt: frozenset[int],
    names: _SideRuleNames,
    rules: ProfileRules,
) -> list[Violation]:
    violations: list[Violation] = []
    n = situation.situation_number

    used_disallowed = sorted(cats & disallowed)
    if used_disallowed:
        codes = ", ".join(f"0x{c:02X}" for c in used_disallowed)
        violations.append(
            Violation(
                names.disallowed,
                f"Situation {n} uses banned categories: {codes}",
                situation_number=n,
            )
        )

    allowed_sets = [
        rule.allowed_categories
        for rule in matching
        if rule.allowed_categories is not None
    ]
    if allowed_sets:
        effective = frozenset.intersection(*allowed_sets)
        bad = sorted(cats - effective)
        if bad:
            codes = ", ".join(f"0x{c:02X}" for c in bad)
            violations.append(
                Violation(
                    names.allowed,
                    f"Situation {n} uses disallowed categories: {codes}",
                    situation_number=n,
                )
            )

    seen: set[frozenset[int]] = set()
    for rule in matching:
        for alternative in rule.mandatory_alternatives:
            if alternative in seen:
                continue
            seen.add(alternative)
            if not (cats & alternative):
                choices = ", ".join(f"0x{c:02X}" for c in sorted(alternative))
                violations.append(
                    Violation(
                        names.mandatory,
                        f"Situation {n} is missing a mandatory category "
                        f"(one of: {choices})",
                        situation_number=n,
                    )
                )

    side_min = max(
        [rules.min_categories]
        + [r.min_categories for r in matching if r.min_categories is not None]
    )
    waive = bool(cats) and cats.issubset(exempt)
    if not waive and len(cats) < side_min:
        violations.append(
            Violation(
                names.min_categories,
                f"Situation {n} has {len(cats)} category(ies) with non-zero "
                f"weight; requires {side_min}.",
                situation_number=n,
            )
        )
    return violations


def _categories_with_weight(weights: CategoryWeights) -> frozenset[int]:
    """Distinct play-category codes that appear with weight > 0."""
    return frozenset(
        cat
        for cat, weight in (
            (weights.play_category1, weights.weight1),
            (weights.play_category2, weights.weight2),
            (weights.play_category3, weights.weight3),
        )
        if weight > 0
    )


__all__ = ["validate_profile"]
