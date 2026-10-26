from __future__ import annotations

import copy
from dataclasses import fields

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


def _empty_situations(count: int) -> list[Situation]:
    return [_default_situation() for _ in range(count)]


def _empty_pat_situations(count: int) -> list[PatSituation]:
    return [_default_pat_situation() for _ in range(count)]


def _make_profile(
    *, profile_type: ProfileType = ProfileType.OFFENSE, **overrides
) -> Profile:
    profile = Profile(
        profile_type=profile_type,
        substitutions=SubstitutionSettings.default(),
        situations=_empty_situations(Profile.NUMBER_SITUATIONS),
        pat_situations=_empty_pat_situations(Profile.NUMBER_PAT_SITUATIONS),
        field_goal_range=35,
        use_audibles=False,
    )
    for name, value in overrides.items():
        setattr(profile, name, value)
    return profile


def _rejects(profile: Profile, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        profile.validate()


# ---------- editing ----------


def test_edit_by_assignment_then_validate() -> None:
    profile = _make_profile()
    profile.field_goal_range = 45
    profile.situations[7].stop_clock = True
    profile.substitutions.kickers.out_percent = 70
    profile.validate()
    expected = _make_profile(field_goal_range=45)
    expected.situations[7] = _default_situation(stop_clock=True)
    expected.substitutions.kickers = SubstitutionPair(70, 90)
    assert profile == expected


def test_deep_copy_edits_apart() -> None:
    original = _make_profile()
    edited = copy.deepcopy(original)
    edited.situations[0].stop_clock = True
    assert original.situations[0].stop_clock is False


# ---------- SubstitutionSettings ----------


def test_substitution_settings_default_uses_80_90() -> None:
    settings = SubstitutionSettings.default()
    for _, pair in settings.pairs():
        assert pair.out_percent == 80
        assert pair.in_percent == 90


def test_substitution_settings_default_gives_each_group_its_own_pair() -> None:
    settings = SubstitutionSettings.default()
    settings.kickers.out_percent = 70
    assert settings.offensive_linemen.out_percent == 80


def test_substitution_settings_pairs_in_file_order() -> None:
    assert [group for group, _ in SubstitutionSettings.default().pairs()] == [
        "offensive_linemen",
        "quarterbacks",
        "running_backs",
        "receivers",
        "defensive_linemen",
        "linebackers",
        "defensive_backs",
        "kickers",
    ]


# ---------- Situation / PatSituation ----------


def test_situation_holds_only_its_rules() -> None:
    assert tuple(f.name for f in fields(Situation)) == (
        "stop_clock",
        "category_weights",
    )
    assert tuple(f.name for f in fields(PatSituation)) == ("category_weights",)


# ---------- validate: the profile ----------


def test_profile_accepts_valid_offense_construction() -> None:
    profile = _make_profile()
    profile.validate()
    assert profile.is_offense is True
    assert profile.is_defense is False


def test_profile_accepts_valid_defense_construction() -> None:
    profile = _make_profile(profile_type=ProfileType.DEFENSE)
    profile.validate()
    assert profile.is_defense is True
    assert profile.is_offense is False


@pytest.mark.parametrize("value", [-1, 2])
def test_validate_rejects_a_profile_type_past_the_limits(value: int) -> None:
    profile = _make_profile()
    profile.profile_type = value  # type: ignore[assignment]
    _rejects(profile, f"profile_type: Must be 0 or 1, got {value}")


# 2520 and 60 are accepted by every valid construction above.
@pytest.mark.parametrize("count", [2519, 2521])
def test_profile_situations_wrong_length_raises(count: int) -> None:
    _rejects(
        _make_profile(situations=_empty_situations(count)),
        r"^situations must have exactly 2520",
    )


@pytest.mark.parametrize("count", [59, 61])
def test_profile_pat_situations_wrong_length_raises(count: int) -> None:
    _rejects(
        _make_profile(pat_situations=_empty_pat_situations(count)),
        r"^pat_situations must have exactly 60",
    )


@pytest.mark.parametrize("value", [4, 51])
def test_profile_field_goal_range_past_the_limits_raises(value: int) -> None:
    _rejects(
        _make_profile(field_goal_range=value),
        rf"field_goal_range must be in \[5, 50\], got {value}",
    )


@pytest.mark.parametrize("value", [5, 50])
def test_profile_field_goal_range_at_the_limits_accepted(value: int) -> None:
    _make_profile(field_goal_range=value).validate()


# ---------- validate: substitution pairs ----------


def _with_quarterbacks(out_percent: int, in_percent: int) -> Profile:
    profile = _make_profile()
    profile.substitutions.quarterbacks = SubstitutionPair(out_percent, in_percent)
    return profile


@pytest.mark.parametrize(
    ("out_percent", "in_percent"),
    [(0, 0), (0, 100), (100, 100), (50, 50)],
)
def test_substitution_pair_at_the_limits_accepted(
    out_percent: int, in_percent: int
) -> None:
    _with_quarterbacks(out_percent, in_percent).validate()


@pytest.mark.parametrize(
    ("out_percent", "in_percent", "message"),
    [
        (-1, 50, "substitutions.quarterbacks.out_percent: Must be 0-100, got -1"),
        (101, 100, "substitutions.quarterbacks.out_percent: Must be 0-100, got 101"),
        (50, -1, "substitutions.quarterbacks.in_percent: Must be 0-100, got -1"),
        (50, 101, "substitutions.quarterbacks.in_percent: Must be 0-100, got 101"),
        (
            90,
            80,
            r"substitutions.quarterbacks.out_percent: Must be at most in_percent "
            r"\(80\), got 90",
        ),
    ],
)
def test_substitution_pair_past_the_limits_rejected(
    out_percent: int, in_percent: int, message: str
) -> None:
    _rejects(_with_quarterbacks(out_percent, in_percent), message)


# ---------- validate: category weights ----------


def _with_weights(**fields: int) -> Profile:
    """Situation 4's weights with `fields` changed."""
    profile = _make_profile()
    weights = profile.situations[3].category_weights
    for name, value in fields.items():
        setattr(weights, name, value)
    return profile


@pytest.mark.parametrize("play_category", [0x00, 0x1A])
def test_play_category_at_the_limits_accepted(play_category: int) -> None:
    _with_weights(play_category2=play_category).validate()


@pytest.mark.parametrize(
    ("play_category", "shown"), [(-1, "-1"), (0x1B, "0x1B")], ids=["-1", "0x1B"]
)
def test_play_category_past_the_limits_rejected(play_category: int, shown: str) -> None:
    _rejects(
        _with_weights(play_category2=play_category),
        f"situation 4: play_category2: Must be 0x00-0x1A, got {shown}",
    )


@pytest.mark.parametrize("weight", [0, 10])
def test_weight_at_the_limits_accepted(weight: int) -> None:
    _with_weights(weight3=weight).validate()


@pytest.mark.parametrize("weight", [-1, 11])
def test_weight_past_the_limits_rejected(weight: int) -> None:
    _rejects(
        _with_weights(weight3=weight),
        f"situation 4: weight3: Must be 0-10, got {weight}",
    )


def test_pat_situation_weights_are_checked_too() -> None:
    profile = _make_profile()
    profile.pat_situations[59].category_weights.weight1 = 11
    _rejects(profile, "PAT situation 60: weight1: Must be 0-10, got 11")


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
    profile = _make_profile(situations=[shared] * Profile.NUMBER_SITUATIONS)
    walked = list(profile.iter_situations())
    assert [number for number, _, _ in walked] == list(range(1, 2521))
    assert [state for _, state, _ in walked] == [
        Profile.game_state(number) for number in range(1, 2521)
    ]


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
    assert profile.stop_clock_situations == []


def test_stop_clock_situations_give_each_flagged_entry_its_number_and_state() -> None:
    # first and middle hold equal values, so a number found by value shows.
    first = _default_situation(stop_clock=True, weight1=3)
    middle = _default_situation(stop_clock=True, weight1=3)
    last = _default_situation(stop_clock=True, weight1=10)
    base = _empty_situations(Profile.NUMBER_SITUATIONS)
    base[4], base[99], base[2519] = first, middle, last

    profile = _make_profile(situations=base)
    assert profile.stop_clock_situations == [
        (5, Profile.game_state(5), first),
        (100, Profile.game_state(100), middle),
        (2520, Profile.game_state(2520), last),
    ]
