"""Unit tests for profile display labels."""

from __future__ import annotations

import pytest

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    MinutesRemaining,
    PatMinutesRemaining,
    PatPointSpread,
    PointSpread,
    ProfileType,
    YardsToGo,
)
from athc.profile import category_label, pat_label, situation_label
from athc.profile.display import sub_label
from tests.unit.profile.conftest import make_profile

OFFENSE = ProfileType.OFFENSE
DEFENSE = ProfileType.DEFENSE

# Short labels by code. Offense has none for Razzle Dazzle Run (0x01) or Pass
# Long Left/Middle (0x07, 0x08); neither side has one for 0x10 and up.
_OFFENSE_LABELS = {
    0x00: "GLR", 0x02: "RL", 0x03: "RM", 0x04: "RR", 0x05: "GLP", 0x06: "PRD",
    0x09: "PLR", 0x0A: "PML", 0x0B: "PMM", 0x0C: "PMR",
    0x0D: "PSL", 0x0E: "PSM", 0x0F: "PSR",
}  # fmt: skip
_DEFENSE_LABELS = {
    0x00: "GLrun", 0x01: "RunDazzle", 0x02: "RunLeft", 0x03: "RunMiddle",
    0x04: "RunRight", 0x05: "GLpass", 0x06: "PassDazzle",
    0x07: "PassLong", 0x08: "PassLong", 0x09: "PassLong",
    0x0A: "PassMedium", 0x0B: "PassMedium", 0x0C: "PassMedium",
    0x0D: "PassShort", 0x0E: "PassShort", 0x0F: "PassShort",
}  # fmt: skip

_MINUTES = {
    MinutesRemaining.OVER_FIVE: ">5",
    MinutesRemaining.TWO_TO_FIVE: ">2-5",
    MinutesRemaining.ONE_TO_TWO: ">1-2",
    MinutesRemaining.FIFTEEN_SEC_TO_ONE: ">:15-1",
    MinutesRemaining.ZERO_TO_FIFTEEN_SEC: "0-:15",
}
_DOWNS = {Down.FIRST: "1st", Down.SECOND: "2nd", Down.THIRD: "3rd", Down.FOURTH: "4th"}
_YARDS = {
    YardsToGo.ZERO_TO_ONE: "0-1",
    YardsToGo.TWO_TO_FIVE: "2-5",
    YardsToGo.SIX_TO_TEN: "6-10",
    YardsToGo.OVER_TEN: ">10",
}
_FIELDS = {
    FieldPosition.INSIDE_DEF_5: "<DEF5",
    FieldPosition.DEF_5_TO_DEF_35: "DEF5-35",
    FieldPosition.DEF_35_TO_OFF_35: "DEF35-OFF35",
    FieldPosition.OFF_35_TO_OFF_5: "OFF35-5",
    FieldPosition.INSIDE_OFF_5: "<OFF5",
}
_SPREADS = {
    PointSpread.AHEAD_8_OR_MORE: "Ahd8+",
    PointSpread.AHEAD_4_TO_7: "Ahd4-7",
    PointSpread.AHEAD_1_TO_3: "Ahd1-3",
    PointSpread.TIED: "Tied",
    PointSpread.BEHIND_1_TO_3: "Beh1-3",
    PointSpread.BEHIND_4_TO_7: "Beh4-7",
    PointSpread.BEHIND_8_OR_MORE: "Beh8+",
}
_PAT_MINUTES = {
    PatMinutesRemaining.OVER_FIVE: ">5",
    PatMinutesRemaining.TWO_TO_FIVE: ">2-5",
    PatMinutesRemaining.ONE_TO_TWO: ">1-2",
    PatMinutesRemaining.ZERO_TO_ONE: "0-1",
}
_PAT_SPREADS = {
    PatPointSpread.AHEAD_12_OR_MORE: "Ahd12+",
    PatPointSpread.AHEAD_9_TO_11: "Ahd9-11",
    PatPointSpread.AHEAD_8: "Ahd8",
    PatPointSpread.AHEAD_6_TO_7: "Ahd6-7",
    PatPointSpread.AHEAD_5: "Ahd5",
    PatPointSpread.AHEAD_2_TO_4: "Ahd2-4",
    PatPointSpread.AHEAD_1: "Ahd1",
    PatPointSpread.TIED: "Tied",
    PatPointSpread.BEHIND_1: "Beh1",
    PatPointSpread.BEHIND_2: "Beh2",
    PatPointSpread.BEHIND_3_TO_4: "Beh3-4",
    PatPointSpread.BEHIND_5: "Beh5",
    PatPointSpread.BEHIND_6_TO_8: "Beh6-8",
    PatPointSpread.BEHIND_9_TO_12: "Beh9-12",
    PatPointSpread.BEHIND_13_OR_MORE: "Beh13+",
}


@pytest.mark.parametrize(
    ("ptype", "labels"), [(OFFENSE, _OFFENSE_LABELS), (DEFENSE, _DEFENSE_LABELS)]
)
def test_category_label_of_every_code(
    ptype: ProfileType, labels: dict[int, str]
) -> None:
    """Every code gets its short label; one without a label renders as hex.
    Defense collapses the three pass directions to one label."""
    expected = {code: labels.get(code, f"0x{code:02X}") for code in range(0x1B)}
    assert {code: category_label(code, ptype) for code in range(0x1B)} == expected


def test_situation_label_of_every_situation() -> None:
    """Each situation's five buckets, in order, each by its own label."""
    for number, state, _ in make_profile(OFFENSE).iter_situations():
        expected = (
            f"{_MINUTES[state.minutes_remaining]} {_DOWNS[state.down]} "
            f"{_YARDS[state.yards_to_go]} {_FIELDS[state.field_position]} "
            f"{_SPREADS[state.point_spread]}"
        )
        assert situation_label(state) == expected, number


def test_pat_label_of_every_pat_situation() -> None:
    for number, state, _ in make_profile(OFFENSE).iter_pat_situations():
        expected = (
            f"{_PAT_MINUTES[state.minutes_remaining]} "
            f"{_PAT_SPREADS[state.point_spread]}"
        )
        assert pat_label(state) == expected, number


def test_sub_label_of_every_group() -> None:
    expected = {
        "offensive_linemen": "OL",
        "quarterbacks": "QB",
        "running_backs": "RB",
        "receivers": "WR",
        "defensive_linemen": "DL",
        "linebackers": "LB",
        "defensive_backs": "DB",
        "kickers": "K",
    }
    assert {group: sub_label(group) for group in expected} == expected
