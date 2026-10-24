"""Unit tests for gameplan validators: counts and their limits, allowed
categories, attribute caps, duplicates, special categories, and each message.

Each side has its own harness; offense gameplans also carry the two stock clock
plays every offense gameplan has. A gameplan's slots hold the pool's plays, and
the validator reads each play's category and typed attributes (the defensive
front, QB run, rollout, pass logic) from its pool record.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
    Play,
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


def make_record(
    name: str, *, user_category: int, front: DefensiveFront | None = None
) -> DefensivePlay:
    play_file = PlayFile(Path(f"{name}.ply"), 0, 0x00, 0, user_category, (), ())
    return DefensivePlay(name, play_file, defensive_front=front)


def make_pool(records: Iterable[OffensivePlay | DefensivePlay]) -> PlayPool:
    pool = PlayPool("root")
    for record in records:
        pool.add(record)
    return pool


def plan_entry(record: Play) -> CustomPlayRef:
    """The slot entry a gameplan holds for `record`: its file and category bytes."""
    play_file = record.play_file
    return CustomPlayRef(
        filename=f"{record.name}.PLY",
        play_category=play_file.play_category,
        special_category=play_file.special_category,
        user_category=play_file.user_category,
    )


def empty_specials() -> tuple[SpecialSlot, ...]:
    return tuple(SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES))


def defense_gameplan(records: Sequence[Play]) -> GamePlan:
    """A defense gameplan holding `records` in its first normal slots."""
    return defense_gameplan_at(dict(enumerate(records)))


def defense_gameplan_at(slots: Mapping[int, Play]) -> GamePlan:
    """A defense gameplan with a play in each given 0-based normal slot."""
    normal: list[CustomPlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    for slot, record in slots.items():
        normal[slot] = plan_entry(record)
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=tuple(normal),
        special_plays=empty_specials(),
    )


def fired(gp: GamePlan, rules: Rules, pool: PlayPool) -> set[RuleName]:
    return {v.rule_name for v in validate_gameplan(gp, rules, pool)}


def run_left(count: int) -> tuple[PlayPool, GamePlan]:
    """`count` Run Left plays, in the pool and in a defense gameplan."""
    records = [make_record(f"RL{i}", user_category=RUN_LEFT) for i in range(count)]
    return make_pool(records), defense_gameplan(records)


def pass_short(fronts: Sequence[DefensiveFront]) -> tuple[PlayPool, GamePlan]:
    """One Pass Short play per front, in the pool and in a defense gameplan."""
    records = [
        make_record(f"PS{i}", user_category=PASS_SHORT, front=front)
        for i, front in enumerate(fronts)
    ]
    return make_pool(records), defense_gameplan(records)


# ── max_count ─────────────────────────────────────────────────────────────────


def test_max_count_fires() -> None:
    """One past the cap: 3 plays over a cap of 2."""
    pool, gp = run_left(3)
    rules = Rules(
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
    pool, gp = run_left(2)
    rules = Rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2)
        }
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_max_count_of_zero_fires() -> None:
    """The lowest cap: one play is one past it."""
    pool, gp = run_left(1)
    rules = Rules(defense_categories={"Run Left": DefenseCategoryRule(max_count=0)})
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Defensive category 'Run Left' has 1 plays; allows at most 0.",
            "Run Left",
        ),
    )


# ── allowed categories ────────────────────────────────────────────────────────


def test_not_allowed_names_the_category() -> None:
    records = [make_record("US1", user_category=USER_SPECIFIC)]
    rules = Rules(allowed_defensive_categories=frozenset({"Run Left"}))
    assert validate_gameplan(defense_gameplan(records), rules, make_pool(records)) == (
        RuleViolation(
            RuleName.CATEGORY_NOT_ALLOWED,
            "Defensive category 'User Specific' is not allowed; has 1 play(s).",
            "User Specific",
        ),
    )


def test_not_allowed_reports_categories_in_name_order() -> None:
    records = [
        make_record("US1", user_category=USER_SPECIFIC),
        make_record("PS1", user_category=PASS_SHORT),
    ]
    rules = Rules(allowed_defensive_categories=frozenset({"Run Left"}))
    violations = validate_gameplan(defense_gameplan(records), rules, make_pool(records))
    assert [v.category for v in violations] == ["Pass Short", "User Specific"]


def test_allowed_clean_when_every_category_is_allowed() -> None:
    pool, gp = run_left(1)
    rules = Rules(allowed_defensive_categories=frozenset({"Run Left"}))
    assert RuleName.CATEGORY_NOT_ALLOWED not in fired(gp, rules, pool)


def test_allowed_empty_is_not_enforced() -> None:
    records = [make_record("US1", user_category=USER_SPECIFIC)]
    gp = defense_gameplan(records)
    assert RuleName.CATEGORY_NOT_ALLOWED not in fired(gp, Rules(), make_pool(records))


# ── 2-DL front cap (typed playpool attribute) ─────────────────────────────────


def test_two_dl_cap_fires() -> None:
    pool, gp = pass_short([DefensiveFront.TWO_DL, DefensiveFront.TWO_DL])
    rules = Rules(
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
    pool, gp = pass_short(
        [DefensiveFront.TWO_DL, DefensiveFront.TWO_DL, DefensiveFront.THREE_FOUR]
    )
    rules = Rules(
        defense_categories={"Pass Short": DefenseCategoryRule(max_two_dl_percent=50)}
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_TWO_DL,
            "Defensive category 'Pass Short' has 2 of 3 2-DL plays; "
            "allows at most 50%.",
            "Pass Short",
        ),
    )


def test_two_dl_cap_clean_with_other_front() -> None:
    """1 of 2 is exactly the 1/2 cap."""
    pool, gp = pass_short([DefensiveFront.TWO_DL, DefensiveFront.THREE_FOUR])
    rules = Rules(
        defense_categories={
            "Pass Short": DefenseCategoryRule(
                required=False, min_count=1, max_two_dl_ratio=Fraction(1, 2)
            )
        }
    )
    assert validate_gameplan(gp, rules, pool) == ()


# Each cap form at its lowest value, and the cap as the message gives it.
ZERO_CAPS = {
    "count": (DefenseCategoryRule(max_two_dl_count=0), "0"),
    "ratio": (DefenseCategoryRule(max_two_dl_ratio=Fraction(0)), "0"),
    "percent": (DefenseCategoryRule(max_two_dl_percent=0), "0%"),
}


@pytest.mark.parametrize("form", ZERO_CAPS)
def test_two_dl_cap_of_zero_fires(form: str) -> None:
    """The lowest cap: one 2-DL play is one past it."""
    rule, shown = ZERO_CAPS[form]
    pool, gp = pass_short([DefensiveFront.TWO_DL])
    rules = Rules(defense_categories={"Pass Short": rule})
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_TWO_DL,
            "Defensive category 'Pass Short' has 1 of 1 2-DL plays; "
            f"allows at most {shown}.",
            "Pass Short",
        ),
    )


@pytest.mark.parametrize("form", ZERO_CAPS)
def test_two_dl_cap_of_zero_clean_without_a_two_dl_play(form: str) -> None:
    rule, _ = ZERO_CAPS[form]
    pool, gp = pass_short([DefensiveFront.THREE_FOUR])
    rules = Rules(defense_categories={"Pass Short": rule})
    assert validate_gameplan(gp, rules, pool) == ()


@pytest.mark.parametrize(
    "rule",
    [
        DefenseCategoryRule(max_two_dl_ratio=Fraction(1)),
        DefenseCategoryRule(max_two_dl_percent=100),
    ],
    ids=["ratio", "percent"],
)
def test_two_dl_cap_at_its_highest_allows_every_play(rule: DefenseCategoryRule) -> None:
    """The highest cap (1, 100%) allows a category of nothing but 2-DL plays."""
    pool, gp = pass_short([DefensiveFront.TWO_DL, DefensiveFront.TWO_DL])
    rules = Rules(defense_categories={"Pass Short": rule})
    assert validate_gameplan(gp, rules, pool) == ()


# ── all issues reported together ──────────────────────────────────────────────


def test_all_issues_reported_including_not_allowed() -> None:
    """One validate_gameplan reports every issue: each category rule in turn,
    then the categories not allowed. An empty required category is reported
    once, not also as short of its minimum."""
    records = [
        make_record("US1", user_category=USER_SPECIFIC),
        make_record("RL0", user_category=RUN_LEFT),
        make_record("RL1", user_category=RUN_LEFT),
        make_record("RL2", user_category=RUN_LEFT),
    ]
    rules = Rules(
        allowed_defensive_categories=frozenset({"Run Left", "Pass Short"}),
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=1, max_count=2),
            "Pass Short": DefenseCategoryRule(required=True, min_count=6),
        },
    )
    assert validate_gameplan(defense_gameplan(records), rules, make_pool(records)) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Defensive category 'Run Left' has 3 plays; allows at most 2.",
            "Run Left",
        ),
        RuleViolation(
            RuleName.CATEGORY_REQUIRED,
            "Required defensive category 'Pass Short' has no plays",
            "Pass Short",
        ),
        RuleViolation(
            RuleName.CATEGORY_NOT_ALLOWED,
            "Defensive category 'User Specific' is not allowed; has 1 play(s).",
            "User Specific",
        ),
    )


# ── min_count ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("required", [True, False], ids=["required", "optional"])
def test_min_count_fires(required: bool) -> None:
    """One below the minimum: 2 plays for a minimum of 3. An optional category
    that has plays must still reach its minimum."""
    pool, gp = run_left(2)
    rules = Rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=required, min_count=3)
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MIN_COUNT,
            "Defensive category 'Run Left' has 2 plays; requires at least 3.",
            "Run Left",
        ),
    )


def test_min_count_clean_at_limit() -> None:
    pool, gp = run_left(3)
    rules = Rules(
        defense_categories={"Run Left": DefenseCategoryRule(required=True, min_count=3)}
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_defense_required_names_the_category() -> None:
    gp = defense_gameplan([])
    rules = Rules(defense_categories={"Pass Short": DefenseCategoryRule(required=True)})
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.CATEGORY_REQUIRED,
            "Required defensive category 'Pass Short' has no plays",
            "Pass Short",
        ),
    )


def test_min_count_not_checked_when_category_empty() -> None:
    """An optional category with no plays trips neither min_count nor required."""
    gp = defense_gameplan([])
    rules = Rules(
        defense_categories={
            "Run Left": DefenseCategoryRule(required=False, min_count=5)
        }
    )
    assert validate_gameplan(gp, rules, make_pool([])) == ()


# ── play resolution ───────────────────────────────────────────────────────────


def test_unresolved_play_message_names_the_play_and_its_slot() -> None:
    ghost = make_record("GHOST", user_category=RUN_LEFT)  # never added to the pool
    gp = defense_gameplan([ghost])
    assert validate_gameplan(gp, Rules(), make_pool([])) == (
        RuleViolation(
            RuleName.UNRESOLVED_PLAY,
            "Play 'GHOST' at slot 1 (1-1) is not in the play pool",
        ),
    )


def test_unresolved_play_is_not_counted_in_its_category() -> None:
    """GHOST is dropped from the counts, so Run Left holds one play, not two."""
    rl0 = make_record("RL0", user_category=RUN_LEFT)
    ghost = make_record("GHOST", user_category=RUN_LEFT)  # never added to the pool
    gp = defense_gameplan([rl0, ghost])
    rules = Rules(defense_categories={"Run Left": DefenseCategoryRule(max_count=1)})
    assert fired(gp, rules, make_pool([rl0])) == {RuleName.UNRESOLVED_PLAY}


def test_duplicate_play_names_both_slots_any_case() -> None:
    """Each repeat names its slot and the first one's; the first is not flagged.
    Slot 5 starts grid row 2 and slot 64 is the last."""
    rl0 = make_record("RL0", user_category=RUN_LEFT)
    gp = defense_gameplan_at(
        {
            0: rl0,
            4: make_record("rl0", user_category=RUN_LEFT),
            63: make_record("Rl0", user_category=RUN_LEFT),
        }
    )
    assert validate_gameplan(gp, Rules(), make_pool([rl0])) == (
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
    pool, gp = run_left(2)
    assert validate_gameplan(gp, Rules(), pool) == ()


# ── side ──────────────────────────────────────────────────────────────────────


def test_defense_gameplan_ignores_offense_rules() -> None:
    pool, gp = run_left(1)
    rules = Rules(
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


def offense_specials() -> tuple[SpecialSlot, ...]:
    """Empty slots plus the stock clock plays every offense gameplan carries."""
    slots = list(empty_specials())
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 0x01, category, 0x00)
        )
    return tuple(slots)


def offense_gameplan(records: Sequence[Play]) -> GamePlan:
    """An offense gameplan holding `records` in its first normal slots."""
    normal = tuple(plan_entry(r) for r in records)
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=normal + (None,) * (GamePlan.NUMBER_NORMAL_PLAYS - len(normal)),
        special_plays=offense_specials(),
    )


def run_middle(count: int, *, qb_run: bool = False) -> tuple[PlayPool, GamePlan]:
    """`count` Run Middle plays, in the pool and in an offense gameplan."""
    records = [
        make_off_record(f"RM{i}", user_category=OFF_RUN_MIDDLE, qb_run=qb_run)
        for i in range(count)
    ]
    return make_pool(records), offense_gameplan(records)


def pass_medium_right(logics: Sequence[PassLogic]) -> tuple[PlayPool, GamePlan]:
    """One Pass Medium Right play per pass logic, in the pool and in an offense
    gameplan."""
    records = [
        make_off_record(
            f"PMR{i}", user_category=OFF_PASS_MEDIUM_RIGHT, pass_logic=logic
        )
        for i, logic in enumerate(logics)
    ]
    return make_pool(records), offense_gameplan(records)


# ── offense: count rules ──────────────────────────────────────────────────────


def test_offense_min_count_fires() -> None:
    """One below the minimum: 2 plays for a minimum of 3."""
    pool, gp = run_middle(2)
    rules = Rules(
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
    rules = Rules(
        offense_categories={
            "Run Middle": OffenseCategoryRule(required=True, min_count=3)
        }
    )
    assert validate_gameplan(gp, rules, pool) == ()


def test_offense_required_fires() -> None:
    """A required offense category with no plays trips required."""
    gp = offense_gameplan([])
    rules = Rules(offense_categories={"Run Middle": OffenseCategoryRule(required=True)})
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.CATEGORY_REQUIRED,
            "Required offensive category 'Run Middle' has no plays",
            "Run Middle",
        ),
    )


def test_offense_max_count_fires() -> None:
    """One past the cap: 3 plays over a cap of 2."""
    pool, gp = run_middle(3)
    rules = Rules(offense_categories={"Run Middle": OffenseCategoryRule(max_count=2)})
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Offensive category 'Run Middle' has 3 plays; allows at most 2.",
            "Run Middle",
        ),
    )


def test_offense_max_count_clean_at_limit() -> None:
    pool, gp = run_middle(2)
    rules = Rules(offense_categories={"Run Middle": OffenseCategoryRule(max_count=2)})
    assert validate_gameplan(gp, rules, pool) == ()


def test_offense_max_count_of_zero_fires() -> None:
    """The lowest cap: one play is one past it."""
    pool, gp = run_middle(1)
    rules = Rules(offense_categories={"Run Middle": OffenseCategoryRule(max_count=0)})
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_COUNT,
            "Offensive category 'Run Middle' has 1 plays; allows at most 0.",
            "Run Middle",
        ),
    )


def test_offense_not_allowed_fires() -> None:
    records = [make_off_record("RR0", user_category=OFF_RUN_RIGHT)]
    rules = Rules(allowed_offensive_categories=frozenset({"Run Middle"}))
    assert validate_gameplan(offense_gameplan(records), rules, make_pool(records)) == (
        RuleViolation(
            RuleName.CATEGORY_NOT_ALLOWED,
            "Offensive category 'Run Right' is not allowed; has 1 play(s).",
            "Run Right",
        ),
    )


def test_offense_gameplan_ignores_defense_rules() -> None:
    pool, gp = run_middle(1)
    rules = Rules(
        defense_categories={"Run Middle": DefenseCategoryRule(max_count=0)},
        allowed_defensive_categories=frozenset({"Run Left"}),
    )
    assert validate_gameplan(gp, rules, pool) == ()


# ── offense: attribute caps ───────────────────────────────────────────────────


def test_offense_max_qb_runs_count_fires() -> None:
    pool, gp = run_middle(2, qb_run=True)
    rules = Rules(
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
    pool, gp = run_middle(1, qb_run=True)
    rules = Rules(
        offense_categories={"Run Middle": OffenseCategoryRule(max_qb_runs_count=1)}
    )
    assert RuleName.CATEGORY_MAX_QB_RUNS not in fired(gp, rules, pool)


def test_offense_max_rollouts_count_fires() -> None:
    records = [
        make_off_record(f"PSR{i}", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)
        for i in range(2)
    ]
    rules = Rules(
        offense_categories={
            "Pass Short Right": OffenseCategoryRule(max_rollouts_count=1)
        }
    )
    assert validate_gameplan(offense_gameplan(records), rules, make_pool(records)) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_ROLLOUTS,
            "Offensive category 'Pass Short Right' has 2 of 2 rollouts; "
            "allows at most 1.",
            "Pass Short Right",
        ),
    )


def test_offense_max_rollouts_count_clean() -> None:
    records = [
        make_off_record("PSR0", user_category=OFF_PASS_SHORT_RIGHT, rollout=True)
    ]
    rules = Rules(
        offense_categories={
            "Pass Short Right": OffenseCategoryRule(max_rollouts_count=1)
        }
    )
    gp = offense_gameplan(records)
    assert RuleName.CATEGORY_MAX_ROLLOUTS not in fired(gp, rules, make_pool(records))


def test_offense_max_timed_ratio_fires() -> None:
    pool, gp = pass_medium_right([PassLogic.TIMED, PassLogic.TIMED])
    rules = Rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_ratio=Fraction(1, 2))
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_TIMED,
            "Offensive category 'Pass Medium Right' has 2 of 2 timed passes; "
            "allows at most 1/2.",
            "Pass Medium Right",
        ),
    )


def test_offense_max_timed_ratio_clean() -> None:
    pool, gp = pass_medium_right([PassLogic.TIMED, PassLogic.CHECK_RECEIVERS])
    rules = Rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_ratio=Fraction(1, 2))
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED not in fired(gp, rules, pool)


def test_offense_max_timed_percent_fires() -> None:
    """2 of 3 timed is 66.6%, over a 50% cap — compared exactly, no rounding."""
    pool, gp = pass_medium_right(
        [PassLogic.TIMED, PassLogic.TIMED, PassLogic.CHECK_RECEIVERS]
    )
    rules = Rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=50)
        }
    )
    assert validate_gameplan(gp, rules, pool) == (
        RuleViolation(
            RuleName.CATEGORY_MAX_TIMED,
            "Offensive category 'Pass Medium Right' has 2 of 3 timed passes; "
            "allows at most 50%.",
            "Pass Medium Right",
        ),
    )


def test_offense_max_timed_percent_clean_at_cap() -> None:
    """1 of 2 timed is exactly 50%, the cap — allowed."""
    pool, gp = pass_medium_right([PassLogic.TIMED, PassLogic.CHECK_RECEIVERS])
    rules = Rules(
        offense_categories={
            "Pass Medium Right": OffenseCategoryRule(max_timed_percent=50)
        }
    )
    assert RuleName.CATEGORY_MAX_TIMED not in fired(gp, rules, pool)


# ── special categories ────────────────────────────────────────────────────────


def special_gameplan(slot: SpecialSlot, *, category: int = 1) -> GamePlan:
    """A defense gameplan whose special `category` holds `slot`."""
    slots = list(empty_specials())
    slots[category - 1] = slot
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * GamePlan.NUMBER_NORMAL_PLAYS,
        special_plays=tuple(slots),
    )


CUSTOM_FG = CustomPlayRef(
    filename="FGDEF.PLY", play_category=0x00, special_category=1, user_category=0
)
STOCK_FG = StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00)


@pytest.mark.parametrize(
    "offense,category,name",
    [(False, 2, "Kick Return"), (True, 3, "Punt")],
    ids=["defense", "offense"],
)
def test_special_category_required_fires(
    offense: bool, category: int, name: str
) -> None:
    """A required special category with no custom or stock play; the message
    carries the side's game name for the slot, not its number."""
    gp = offense_gameplan([]) if offense else defense_gameplan([])
    rules = Rules(required_special_categories=frozenset({category}))
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.SPECIAL_CATEGORY_REQUIRED,
            f"Required special category '{name}' has no play",
            name,
        ),
    )


@pytest.mark.parametrize(
    "slot",
    [SpecialSlot(custom=CUSTOM_FG), SpecialSlot(stock=STOCK_FG)],
    ids=["custom", "stock"],
)
def test_special_category_required_met_by_either_play(slot: SpecialSlot) -> None:
    rules = Rules(required_special_categories=frozenset({1}))
    assert validate_gameplan(special_gameplan(slot), rules, make_pool([])) == ()


@pytest.mark.parametrize(
    "category,name",
    [(1, "Field Goal/PAT Defense"), (10, "Squib Return")],
    ids=["first", "last"],
)
def test_custom_special_play_required_fires(category: int, name: str) -> None:
    """With custom_special_play_required, a stock-only special slot is flagged,
    in the first and the last category that has a custom slot."""
    stock = StockPlayRef(f"STOCK{category}", 0, 0, 0x00, category, 0x00)
    gp = special_gameplan(SpecialSlot(stock=stock), category=category)
    rules = Rules(custom_special_play_required=True)
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED,
            f"Special category '{name}' uses a stock play; a custom play is required",
            name,
        ),
    )


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
    rules = Rules(custom_special_play_required=True)
    assert validate_gameplan(special_gameplan(slot), rules, make_pool([])) == ()


def test_custom_special_play_not_required_by_default() -> None:
    gp = special_gameplan(SpecialSlot(stock=STOCK_FG))
    assert validate_gameplan(gp, Rules(), make_pool([])) == ()


def test_required_clock_category_satisfied_on_offense() -> None:
    """Every offense gameplan carries both stock clock plays, so requiring them passes."""
    gp = offense_gameplan([])
    rules = Rules(required_special_categories=frozenset({11, 12}))
    assert validate_gameplan(gp, rules, make_pool([])) == ()


def test_required_clock_category_fires_on_defense() -> None:
    """Defense has no clock plays, nor clock categories of its own; a league
    requiring Stop Clock is told so by the rules-file name."""
    gp = defense_gameplan([])
    rules = Rules(required_special_categories=frozenset({12}))
    assert validate_gameplan(gp, rules, make_pool([])) == (
        RuleViolation(
            RuleName.SPECIAL_CATEGORY_REQUIRED,
            "Required special category 'Stop Clock' has no play",
            "Stop Clock",
        ),
    )


def test_custom_special_play_required_ignores_clock_categories() -> None:
    """Clock categories are stock-only, so their stock plays never trip the rule."""
    gp = offense_gameplan([])
    rules = Rules(custom_special_play_required=True)
    assert validate_gameplan(gp, rules, make_pool([])) == ()
