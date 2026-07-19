"""Unit tests for `check_gameplan_compatibility` — profile categories vs gameplan
custom plays. Profiles and gameplans are constructed for surgical control over
which categories are used and which custom plays exist.
"""

from __future__ import annotations

from athc.fbpro98_gameplan import CustomPlayRef, GamePlan, StockPlayRef
from athc.fbpro98_gameplan import ProfileType as GamePlanType
from athc.fbpro98_play import (
    DefensiveCategory,
    OffensiveCategory,
    resolve_category,
)
from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionSettings,
)
from athc.profile import (
    CompatKind,
    check_gameplan_compatibility,
    gameplan_extra_categories,
)
from athc.profile.compat import (
    _DEFENSE_NORMAL_CODES,
    _OFFENSE_NORMAL_CODES,
    _SPECIAL_SLOT_BY_CODE,
)
from athc.profile.rules import (
    FAKE_FIELD_GOAL_RUN,
    FIELD_GOAL_PAT,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_LEFT,
    PASS_SHORT_RANDOM,
    PUNT,
    RUN_CLOCK,
    RUN_MIDDLE,
)

# user_category bytes (.ply game-category) for the gameplan custom plays we build.
OFF_RUN_MIDDLE = 0x09
OFF_GOAL_LINE_RUN = 0x31
DEF_PASS_LONG = 0x22  # collapses long left/middle/right
DEF_GOAL_LINE_PASS = 0x32

_CLOCK = (
    CustomPlayRef(
        "C1.PLY", play_category=0x01, special_category=11, user_category=0x09
    ),
    CustomPlayRef(
        "C2.PLY", play_category=0x01, special_category=12, user_category=0x09
    ),
)


def weights(c1: int, w1: int, c2: int, w2: int, c3: int, w3: int) -> CategoryWeights:
    return CategoryWeights(c1, w1, c2, w2, c3, w3)


def make_profile(
    *, offense: bool, sit: CategoryWeights, pat: CategoryWeights
) -> Profile:
    """Profile whose every situation uses `sit` and every PAT uses `pat`, so the
    used-category set is exactly the non-zero codes in those two triples."""
    ptype = ProfileType.OFFENSE if offense else ProfileType.DEFENSE
    return Profile(
        profile_type=ptype,
        substitutions=SubstitutionSettings.default(),
        situations=tuple(
            Situation.from_situation_number(n, False, sit)
            for n in range(1, Profile.NUMBER_SITUATIONS + 1)
        ),
        pat_situations=tuple(
            PatSituation.from_situation_number(n, pat)
            for n in range(1, Profile.NUMBER_PAT_SITUATIONS + 1)
        ),
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
    plays = tuple(
        CustomPlayRef(f"N{i}.PLY", parity, 0, uc) for i, uc in enumerate(normal)
    )
    normal_plays = plays + (None,) * (64 - len(plays))
    slots: list[CustomPlayRef | StockPlayRef | None] = [None] * 20
    for s in special:
        slots[(s - 1) * 2] = CustomPlayRef(f"SP{s}.PLY", parity, s, 0)
    for s in stock_special:
        slots[(s - 1) * 2 + 1] = StockPlayRef(f"ST{s}", 0, 0, parity, s, 0)
    return GamePlan(
        profile_type=GamePlanType.OFFENSE if offense else GamePlanType.DEFENSE,
        normal_plays=normal_plays,
        special_plays=tuple(slots),
        clock_plays=_CLOCK if offense else (None, None),
    )


# ── normal categories (offense) ────────────────────────────────────────────────


def test_offense_normal_covered() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))
    assert check_gameplan_compatibility(prof, gp) == ()


def test_offense_normal_missing() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(GOAL_LINE_RUN, 4, GOAL_LINE_RUN, 0, GOAL_LINE_RUN, 0),
        pat=weights(GOAL_LINE_RUN, 4, GOAL_LINE_RUN, 0, GOAL_LINE_RUN, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))
    issues = check_gameplan_compatibility(prof, gp)
    assert len(issues) == 1
    assert issues[0].kind == CompatKind.MISSING_NORMAL_CATEGORY
    assert issues[0].category_code == GOAL_LINE_RUN
    assert "GLR" in issues[0].message


# ── special categories (offense) ───────────────────────────────────────────────


def test_offense_special_covered() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), special=(1,))
    assert check_gameplan_compatibility(prof, gp) == ()


def test_offense_special_missing() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(PUNT, 4, RUN_MIDDLE, 6, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))  # no special slot 3
    issues = check_gameplan_compatibility(prof, gp)
    assert [i.category_code for i in issues] == [PUNT]
    assert issues[0].kind == CompatKind.MISSING_SPECIAL_CATEGORY
    assert "Punt" in issues[0].message


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


def test_defense_pass_direction_collapses() -> None:
    """A defense 'Pass Long' custom play covers any directional long-pass code."""
    prof = make_profile(
        offense=False,
        sit=weights(PASS_LONG_LEFT, 4, PASS_LONG_LEFT, 0, PASS_LONG_LEFT, 0),
        pat=weights(PASS_LONG_LEFT, 4, PASS_LONG_LEFT, 0, PASS_LONG_LEFT, 0),
    )
    gp = make_gameplan(offense=False, normal=(DEF_PASS_LONG,))
    assert check_gameplan_compatibility(prof, gp) == ()


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
    gp = make_gameplan(offense=False, normal=(0x08,))  # Run Middle; no special slot 1
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


def test_zero_weight_category_is_ignored() -> None:
    """A category present only with weight 0 is not 'used' and never flagged."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, GOAL_LINE_RUN, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,))  # no GLR
    assert check_gameplan_compatibility(prof, gp) == ()


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


# ── reverse: gameplan categories not used by the profile (warnings) ─────────────


def test_extra_offense_normal_category_warned() -> None:
    """A gameplan normal play whose category the profile never weights -> warning."""
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE, OFF_GOAL_LINE_RUN))
    warnings = gameplan_extra_categories(prof, gp)
    assert len(warnings) == 1
    assert warnings[0].kind == CompatKind.EXTRA_NORMAL_CATEGORY
    assert "Goal Line Run" in warnings[0].message


def test_extra_special_category_warned() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), special=(1,))
    warnings = gameplan_extra_categories(prof, gp)
    assert [w.kind for w in warnings] == [CompatKind.EXTRA_SPECIAL_CATEGORY]
    assert "Field Goal/PAT" in warnings[0].message


def test_used_categories_are_not_warned() -> None:
    prof = make_profile(
        offense=True,
        sit=weights(RUN_MIDDLE, 4, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
        pat=weights(FIELD_GOAL_PAT, 10, FIELD_GOAL_PAT, 0, FIELD_GOAL_PAT, 0),
    )
    gp = make_gameplan(offense=True, normal=(OFF_RUN_MIDDLE,), special=(1,))
    assert gameplan_extra_categories(prof, gp) == ()


def test_defense_direction_collapse_not_falsely_warned() -> None:
    """A defense 'Pass Long' play covers L/M/R; if the profile uses any one of
    them the category is used, so no false 'extra' warning for the others."""
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
    msgs = [w.message for w in gameplan_extra_categories(prof, gp)]
    assert msgs == [
        "gameplan play category Goal Line Run is not used by the profile",
        "gameplan play category Goal Line Pass is not used by the profile",
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


# ── map consistency with the model tables (guards transcription) ────────────────


def test_offense_normal_map_covers_all_offense_categories() -> None:
    names = {c.long for c in OffensiveCategory if c.long != "User Specific"}
    assert set(_OFFENSE_NORMAL_CODES) == names
    codes = frozenset().union(*_OFFENSE_NORMAL_CODES.values())
    assert codes == frozenset(range(0x00, 0x10))


def test_defense_normal_map_covers_all_defense_categories() -> None:
    names = {c.long for c in DefensiveCategory if c.long != "User Specific"}
    assert set(_DEFENSE_NORMAL_CODES) == names
    codes = frozenset().union(*_DEFENSE_NORMAL_CODES.values())
    assert codes == frozenset(range(0x00, 0x10))


def test_special_slot_map_matches_model_names() -> None:
    """Each profile special code maps to the slot the game labels the same way."""
    expected = {
        FIELD_GOAL_PAT: "Field Goal/PAT",
        PUNT: "Punt",
        FAKE_FIELD_GOAL_RUN: "Fake FG Run",
    }
    for code, name in expected.items():
        slot = _SPECIAL_SLOT_BY_CODE[code]
        assert resolve_category(0x01, slot, 0x00).long == name
