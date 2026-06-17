"""Build a PlayPool: walk a play tree, classify each .ply, index by name.

Side and pool category come from the folder layout (fixed in code); the
filename-derived flags/enums (`rollout`, `qb_draw`, `pass_logic`) come from the
league's filename filters in `PlaypoolRules`.
"""

from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path

from athc.fbpro98_play import InvalidPlayFileError, PlayFile, read_play
from athc.playpool.records import (
    PASS_CATEGORIES,
    RUN_CATEGORIES,
    DefensiveFront,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassLogic,
    PlayRecord,
    SpecialTeamsPlayRecord,
)
from athc.playpool.rules import PlaypoolRules

StrPath = str | PathLike[str]

logger = logging.getLogger(__name__)


class PlayPool:
    """All plays under a root directory, indexed by name and split by side."""

    def __init__(
        self, root_dir: StrPath, *, rules: PlaypoolRules | None = None
    ) -> None:
        self.root_dir = Path(root_dir)
        self.rules = rules if rules is not None else PlaypoolRules()
        self.offensive_plays: list[OffensivePlayRecord] = []
        self.defensive_plays: list[DefensivePlayRecord] = []
        self.special_teams_plays: list[SpecialTeamsPlayRecord] = []
        self._plays_by_name: dict[str, PlayRecord] = {}

    def find_by_name(self, name: str) -> PlayRecord | None:
        return self._plays_by_name.get(name.upper())

    def _register(self, play: PlayRecord) -> None:
        key = play.name.upper()
        if key in self._plays_by_name:
            logger.warning("Duplicate play name '%s'; last loaded wins", play.name)
        self._plays_by_name[key] = play

    def _process_play_file(self, file_path: Path) -> None:
        try:
            play_file = read_play(file_path)
        except InvalidPlayFileError as exc:
            logger.warning("Skipping invalid play file: %s", exc)
            return

        name = file_path.stem
        parent = file_path.parent.name
        grandparent = file_path.parent.parent.name
        side = self._side_for(file_path)
        if side == "Offense":
            self._process_offensive(name, parent, grandparent, play_file)
        elif side == "Defense":
            self._process_defensive(name, parent, grandparent, play_file)
        elif side == "Special":
            self._process_special(name, play_file)
        else:
            logger.warning(
                "Skipping play outside Offense/Defense/Special: %s", file_path
            )

    def _side_for(self, file_path: Path) -> str | None:
        """Side from the first Offense/Defense/Special ancestor folder, else None."""
        try:
            folders = file_path.relative_to(self.root_dir).parent.parts
        except ValueError:
            folders = file_path.parent.parts
        for side in ("Offense", "Defense", "Special"):
            if side in folders:
                return side
        return None

    def _process_offensive(
        self, name: str, parent: str, grandparent: str, play_file: PlayFile
    ) -> None:
        screen = parent == "Screens"
        pool_category = grandparent if screen else parent
        is_pass = pool_category in PASS_CATEGORIES
        is_run = pool_category in RUN_CATEGORIES

        qb_draw = is_run and self.rules.qb_draw.matches(name)
        rollout = is_pass and self.rules.rollout.matches(name)
        pass_logic: PassLogic | None = None
        if is_pass:
            timed = self.rules.timed.matches(name)
            pass_logic = PassLogic.TIMED if timed else PassLogic.CHECK_RECEIVERS

        play = OffensivePlayRecord(
            name=name,
            play_file=play_file,
            pool_category=pool_category,
            screen=screen,
            rollout=rollout,
            qb_draw=qb_draw,
            pass_logic=pass_logic,
        )
        self.offensive_plays.append(play)
        self._register(play)

    def _process_defensive(
        self, name: str, parent: str, grandparent: str, play_file: PlayFile
    ) -> None:
        front: DefensiveFront | None = None
        if grandparent == "R&SDefs":
            pool_category = parent
            front = DefensiveFront.TWO_DL
        elif parent.startswith("34"):
            pool_category = parent[2:]
            front = DefensiveFront.THREE_FOUR
        elif parent.startswith("43"):
            pool_category = parent[2:]
            front = DefensiveFront.FOUR_THREE
        else:
            pool_category = parent

        play = DefensivePlayRecord(
            name=name,
            play_file=play_file,
            pool_category=pool_category,
            defensive_front=front,
        )
        self.defensive_plays.append(play)
        self._register(play)

    def _process_special(self, name: str, play_file: PlayFile) -> None:
        play = SpecialTeamsPlayRecord(name=name, play_file=play_file)
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
    root_dir: StrPath, *, rules: PlaypoolRules | None = None
) -> PlayPool:
    """Scan `root_dir` for .ply files and classify them; invalid files skipped.

    With no `rules`, filename-derived attributes stay off (folder classification
    still applies).
    """
    pool = PlayPool(root_dir, rules=rules)
    logger.info("Processing .ply files in '%s'", pool.root_dir)
    for file_path in pool.root_dir.glob("**/*.ply"):
        pool._process_play_file(file_path)
    return pool


__all__ = ["PlayPool", "read_play_pool"]
