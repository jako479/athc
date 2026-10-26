"""Apply play-list updates to a GamePlan in place: resolve names via the pool,
fill slots.

Pure logic (no Click, no I/O): callers read/write the `.pln` themselves. Side and
special classification come from each play's `.ply` header, not the rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from athc.errors import AthcError
from athc.fbpro98_gameplan import CustomPlayRef, GamePlan, PlayRef
from athc.playpool import Play, PlayPool

MAX_NORMAL_PLAYS = GamePlan.NUMBER_NORMAL_PLAYS


class PlayLine(NamedTuple):
    """One play name (empty for a blank line) and the line of the list it is on
    (1-based, blank and `::` lines counted), so an error points at the line the
    user sees."""

    line: int
    name: str


class InvalidPlay(NamedTuple):
    """One play the list cannot place: its line and a sentence saying why.
    The caller names the list or the gameplan, so the line reads right."""

    line: int
    reason: str


class InvalidPlayListError(AthcError):
    """Every play the list cannot place, so the user sees them all at once."""

    def __init__(self, invalid_plays: Sequence[InvalidPlay]) -> None:
        self.invalid_plays = list(invalid_plays)
        super().__init__(f"{len(self.invalid_plays)} invalid play(s).")


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


def apply_normal_plays(gp: GamePlan, plays: Sequence[PlayLine], pool: PlayPool) -> None:
    """Place plays into the 64 normal slots of `gp`, in input order (>64 truncates;
    blank = empty slot); the slots past the list are emptied. Every line is
    resolved first, so an InvalidPlayListError leaves `gp` as it was."""
    entries: list[PlayRef | None] = []
    invalid_plays: list[InvalidPlay] = []
    for slot, play in enumerate(list(plays)[:MAX_NORMAL_PLAYS]):
        entries.append(_resolve_normal_line(slot, play, gp, pool, invalid_plays))
    if invalid_plays:
        raise InvalidPlayListError(invalid_plays)
    gp.normal_plays = entries + [None] * (MAX_NORMAL_PLAYS - len(entries))


def apply_special_plays(
    gp: GamePlan, plays: Sequence[PlayLine], pool: PlayPool
) -> None:
    """Merge custom special plays into `gp` (unlisted categories preserved). Each
    play self-slots by its special category. Every line is resolved first, so
    an InvalidPlayListError leaves `gp` as it was."""
    merged = gp.custom_special_plays
    seen_names: dict[str, int] = {}
    seen_categories: set[int] = set()
    invalid_plays: list[InvalidPlay] = []
    for play in plays:
        name = play.name.strip()
        if not name:
            continue
        entry = _resolve_special_line(
            play.line, name, gp, pool, seen_names, seen_categories, invalid_plays
        )
        if entry is not None:
            merged[entry.special_category - 1] = entry
            seen_names[name.upper()] = entry.special_category
            seen_categories.add(entry.special_category)
    if invalid_plays:
        raise InvalidPlayListError(invalid_plays)
    for category, custom in zip(
        GamePlan.CUSTOM_SPECIAL_CATEGORIES, merged, strict=True
    ):
        gp.special_plays[category - 1].custom = custom


def _resolve_normal_line(
    slot: int,
    play: PlayLine,
    gp: GamePlan,
    pool: PlayPool,
    invalid_plays: list[InvalidPlay],
) -> CustomPlayRef | None:
    name = play.name.strip()
    if not name:
        return None
    grid = _normal_slot_grid(slot)
    record = pool.find_by_name(name)
    if record is None:
        invalid_plays.append(
            InvalidPlay(play.line, f"'{name}' is not in the play pool (slot {grid}).")
        )
        return None
    pf = record.play_file
    if pf.is_special:
        invalid_plays.append(
            InvalidPlay(
                play.line,
                f"'{name}' is a special play and cannot go in a normal slot.",
            )
        )
        return None
    if gp.is_offense and pf.is_defensive:
        invalid_plays.append(
            InvalidPlay(
                play.line,
                f"'{name}' is a defensive play, but the game plan is offensive.",
            )
        )
        return None
    if gp.is_defense and pf.is_offensive:
        invalid_plays.append(
            InvalidPlay(
                play.line,
                f"'{name}' is an offensive play, but the game plan is defensive.",
            )
        )
        return None
    return build_custom_play(record, pool.root_dir)


def _resolve_special_line(
    line: int,
    name: str,
    gp: GamePlan,
    pool: PlayPool,
    seen_names: dict[str, int],
    seen_categories: set[int],
    invalid_plays: list[InvalidPlay],
) -> CustomPlayRef | None:
    upper = name.upper()
    if upper in seen_names:
        invalid_plays.append(
            InvalidPlay(
                line,
                f"Duplicate special play '{name}', "
                f"already used for special category {seen_names[upper]}.",
            )
        )
        return None
    record = pool.find_by_name(name)
    if record is None:
        invalid_plays.append(InvalidPlay(line, f"'{name}' is not in the play pool."))
        return None
    pf = record.play_file
    if not pf.is_special:
        invalid_plays.append(InvalidPlay(line, f"'{name}' is not a special play."))
        return None
    if gp.is_offense and not pf.is_offensive:
        invalid_plays.append(
            InvalidPlay(
                line,
                f"'{name}' is a defensive special play, "
                "but the game plan is offensive.",
            )
        )
        return None
    if gp.is_defense and not pf.is_defensive:
        invalid_plays.append(
            InvalidPlay(
                line,
                f"'{name}' is an offensive special play, "
                "but the game plan is defensive.",
            )
        )
        return None
    cat = pf.special_category
    if cat not in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
        invalid_plays.append(
            InvalidPlay(
                line,
                f"'{name}' is in special category {cat}, which has no custom slot.",
            )
        )
        return None
    if cat in seen_categories:
        invalid_plays.append(
            InvalidPlay(
                line,
                f"'{name}' targets special category {cat}, "
                "already filled by another play.",
            )
        )
        return None
    return build_custom_play(record, pool.root_dir)
