from __future__ import annotations

from dataclasses import replace

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    MinutesRemaining,
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


def _default_situation(
    *,
    situation_number: int = 1,
    stop_clock: bool = False,
    weight1: int = 0,
    play_category: int = 0x00,
) -> Situation:
    return Situation.from_situation_number(
        situation_number=situation_number,
        stop_clock=stop_clock,
        category_weights=_default_weights(play_category=play_category, weight1=weight1),
    )


def _default_pat_situation(*, situation_number: int = 1) -> PatSituation:
    return PatSituation.from_situation_number(
        situation_number=situation_number, category_weights=_default_weights()
    )


def _empty_situations(count: int) -> tuple[Situation, ...]:
    return tuple(_default_situation(situation_number=n) for n in range(1, count + 1))


def _empty_pat_situations(count: int) -> tuple[PatSituation, ...]:
    return tuple(
        _default_pat_situation(situation_number=n) for n in range(1, count + 1)
    )


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


# ---------- Situation ----------


def test_situation_from_first_situation_number_yields_expected_game_state() -> None:
    situation = Situation.from_situation_number(
        situation_number=1, stop_clock=False, category_weights=_default_weights()
    )
    assert situation.minutes_remaining is MinutesRemaining.OVER_FIVE
    assert situation.down is Down.FIRST
    assert situation.yards_to_go is YardsToGo.ZERO_TO_ONE
    assert situation.field_position is FieldPosition.INSIDE_DEF_5
    assert situation.point_spread is PointSpread.AHEAD_8_OR_MORE


def test_situation_from_last_situation_number_yields_expected_game_state() -> None:
    situation = Situation.from_situation_number(
        situation_number=2520, stop_clock=False, category_weights=_default_weights()
    )
    assert situation.minutes_remaining is MinutesRemaining.ZERO_TO_FIFTEEN_SEC
    assert situation.down is Down.FOURTH
    assert situation.yards_to_go is YardsToGo.OVER_TEN
    assert situation.field_position is FieldPosition.INSIDE_OFF_5
    assert situation.point_spread is PointSpread.BEHIND_8_OR_MORE


# The first situation of each bucket group, from docs/formats/prf.md section 2.3.4.
SITUATION_GROUP_STARTS = [
    (
        2,
        (
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_4_TO_7,
        ),
    ),
    (
        8,
        (
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        36,
        (
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.TWO_TO_FIVE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        71,
        (
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.SIX_TO_TEN,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        99,
        (
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.OVER_TEN,
            FieldPosition.DEF_5_TO_DEF_35,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        127,
        (
            MinutesRemaining.OVER_FIVE,
            Down.SECOND,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
    (
        505,
        (
            MinutesRemaining.TWO_TO_FIVE,
            Down.FIRST,
            YardsToGo.ZERO_TO_ONE,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.AHEAD_8_OR_MORE,
        ),
    ),
]


@pytest.mark.parametrize(("situation_number", "game_state"), SITUATION_GROUP_STARTS)
def test_situation_decodes_the_first_number_of_each_group(
    situation_number: int,
    game_state: tuple[MinutesRemaining, Down, YardsToGo, FieldPosition, PointSpread],
) -> None:
    situation = _default_situation(situation_number=situation_number)
    assert (
        situation.minutes_remaining,
        situation.down,
        situation.yards_to_go,
        situation.field_position,
        situation.point_spread,
    ) == game_state


def test_every_situation_number_round_trips_through_its_game_state() -> None:
    for situation_number in range(1, Profile.NUMBER_SITUATIONS + 1):
        # Construction re-encodes the decoded state and raises on a mismatch.
        _default_situation(situation_number=situation_number)


@pytest.mark.parametrize("situation_number", [0, 2521])
def test_situation_rejects_situation_number_past_limits(situation_number: int) -> None:
    with pytest.raises(ValueError, match=r"\[1, 2520\]"):
        _default_situation(situation_number=situation_number)


@pytest.mark.parametrize("situation_number", [0, 2521])
def test_situation_constructor_rejects_situation_number_past_limits(
    situation_number: int,
) -> None:
    with pytest.raises(ValueError, match=r"\[1, 2520\]"):
        Situation(
            situation_number=situation_number,
            minutes_remaining=MinutesRemaining.OVER_FIVE,
            down=Down.FIRST,
            yards_to_go=YardsToGo.ZERO_TO_ONE,
            field_position=FieldPosition.INSIDE_DEF_5,
            point_spread=PointSpread.AHEAD_8_OR_MORE,
            stop_clock=False,
            category_weights=_default_weights(),
        )


def test_situation_rejects_six_to_ten_yards_inside_def_5() -> None:
    """6-10 yards-to-go from inside DEF 5 is structurally invalid."""
    with pytest.raises(ValueError, match="invalid combo"):
        Situation._situation_number_from_game_state(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.SIX_TO_TEN,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.TIED,
        )


def test_situation_rejects_over_ten_yards_inside_def_5() -> None:
    """>10 yards-to-go from inside DEF 5 is structurally invalid."""
    with pytest.raises(ValueError, match="invalid combo"):
        Situation._situation_number_from_game_state(
            MinutesRemaining.OVER_FIVE,
            Down.FIRST,
            YardsToGo.OVER_TEN,
            FieldPosition.INSIDE_DEF_5,
            PointSpread.TIED,
        )


def test_situation_rejects_mismatched_situation_number() -> None:
    with pytest.raises(ValueError, match="does not match game state"):
        Situation(
            situation_number=2,
            minutes_remaining=MinutesRemaining.OVER_FIVE,
            down=Down.FIRST,
            yards_to_go=YardsToGo.ZERO_TO_ONE,
            field_position=FieldPosition.INSIDE_DEF_5,
            point_spread=PointSpread.AHEAD_8_OR_MORE,
            stop_clock=False,
            category_weights=_default_weights(),
        )


# ---------- PatSituation ----------


def test_pat_situation_from_first_situation_number_yields_expected_game_state() -> None:
    pat = PatSituation.from_situation_number(
        situation_number=1, category_weights=_default_weights()
    )
    assert pat.minutes_remaining is PatMinutesRemaining.OVER_FIVE
    assert pat.point_spread is PatPointSpread.AHEAD_12_OR_MORE


def test_pat_situation_from_last_situation_number_yields_expected_game_state() -> None:
    pat = PatSituation.from_situation_number(
        situation_number=60, category_weights=_default_weights()
    )
    assert pat.minutes_remaining is PatMinutesRemaining.ZERO_TO_ONE
    assert pat.point_spread is PatPointSpread.BEHIND_13_OR_MORE


# The first PAT situation of each bucket group, from prf.md section 2.5.1.
PAT_SITUATION_GROUP_STARTS = [
    (2, (PatMinutesRemaining.OVER_FIVE, PatPointSpread.AHEAD_9_TO_11)),
    (16, (PatMinutesRemaining.TWO_TO_FIVE, PatPointSpread.AHEAD_12_OR_MORE)),
]


@pytest.mark.parametrize(("situation_number", "game_state"), PAT_SITUATION_GROUP_STARTS)
def test_pat_situation_decodes_the_first_number_of_each_group(
    situation_number: int, game_state: tuple[PatMinutesRemaining, PatPointSpread]
) -> None:
    pat = _default_pat_situation(situation_number=situation_number)
    assert (pat.minutes_remaining, pat.point_spread) == game_state


def test_every_pat_situation_number_round_trips_through_its_game_state() -> None:
    for situation_number in range(1, Profile.NUMBER_PAT_SITUATIONS + 1):
        # Construction re-encodes the decoded state and raises on a mismatch.
        _default_pat_situation(situation_number=situation_number)


@pytest.mark.parametrize("situation_number", [0, 61])
def test_pat_situation_rejects_situation_number_past_limits(
    situation_number: int,
) -> None:
    with pytest.raises(ValueError, match=r"\[1, 60\]"):
        _default_pat_situation(situation_number=situation_number)


@pytest.mark.parametrize("situation_number", [0, 61])
def test_pat_situation_constructor_rejects_situation_number_past_limits(
    situation_number: int,
) -> None:
    with pytest.raises(ValueError, match=r"\[1, 60\]"):
        PatSituation(
            situation_number=situation_number,
            minutes_remaining=PatMinutesRemaining.OVER_FIVE,
            point_spread=PatPointSpread.AHEAD_12_OR_MORE,
            category_weights=_default_weights(),
        )


def test_pat_situation_rejects_mismatched_situation_number() -> None:
    with pytest.raises(ValueError, match="does not match game state"):
        PatSituation(
            situation_number=2,
            minutes_remaining=PatMinutesRemaining.OVER_FIVE,
            point_spread=PatPointSpread.AHEAD_12_OR_MORE,
            category_weights=_default_weights(),
        )


# ---------- Profile invariants ----------


def test_profile_accepts_valid_offense_construction() -> None:
    profile = _make_profile()
    assert profile.is_offense is True
    assert profile.is_defense is False


def test_profile_accepts_valid_defense_construction() -> None:
    profile = _make_profile(profile_type=ProfileType.DEFENSE)
    assert profile.is_defense is True
    assert profile.is_offense is False


def test_profile_situations_wrong_length_raises() -> None:
    with pytest.raises(ValueError, match="situations must have exactly"):
        _make_profile(situations=_empty_situations(10))


def test_profile_pat_situations_wrong_length_raises() -> None:
    with pytest.raises(ValueError, match="pat_situations must have exactly"):
        _make_profile(pat_situations=_empty_pat_situations(5))


@pytest.mark.parametrize("value", [0, 4, 51, 100])
def test_profile_field_goal_range_out_of_bounds_raises(value: int) -> None:
    with pytest.raises(ValueError, match="field_goal_range"):
        _make_profile(field_goal_range=value)


@pytest.mark.parametrize("value", [5, 25, 50])
def test_profile_field_goal_range_at_bounds_accepted(value: int) -> None:
    profile = _make_profile(field_goal_range=value)
    assert profile.field_goal_range == value


# ---------- stop_clock_situations property ----------


def test_stop_clock_situations_empty_when_no_flags_set() -> None:
    profile = _make_profile()
    assert profile.stop_clock_situations == ()


def test_stop_clock_situations_pairs_each_flagged_entry_with_its_number() -> None:
    first = _default_situation(situation_number=5, stop_clock=True, weight1=3)
    middle = _default_situation(situation_number=100, stop_clock=True, weight1=7)
    last = _default_situation(situation_number=2520, stop_clock=True, weight1=10)
    base = list(_empty_situations(Profile.NUMBER_SITUATIONS))
    for situation in (first, middle, last):
        # base[i] holds the situation with situation_number == i + 1
        base[situation.situation_number - 1] = situation

    profile = _make_profile(situations=tuple(base))
    assert profile.stop_clock_situations == ((5, first), (100, middle), (2520, last))
