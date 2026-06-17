"""Structural diff of two `.prf` coaching profiles.

Records share fixed, identical keys (situations 1-2520, PAT 1-60, 8 substitution
groups), so the diff aligns by position and compares fields — no sequence diff
needed. `diff_profiles` builds a `ProfileDiff`; rendering is a CLI concern.
"""

from __future__ import annotations

from dataclasses import dataclass

from athc.fbpro98_profile import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
)
from athc.profile.display import SUB_GROUPS, pat_label, situation_label, sub_label


@dataclass(frozen=True, slots=True)
class ScalarChange:
    """One changed scalar field, pre-formatted for display."""

    path: str
    old: str
    new: str


@dataclass(frozen=True, slots=True)
class SlotChange:
    """One changed play slot (1-3). `old`/`new` are `(category code, weight)`."""

    slot: int
    old: tuple[int, int]
    new: tuple[int, int]


@dataclass(frozen=True, slots=True)
class SituationChange:
    """A changed situation (or PAT): its number, game-state label, and field changes."""

    number: int
    label: str
    stop: ScalarChange | None  # None for PAT and unchanged stop_clock
    slots: tuple[SlotChange, ...]


@dataclass(frozen=True, slots=True)
class ProfileDiff:
    """Every difference from one profile to another. Empty when identical."""

    profile_type: ProfileType
    profile: tuple[ScalarChange, ...]
    situations: tuple[SituationChange, ...]
    pat: tuple[SituationChange, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.profile or self.situations or self.pat)


def diff_profiles(a: Profile, b: Profile) -> ProfileDiff:
    """Return the differences from `a` to `b`. Raises ValueError if the sides differ."""
    if a.profile_type != b.profile_type:
        raise ValueError(
            f"cannot diff {a.profile_type.name} against {b.profile_type.name}"
        )
    return ProfileDiff(
        profile_type=a.profile_type,
        profile=_scalar_changes(a, b),
        situations=_situation_changes(a.situations, b.situations),
        pat=_pat_changes(a.pat_situations, b.pat_situations),
    )


def _scalar_changes(a: Profile, b: Profile) -> tuple[ScalarChange, ...]:
    changes: list[ScalarChange] = []
    if a.field_goal_range != b.field_goal_range:
        changes.append(
            ScalarChange(
                "field_goal_range", str(a.field_goal_range), str(b.field_goal_range)
            )
        )
    if a.use_audibles != b.use_audibles:
        changes.append(
            ScalarChange("audibles", _on_off(a.use_audibles), _on_off(b.use_audibles))
        )
    for group in SUB_GROUPS:
        pa = getattr(a.substitutions, group)
        pb = getattr(b.substitutions, group)
        if (pa.out_percent, pa.in_percent) != (pb.out_percent, pb.in_percent):
            changes.append(
                ScalarChange(
                    f"sub.{sub_label(group)}",
                    f"{pa.out_percent}/{pa.in_percent}",
                    f"{pb.out_percent}/{pb.in_percent}",
                )
            )
    return tuple(changes)


def _situation_changes(
    a: tuple[Situation, ...], b: tuple[Situation, ...]
) -> tuple[SituationChange, ...]:
    out: list[SituationChange] = []
    for sa, sb in zip(a, b, strict=True):
        stop = None
        if sa.stop_clock != sb.stop_clock:
            stop = ScalarChange("stop", _no_yes(sa.stop_clock), _no_yes(sb.stop_clock))
        slots = _slot_changes(sa.category_weights, sb.category_weights)
        if stop is not None or slots:
            out.append(
                SituationChange(sa.situation_number, situation_label(sa), stop, slots)
            )
    return tuple(out)


def _pat_changes(
    a: tuple[PatSituation, ...], b: tuple[PatSituation, ...]
) -> tuple[SituationChange, ...]:
    out: list[SituationChange] = []
    for pa, pb in zip(a, b, strict=True):
        slots = _slot_changes(pa.category_weights, pb.category_weights)
        if slots:
            out.append(SituationChange(pa.situation_number, pat_label(pa), None, slots))
    return tuple(out)


def _slot_changes(a: CategoryWeights, b: CategoryWeights) -> tuple[SlotChange, ...]:
    a_slots = (
        (a.play_category1, a.weight1),
        (a.play_category2, a.weight2),
        (a.play_category3, a.weight3),
    )
    b_slots = (
        (b.play_category1, b.weight1),
        (b.play_category2, b.weight2),
        (b.play_category3, b.weight3),
    )
    return tuple(
        SlotChange(i, oa, ob)
        for i, (oa, ob) in enumerate(zip(a_slots, b_slots, strict=True), 1)
        if oa != ob
    )


def _on_off(v: bool) -> str:
    return "On" if v else "Off"


def _no_yes(v: bool) -> str:
    return "Yes" if v else "No"
