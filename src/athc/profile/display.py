"""Compact display labels for profile diffs: game-state buckets and play categories.

Bucket strings follow the in-game UI. Category labels use short names — offense
caps (`RM`, `PSL`), defense words (`PassShort`, `GLpass`), defense pass directions
collapsed. A code outside the side's set renders as raw `0xNN`. These are display
labels only (presentation), not rules.
"""

from __future__ import annotations

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    MinutesRemaining,
    PatMinutesRemaining,
    PatPointSpread,
    PatSituation,
    PointSpread,
    ProfileType,
    Situation,
    YardsToGo,
)

_MINUTES = {
    MinutesRemaining.OVER_FIVE: ">5",
    MinutesRemaining.TWO_TO_FIVE: ">2-5",
    MinutesRemaining.ONE_TO_TWO: ">1-2",
    MinutesRemaining.FIFTEEN_SEC_TO_ONE: ">:15-1",
    MinutesRemaining.ZERO_TO_FIFTEEN_SEC: "0-:15",
}
_DOWN = {Down.FIRST: "1st", Down.SECOND: "2nd", Down.THIRD: "3rd", Down.FOURTH: "4th"}
_YARDS = {
    YardsToGo.ZERO_TO_ONE: "0-1",
    YardsToGo.TWO_TO_FIVE: "2-5",
    YardsToGo.SIX_TO_TEN: "6-10",
    YardsToGo.OVER_TEN: ">10",
}
_FIELD = {
    FieldPosition.INSIDE_DEF_5: "<DEF5",
    FieldPosition.DEF_5_TO_DEF_35: "DEF5-35",
    FieldPosition.DEF_35_TO_OFF_35: "DEF35-OFF35",
    FieldPosition.OFF_35_TO_OFF_5: "OFF35-5",
    FieldPosition.INSIDE_OFF_5: "<OFF5",
}
_SPREAD = {
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
_PAT_SPREAD = {
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

# .prf category code -> short string, per side (see module docstring).
_OFFENSE_SHORT = {
    0x00: "GLR", 0x02: "RL", 0x03: "RM", 0x04: "RR", 0x05: "GLP", 0x06: "PRD",
    0x09: "PLR", 0x0A: "PML", 0x0B: "PMM", 0x0C: "PMR",
    0x0D: "PSL", 0x0E: "PSM", 0x0F: "PSR",
}  # fmt: skip
_DEFENSE_SHORT = {
    0x00: "GLrun", 0x01: "RunDazzle", 0x02: "RunLeft",
    0x03: "RunMiddle", 0x04: "RunRight",
    0x05: "GLpass", 0x06: "PassDazzle",
    0x07: "PassLong", 0x08: "PassLong", 0x09: "PassLong",
    0x0A: "PassMedium", 0x0B: "PassMedium", 0x0C: "PassMedium",
    0x0D: "PassShort", 0x0E: "PassShort", 0x0F: "PassShort",
}  # fmt: skip

# Substitution position groups, in .prf order, with their short labels.
SUB_GROUPS: tuple[str, ...] = (
    "offensive_linemen",
    "quarterbacks",
    "running_backs",
    "receivers",
    "defensive_linemen",
    "linebackers",
    "defensive_backs",
    "kickers",
)
_SUB_LABELS = {
    "offensive_linemen": "OL",
    "quarterbacks": "QB",
    "running_backs": "RB",
    "receivers": "WR",
    "defensive_linemen": "DL",
    "linebackers": "LB",
    "defensive_backs": "DB",
    "kickers": "K",
}


def category_label(code: int, profile_type: ProfileType) -> str:
    """Short label for a category code, or `0xNN` if outside the side's set."""
    table = _OFFENSE_SHORT if profile_type == ProfileType.OFFENSE else _DEFENSE_SHORT
    return table.get(code, f"0x{code:02X}")


def situation_label(s: Situation) -> str:
    """`>5 3rd 2-5 DEF35-OFF35 Tied` — the five game-state buckets."""
    return (
        f"{_MINUTES[s.minutes_remaining]} {_DOWN[s.down]} {_YARDS[s.yards_to_go]} "
        f"{_FIELD[s.field_position]} {_SPREAD[s.point_spread]}"
    )


def pat_label(p: PatSituation) -> str:
    """`>5 Tied` — the two PAT game-state buckets."""
    return f"{_PAT_MINUTES[p.minutes_remaining]} {_PAT_SPREAD[p.point_spread]}"


def sub_label(group: str) -> str:
    """Short label for a substitution position group (e.g. `quarterbacks` -> `QB`)."""
    return _SUB_LABELS[group]
