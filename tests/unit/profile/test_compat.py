"""Unit tests for `check_gameplan_compatibility` — profile categories vs gameplan
custom plays. Profiles and gameplans are constructed for surgical control over
which categories are used and which custom plays exist.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    SpecialSlot,
    StockPlayRef,
)
from athc.fbpro98_gameplan import ProfileType as GamePlanType
from athc.fbpro98_play import DefensiveCategory, OffensiveCategory
from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionSettings,
)
from athc.profile import (
    CompatIssue,
    CompatKind,
    check_gameplan_compatibility,
    gameplan_extra_categories,
)
from athc.profile.rules import (
    FAKE_FIELD_GOAL_PASS,
    FAKE_FIELD_GOAL_RUN,
    FAKE_PUNT_PASS,
    FAKE_PUNT_RUN,
    FIELD_GOAL_PAT,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_LEFT,
    PASS_LONG_RIGHT,
    PASS_SHORT_RANDOM,
    PUNT,
    RUN_CLOCK,
    RUN_MIDDLE,
)
from tests.unit.profile.conftest import (
    DEFENSE_CODES_BY_NAME,
    OFFENSE_CODES_BY_NAME,
    weights,
)

# user_category bytes (.ply game-category) for the gameplan custom plays we build.
OFF_RUN_MIDDLE = 0x09
OFF_GOAL_LINE_RUN = 0x31
DEF_RUN_MIDDLE = 0x08
DEF_PASS_LONG = 0x22  # collapses long left/middle/right
DEF_GOAL_LINE_PASS = 0x32

NORMAL_CODES = frozenset(range(0x00, 0x10))


def make_profile(
    *, offense: bool, sit: CategoryWeights, pat: CategoryWeights
) -> Profile:
    """Profile whose every situation uses `sit` and every PAT uses `pat`, so the
    used-category set is exactly the non-zero codes in those two triples."""
    ptype = ProfileType.OFFENSE if offense else ProfileType.DEFENSE
    return Profile(
        profile_type=ptype,
        substitutions=SubstitutionSettings.default(),
        situations=[
            Situation(stop_clock=False, category_weights=sit)
            for _ in range(Profile.NUMBER_SITUATIONS)
        ],
        pat_situations=[
            PatSituation(category_weights=pat)
            for _ in range(Profile.NUMBER_PAT_SITUATIONS)
        ],
        field_goal_range=20,
        use_audibles=False,
    )


def profile_using(codes: Iterable[int], *, offense: bool) -> Profile:
    """Profile whose situations take `codes` in turn, one each at weight 1, so
    the used-category set is exactly `codes`."""
    cycle = sorted(codes)
    first = weights(cycle[0], 1, 0, 0, 0, 0)
    return Profile(
        profile_type=ProfileType.OFFENSE if offense else ProfileType.DEFENSE,
        substitutions=SubstitutionSettings.default(),
        situations=[
            Situation(
                stop_clock=False,
                category_weights=weights(cycle[i % len(cycle)], 1, 0, 0, 0, 0),
            )
            for i in range(Profile.NUMBER_SITUATIONS)
        ],
        pat_situations=[
            PatSituation(category_weights=first)
            for _ in range(Profile.NUMBER_PAT_SITUATIONS)
        ],
        field_goal_range=20,
        use_audibles=False,
    )


def make_gameplan(
    *,
    offense: bool,
    normal: tuple[int, ...] = (),
    special: tuple[int, ...] = (),
    stock_special: tuple[int, ...] = (),
) -> GamePlan:
    """Gameplan with one custom normal play per `normal` user_category, and custom
    (or stock) special plays in the given special-category slots (1-10)."""
    parity = 0x01 if offense else 0x00
    normal_plays: list[PlayRef | None] = [
        CustomPlayRef(f"N{i}.PLY", parity, 0, uc) for i, uc in enumerate(normal)
    ]
    normal_plays += [None] * (64 - len(normal_plays))
    slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for s in special:
        slots[s - 1] = SpecialSlot(custom=CustomPlayRef(f"SP{s}.PLY", parity, s, 0))
    for s in stock_special:
        slots[s - 1] = SpecialSlot(stock=StockPlayRef(f"ST{s}", 0, 0, parity, s, 0))
    if offense:
        for s in (11, 12):
            slots[s - 1] = SpecialSlot(
                stock=StockPlayRef(f"CLOCK{s}", 0, 0, parity, s, 0)
            )
    return GamePlan(
        profile_type=GamePlanType.OFFENSE if offense else GamePlanType.DEFENSE,
        normal_plays=normal_plays,
        special_plays=slots,
    )


# ── normal categories ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("offense", "category"),
    [
        pytest.param(True, c, id=f"offense-{c.long}")
        for c in OffensiveCategory
        if c is not OffensiveCategory.USER_SPECIFIC
    ]
    + [
        pytest.param(False, c, id=f"defense-{c.long}")
        for c in DefensiveCategory
        if c is not DefensiveCategory.USER_SPECIFIC
    ],
)
def test_custom_play_backs_exactly_its_categorys_codes(
    offense: bool, category: OffensiveCategory | DefensiveCategory
) -> None:
    """A custom play of each game category backs that category's codes and no
    other: a profile using every normal code is missing all the rest."""
    backed = (OFFENSE_CODES_BY_NAME if offense else DEFENSE_CODES_BY_NAME)[
        category.long
    ]
    prof = profile_using(NORMAL_CODES, offense=offense)
    gp = make_gameplan(offense=offense, normal=(category.code,))
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == sorted(NORMAL_CODES - backed)


def test_offense_normal_missing() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(GOAL_LINE_RUN, 4, GOAL_LINE_RUN, 0, GOAL_LINE_RUN, 0),
        pat=weights(GOAL_LINE_RUN, 4, GOAL_LINE_RUN, 0, GOAL_LINE_RUN, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))
    assert check_gameplan_compatibility(prof, gp) == (
        CompatIssue(
            CompatKind.MISSING_NORMAL_CATEGORY,
            GOAL_LINE_RUN,
            "play category GLR (0x00) has no custom play in the game plan",
        ),
    )


# ── special categories ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("code", "slot", "name"),
    [
        (FIELD_GOAL_PAT, 1, "Field Goal/PAT"),
        (PUNT, 3, "Punt"),
        (FAKE_FIELD_GOAL_RUN, 5, "Fake FG Run"),
        (FAKE_FIELD_GOAL_PASS, 6, "Fake FG Pass"),
        (FAKE_PUNT_RUN, 7, "Fake Punt Run"),
        (FAKE_PUNT_PASS, 8, "Fake Punt Pass"),
    ],
)
def test_special_category_needs_a_custom_play_in_its_slot(
    code: int, slot: int, name: str
) -> None:
    """Each special code is backed by its own slot alone: that slot's custom
    play covers it, and custom plays in every other slot do not."""
    prof = make_profile(
        offense=True,
        sit=weights(code, 4, code, 0, code, 0),
        pat=weights(code, 4, code, 0, code, 0),
    )
    others = tuple(s for s in range(1, 11) if s != slot)
    covered = make_gameplan(offense=True, special=(slot,))
    uncovered = make_gameplan(offense=True, special=others)
    assert check_gameplan_compatibility(prof, covered) == ()
    assert check_gameplan_compatibility(prof, uncovered) == (
        CompatIssue(
            CompatKind.MISSING_SPECIAL_CATEGORY,
            code,
            f"special category {name} has no custom special play in the game plan",
        ),
    )


def test_special_stock_only_is_not_enough() -> None:
    """A custom special play is required; a stock-only slot still fails."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), stock_special=(1,))
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == [FIELD_GOAL_PAT]


# ── defense ────────────────────────────────────────────────────────────────────


def test_defense_each_unbacked_direction_is_its_own_issue() -> None:
    """With no Pass Long play, each long-pass direction the profile uses is
    reported, by its own code."""
    prof = make_profile(
        offense=False,
        sit=weights(PASS_LONG_LEFT, 4, PASS_LONG_RIGHT, 3, RUN_MIDDLE, 3),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=False, normal=(DEF_RUN_MIDDLE,))
    assert check_gameplan_compatibility(prof, gp) == tuple(
        CompatIssue(
            CompatKind.MISSING_NORMAL_CATEGORY,
            code,
            f"play category PassLong (0x{code:02X}) has no custom play "
            "in the game plan",
        )
        for code in (PASS_LONG_LEFT, PASS_LONG_RIGHT)
    )


def test_defense_normal_missing() -> None:
    prof = make_profile(
        offense=False,
        sit=weights(GOAL_LINE_PASS, 4, GOAL_LINE_PASS, 0, GOAL_LINE_PASS, 0),
        pat=weights(GOAL_LINE_PASS, 4, GOAL_LINE_PASS, 0, GOAL_LINE_PASS, 0),
    )
    gp = make_gameplan(offense=False, normal=(DEF_PASS_LONG,))
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == [GOAL_LINE_PASS]
    assert "GLpass" in issues[0].message


def test_defense_special_missing() -> None:
    """Defense special slots map by the same number (FG/PAT = slot 1)."""
    prof = make_profile(
        offense=False,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=False, normal=(DEF_RUN_MIDDLE,))  # no special slot 1
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == [FIELD_GOAL_PAT]
    assert issues[0].kind == CompatKind.MISSING_SPECIAL_CATEGORY


# ── skipped / ignored categories ───────────────────────────────────────────────


def test_clock_and_random_categories_are_skipped() -> None:
    """Clock and 'random' meta-categories aren't backed by custom plays."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_CLOCK, 4, PASS_SHORT_RANDOM, 4, RUN_CLOCK, 0),
        pat=weights(RUN_CLOCK, 4, PASS_SHORT_RANDOM, 4, RUN_CLOCK, 0),
    )
    gp = make_gameplan(offense=True)  # empty pool of normal plays
    assert check_gameplan_compatibility(prof, gp) == ()


def test_user_specific_normal_play_covers_nothing() -> None:
    """A 'User Specific' normal play (user_category 0xFF) backs no league category."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(0xFF,))  # User Specific only
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == [RUN_MIDDLE]


@pytest.mark.parametrize(("weight", "flagged"), [(0, False), (1, True)])
def test_category_is_used_from_weight_one(weight: int, flagged: bool) -> None:
    """A category present only with weight 0 is not 'used' and never flagged;
    at weight 1 it is."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, GOAL_LINE_RUN, weight, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))  # no GLR
    codes = [i.category_code for i in check_gameplan_compatibility(prof, gp)]
    assert codes == ([GOAL_LINE_RUN] if flagged else [])


# ── combined / ordering ────────────────────────────────────────────────────────


def test_multiple_issues_sorted_normal_then_special() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(GOAL_LINE_RUN, 4, PASS_LONG_LEFT, 4, PUNT, 2),
        pat=weights(
            FAKE_FIELD_GOAL_RUN, 10, FAKE_FIELD_GOAL_RUN, 0, FAKE_FIELD_GOAL_RUN, 0
        ),
    )
    gp = make_gameplan(offense=True)  # nothing covered
    codes = [i.category_code for i in check_gameplan_compatibility(prof, gp)]
    # normal codes (ascending) first, then special codes (ascending);
    # FAKE_FIELD_GOAL_RUN (0x11) sorts before PUNT (0x13).
    assert codes == [GOAL_LINE_RUN, PASS_LONG_LEFT, FAKE_FIELD_GOAL_RUN, PUNT]


def test_pat_only_category_is_checked() -> None:
    """A category used solely in PAT situations is still checked."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))  # no special slot 1
    assert [i.category_code for i in check_gameplan_compatibility(prof, gp)] == [
        FIELD_GOAL_PAT
    ]


def test_fully_compatible_returns_empty() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, GOAL_LINE_RUN, 3, PUNT, 1),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(
        offense=True,
        normal=(OFF_RUN_MIDDLE, OFF_GOAL_LINE_RUN),
        special=(1, 3),
    )
    assert check_gameplan_compatibility(prof, gp) == ()


# ── reverse: gameplan categories not used by the profile ──────────────────────


def test_extra_offense_normal_category_reported() -> None:
    """A gameplan normal play whose category the profile never weights -> issue."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE, OFF_GOAL_LINE_RUN))
    issues = gameplan_extra_categories(prof, gp)
    assert len(issues) == 1
    assert issues[0].kind == CompatKind.EXTRA_NORMAL_CATEGORY
    assert issues[0].category_code is None
    assert "Goal Line Run" in issues[0].message


def test_extra_special_category_reported() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), special=(1,))
    issues = gameplan_extra_categories(prof, gp)
    assert [i.kind for i in issues] == [CompatKind.EXTRA_SPECIAL_CATEGORY]
    assert "Field Goal/PAT" in issues[0].message


def test_used_categories_are_not_reported() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), special=(1,))
    assert gameplan_extra_categories(prof, gp) == ()


def test_defense_direction_collapse_not_falsely_reported() -> None:
    """A defense 'Pass Long' play covers L/M/R; if the profile uses any one of
    them the category is used, so no false 'extra' issue for the others."""
    prof = make_profile(
        offense=False,
        sit=weights(PASS_LONG_LEFT, 4, PASS_LONG_LEFT, 0, PASS_LONG_LEFT, 0),
        pat=weights(PASS_LONG_LEFT, 4, PASS_LONG_LEFT, 0, PASS_LONG_LEFT, 0),
    )
    gp = make_gameplan(offense=False, normal=(DEF_PASS_LONG,))
    assert gameplan_extra_categories(prof, gp) == ()


def test_extra_normal_sorted_by_code() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    # Goal Line Run (0x00) before Goal Line Pass (0x05) by minimum code.
    gp = make_gameplan(offense=True, normal=(0x33, OFF_GOAL_LINE_RUN, OFF_RUN_MIDDLE))
    msgs = [i.message for i in gameplan_extra_categories(prof, gp)]
    assert msgs == [
        "play category Goal Line Run is in the game plan but not used by the profile",
        "play category Goal Line Pass is in the game plan but not used by the profile",
    ]


def test_stock_special_play_is_not_an_extra() -> None:
    """A stock-only special slot has no custom play, so it is never flagged."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), stock_special=(1,))
    assert gameplan_extra_categories(prof, gp) == ()


def test_user_specific_play_is_not_an_extra() -> None:
    """A User Specific custom play backs no category, so it is never extra."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    user_specific = OffensiveCategory.USER_SPECIFIC.code
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE, user_specific))
    assert gameplan_extra_categories(prof, gp) == ()
