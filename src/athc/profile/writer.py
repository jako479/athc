"""Copy selected fields between `.prf` profiles; `apply` returns the updated Profile."""

from __future__ import annotations

from dataclasses import replace
from os import PathLike
from pathlib import Path

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    Profile,
    ProfileType,
    Situation,
    read_profile,
)

StrPath = str | PathLike[str]

GOAL_LINE_POSITIONS: frozenset[FieldPosition] = frozenset(
    {FieldPosition.INSIDE_DEF_5, FieldPosition.INSIDE_OFF_5}
)


class ProfileTypeMismatchError(ValueError):
    """Raised when the source and target profile types differ."""

    def __init__(self, source_type: ProfileType, target_type: ProfileType) -> None:
        self.source_type = source_type
        self.target_type = target_type
        super().__init__(
            f"Profile type mismatch: source is {source_type.name}, "
            f"target is {target_type.name}. "
            f"copy only copies offense -> offense or defense -> defense."
        )


class ProfileWriter:
    """Loads source and target `.prf` files and copies selected fields between them."""

    def __init__(self, source_path: StrPath, target_path: StrPath) -> None:
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)

    def apply(
        self,
        *,
        copy_stop_clock: bool = False,
        copy_sub_percent: bool = False,
        copy_field_goal_range: bool = False,
        copy_fourth_down: bool = False,
        copy_goal_line: bool = False,
    ) -> Profile:
        """Apply the requested copies and return the updated target Profile.

        Raises `ProfileTypeMismatchError` before any field if the sides differ.
        `fourth_down` / `goal_line` copy whole situations (stop_clock + weights);
        overlap with `stop_clock` is idempotent.
        """
        source = read_profile(str(self.source_path))
        target = read_profile(str(self.target_path))
        if source.profile_type != target.profile_type:
            raise ProfileTypeMismatchError(source.profile_type, target.profile_type)
        profile = target
        if copy_sub_percent:
            profile = replace(profile, substitutions=source.substitutions)
        if copy_field_goal_range:
            profile = replace(profile, field_goal_range=source.field_goal_range)
        if copy_stop_clock or copy_fourth_down or copy_goal_line:
            profile = _copy_situations(
                profile,
                source,
                stop_clock=copy_stop_clock,
                fourth_down=copy_fourth_down,
                goal_line=copy_goal_line,
            )
        return profile


def _copy_situations(
    target: Profile,
    source: Profile,
    *,
    stop_clock: bool,
    fourth_down: bool,
    goal_line: bool,
) -> Profile:
    """`stop_clock` copies the bit on every situation; `fourth_down` / `goal_line`
    copy the whole situation (stop_clock + weights) where the predicate matches.
    Whole-situation copy wins on overlap."""
    situations: list[Situation] = []
    for t, s in zip(target.situations, source.situations, strict=True):
        whole = (fourth_down and t.down == Down.FOURTH) or (
            goal_line and t.field_position in GOAL_LINE_POSITIONS
        )
        if whole:
            situations.append(
                replace(t, stop_clock=s.stop_clock, category_weights=s.category_weights)
            )
        elif stop_clock:
            situations.append(replace(t, stop_clock=s.stop_clock))
        else:
            situations.append(t)
    return replace(target, situations=tuple(situations))
