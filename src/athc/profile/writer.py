"""Copy selected fields between `.prf` profiles; `apply` returns the updated Profile."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from athc.fbpro98_profile import (
    Down,
    FieldPosition,
    Profile,
    read_profile,
)
from athc.profile.errors import ProfileTypeMismatchError

StrPath = str | PathLike[str]

GOAL_LINE_POSITIONS: frozenset[FieldPosition] = frozenset(
    {FieldPosition.INSIDE_DEF_5, FieldPosition.INSIDE_OFF_5}
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
        copy_pat_logic: bool = False,
    ) -> Profile:
        """Read both profiles, apply the requested copies to the target in
        place and return it; neither file is written.

        Raises `ProfileTypeMismatchError` before any field if the sides differ.
        `fourth_down` / `goal_line` copy whole situations (stop_clock + weights);
        overlap with `stop_clock` is idempotent. `pat_logic` copies the whole
        60-situation PAT table.
        """
        source = read_profile(str(self.source_path))
        target = read_profile(str(self.target_path))
        if source.profile_type != target.profile_type:
            raise ProfileTypeMismatchError(
                source.profile_type,
                target.profile_type,
                f"Cannot copy from {self.source_path} "
                f"({source.profile_type.name.lower()}) to a "
                f"{target.profile_type.name.lower()} profile.",
                self.target_path,
            )
        if copy_sub_percent:
            target.substitutions = source.substitutions
        if copy_field_goal_range:
            target.field_goal_range = source.field_goal_range
        if copy_pat_logic:
            target.pat_situations = source.pat_situations
        if copy_stop_clock or copy_fourth_down or copy_goal_line:
            _copy_situations(
                target,
                source,
                stop_clock=copy_stop_clock,
                fourth_down=copy_fourth_down,
                goal_line=copy_goal_line,
            )
        return target


def _copy_situations(
    target: Profile,
    source: Profile,
    *,
    stop_clock: bool,
    fourth_down: bool,
    goal_line: bool,
) -> None:
    """`stop_clock` copies the bit on every situation; `fourth_down` / `goal_line`
    copy the whole situation (stop_clock + weights) where the predicate matches.
    Whole-situation copy wins on overlap."""
    for (number, state, t), s in zip(
        target.iter_situations(), source.situations, strict=True
    ):
        whole = (fourth_down and state.down == Down.FOURTH) or (
            goal_line and state.field_position in GOAL_LINE_POSITIONS
        )
        if whole:
            target.situations[number - 1] = s
        elif stop_clock:
            t.stop_clock = s.stop_clock
