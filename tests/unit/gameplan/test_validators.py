"""Unit tests for gameplan validators: max_count, disallowed, attribute caps.

Defense gameplans are used because they need no clock plays. Each play's game
category comes from its pool record (`user_category`), and the validator reads
typed playpool attributes (here, the defensive front).
"""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path

from athc.fbpro98_gameplan import GamePlan, ProfileType
from athc.fbpro98_gameplan.model import CustomPlayRef, StockPlayRef
from athc.fbpro98_play import PlayFile
from athc.gameplan import RuleName, validate_gameplan
from athc.gameplan.rules import DefenseCategoryRule, OffenseCategoryRule, Rules
from athc.playpool import (
    DefensiveFront,
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
        pool._register(record)
        pool.defensive_plays.append(record)
    return pool


def defense_gameplan(names: list[str]) -> GamePlan:
    normal = tuple(make_play(n) for n in names) + (None,) * (64 - len(names))
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=normal,
        special_plays=(None,) * 20,
        clock_plays=(None, None),
    )


def def_rules(**over: object) -> Rules:
    """All `Rules` fields default to empty; override only what a test needs."""
    return Rules(**over)  # type: ignore[arg-type]


def fired(gp: GamePlan, rules: Rules, pool: PlayPool) -> set[RuleName]:
    return {v.rule_name for v in validate_gameplan(gp, rules, pool)}


# ── max_count ─────────────────────────────────────────────────────────────────


def test_max_count_fires() -> None:
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(3))
    gp = defense_gameplan(["RL0", "RL1", "RL2"])
    rules = def_rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2)
        }
    )
    assert RuleName.CATEGORY_MAX_COUNT in fired(gp, rules, pool)


def test_max_count_clean_within_limit() -> None:
    pool = make_pool(make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(2))
    gp = defense_gameplan(["RL0", "RL1"])
    rules = def_rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=5)
        }
    )
    assert RuleName.CATEGORY_MAX_COUNT not in fired(gp, rules, pool)


# ── disallowed categories ─────────────────────────────────────────────────────


def test_disallowed_fires() -> None:
    pool = make_pool([make_record("US1", user_category=USER_SPECIFIC)])
    gp = defense_gameplan(["US1"])
    rules = def_rules(disallowed_defensive_categories=frozenset({"User Specific"}))
    assert RuleName.CATEGORY_DISALLOWED in fired(gp, rules, pool)


def test_disallowed_clean_when_unused() -> None:
    pool = make_pool([make_record("RL1", user_category=RUN_LEFT)])
    gp = defense_gameplan(["RL1"])
    rules = def_rules(disallowed_defensive_categories=frozenset({"User Specific"}))
    assert RuleName.CATEGORY_DISALLOWED not in fired(gp, rules, pool)


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
                required=False, min_count=1, max_two_dl_percent=Fraction(1, 2)
            )
        }
    )
    assert RuleName.CATEGORY_MAX_TWO_DL_PERCENT in fired(gp, rules, pool)


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
                required=False, min_count=1, max_two_dl_percent=Fraction(1, 2)
            )
        }
    )
    assert RuleName.CATEGORY_MAX_TWO_DL_PERCENT not in fired(gp, rules, pool)


# ── all issues reported together ──────────────────────────────────────────────


def test_all_issues_reported_including_disallowed() -> None:
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
        disallowed_defensive_categories=frozenset({"User Specific"}),
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2),
            "Pass Short": DefenseCategoryRule(required=True, min_count=6),
        },
    )
    kinds = fired(gp, rules, pool)
    assert {
        RuleName.CATEGORY_DISALLOWED,  # User Specific present
        RuleName.CATEGORY_MAX_COUNT,  # 3 Run Left > 2
        RuleName.CATEGORY_REQUIRED,  # no Pass Short
    } <= kinds


# ── min_count ─────────────────────────────────────────────────────────────────


def test_min_count_fires() -> None:
    pool = make_pool([make_record("RL0", user_category=RUN_LEFT)])
    gp = defense_gameplan(["RL0"])
    rules = def_rules(
        defense_categories={"Run Left": DefenseCategoryRule(required=True, min_count=3)}
    )
    assert RuleName.CATEGORY_MIN_COUNT in fired(gp, rules, pool)


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


# ── offense harness ───────────────────────────────────────────────────────────


def make_off_record(
    name: str,
    *,
    user_category: int,
    qb_draw: bool = False,
    rollout: bool = False,
    pass_logic: PassLogic | None = None,
) -> OffensivePlay:
    play_file = PlayFile(Path(f"{name}.ply"), 0, 0x01, 0, user_category, (), ())
    return OffensivePlay(
        name,
        play_file,
        qb_draw=qb_draw,
        rollout=rollout,
        pass_logic=pass_logic,
    )


def make_off_pool(records: Iterable[OffensivePlay]) -> PlayPool:
    pool = PlayPool("root")
    for record in records:
        pool._register(record)
        pool.offensive_plays.append(record)
    return pool


def make_off_play(name: str, *, user_category: int) -> CustomPlayRef:
    return CustomPlayRef(
        filename=f"{name}.PLY",
        play_category=0x01,
        special_category=0,
        user_category=user_category,
    )


# Clock plays are required for offense gameplans (special categories 11 and 12).
_CLOCK_PLAYS = (
    CustomPlayRef(filename="CLOCK1.PLY", play_category=0x01, special_category=11,
               user_category=OFF_RUN_MIDDLE),
    CustomPlayRef(filename="CLOCK2.PLY", play_category=0x01, special_category=12,
               user_category=OFF_RUN_MIDDLE),
)  # fmt: skip


def offense_gameplan(plays: list[CustomPlayRef]) -> GamePlan:
    normal = tuple(plays) + (None,) * (64 - len(plays))
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=normal,
        special_plays=(None,) * 20,
        clock_plays=_CLOCK_PLAYS,
    )


def off_rules(**over: object) -> Rules:
    return Rules(**over)  # type: ignore[arg-type]


# ── offense: count rules ──────────────────────────────────────────────────────


def test_offense_min_count_fires() -> None:
    pool = make_off_pool([make_off_record("RM0", user_category=OFF_RUN_MIDDLE)])
    gp = offense_gameplan([make_off_play("RM0", user_category=OFF_RUN_MIDDLE)])
    rules = off_rules(
        offense_categories={
            "Run Middle": OffenseCategoryRule(required=True, min_count=3)
        }
    )
    assert RuleName.CATEGORY_MIN_COUNT in fired(gp, rules, pool)


def test_offense_required_fires() -> None:
    """A required offense category with no plays trips required."""
    gp = offense_gameplan([])
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(required=True)}
    )
    assert RuleName.CATEGORY_REQUIRED in fired(gp, rules, make_off_pool([]))


def test_offense_max_count_fires() -> None:
    pool = make_off_pool(
        make_off_record(f"RM{i}", user_category=OFF_RUN_MIDDLE) for i in range(3)
    )
    gp = offense_gameplan(
        [make_off_play(f"RM{i}", user_category=OFF_RUN_MIDDLE) for i in range(3)]
    )
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_count=2)}
    )
    assert RuleName.CATEGORY_MAX_COUNT in fired(gp, rules, pool)


def test_offense_disallowed_fires() -> None:
    pool = make_off_pool([make_off_record("RR0", user_category=OFF_RUN_RIGHT)])
    gp = offense_gameplan([make_off_play("RR0", user_category=OFF_RUN_RIGHT)])
    rules = off_rules(disallowed_offensive_categories=frozenset({"Run Right"}))
    assert RuleName.CATEGORY_DISALLOWED in fired(gp, rules, pool)


# ── offense: attribute caps ───────────────────────────────────────────────────


def test_offense_max_qb_draws_fires() -> None:
    pool = make_off_pool(
        make_off_record(f"RM{i}", user_category=OFF_RUN_MIDDLE, qb_draw=True)
        for i in range(2)
    )
    gp = offense_gameplan(
        [make_off_play(f"RM{i}", user_category=OFF_RUN_MIDDLE) for i in range(2)]
    )
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_qb_draws=1)}
    )
    assert RuleName.CATEGORY_MAX_QB_DRAWS in fired(gp, rules, pool)


def test_offense_max_qb_draws_clean() -> None:
    pool = make_off_pool(
        [make_off_record("RM0", user_category=OFF_RUN_MIDDLE, qb_draw=True)]
    )
    gp = offense_gameplan([make_off_play("RM0", user_category=OFF_RUN_MIDDLE)])
    rules = off_rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_qb_draws=1)}
    )
    assert RuleName.CATEGORY_MAX_QB_DRAWS not in fired(gp, rules, pool)


def test_offense_max_rollouts_fires() -> None:
    pool = make_off_pool(
        make_off_record(f"PSR{i}", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)
        for i in range(2)
    )
    gp = offense_gameplan(
        [make_off_play(f"PSR{i}", user_category=OFF_PASS_SHORT_RIGHT) for i in range(2)]
    )
    rules = off_rules(
        offense_categories={"Pass Short Right": OffenseCategoryRule(max_rollouts=1)}
    )
    assert RuleName.CATEGORY_MAX_ROLLOUTS in fired(gp, rules, pool)


def test_offense_max_rollouts_clean() -> None:
    pool = make_off_pool(
        [make_off_record("PSR0", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)]
    )
    gp = offense_gameplan([make_off_play("PSR0", user_category=OFF_PASS_SHORT_RIGHT)])
    rules = off_rules(
        offense_categories={"Pass Short Right": OffenseCategoryRule(max_rollouts=1)}
    )
    assert RuleName.CATEGORY_MAX_ROLLOUTS not in fired(gp, rules, pool)


def test_offense_max_timed_percent_fires() -> None:
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
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=Fraction(1, 2))
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED_PERCENT in fired(gp, rules, pool)


def test_offense_max_timed_percent_clean() -> None:
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
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=Fraction(1, 2))
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED_PERCENT not in fired(gp, rules, pool)


# ── special categories ────────────────────────────────────────────────────────


def test_special_category_required_fires() -> None:
    """A required special category with no custom/stock play is flagged."""
    gp = defense_gameplan([])  # special_plays are all None
    rules = def_rules(required_special_categories=frozenset({1}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED in fired(gp, rules, make_pool([]))


def test_custom_special_play_required_fires() -> None:
    """With custom_special_play_required, a stock-only special slot is flagged."""
    # custom_1 unset, stock_1 set (category 1).
    stock = StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00)
    specials = (None, stock) + (None,) * 18
    gp = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * 64,
        special_plays=specials,
        clock_plays=(None, None),
    )
    rules = def_rules(custom_special_play_required=True)
    assert RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED in fired(gp, rules, make_pool([]))
