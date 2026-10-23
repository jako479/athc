from __future__ import annotations

from dataclasses import fields, replace

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    GameState,
    MinutesRemaining,
    PatGameState,
    PatMinutesRemaining,
    PatPointSpread,
    PatSituation,
    PointSpread,
    Profile,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
    YardsToGo,
)


def _default_weights(*, play_category: int = 0x00, weight1: int = 0) -> CategoryWeights:
    return CategoryWeights(
        play_category1=play_category,
        weight1=weight1,
        play_category2=play_category,
        weight2=0,
        play_category3=play_category,
        weight3=0,
    )


def _default_situation(*, stop_clock: bool = False, weight1: int = 0) -> Situation:
    return Situation(
        stop_clock=stop_clock, category_weights=_default_weights(weight1=weight1)
    )


def _default_pat_situation() -> PatSituation:
    return PatSituation(category_weights=_default_weights())


def _empty_situations(count: int) -> tuple[Situation, ...]:
    return tuple(_default_situation() for _ in range(count))


def _empty_pat_situations(count: int) -> tuple[PatSituation, ...]:
    return tuple(_default_pat_situation() for _ in range(count))


def _make_profile(
    *, profile_type: ProfileType = ProfileType.OFFENSE, **overrides
) -> Profile:
    base = Profile(
        profile_type=profile_type,
        substitutions=SubstitutionSettings.default(),
        situations=_empty_situations(Profile.NUMBER_SITUATIONS),
        pat_situations=_empty_pat_situations(Profile.NUMBER_PAT_SITUATIONS),
        field_goal_range=35,
        use_audibles=False,
    )
    return replace(base, **overrides)


# ---------- SubstitutionPair ----------


@pytest.mark.parametrize(
    ("out_percent", "in_percent"),
    [(80, 90), (0, 0), (0, 100), (100, 100), (50, 50)],
)
def test_substitution_pair_accepts_values_within_limits(
    out_percent: int, in_percent: int
) -> None:
    pair = SubstitutionPair(out_percent=out_percent, in_percent=in_percent)
    assert (pair.out_percent, pair.in_percent) == (out_percent, in_percent)


@pytest.mark.parametrize(
    ("out_percent", "in_percent", "message"),
    [
        (-1, 50, "out_percent must be in"),
        (101, 100, "out_percent must be in"),
        (50, -1, "in_percent must be in"),
        (50, 101, "in_percent must be in"),
        (90, 80, "must be <="),
    ],
)
def test_substitution_pair_rejects_values_past_limits(
    out_percent: int, in_percent: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SubstitutionPair(out_percent=out_percent, in_percent=in_percent)


# ---------- SubstitutionSettings ----------


def test_substitution_settings_default_uses_80_90() -> None:
    settings = SubstitutionSettings.default()
    for group in (
        settings.offensive_linemen,
        settings.quarterbacks,
        settings.running_backs,
        settings.receivers,
        settings.defensive_linemen,
        settings.linebackers,
        settings.defensive_backs,
        settings.kickers,
    ):
        assert group.out_percent == 80
        assert group.in_percent == 90


# ---------- CategoryWeights ----------


def test_category_weights_accepts_valid_values() -> None:
    weights = CategoryWeights(
        play_category1=0x07,
        weight1=10,
        play_category2=0x10,
        weight2=5,
        play_category3=0x00,
        weight3=0,
    )
    assert weights.weight1 == 10
    assert weights.play_category1 == 0x07


@pytest.mark.parametrize("play_category", [0x00, 0x1A])
def test_category_weights_accepts_play_category_at_limits(play_category: int) -> None:
    weights = _default_weights(play_category=play_category)
    assert weights.play_category1 == play_category


@pytest.mark.parametrize("play_category", [-1, 0x1B])
def test_category_weights_rejects_play_category_past_limits(
    play_category: int,
) -> None:
    with pytest.raises(ValueError, match="play_category1"):
        _default_weights(play_category=play_category)


@pytest.mark.parametrize("weight", [0, 10])
def test_category_weights_accepts_weight_at_limits(weight: int) -> None:
    assert _default_weights(weight1=weight).weight1 == weight


@pytest.mark.parametrize("weight", [-1, 11])
def test_category_weights_rejects_weight_past_limits(weight: int) -> None:
    with pytest.raises(ValueError, match="weight1"):
        _default_weights(weight1=weight)


# ---------- Situation / PatSituation ----------


def test_situation_holds_only_its_rules() -> None:
    assert tuple(f.name for f in fields(Situation)) == (
        "stop_clock",
        "category_weights",
    )
    assert tuple(f.name for f in fields(PatSituation)) == ("category_weights",)


# ---------- Profile invariants ----------


def test_profile_accepts_valid_offense_construction() -> None:
    profile = _make_profile()
    assert profile.is_offense is True
    assert profile.is_defense is False


def test_profile_accepts_valid_defense_construction() -> None:
    profile = _make_profile(profile_type=ProfileType.DEFENSE)
    assert profile.is_defense is True
    assert profile.is_offense is False


# 2520 and 60 are accepted by every valid construction above.
@pytest.mark.parametrize("count", [2519, 2521])
def test_profile_situations_wrong_length_raises(count: int) -> None:
    with pytest.raises(ValueError, match=r"^situations must have exactly 2520"):
        _make_profile(situations=_empty_situations(count))


@pytest.mark.parametrize("count", [59, 61])
def test_profile_pat_situations_wrong_length_raises(count: int) -> None:
    with pytest.raises(ValueError, match=r"^pat_situations must have exactly 60"):
        _make_profile(pat_situations=_empty_pat_situations(count))


@pytest.mark.parametrize("value", [0, 4, 51, 100])
def test_profile_field_goal_range_out_of_bounds_raises(value: int) -> None:
    with pytest.raises(ValueError, match="field_goal_range"):
        _make_profile(field_goal_range=value)


@pytest.mark.parametrize("value", [5, 25, 50])
def test_profile_field_goal_range_at_bounds_accepted(value: int) -> None:
    profile = _make_profile(field_goal_range=value)
    assert profile.field_goal_range == value


# ---------- Profile game-state decode ----------


# Both ends of the layout and the first and last cell of each yards-to-go group,
# plus a down and a minutes boundary, from docs/formats/prf.md section 2.3.4.
SITUATION_CORNERS = [
    (
        1,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        7,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        8,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        35,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        36,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.TWO_TO_FIVE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        70,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.TWO_TO_FIVE,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        71,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.SIX_TO_TEN,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        98,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.SIX_TO_TEN,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        99,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.OVER_TEN,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        126,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.OVER_TEN,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        127,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.SECOND,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        504,
        GameState(
            MinutesRemaining.OVER_FIVE,
            Down.FOURTH,
            YardsToGo.OVER_TEN,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
    (
        505,
        GameState(
            MinutesRemaining.TWO_TO_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        2520,
        GameState(
            MinutesRemaining.ZERO_TO_FIFTEEN_SEC,
            Down.FOURTH,
            YardsToGo.OVER_TEN,
            FieldPosition.INSIDE_OFF_5,
            PointSpread.BEHIND_8_OR_MORE,
        ),
    ),
]


@pytest.mark.parametrize(("situation_number", "state"), SITUATION_CORNERS)
def test_game_state_decodes_the_layout_corners(
    situation_number: int, state: GameState
) -> None:
    assert Profile.game_state(situation_number) == state


@pytest.mark.parametrize("situation_number", [0, 2521])
def test_game_state_rejects_numbers_past_limits(situation_number: int) -> None:
    with pytest.raises(ValueError, match=r"\[1, 2520\]"):
        Profile.game_state(situation_number)


# Both ends of the PAT layout and the minutes boundary, from prf.md section 2.5.1.
PAT_CORNERS = [
    (1, PatGameState(PatMinutesRemaining.OVER_FIVE, PatPointSpread.AHEAD_12_OR_MORE)),
    (15, PatGameState(PatMinutesRemaining.OVER_FIVE, PatPointSpread.BEHIND_13_OR_MORE)),
    (
        16,
        PatGameState(PatMinutesRemaining.TWO_TO_FIVE, PatPointSpread.AHEAD_12_OR_MORE),
    ),
    (
        60,
        PatGameState(PatMinutesRemaining.ZERO_TO_ONE, PatPointSpread.BEHIND_13_OR_MORE),
    ),
]


@pytest.mark.parametrize(("situation_number", "state"), PAT_CORNERS)
def test_pat_game_state_decodes_the_layout_corners(
    situation_number: int, state: PatGameState
) -> None:
    assert Profile.pat_game_state(situation_number) == state


@pytest.mark.parametrize("situation_number", [0, 61])
def test_pat_game_state_rejects_numbers_past_limits(situation_number: int) -> None:
    with pytest.raises(ValueError, match=r"\[1, 60\]"):
        Profile.pat_game_state(situation_number)


# ---------- Situation walks ----------


def test_iter_situations_walks_every_slot_in_order() -> None:
    profile = _make_profile()
    walked = list(profile.iter_situations())
    assert [number for number, _, _ in walked] == list(range(1, 2521))
    for number, state, situation in walked:
        assert state == Profile.game_state(number)
        assert situation is profile.situations[number - 1]


def test_iter_situations_numbers_slots_holding_the_same_situation() -> None:
    shared = _default_situation()
    profile = _make_profile(situations=(shared,) * Profile.NUMBER_SITUATIONS)
    walked = list(profile.iter_situations())
    assert [number for number, _, _ in walked] == list(range(1, 2521))
    assert len({state for _, state, _ in walked}) == 2520


def test_iter_pat_situations_walks_every_slot_in_order() -> None:
    profile = _make_profile()
    walked = list(profile.iter_pat_situations())
    assert [number for number, _, _ in walked] == list(range(1, 61))
    for number, state, pat in walked:
        assert state == Profile.pat_game_state(number)
        assert pat is profile.pat_situations[number - 1]


# ---------- stop_clock_situations property ----------


def test_stop_clock_situations_empty_when_no_flags_set() -> None:
    profile = _make_profile()
    assert profile.stop_clock_situations == ()


def test_stop_clock_situations_give_each_flagged_entry_its_number_and_state() -> None:
    # first and middle hold equal values, so a number found by value shows.
    first = _default_situation(stop_clock=True, weight1=3)
    middle = _default_situation(stop_clock=True, weight1=3)
    last = _default_situation(stop_clock=True, weight1=10)
    base = list(_empty_situations(Profile.NUMBER_SITUATIONS))
    base[4], base[99], base[2519] = first, middle, last

    profile = _make_profile(situations=tuple(base))
    assert profile.stop_clock_situations == (
        (5, Profile.game_state(5), first),
        (100, Profile.game_state(100), middle),
        (2520, Profile.game_state(2520), last),
    )
