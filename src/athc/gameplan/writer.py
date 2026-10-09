"""Apply play-list updates to a GamePlan: resolve names via the pool, fill slots.

Pure logic (no Click, no I/O): callers read/write the `.pln` themselves. Side and
special-teams classification come from each play's `.ply` header, not the rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from athc.errors import AthcError
from athc.fbpro98_gameplan import CustomPlayRef, GamePlan
from athc.playpool import Play, PlayPool

MAX_NORMAL_PLAYS = GamePlan.NUMBER_NORMAL_PLAYS


class InvalidPlayInputError(AthcError):
    """Aggregates per-line input violations so the user sees every problem at once."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = list(violations)
        body = "\n  - ".join(self.violations)
        super().__init__(f"{len(self.violations)} invalid input line(s):\n  - {body}")


def _normal_slot_grid(slot_index: int) -> str:
    """In-game `G-C` coord for a 0-based slot: slot 0 -> `1-1`, slot 63 -> `16-4`."""
    return f"{slot_index // 4 + 1}-{slot_index % 4 + 1}"


def build_custom_play(record: Play, root_dir: Path) -> CustomPlayRef:
    """Build the `.pln` slot entry from a pool record: the play pool's folder name,
    then the play's path inside the pool."""
    relative = str(record.file_path.relative_to(root_dir)).replace("/", "\\")
    pf = record.play_file
    return CustomPlayRef(
        filename=f"{root_dir.name}\\{relative}",
        play_category=pf.play_category,
        special_category=pf.special_category,
        user_category=pf.user_category,
    )


def apply_normal_plays(gp: GamePlan, lines: Sequence[str], pool: PlayPool) -> GamePlan:
    """Place plays into the 64 normal slots in input order (>64 truncates; blank = empty
    slot). Per-line failures raise InvalidPlayInputError. Returns a new GamePlan."""
    entries: list[CustomPlayRef | None] = []
    violations: list[str] = []
    for slot, line in enumerate(list(lines)[:MAX_NORMAL_PLAYS]):
        entries.append(_resolve_normal_line(slot, line, gp, pool, violations))
    if violations:
        raise InvalidPlayInputError(violations)
    return gp.with_normal_plays(entries)  # with_normal_plays pads to 64


def apply_special_plays(gp: GamePlan, lines: Sequence[str], pool: PlayPool) -> GamePlan:
    """Merge custom special plays (unlisted categories preserved). Each play self-slots
    by its special category. Per-line failures raise InvalidPlayInputError."""
    merged: list[CustomPlayRef | None] = list(gp.custom_special_plays)
    seen_names: dict[str, int] = {}
    seen_categories: set[int] = set()
    violations: list[str] = []
    for index, line in enumerate(lines):
        name = line.strip()
        if not name:
            continue
        entry = _resolve_special_line(
            index, name, gp, pool, seen_names, seen_categories, violations
        )
        if entry is not None:
            merged[entry.special_category - 1] = entry
            seen_names[name.upper()] = entry.special_category
            seen_categories.add(entry.special_category)
    if violations:
        raise InvalidPlayInputError(violations)
    return gp.with_custom_special_plays(merged)


def _resolve_normal_line(
    slot: int, line: str, gp: GamePlan, pool: PlayPool, violations: list[str]
) -> CustomPlayRef | None:
    name = line.strip()
    if not name:
        return None
    line_no = slot + 1
    grid = _normal_slot_grid(slot)
    record = pool.find_by_name(name)
    if record is None:
        violations.append(
            f"line {line_no}: '{name}' not found in the play pool (slot {grid})"
        )
        return None
    pf = record.play_file
    if pf.is_special_teams:
        violations.append(
            f"line {line_no}: '{name}' is a special teams play, cannot add to "
            "normal slots"
        )
        return None
    if gp.is_offense and pf.is_defensive:
        violations.append(
            f"line {line_no}: '{name}' is a defensive play but gameplan is offensive"
        )
        return None
    if gp.is_defense and pf.is_offensive:
        violations.append(
            f"line {line_no}: '{name}' is an offensive play but gameplan is defensive"
        )
        return None
    return build_custom_play(record, pool.root_dir)


def _resolve_special_line(
    index: int,
    name: str,
    gp: GamePlan,
    pool: PlayPool,
    seen_names: dict[str, int],
    seen_categories: set[int],
    violations: list[str],
) -> CustomPlayRef | None:
    upper = name.upper()
    line_no = index + 1
    if upper in seen_names:
        violations.append(
            f"line {line_no}: duplicate special play '{name}', "
            f"already used for special category {seen_names[upper]}"
        )
        return None
    record = pool.find_by_name(name)
    if record is None:
        violations.append(f"line {line_no}: '{name}' not found in the play pool")
        return None
    pf = record.play_file
    if not pf.is_special_teams:
        violations.append(f"line {line_no}: '{name}' is not a special teams play")
        return None
    if gp.is_offense and not pf.is_offensive:
        violations.append(
            f"line {line_no}: '{name}' is a defensive special play "
            "but gameplan is offensive"
        )
        return None
    if gp.is_defense and not pf.is_defensive:
        violations.append(
            f"line {line_no}: '{name}' is an offensive special play "
            "but gameplan is defensive"
        )
        return None
    cat = pf.special_category
    if cat not in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
        violations.append(
            f"line {line_no}: '{name}' is in special category {cat}, "
            "which has no custom slot"
        )
        return None
    if cat in seen_categories:
        violations.append(
            f"line {line_no}: '{name}' targets special category {cat}, "
            "already filled by another play"
        )
        return None
    return build_custom_play(record, pool.root_dir)
