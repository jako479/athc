"""Build a PlayPool: walk a tree, classify each .ply from its file, index by name.

Side, category and the play attributes (rollout, QB run, pass logic, defensive
front) come from the parsed play file, so any folder layout works — a league
tree, an arbitrary tree, or a flat directory. Folders are optional: a recognized
folder adds the one attribute the bytes can't carry (offense `screen`) and lets
the reader warn (with the play's path) when a play sits in a folder that
contradicts its file. Category folders are named by the league's labels
(`CategoryLabels`, from league.toml).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath

from athc.errors import error_line
from athc.fbpro98_play import (
    CategoryLabels,
    InvalidPlayFileError,
    OffensiveCategory,
    PlayCategory,
    PlayFile,
    read_play,
)
from athc.playpool.model import (
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    PlayPool,
    SpecialPlay,
    StrPath,
)

# A pass is a rollout when its QB gets beyond this many units (90 = 1 yard) outside the
# outermost offensive lineman on that side, at his spot at the snap, before he
# throws.
ROLLOUT_MARGIN = 100

# ── League folder conventions (optional; only these names mean anything). The
# side, screen and front folder names are fixed; category folders are named by
# the league's labels. ────────────────────────────────────────────────────────
SCREENS_FOLDER = "Screens"  # offense pass screen
RNS_FOLDER = "R&SDefs"  # Run-and-Shoot defenses (a defense folder)
SIDE_FOLDERS = ("Offense", "Defense", "Special")
_SIDE_ADJECTIVE = {
    "Offense": "Offensive",
    "Defense": "Defensive",
    "Special": "Special",
}
# Category folders use the league's labels (league.toml) — resolved per side.


def _file_side(play: PlayFile) -> str:
    """'Offense' | 'Defense' | 'Special' from the play file's own bytes."""
    if play.is_special:
        return "Special"
    return "Offense" if play.is_offensive else "Defense"


@dataclass(frozen=True, slots=True)
class _FolderInfo:
    """What a play's folder names imply under the league's conventions (empty if
    none do)."""

    side: str | None = None
    category: PlayCategory | None = None
    screen: bool = False


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
    for part in parts:
        if part in SIDE_FOLDERS:
            side = part
        elif part == SCREENS_FOLDER:
            side, screen = "Offense", True
        elif part == RNS_FOLDER:
            side = "Defense"
        elif (
            part[:2] in ("34", "43")
            and (front := labels.defense_by_label(part[2:])) is not None
        ):  # a front, then a defense label
            side, category = "Defense", front
        else:
            member = _category_folder(part, file_side, labels)
            if member is not None:
                side = "Offense" if isinstance(member, OffensiveCategory) else "Defense"
                category = member
    return _FolderInfo(side, category, screen)


def _warnings(info: _FolderInfo, play: PlayFile, path: str) -> list[str]:
    """Warning (starting with the play's path) when a recognized league folder
    contradicts the play file: a wrong side, or — when the side matches — a
    category that differs from the folder's. Unrecognized folders never warn.
    A wrong side is reported alone (a cross-side category comparison would be
    noise)."""
    file_side = _file_side(play)
    if info.side and info.side != file_side:
        side = _SIDE_ADJECTIVE[file_side]
        return [f"{path}: {side} play in the {info.side.lower()} tree."]
    file_category = play.category
    if info.category is not None and file_category != info.category:
        return [f"{path}: {file_category.long} play in a {info.category.long} folder."]
    return []


def folder_warnings(
    rel_path: StrPath, play: PlayFile, labels: CategoryLabels
) -> list[str]:
    """Folder/file mismatch warnings for a play at `rel_path` (relative to the
    pool root), with the league's category `labels`; empty when nothing is wrong."""
    rel = PurePath(rel_path)
    info = _folder_info(rel.parent.parts, _file_side(play), labels)
    return _warnings(info, play, rel.as_posix())


def _warn(pool: PlayPool, message: str) -> None:
    """Keep a problem on the pool as an issue; the reader never logs."""
    pool.issues.append(message)


def _add(pool: PlayPool, play: OffensivePlay | DefensivePlay | SpecialPlay) -> None:
    if pool.find_by_name(play.name) is not None:
        _warn(pool, f"Duplicate play name '{play.name}'. The last one loaded wins.")
    pool.add(play)


def _offensive(name: str, play_file: PlayFile, *, screen: bool) -> OffensivePlay:
    """An offensive record; the play's category keeps QB run to run plays and
    screen, rollout and pass logic to pass plays."""
    category = play_file.category
    is_run = category.is_run
    is_pass = category.is_pass
    qb_run = is_run and play_file.is_qb_run
    rollout = is_pass and play_file.is_rollout(ROLLOUT_MARGIN)
    pass_logic: PassLogic | None = None
    if is_pass:
        pass_logic = (
            PassLogic.TIMED if play_file.is_timed_pass else PassLogic.CHECK_RECEIVERS
        )
    return OffensivePlay(
        name=name,
        play_file=play_file,
        screen=is_pass and screen,
        rollout=rollout,
        qb_run=qb_run,
        pass_logic=pass_logic,
    )


def _read_play_file(pool: PlayPool, file_path: Path, labels: CategoryLabels) -> None:
    """Parse one .ply, classify it from its file and folders, and add it to
    `pool`; an invalid or unreadable file is skipped and noted as an issue."""
    try:
        play_file = read_play(file_path)
    except InvalidPlayFileError as exc:
        _warn(pool, f"{exc} Skipped.")
        return
    except OSError as exc:
        _warn(pool, f"{error_line(exc)} Skipped.")
        return

    name = file_path.stem
    rel = file_path.relative_to(pool.root_dir)
    info = _folder_info(rel.parent.parts, _file_side(play_file), labels)
    for message in _warnings(info, play_file, rel.as_posix()):
        _warn(pool, message)

    if play_file.is_special:
        _add(pool, SpecialPlay(name=name, play_file=play_file))
    elif play_file.is_offensive:
        _add(pool, _offensive(name, play_file, screen=info.screen))
    else:
        _add(
            pool,
            DefensivePlay(
                name=name,
                play_file=play_file,
                defensive_front=play_file.defensive_front,
            ),
        )


def read_play_pool(
    root_dir: StrPath, *, labels: CategoryLabels | None = None
) -> PlayPool:
    """Scan `root_dir` for .ply files, in sorted path order, and classify them;
    invalid and unreadable files are skipped with a warning. With duplicate
    names the last in that order wins.

    Each play's side, category and attributes come from the file itself. With
    no `labels`, no folder name means a category (the fixed side and screen
    folders still apply).
    """
    pool = PlayPool(root_dir)
    labels = labels if labels is not None else CategoryLabels()
    for file_path in sorted(pool.root_dir.glob("**/*.ply")):
        _read_play_file(pool, file_path, labels)
    return pool


__all__ = ["ROLLOUT_MARGIN", "folder_warnings", "read_play_pool"]
