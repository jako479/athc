"""Unit tests for gameplan validators: counts and their limits, allowed
categories, attribute caps, duplicates, special categories, and each message.

Defense gameplans are used because they need no clock plays. Each play's game
category comes from its pool record (`user_category`), and the validator reads
typed playpool attributes (here, the defensive front).
"""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path

import pytest

from athc.fbpro98_gameplan import GamePlan, ProfileType
from athc.fbpro98_gameplan.model import CustomPlayRef, SpecialSlot, StockPlayRef
from athc.fbpro98_play import DefensiveFront, PlayFile
from athc.gameplan import RuleName, RuleViolation, validate_gameplan
from athc.gameplan.rules import DefenseCategoryRule, OffenseCategoryRule, Rules
from athc.playpool import (
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    PlayPool,
)

RUN_LEFT = 0x04  # defense game-category byte
PASS_SHORT = 0x02
USER_SPECIFIC = 0xFE

# Offense game-category bytes (user_category -> category name).
OFF_RUN_MIDDLE = 0x09
OFF_RUN_RIGHT = 0x01
OFF_PASS_SHORT_RIGHT = 0x03
OFF_PASS_MEDIUM_RIGHT = 0x13


def make_play(name: str) -> CustomPlayRef:
    return CustomPlayRef(
        filename=f"{name}.PLY",
        play_category=0x00,
        special_category=0,
        user_category=0x04,
    )


def make_record(
    name: str, *, user_category: int, front: DefensiveFront | None = None
) -> DefensivePlay:
    play_file = PlayFile(Path(f"{name}.ply"), 0, 0x00, 0, user_category, (), ())
    return DefensivePlay(name, play_file, defensive_front=front)


def make_pool(records: Iterable[DefensivePlay]) -> PlayPool:
    pool = PlayPool("root")
    for record in records:
        pool.add(record)
    return pool


def empty_specials() -> tuple[SpecialSlot, ...]:
    return tuple(SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES))


def defense_gameplan(names: list[str]) -> GamePlan:
    normal = tuple(make_play(n) for n in names) + (None,) * (64 - len(names))
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=normal,
        special_plays=empty_specials(),
    )


def defense_gameplan_at(slots: dict[int, str]) -> GamePlan:
    """A defense gameplan with a play in each given 0-based normal slot."""
    normal: list[CustomPlayRef | None] = [None] * 64
    for slot, name in slots.items():
        normal[slot] = make_play(name)
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=tuple(normal),
        special_plays=empty_specials(),
    )


def def_rules(**over: object) -> Rules:
    """All `Rules` fields default to empty; override only what a test needs."""
    return Rules(**over)  # type: ignore[arg-type]


def fired(gp: GamePlan, rules: Rules, pool: PlayPool) -> set[RuleName]:
    return {v.rule_name for v in validate_gameplan(gp, rules, pool)}


# ── max_count ─────────────────────────────────────────────────────────────────


def test_max_count_fires() -> None:
    """One past the cap: 3 plays over a cap of 2."""
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(3))
    gp = defense_gameplan(["RL0", "RL1", "RL2"])
    rules = def_rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2)
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Defensive category 'Run Left' has 3 plays; allows at most 2.",
            "Run Left",
        ),
    )


def test_max_count_clean_at_limit() -> None:
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(2))
    gp = defense_gameplan(["RL0", "RL1"])
    rules = def_rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2)
        }
    )
    assert validate_gameplan(gp, rules, pool) == ()


# ── allowed categories ────────────────────────────────────────────────────────


def test_not_allowed_names_the_category() -> None:
    pool = make_pool([make_record("US1", user_category=USER_SPECIFIC)])
    gp = defense_gameplan(["US1"])
    rules = def_rules(allowed_defensive_categories=frozenset({"Run Left"}))
    (violation,) = validate_gameplan(gp, rules, pool)
    assert violation.rule_name == RuleName.CATEGORY_NOT_ALLOWED
    assert violation.message == (
        "Defensive category 'User Specific' is not allowed; has 1 play(s)."
    )
    assert violation.category == "User Specific"


def test_not_allowed_reports_categories_in_name_order() -> None:
    pool = make_pool(
        [
            make_record("US1", user_category=USER_SPECIFIC),
            make_record("PS1", user_category=PASS_SHORT),
        ]
    )
    gp = defense_gameplan(["US1", "PS1"])
    rules = def_rules(allowed_defensive_categories=frozenset({"Run Left"}))
    assert [v.category for v in validate_gameplan(gp, rules, pool)] == [
        "Pass Short",
        "User Specific",
    ]


def test_allowed_clean_when_every_category_is_allowed() -> None:
    pool = make_pool([make_record("RL1", user_category=RUN_LEFT)])
    gp = defense_gameplan(["RL1"])
    rules = def_rules(allowed_defensive_categories=frozenset({"Run Left"}))
    assert RuleName.CATEGORY_NOT_ALLOWED not in fired(gp, rules, pool)


def test_allowed_empty_is_not_enforced() -> None:
    pool = make_pool([make_record("US1", user_category=USER_SPECIFIC)])
    gp = defense_gameplan(["US1"])
    assert RuleName.CATEGORY_NOT_ALLOWED not in fired(gp, def_rules(), pool)


# ── 2-DL front cap (typed playpool attribute) ─────────────────────────────────


def test_two_dl_cap_fires() -> None:
    pool = make_pool(
        make_record(f"PS{i}", user_category=PASS_SHORT, front=DefensiveFront.TWO_DL)
        for i in range(2)
    )
    gp = defense_gameplan(["PS0", "PS1"])
    rules = def_rules(
        defense_categories={
            "Pass Short": DefenseCategoryRule(
                required=False, min_count=1, max_two_dl_ratio=Fraction(1, 2)
            )
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_TWO_DL,
            "Defensive category 'Pass Short' has 2 of 2 2-DL plays; "
            "allows at most 1/2.",
            "Pass Short",
        ),
    )


def test_two_dl_percent_cap_names_the_percent() -> None:
    """2 of 3 is over 50%; the message gives the cap as the rules file does."""
    fronts = [DefensiveFront.TWO_DL, DefensiveFront.TWO_DL, DefensiveFront.THREE_FOUR]
    pool = make_pool(
        make_record(f"PS{i}", user_category=PASS_SHORT, front=front)
        for i, front in enumerate(fronts)
    )
    gp = defense_gameplan(["PS0", "PS1", "PS2"])
    rules = def_rules(
        defense_categories={"Pass Short": DefenseCategoryRule(max_two_dl_percent=50)}
    )
    assert _messages(gp, rules, pool) == [
        "Defensive category 'Pass Short' has 2 of 3 2-DL plays; allows at most 50%."
    ]


def test_two_dl_cap_clean_with_other_front() -> None:
    pool = make_pool(
        [
            make_record("PS0", user_category=PASS_SHORT, front=DefensiveFront.TWO_DL),
            make_record(
                "PS1", user_category=PASS_SHORT, front=DefensiveFront.THREE_FOUR
            ),
        ]
    )
    gp = defense_gameplan(["PS0", "PS1"])
    rules = def_rules(
        defense_categories={
            "Pass Short": DefenseCategoryRule(
                required=False, min_count=1, max_two_dl_ratio=Fraction(1, 2)
            )
        }
    )
    assert RuleName.CATEGORY_MAX_TWO_DL not in fired(gp, rules, pool)


# ── all issues reported together ──────────────────────────────────────────────


def test_all_issues_reported_including_not_allowed() -> None:
    """One validate_gameplan reports every distinct issue, not just the first."""
    pool = make_pool(
        [
            make_record("US1", user_category=USER_SPECIFIC),
            make_record("RL0", user_category=RUN_LEFT),
            make_record("RL1", user_category=RUN_LEFT),
            make_record("RL2", user_category=RUN_LEFT),
        ]
    )
    gp = defense_gameplan(["US1", "RL0", "RL1", "RL2"])
    rules = def_rules(
        allowed_defensive_categories=frozenset({"Run Left", "Pass Short"}),
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2),
            "Pass Short": DefenseCategoryRule(required=True, min_count=6),
        },
    )
    kinds = fired(gp, rules, pool)
    assert {
        RuleName.CATEGORY_NOT_ALLOWED,  # User Specific present
        RuleName.CATEGORY_MAX_COUNT,  # 3 Run Left > 2
        RuleName.CATEGORY_REQUIRED,  # no Pass Short
    } <= kinds


# ── min_count ─────────────────────────────────────────────────────────────────


def test_min_count_fires() -> None:
    """One below the minimum: 2 plays for a minimum of 3."""
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(2))
    gp = defense_gameplan(["RL0", "RL1"])
    rules = def_rules(
        defense_categories={"Run Left": DefenseCategoryRule(required=True, min_count=3)}
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MIN_COUNT,
            "Defensive category 'Run Left' has 2 plays; requires at least 3.",
            "Run Left",
        ),
    )


def test_min_count_clean_at_limit() -> None:
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(3))
    gp = defense_gameplan(["RL0", "RL1", "RL2"])
    rules = def_rules(
        defense_categories={"Run Left": DefenseCategoryRule(required=True, min_count=3)}
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_defense_required_names_the_category() -> None:
    gp = defense_gameplan([])
    rules = def_rules(
        defense_categories={"Pass Short": DefenseCategoryRule(required=True)}
    )
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.CATEGORY_REQUIRED,
            "Required defensive category 'Pass Short' has no plays",
            "Pass Short",
        ),
    )


def test_min_count_not_checked_when_category_empty() -> None:
    """An optional category with no plays trips neither min_count nor required."""
    pool = make_pool([])
    gp = defense_gameplan([])
    rules = def_rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=5)
        }
    )
    got = fired(gp, rules, pool)
    assert RuleName.CATEGORY_MIN_COUNT not in got
    assert RuleName.CATEGORY_REQUIRED not in got


# ── play resolution ───────────────────────────────────────────────────────────


def test_unresolved_play_fires() -> None:
    gp = defense_gameplan(["GHOST"])
    assert RuleName.UNRESOLVED_PLAY in fired(gp, def_rules(), make_pool([]))


def test_unresolved_play_message_names_the_play_and_its_slot() -> None:
    gp = defense_gameplan(["GHOST"])
    (violation,) = validate_gameplan(gp, def_rules(), make_pool([]))
    assert violation.rule_name == RuleName.UNRESOLVED_PLAY
    assert violation.message == "Play 'GHOST' at slot 1 (1-1) is not in the play pool"
    assert violation.category is None


def test_unresolved_play_is_not_counted_in_its_category() -> None:
    """GHOST is dropped from the counts, so Run Left holds one play, not two."""
    pool = make_pool([make_record("RL0", user_category=RUN_LEFT)])
    gp = defense_gameplan(["RL0", "GHOST"])
    rules = def_rules(defense_categories={"Run Left": DefenseCategoryRule(max_count=1)})
    assert fired(gp, rules, pool) == {RuleName.UNRESOLVED_PLAY}


def test_duplicate_play_names_both_slots_any_case() -> None:
    """Each repeat names its slot and the first one's; the first is not flagged.
    Slot 5 starts grid row 2 and slot 64 is the last."""
    pool = make_pool([make_record("RL0", user_category=RUN_LEFT)])
    gp = defense_gameplan_at({0: "RL0", 4: "rl0", 63: "Rl0"})
    assert validate_gameplan(gp, def_rules(), pool) == (
        RuleViolation(
            RuleName.DUPLICATE_PLAY,
            "Duplicate play 'rl0' at slot 5 (2-1) (already at slot 1 (1-1))",
        ),
        RuleViolation(
            RuleName.DUPLICATE_PLAY,
            "Duplicate play 'Rl0' at slot 64 (16-4) (already at slot 1 (1-1))",
        ),
    )


def test_different_plays_are_not_duplicates() -> None:
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(2))
    gp = defense_gameplan(["RL0", "RL1"])
    assert validate_gameplan(gp, def_rules(), pool) == ()


# ── side ──────────────────────────────────────────────────────────────────────


def test_defense_gameplan_ignores_offense_rules() -> None:
    pool = make_pool([make_record("RL0", user_category=RUN_LEFT)])
    gp = defense_gameplan(["RL0"])
    rules = def_rules(
        offense_categories={"Run Left": OffenseCategoryRule(max_count=0)},
        allowed_offensive_categories=frozenset({"Run Middle"}),
    )
    assert validate_gameplan(gp, rules, pool) == ()


# ── offense harness ───────────────────────────────────────────────────────────


def make_off_record(
    name: str,
    *,
    user_category: int,
    qb_run: bool = False,
    rollout: bool = False,
    pass_logic: PassLogic | None = None,
) -> OffensivePlay:
    play_file = PlayFile(Path(f"{name}.ply"), 0, 0x01, 0, user_category, (), ())
    return OffensivePlay(
        name,
        play_file,
        qb_run=qb_run,
        rollout=rollout,
        pass_logic=pass_logic,
    )


def make_off_pool(records: Iterable[OffensivePlay]) -> PlayPool:
    pool = PlayPool("root")
    for record in records:
        pool.add(record)
    return pool


def make_off_play(name: str, *, user_category: int) -> CustomPlayRef:
    return CustomPlayRef(
        filename=f"{name}.PLY",
        play_category=0x01,
        special_category=0,
        user_category=user_category,
    )


def offense_specials() -> tuple[SpecialSlot, ...]:
    """Empty slots plus the stock clock plays every offense gameplan carries."""
    slots = list(empty_specials())
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 0x01, category, 0x00)
        )
    return tuple(slots)


def offense_gameplan(plays: list[CustomPlayRef]) -> GamePlan:
    normal = tuple(plays) + (None,) * (64 - len(plays))
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=normal,
        special_plays=offense_specials(),
    )


def off_rules(**over: object) -> Rules:
    return Rules(**over)  # type: ignore[arg-type]


# ── offense: count rules ──────────────────────────────────────────────────────


def run_middle(count: int, *, qb_run: bool = False) -> tuple[PlayPool, GamePlan]:
    """`count` Run Middle plays, in the pool and in an offense gameplan."""
    pool = make_off_pool(
        make_off_record(f"RM{i}", user_category=OFF_RUN_MIDDLE, qb_run=qb_run)
        for i in range(count)
    )
    gp = offense_gameplan(
        [make_off_play(f"RM{i}", user_category=OFF_RUN_MIDDLE) for i in range(count)]
    )
    return pool, gp


def test_offense_min_count_fires() -> None:
    """One below the minimum: 2 plays for a minimum of 3."""
    pool, gp = run_middle(2)
    rules = off_rules(
        offense_categories={
            "Run Middle": OffenseCategoryRule(required=True, min_count=3)
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MIN_COUNT,
            "Offensive category 'Run Middle' has 2 plays; requires at least 3.",
            "Run Middle",
        ),
    )


def test_offense_min_count_clean_at_limit() -> None:
    pool, gp = run_middle(3)
    rules = off_rules(
        offense_categories={
            "Run Middle": OffenseCategoryRule(required=True, min_count=3)
        }
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_offense_required_fires() -> None:
    """A required offense category with no plays trips required."""
    gp = offense_gameplan([])
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(required=True)}
    )
    assert validate_gameplan(gp, rules, make_off_pool([])) == (
        RuleViolation(
            RuleName.CATEGORY_REQUIRED,
            "Required offensive category 'Run Middle' has no plays",
            "Run Middle",
        ),
    )


def test_offense_max_count_fires() -> None:
    """One past the cap: 3 plays over a cap of 2."""
    pool, gp = run_middle(3)
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_count=2)}
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Offensive category 'Run Middle' has 3 plays; allows at most 2.",
            "Run Middle",
        ),
    )


def test_offense_max_count_clean_at_limit() -> None:
    pool, gp = run_middle(2)
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_count=2)}
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_offense_not_allowed_fires() -> None:
    pool = make_off_pool([make_off_record("RR0", user_category=OFF_RUN_RIGHT)])
    gp = offense_gameplan([make_off_play("RR0", user_category=OFF_RUN_RIGHT)])
    rules = off_rules(allowed_offensive_categories=frozenset({"Run Middle"}))
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_NOT_ALLOWED,
            "Offensive category 'Run Right' is not allowed; has 1 play(s).",
            "Run Right",
        ),
    )


def test_offense_gameplan_ignores_defense_rules() -> None:
    pool, gp = run_middle(1)
    rules = off_rules(
        defense_categories={"Run Middle": DefenseCategoryRule(max_count=0)},
        allowed_defensive_categories=frozenset({"Run Left"}),
    )
    assert validate_gameplan(gp, rules, pool) == ()


# ── offense: attribute caps ───────────────────────────────────────────────────


def test_offense_max_qb_runs_count_fires() -> None:
    pool, gp = run_middle(2, qb_run=True)
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_qb_runs_count=1)}
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_QB_RUNS,
            "Offensive category 'Run Middle' has 2 of 2 QB runs; allows at most 1.",
            "Run Middle",
        ),
    )


def test_offense_max_qb_runs_count_clean() -> None:
    pool = make_off_pool(
        [make_off_record("RM0", user_category=OFF_RUN_MIDDLE, qb_run=True)]
    )
    gp = offense_gameplan([make_off_play("RM0", user_category=OFF_RUN_MIDDLE)])
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_qb_runs_count=1)}
    )
    assert RuleName.CATEGORY_MAX_QB_RUNS not in fired(gp, rules, pool)


def test_offense_max_rollouts_count_fires() -> None:
    pool = make_off_pool(
        make_off_record(f"PSR{i}", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)
        for i in range(2)
    )
    gp = offense_gameplan(
        [make_off_play(f"PSR{i}", user_category=OFF_PASS_SHORT_RIGHT) for i in range(2)]
    )
    rules = off_rules(
        offense_categories={
            "Pass Short Right": OffenseCategoryRule(max_rollouts_count=1)
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_ROLLOUTS,
            "Offensive category 'Pass Short Right' has 2 of 2 rollouts; "
            "allows at most 1.",
            "Pass Short Right",
        ),
    )


def test_offense_max_rollouts_count_clean() -> None:
    pool = make_off_pool(
        [make_off_record("PSR0", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)]
    )
    gp = offense_gameplan([make_off_play("PSR0", user_category=OFF_PASS_SHORT_RIGHT)])
    rules = off_rules(
        offense_categories={
            "Pass Short Right": OffenseCategoryRule(max_rollouts_count=1)
        }
    )
    assert RuleName.CATEGORY_MAX_ROLLOUTS not in fired(gp, rules, pool)


def test_offense_max_timed_ratio_fires() -> None:
    pool = make_off_pool(
        make_off_record(
            f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT, pass_logic=PassLogic.TIMED
        )
        for i in range(2)
    )
    gp = offense_gameplan(
        [
            make_off_play(f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT)
            for i in range(2)
        ]
    )
    rules = off_rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_ratio=Fraction(1, 2))
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED in fired(gp, rules, pool)


def test_offense_max_timed_ratio_clean() -> None:
    pool = make_off_pool(
        [
            make_off_record(
                "PMR0", user_category=OFF_PASS_MEDIUM_RIGHT, pass_logic=PassLogic.TIMED
            ),
            make_off_record(
                "PMR1",
                user_category=OFF_PASS_MEDIUM_RIGHT,
                pass_logic=PassLogic.CHECK_RECEIVERS,
            ),
        ]
    )
    gp = offense_gameplan(
        [
            make_off_play(f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT)
            for i in range(2)
        ]
    )
    rules = off_rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_ratio=Fraction(1, 2))
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED not in fired(gp, rules, pool)


def test_offense_max_timed_percent_fires() -> None:
    """2 of 3 timed is 66.6%, over a 50% cap — compared exactly, no rounding."""
    pool = make_off_pool(
        [
            make_off_record(
                f"PMR{i}",
                user_category=OFF_PASS_MEDIUM_RIGHT,
                pass_logic=PassLogic.TIMED,
            )
            for i in range(2)
        ]
        + [
            make_off_record(
                "PMR2",
                user_category=OFF_PASS_MEDIUM_RIGHT,
                pass_logic=PassLogic.CHECK_RECEIVERS,
            )
        ]
    )
    gp = offense_gameplan(
        [
            make_off_play(f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT)
            for i in range(3)
        ]
    )
    rules = off_rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=50)
        }
    )
    assert _messages(gp, rules, pool) == [
        "Offensive category 'Pass Medium Right' has 2 of 3 timed passes; "
        "allows at most 50%."
    ]


def test_offense_max_timed_percent_clean_at_cap() -> None:
    """1 of 2 timed is exactly 50%, the cap — allowed."""
    pool = make_off_pool(
        [
            make_off_record(
                "PMR0", user_category=OFF_PASS_MEDIUM_RIGHT, pass_logic=PassLogic.TIMED
            ),
            make_off_record(
                "PMR1",
                user_category=OFF_PASS_MEDIUM_RIGHT,
                pass_logic=PassLogic.CHECK_RECEIVERS,
            ),
        ]
    )
    gp = offense_gameplan(
        [
            make_off_play(f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT)
            for i in range(2)
        ]
    )
    rules = off_rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=50)
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED not in fired(gp, rules, pool)


# ── special categories ────────────────────────────────────────────────────────


def test_special_category_required_fires() -> None:
    """A required special category with no custom/stock play is flagged."""
    gp = defense_gameplan([])  # special_plays are all None
    rules = def_rules(required_special_categories=frozenset({1}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED in fired(gp, rules, make_pool([]))


def test_custom_special_play_required_fires() -> None:
    """With custom_special_play_required, a stock-only special slot is flagged."""
    slots = list(empty_specials())
    slots[0] = SpecialSlot(stock=StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00))
    gp = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * 64,
        special_plays=tuple(slots),
    )
    rules = def_rules(custom_special_play_required=True)
    assert RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED in fired(gp, rules, make_pool([]))


def special_gameplan(slot: SpecialSlot) -> GamePlan:
    """A defense gameplan whose special category 1 holds `slot`."""
    slots = list(empty_specials())
    slots[0] = slot
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * 64,
        special_plays=tuple(slots),
    )


CUSTOM_FG = CustomPlayRef(
    filename="FGDEF.PLY", play_category=0x00, special_category=1, user_category=0
)
STOCK_FG = StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00)


@pytest.mark.parametrize(
    "slot",
    [SpecialSlot(custom=CUSTOM_FG), SpecialSlot(stock=STOCK_FG)],
    ids=["custom", "stock"],
)
def test_special_category_required_met_by_either_play(slot: SpecialSlot) -> None:
    rules = def_rules(required_special_categories=frozenset({1}))
    assert validate_gameplan(special_gameplan(slot), rules, make_pool([])) == ()


@pytest.mark.parametrize(
    "slot",
    [
        SpecialSlot(custom=CUSTOM_FG),
        SpecialSlot(stock=STOCK_FG, custom=CUSTOM_FG),
        SpecialSlot(),
    ],
    ids=["custom", "stock and custom", "empty"],
)
def test_custom_special_play_required_clean(slot: SpecialSlot) -> None:
    """Only a stock play with no custom one trips the rule; an empty slot is
    the required-special rule's concern."""
    rules = def_rules(custom_special_play_required=True)
    assert validate_gameplan(special_gameplan(slot), rules, make_pool([])) == ()


def test_custom_special_play_not_required_by_default() -> None:
    gp = special_gameplan(SpecialSlot(stock=STOCK_FG))
    assert validate_gameplan(gp, def_rules(), make_pool([])) == ()


def test_required_clock_category_satisfied_on_offense() -> None:
    """Every offense gameplan carries both stock clock plays, so requiring them passes."""
    gp = offense_gameplan([])
    rules = off_rules(required_special_categories=frozenset({11, 12}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED not in fired(gp, rules, make_off_pool([]))


def test_required_clock_category_fires_on_defense() -> None:
    """Defense has no clock plays; a league requiring Stop Clock is told so."""
    gp = defense_gameplan([])
    rules = def_rules(required_special_categories=frozenset({12}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED in fired(gp, rules, make_pool([]))


def test_custom_special_play_required_ignores_clock_categories() -> None:
    """Clock categories are stock-only, so their stock plays never trip the rule."""
    gp = offense_gameplan([])
    rules = off_rules(custom_special_play_required=True)
    assert RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED not in fired(
        gp, rules, make_off_pool([])
    )


def _messages(gp: GamePlan, rules: Rules, pool: PlayPool) -> list[str]:
    return [v.message for v in validate_gameplan(gp, rules, pool)]


def test_special_category_required_names_the_category() -> None:
    """The message carries the side's game name for the slot, not its number."""
    gp = defense_gameplan([])
    rules = def_rules(required_special_categories=frozenset({2}))
    (violation,) = validate_gameplan(gp, rules, make_pool([]))
    assert violation.message == "Required special category 'Kick Return' has no play"
    assert violation.category == "Kick Return"


def test_required_clock_category_on_defense_uses_offense_name() -> None:
    """Defense has no clock categories of its own, so the rules-file name is used."""
    gp = defense_gameplan([])
    rules = def_rules(required_special_categories=frozenset({12}))
    assert "Required special category 'Stop Clock' has no play" in _messages(
        gp, rules, make_pool([])
    )


def test_custom_special_play_required_names_the_category() -> None:
    slots = list(empty_specials())
    slots[0] = SpecialSlot(stock=StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00))
    gp = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * 64,
        special_plays=tuple(slots),
    )
    rules = def_rules(custom_special_play_required=True)
    assert (
        "Special category 'Field Goal/PAT Defense' uses a stock play; "
        "a custom play is required"
    ) in _messages(gp, rules, make_pool([]))


def test_a_rule_violation_is_a_named_tuple() -> None:
    violation = RuleViolation(RuleName.DUPLICATE_PLAY, "Twice.")
    assert violation == (RuleName.DUPLICATE_PLAY, "Twice.", None)
    rule_name, message, category = violation
    assert (rule_name, message, category) == (RuleName.DUPLICATE_PLAY, "Twice.", None)
