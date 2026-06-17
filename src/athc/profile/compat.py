"""Check a coaching profile's play categories against a gameplan's custom plays.

A profile weights play categories per situation (and PAT); the gameplan must back
every used category with at least one *custom* play. Normal run/pass categories
map to the 64 normal slots; special-teams categories (FG/PAT, punt, the fakes)
map to the 10 custom special slots. Clock and "random" meta-categories aren't
backed by individual custom plays and are skipped.

Profile and gameplan must be the same side (offense/defense) — the caller checks
that first. Rules are not consulted here; this only compares categories to plays.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from athc.fbpro98_gameplan import GamePlan, Play
from athc.fbpro98_play.model import DEFENSIVE_CATEGORIES, OFFENSIVE_CATEGORIES
from athc.fbpro98_profile import CategoryWeights, Profile
from athc.profile.display import category_label
from athc.profile.rules import (
    FAKE_FIELD_GOAL_PASS,
    FAKE_FIELD_GOAL_RUN,
    FAKE_PUNT_PASS,
    FAKE_PUNT_RUN,
    FIELD_GOAL_PAT,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_ANY,
    PASS_LONG_LEFT,
    PASS_LONG_MIDDLE,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_ANY,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_ANY,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    PUNT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RIGHT,
)

# The 16 normal (non-special, non-clock) play-category codes a profile can use.
_NORMAL_CODES: frozenset[int] = frozenset(range(0x00, 0x10))

# Gameplan offense category name -> the profile code it covers. Names match the
# fbpro98_play OFFENSIVE_CATEGORIES table; offense keeps pass directions.
_OFFENSE_NORMAL_CODES: dict[str, frozenset[int]] = {
    "Goal Line Run": frozenset({GOAL_LINE_RUN}),
    "Razzle Dazzle Run": frozenset({RAZZLE_DAZZLE_RUN}),
    "Run Left": frozenset({RUN_LEFT}),
    "Run Middle": frozenset({RUN_MIDDLE}),
    "Run Right": frozenset({RUN_RIGHT}),
    "Goal Line Pass": frozenset({GOAL_LINE_PASS}),
    "Razzle Dazzle Pass": frozenset({RAZZLE_DAZZLE_PASS}),
    "Pass Long Left": frozenset({PASS_LONG_LEFT}),
    "Pass Long Middle": frozenset({PASS_LONG_MIDDLE}),
    "Pass Long Right": frozenset({PASS_LONG_RIGHT}),
    "Pass Medium Left": frozenset({PASS_MEDIUM_LEFT}),
    "Pass Medium Middle": frozenset({PASS_MEDIUM_MIDDLE}),
    "Pass Medium Right": frozenset({PASS_MEDIUM_RIGHT}),
    "Pass Short Left": frozenset({PASS_SHORT_LEFT}),
    "Pass Short Middle": frozenset({PASS_SHORT_MIDDLE}),
    "Pass Short Right": frozenset({PASS_SHORT_RIGHT}),
}

# Gameplan defense category name -> profile codes covered. Names match the
# fbpro98_play DEFENSIVE_CATEGORIES table; defense collapses pass directions, so
# one play covers all three (e.g. "Pass Long" -> long left/middle/right).
_DEFENSE_NORMAL_CODES: dict[str, frozenset[int]] = {
    "Goal Line Run": frozenset({GOAL_LINE_RUN}),
    "Run Dazzle": frozenset({RAZZLE_DAZZLE_RUN}),
    "Run Left": frozenset({RUN_LEFT}),
    "Run Middle": frozenset({RUN_MIDDLE}),
    "Run Right": frozenset({RUN_RIGHT}),
    "Goal Line Pass": frozenset({GOAL_LINE_PASS}),
    "Pass Dazzle": frozenset({RAZZLE_DAZZLE_PASS}),
    "Pass Long": PASS_LONG_ANY,
    "Pass Medium": PASS_MEDIUM_ANY,
    "Pass Short": PASS_SHORT_ANY,
}

# Profile special-teams code -> gameplan custom special slot (1-10). Slot numbers
# are side-independent (FG/PAT = 1 on offense and defense, etc.).
_SPECIAL_SLOT_BY_CODE: dict[int, int] = {
    FIELD_GOAL_PAT: 1,
    PUNT: 3,
    FAKE_FIELD_GOAL_RUN: 5,
    FAKE_FIELD_GOAL_PASS: 6,
    FAKE_PUNT_RUN: 7,
    FAKE_PUNT_PASS: 8,
}

# Readable names for the special-teams codes a profile can reference.
_SPECIAL_NAME: dict[int, str] = {
    FIELD_GOAL_PAT: "Field Goal/PAT",
    PUNT: "Punt",
    FAKE_FIELD_GOAL_RUN: "Fake FG Run",
    FAKE_FIELD_GOAL_PASS: "Fake FG Pass",
    FAKE_PUNT_RUN: "Fake Punt Run",
    FAKE_PUNT_PASS: "Fake Punt Pass",
}


class CompatKind(StrEnum):
    """Identifier for each kind of profile/gameplan incompatibility."""

    MISSING_NORMAL_CATEGORY = "missing_normal_category"
    MISSING_SPECIAL_CATEGORY = "missing_special_category"


@dataclass(frozen=True, slots=True)
class CompatIssue:
    """One profile/gameplan incompatibility. `category_code` is the .prf category
    byte the profile uses but the gameplan does not cover."""

    kind: CompatKind
    category_code: int
    message: str


def check_gameplan_compatibility(
    profile: Profile, gameplan: GamePlan
) -> tuple[CompatIssue, ...]:
    """Report categories the profile uses that the gameplan has no custom play for.

    Profile and gameplan must already be the same side. Normal categories are
    checked against the 64 normal slots, special-teams categories against the 10
    custom special slots; clock/random categories are ignored.
    """
    used = _used_categories(profile)
    issues: list[CompatIssue] = []

    name_codes = _OFFENSE_NORMAL_CODES if profile.is_offense else _DEFENSE_NORMAL_CODES
    present = _present_normal_codes(gameplan, name_codes)
    for code in sorted((used & _NORMAL_CODES) - present):
        label = category_label(code, profile.profile_type)
        issues.append(
            CompatIssue(
                CompatKind.MISSING_NORMAL_CATEGORY,
                code,
                f"play category {label} (0x{code:02X}) has no custom play "
                f"in the gameplan",
            )
        )

    for code in sorted(used & _SPECIAL_SLOT_BY_CODE.keys()):
        slot = _SPECIAL_SLOT_BY_CODE[code]
        if gameplan.custom_special_plays[slot - 1] is None:
            issues.append(
                CompatIssue(
                    CompatKind.MISSING_SPECIAL_CATEGORY,
                    code,
                    f"special-teams category {_SPECIAL_NAME[code]} has no custom "
                    f"special play in the gameplan",
                )
            )

    return tuple(issues)


def _used_categories(profile: Profile) -> frozenset[int]:
    """Distinct play-category codes weighted > 0 across situations and PATs."""
    codes: set[int] = set()
    for situation in profile.situations:
        codes |= _weighted(situation.category_weights)
    for pat in profile.pat_situations:
        codes |= _weighted(pat.category_weights)
    return frozenset(codes)


def _weighted(weights: CategoryWeights) -> frozenset[int]:
    return frozenset(
        cat
        for cat, weight in (
            (weights.play_category1, weights.weight1),
            (weights.play_category2, weights.weight2),
            (weights.play_category3, weights.weight3),
        )
        if weight > 0
    )


def _present_normal_codes(
    gameplan: GamePlan, name_codes: dict[str, frozenset[int]]
) -> frozenset[int]:
    """Profile codes covered by the gameplan's custom normal plays."""
    codes: set[int] = set()
    for play in gameplan.normal_plays:
        if play is None:
            continue
        name = _normal_category_name(play, offense=gameplan.is_offense)
        if name is not None:
            codes |= name_codes.get(name, frozenset())
    return frozenset(codes)


def _normal_category_name(play: Play, *, offense: bool) -> str | None:
    """Game category name for a normal custom play, via its `user_category`.

    Mirrors `PlayFile.category_name`'s normal-play branch (full byte, then the
    masked base) over the same offense/defense tables.
    """
    table = OFFENSIVE_CATEGORIES if offense else DEFENSIVE_CATEGORIES
    return table.get(play.user_category, table.get(play.user_category & 0x3F))


__all__ = [
    "CompatIssue",
    "CompatKind",
    "check_gameplan_compatibility",
]
