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
    return PatSituation.from_situation_number(situation_number=situation_number, category_weights=_default_weights())


def _empty_situations(count: int) -> tuple[Situation, ...]:
    return tuple(_default_situation(situation_number=n) for n in range(1, count + 1))


def _empty_pat_situations(count: int) -> tuple[PatSituation, ...]:
    return tuple(_default_pat_situation(situation_number=n) for n in range(1, count + 1))


def _make_profile(*, profile_type: ProfileType = ProfileType.OFFENSE, **overrides) -> Profile:
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


def test_substitution_pair_accepts_valid_values() -> None:
    pair = SubstitutionPair(out_percent=80, in_percent=90)
    assert pair.out_percent == 80
    assert pair.in_percent == 90


def test_substitution_pair_rejects_out_above_in() -> None:
    with pytest.raises(ValueError, match="must be <="):
        SubstitutionPair(out_percent=90, in_percent=80)


def test_substitution_pair_rejects_out_below_zero() -> None:
    with pytest.raises(ValueError, match="out_percent must be in"):
        SubstitutionPair(out_percent=-1, in_percent=50)


def test_substitution_pair_rejects_in_above_100() -> None:
    with pytest.raises(ValueError, match="in_percent must be in"):
        SubstitutionPair(out_percent=50, in_percent=101)


def test_substitution_pair_accepts_equal_values() -> None:
    pair = SubstitutionPair(out_percent=50, in_percent=50)
    assert pair.out_percent == pair.in_percent


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


def test_category_weights_rejects_play_category_above_max() -> None:
    with pytest.raises(ValueError, match="play_category1"):
        CategoryWeights(
            play_category1=0x1B,
            weight1=0,
            play_category2=0x00,
            weight2=0,
            play_category3=0x00,
            weight3=0,
        )


def test_category_weights_rejects_weight_above_10() -> None:
    with pytest.raises(ValueError, match="weight2"):
        CategoryWeights(
            play_category1=0x00,
            weight1=0,
            play_category2=0x00,
            weight2=11,
            play_category3=0x00,
            weight3=0,
        )


def test_category_weights_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="weight3"):
        CategoryWeights(
            play_category1=0x00,
            weight1=0,
            play_category2=0x00,
            weight2=0,
            play_category3=0x00,
            weight3=-1,
        )


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
    assert situation.down.value == 4
    assert situation.yards_to_go is YardsToGo.OVER_TEN
    assert situation.field_position is FieldPosition.INSIDE_OFF_5
    assert situation.point_spread is PointSpread.BEHIND_8_OR_MORE


def test_situation_round_trip_for_every_valid_situation_number() -> None:
    for situation_number in range(1, Profile.NUMBER_SITUATIONS + 1):
        state = Situation._game_state_from_situation_number(situation_number)
        assert Situation._situation_number_from_game_state(*state) == situation_number


def test_situation_rejects_out_of_range_situation_number() -> None:
    with pytest.raises(ValueError, match=r"\[1, 2520\]"):
        Situation._game_state_from_situation_number(2521)
    with pytest.raises(ValueError, match=r"\[1, 2520\]"):
        Situation._game_state_from_situation_number(0)


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
    pat = PatSituation.from_situation_number(situation_number=1, category_weights=_default_weights())
    assert pat.minutes_remaining is PatMinutesRemaining.OVER_FIVE
    assert pat.point_spread is PatPointSpread.AHEAD_12_OR_MORE


def test_pat_situation_from_last_situation_number_yields_expected_game_state() -> None:
    pat = PatSituation.from_situation_number(situation_number=60, category_weights=_default_weights())
    assert pat.minutes_remaining is PatMinutesRemaining.ZERO_TO_ONE
    assert pat.point_spread is PatPointSpread.BEHIND_13_OR_MORE


def test_pat_situation_round_trip_for_every_valid_situation_number() -> None:
    for situation_number in range(1, Profile.NUMBER_PAT_SITUATIONS + 1):
        state = PatSituation._game_state_from_situation_number(situation_number)
        assert PatSituation._situation_number_from_game_state(*state) == situation_number


def test_pat_situation_rejects_out_of_range_situation_number() -> None:
    with pytest.raises(ValueError, match=r"\[1, 60\]"):
        PatSituation._game_state_from_situation_number(61)


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


def test_stop_clock_situations_returns_only_flagged_entries() -> None:
    base = list(_empty_situations(Profile.NUMBER_SITUATIONS))
    # base[i] holds the situation with situation_number == i + 1
    base[4] = _default_situation(situation_number=5, stop_clock=True, weight1=3)
    base[99] = _default_situation(situation_number=100, stop_clock=True, weight1=7)
    base[2519] = _default_situation(situation_number=2520, stop_clock=True, weight1=10)

    profile = _make_profile(situations=tuple(base))
    situation_numbers = [n for n, _ in profile.stop_clock_situations]
    assert situation_numbers == [5, 100, 2520]


def test_stop_clock_situations_yields_situation_number_situation_pairs() -> None:
    base = list(_empty_situations(Profile.NUMBER_SITUATIONS))
    base[41] = _default_situation(situation_number=42, stop_clock=True, weight1=4)
    profile = _make_profile(situations=tuple(base))
    pairs = profile.stop_clock_situations
    assert len(pairs) == 1
    situation_number, situation = pairs[0]
    assert situation_number == 42
    assert situation.stop_clock is True
    assert situation.category_weights.weight1 == 4


def test_stop_clock_situations_excludes_pat_situations() -> None:
    """The property only inspects `situations`, not `pat_situations`. PAT has no stop_clock."""
    profile = _make_profile()
    assert profile.stop_clock_situations == ()
