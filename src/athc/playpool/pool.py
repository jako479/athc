"""Build a PlayPool: walk a tree, classify each .ply from its file, index by name.

Side and category come from the parsed play file, so any folder layout works —
a league tree, an arbitrary tree, or a flat directory. Folders are optional: a
recognized folder adds an attribute the bytes can't carry (offense `screen`,
defense `defensive_front`) and lets the pool warn (with the play's path) when a
play sits in a folder that contradicts its file. Category folders are named by
the league's labels (`CategoryLabels`, from league.toml); the filename-derived
flags (`rollout`, `qb_draw`, `pass_logic`) come from the league's `PlaypoolRules`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path, PurePath

from athc.fbpro98_play import (
    CategoryLabels,
    InvalidPlayFileError,
    OffensiveCategory,
    PlayCategory,
    PlayFile,
    read_play,
)
from athc.playpool.records import (
    DefensiveFront,
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    Play,
    SpecialTeamsPlay,
)
from athc.playpool.rules import PlaypoolRules

StrPath = str | PathLike[str]

logger = logging.getLogger(__name__)

# ── League folder conventions (optional; only these names mean anything). The
# side, screen and front folder names are fixed; category folders are named by
# the league's labels. ────────────────────────────────────────────────────────
SCREENS_FOLDER = "Screens"  # offense pass screen
RNS_FOLDER = "R&SDefs"  # Run-and-Shoot defense → 2-DL front
SIDE_FOLDERS = ("Offense", "Defense", "Special")
_SIDE_ADJECTIVE = {
    "Offense": "Offensive",
    "Defense": "Defensive",
    "Special": "Special-teams",
}
# Category folders use the league's labels (league.toml) — resolved per side.


def _file_side(play: PlayFile) -> str:
    """'Offense' | 'Defense' | 'Special' from the play file's own bytes."""
    if play.is_special_teams:
        return "Special"
    return "Offense" if play.is_offensive else "Defense"


@dataclass(frozen=True, slots=True)
class _FolderInfo:
    """What a play's folder names imply under the league's conventions (empty if
    none do)."""

    side: str | None = None
    category: PlayCategory | None = None
    screen: bool = False
    front: DefensiveFront | None = None


def _category_folder(
    name: str, file_side: str, labels: CategoryLabels
) -> PlayCategory | None:
    """`name` as a league category label — the play's own side first, so a label
    both sides use means the play's side; the other side next, so a play filed
    under the other side's label still gets its wrong-side warning."""
    lookups = [labels.offense_by_label, labels.defense_by_label]
    if file_side == "Defense":
        lookups.reverse()
    for lookup in lookups:
        member = lookup(name)
        if member is not None:
            return member
    return None


def _folder_info(
    parts: Sequence[str], file_side: str, labels: CategoryLabels
) -> _FolderInfo:
    """Read the league's folder conventions from a play's folder names (root→file
    order) for a play whose file says `file_side`. Deeper category folders win;
    unrecognized names are ignored."""
    side = None
    category: PlayCategory | None = None
    screen = False
    front: DefensiveFront | None = None
    for part in parts:
        if part in SIDE_FOLDERS:
            side = part
        elif part == SCREENS_FOLDER:
            side, screen = "Offense", True
        elif part == RNS_FOLDER:
            side, front = "Defense", DefensiveFront.TWO_DL
        elif part[:2] in ("34", "43"):
            side = "Defense"
            front = (
                DefensiveFront.THREE_FOUR
                if part[:2] == "34"
                else DefensiveFront.FOUR_THREE
            )
            member = labels.defense_by_label(part[2:])
            if member is not None:
                category = member
        else:
            member = _category_folder(part, file_side, labels)
            if member is not None:
                side = "Offense" if isinstance(member, OffensiveCategory) else "Defense"
                category = member
    return _FolderInfo(side, category, screen, front)


def _warnings(info: _FolderInfo, play: PlayFile, path: str) -> list[str]:
    """Warning (ending in the play's path) when a recognized league folder
    contradicts the play file: a wrong side, or — when the side matches — a
    category that differs from the folder's. Unrecognized folders never warn.
    A wrong side is reported alone (a cross-side category comparison would be
    noise)."""
    file_side = _file_side(play)
    if info.side and info.side != file_side:
        return [
            f"{_SIDE_ADJECTIVE[file_side]} play in the {info.side.lower()} tree: {path}"
        ]
    file_category = play.category
    if info.category is not None and file_category != info.category:
        return [f"{file_category.long} play in a {info.category.long} folder: {path}"]
    return []


def folder_warnings(
    rel_path: StrPath, play: PlayFile, labels: CategoryLabels
) -> list[str]:
    """Folder/file mismatch warnings for a play at `rel_path` (relative to the
    pool root), with the league's category `labels`; empty when nothing is wrong."""
    rel = PurePath(rel_path)
    info = _folder_info(rel.parent.parts, _file_side(play), labels)
    return _warnings(info, play, rel.as_posix())


class PlayPool:
    """All plays under a root directory, indexed by name and split by side."""

    def __init__(
        self,
        root_dir: StrPath,
        *,
        rules: PlaypoolRules | None = None,
        labels: CategoryLabels | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.rules = rules if rules is not None else PlaypoolRules()
        self.labels = labels if labels is not None else CategoryLabels()
        self.offensive_plays: list[OffensivePlay] = []
        self.defensive_plays: list[DefensivePlay] = []
        self.special_teams_plays: list[SpecialTeamsPlay] = []
        # Kept as well as logged, so a caller like playpool check can print and
        # count them as findings.
        self.issues: list[str] = []
        self._plays_by_name: dict[str, Play] = {}

    def find_by_name(self, name: str) -> Play | None:
        return self._plays_by_name.get(name.upper())

    def _warn(self, message: str) -> None:
        logger.warning(message)
        self.issues.append(message)

    def _register(self, play: Play) -> None:
        key = play.name.upper()
        if key in self._plays_by_name:
            self._warn(f"Duplicate play name '{play.name}'; last loaded wins")
        self._plays_by_name[key] = play

    def _process_play_file(self, file_path: Path) -> None:
        try:
            play_file = read_play(file_path)
        except InvalidPlayFileError as exc:
            self._warn(f"Skipping invalid play file: {exc}")
            return

        name = file_path.stem
        try:
            rel = file_path.relative_to(self.root_dir)
        except ValueError:
            rel = Path(file_path.name)
        info = _folder_info(rel.parent.parts, _file_side(play_file), self.labels)
        for message in _warnings(info, play_file, rel.as_posix()):
            self._warn(message)

        if play_file.is_special_teams:
            self._add(SpecialTeamsPlay(name=name, play_file=play_file))
        elif play_file.is_offensive:
            self._add(self._offensive(name, play_file, screen=info.screen))
        else:
            self._add(
                DefensivePlay(
                    name=name, play_file=play_file, defensive_front=info.front
                )
            )

    def _offensive(
        self, name: str, play_file: PlayFile, *, screen: bool
    ) -> OffensivePlay:
        category = play_file.category
        is_run = category.is_run
        is_pass = category.is_pass
        qb_draw = is_run and self.rules.qb_draw.matches(name)
        rollout = is_pass and self.rules.rollout.matches(name)
        pass_logic: PassLogic | None = None
        if is_pass:
            pass_logic = (
                PassLogic.TIMED
                if self.rules.timed.matches(name)
                else PassLogic.CHECK_RECEIVERS
            )
        return OffensivePlay(
            name=name,
            play_file=play_file,
            screen=screen,
            rollout=rollout,
            qb_draw=qb_draw,
            pass_logic=pass_logic,
        )

    def _add(self, play: Play) -> None:
        if isinstance(play, OffensivePlay):
            self.offensive_plays.append(play)
        elif isinstance(play, DefensivePlay):
            self.defensive_plays.append(play)
        elif isinstance(play, SpecialTeamsPlay):
            self.special_teams_plays.append(play)
        self._register(play)

    def to_dict(self, *, relative_to: StrPath | None = None) -> dict[str, object]:
        """Serialize the pool to a JSON-friendly dict (plays sorted by name)."""
        base = Path(relative_to) if relative_to is not None else None
        return {
            "offensive_plays": [
                p.to_dict(relative_to=base)
                for p in sorted(self.offensive_plays, key=lambda p: p.name)
            ],
            "defensive_plays": [
                p.to_dict(relative_to=base)
                for p in sorted(self.defensive_plays, key=lambda p: p.name)
            ],
            "special_teams_plays": [
                p.to_dict(relative_to=base)
                for p in sorted(self.special_teams_plays, key=lambda p: p.name)
            ],
        }


def read_play_pool(
    root_dir: StrPath,
    *,
    rules: PlaypoolRules | None = None,
    labels: CategoryLabels | None = None,
) -> PlayPool:
    """Scan `root_dir` for .ply files and classify them; invalid files skipped.

    Each play's side and category come from the file itself. With no `rules`,
    filename-derived attributes stay off; with no `labels`, no folder name means
    anything.
    """
    pool = PlayPool(root_dir, rules=rules, labels=labels)
    logger.info("Processing .ply files in '%s'", pool.root_dir)
    for file_path in pool.root_dir.glob("**/*.ply"):
        pool._process_play_file(file_path)
    return pool


__all__ = ["PlayPool", "folder_warnings", "read_play_pool"]
