"""Validate a `GamePlan` against a `Rules` set, using a `PlayPool` to resolve
each play's category and attributes.

`validate_gameplan` is the entry point. Attribute caps read the typed fields the
playpool sets on each record: offense `qb_draw` / `rollout` (bool) and
`pass_logic` (`PassLogic.TIMED`); defense `defensive_front` (`DefensiveFront.TWO_DL`,
the Run-and-Shoot front).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fractions import Fraction

from athc.fbpro98_gameplan import GamePlan
from athc.gameplan.model import RuleName, Violation
from athc.gameplan.rules import DefenseCategoryRule, OffenseCategoryRule, Rules
from athc.playpool import (
    DefensiveFront,
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    Play,
    PlayPool,
)


def validate_gameplan(
    gameplan: GamePlan, rules: Rules, play_pool: PlayPool
) -> tuple[Violation, ...]:
    """Run every validator against `gameplan` and return the combined report."""
    violations: list[Violation] = []

    resolved, name_violations = _resolve_normal_plays(gameplan, play_pool)
    violations.extend(name_violations)

    if gameplan.is_offense:
        violations.extend(_validate_offense(resolved, rules.offense_categories))
        violations.extend(
            _validate_disallowed(
                resolved, rules.disallowed_offensive_categories, "Offensive"
            )
        )
    else:
        violations.extend(_validate_defense(resolved, rules.defense_categories))
        violations.extend(
            _validate_disallowed(
                resolved, rules.disallowed_defensive_categories, "Defensive"
            )
        )

    violations.extend(
        _validate_special_categories(gameplan, rules.required_special_categories)
    )
    if rules.custom_special_play_required:
        violations.extend(_validate_custom_special_plays(gameplan))

    return tuple(violations)


def _resolve_normal_plays(
    gameplan: GamePlan, play_pool: PlayPool
) -> tuple[list[Play], list[Violation]]:
    """Resolve each filled normal slot against the pool, reporting duplicate and
    unresolved plays. Unresolved plays are dropped from category counts."""
    resolved: list[Play] = []
    violations: list[Violation] = []
    seen: dict[str, int] = {}

    for slot, play in enumerate(gameplan.normal_plays):
        if play is None:
            continue
        upper = play.name.upper()
        if upper in seen:
            violations.append(
                Violation(
                    rule_name=RuleName.DUPLICATE_PLAY,
                    message=(
                        f"Duplicate play '{play.name}' at {_slot_label(slot)} "
                        f"(already at {_slot_label(seen[upper])})"
                    ),
                )
            )
        else:
            seen[upper] = slot

        record = play_pool.find_by_name(play.name)
        if record is None:
            violations.append(
                Violation(
                    rule_name=RuleName.UNRESOLVED_PLAY,
                    message=f"Play '{play.name}' at {_slot_label(slot)} "
                    "not found in play pool",
                )
            )
            continue
        resolved.append(record)

    return resolved, violations


def _validate_offense(
    records: list[Play], category_rules: Mapping[str, OffenseCategoryRule]
) -> list[Violation]:
    by_category = _group_by_category(records)
    violations: list[Violation] = []

    for category, rule in category_rules.items():
        plays = by_category.get(category, [])
        if not plays:
            if rule.required:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_REQUIRED,
                        f"Required offensive category '{category}' has no plays",
                        category,
                    )
                )
            continue

        if len(plays) < rule.min_count:
            violations.append(
                Violation(
                    RuleName.CATEGORY_MIN_COUNT,
                    f"Offensive category '{category}' has {len(plays)} plays; "
                    f"requires at least {rule.min_count}.",
                    category,
                )
            )

        if rule.max_count is not None and len(plays) > rule.max_count:
            violations.append(
                Violation(
                    RuleName.CATEGORY_MAX_COUNT,
                    f"Offensive category '{category}' has {len(plays)} plays; "
                    f"allows at most {rule.max_count}.",
                    category,
                )
            )

        if rule.max_qb_draws is not None:
            qb_draws = sum(
                1 for p in plays if isinstance(p, OffensivePlay) and p.qb_draw
            )
            if qb_draws > rule.max_qb_draws:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_MAX_QB_DRAWS,
                        f"Offensive category '{category}' has {qb_draws} QB draws; "
                        f"allows at most {rule.max_qb_draws}.",
                        category,
                    )
                )

        if rule.max_rollouts is not None:
            rollouts = sum(
                1 for p in plays if isinstance(p, OffensivePlay) and p.rollout
            )
            if rollouts > rule.max_rollouts:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_MAX_ROLLOUTS,
                        f"Offensive category '{category}' has {rollouts} rollouts; "
                        f"allows at most {rule.max_rollouts}.",
                        category,
                    )
                )

        if rule.max_timed_percent is not None:
            timed = sum(
                1
                for p in plays
                if isinstance(p, OffensivePlay) and p.pass_logic == PassLogic.TIMED
            )
            if Fraction(timed, len(plays)) > rule.max_timed_percent:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_MAX_TIMED_PERCENT,
                        f"Offensive category '{category}' has {timed} of {len(plays)} "
                        f"timed passes; allows at most "
                        f"{_format_percent(rule.max_timed_percent)}.",
                        category,
                    )
                )

    return violations


def _validate_defense(
    records: list[Play], category_rules: Mapping[str, DefenseCategoryRule]
) -> list[Violation]:
    by_category = _group_by_category(records)
    violations: list[Violation] = []

    for category, rule in category_rules.items():
        plays = by_category.get(category, [])
        if not plays:
            if rule.required:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_REQUIRED,
                        f"Required defensive category '{category}' has no plays",
                        category,
                    )
                )
            continue

        if len(plays) < rule.min_count:
            violations.append(
                Violation(
                    RuleName.CATEGORY_MIN_COUNT,
                    f"Defensive category '{category}' has {len(plays)} plays; "
                    f"requires at least {rule.min_count}.",
                    category,
                )
            )

        if rule.max_count is not None and len(plays) > rule.max_count:
            violations.append(
                Violation(
                    RuleName.CATEGORY_MAX_COUNT,
                    f"Defensive category '{category}' has {len(plays)} plays; "
                    f"allows at most {rule.max_count}.",
                    category,
                )
            )

        if rule.max_two_dl_percent is not None:
            two_dl = sum(
                1
                for p in plays
                if isinstance(p, DefensivePlay)
                and p.defensive_front == DefensiveFront.TWO_DL
            )
            if Fraction(two_dl, len(plays)) > rule.max_two_dl_percent:
                violations.append(
                    Violation(
                        RuleName.CATEGORY_MAX_TWO_DL_PERCENT,
                        f"Defensive category '{category}' has {two_dl} of {len(plays)} "
                        f"2-DL plays; allows at most "
                        f"{_format_percent(rule.max_two_dl_percent)}.",
                        category,
                    )
                )

    return violations


def _validate_disallowed(
    records: list[Play], disallowed: frozenset[str], side: str
) -> list[Violation]:
    """A gameplan may not contain plays in a disallowed category."""
    by_category = _group_by_category(records)
    violations: list[Violation] = []
    for category in sorted(disallowed):
        plays = by_category.get(category, [])
        if plays:
            violations.append(
                Violation(
                    RuleName.CATEGORY_DISALLOWED,
                    f"{side} category '{category}' is not allowed; "
                    f"has {len(plays)} play(s).",
                    category,
                )
            )
    return violations


def _validate_special_categories(
    gameplan: GamePlan, required: frozenset[int]
) -> list[Violation]:
    """Each required special category must have a custom or stock play set.
    special_plays = (custom_1, stock_1, ..., custom_10, stock_10)."""
    violations: list[Violation] = []
    for category in sorted(required):
        custom = gameplan.special_plays[(category - 1) * 2]
        stock = gameplan.special_plays[(category - 1) * 2 + 1]
        if custom is None and stock is None:
            violations.append(
                Violation(
                    RuleName.SPECIAL_CATEGORY_REQUIRED,
                    f"Required special category {category} has no play",
                )
            )
    return violations


def _validate_custom_special_plays(gameplan: GamePlan) -> list[Violation]:
    """If a special category is populated, its custom slot must be set."""
    violations: list[Violation] = []
    for category in range(1, 11):
        custom = gameplan.special_plays[(category - 1) * 2]
        stock = gameplan.special_plays[(category - 1) * 2 + 1]
        if stock is not None and custom is None:
            violations.append(
                Violation(
                    RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED,
                    f"Special category {category} uses a stock play; "
                    "a custom play is required",
                )
            )
    return violations


def _group_by_category(
    records: Iterable[Play],
) -> dict[str, list[Play]]:
    grouped: dict[str, list[Play]] = {}
    for record in records:
        grouped.setdefault(record.category.long, []).append(record)
    return grouped


def _slot_label(slot: int) -> str:
    """Format a 0-based normal slot as `slot N (G-C)` — 1-based number, then the
    in-game grid position (group 1..16 of 4, column 1..4)."""
    return f"slot {slot + 1} ({slot // 4 + 1}-{slot % 4 + 1})"


def _format_percent(value: Fraction) -> str:
    text = f"{float(value) * 100:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return f"{text}%"


__all__ = ["validate_gameplan"]
