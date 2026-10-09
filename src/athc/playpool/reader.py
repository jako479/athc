"""Build a PlayPool: walk a tree, classify each .ply from its file, index by name.

Side and category come from the parsed play file, so any folder layout works —
a league tree, an arbitrary tree, or a flat directory. Folders are optional: a
recognized folder adds an attribute the bytes can't carry (offense `screen`,
defense `defensive_front`) and lets the reader warn (with the play's path) when
a play sits in a folder that contradicts its file. Category folders are named by
the league's labels (`CategoryLabels`, from league.toml); the filename-derived
flags (`rollout`, `qb_draw`, `pass_logic`) come from the league's `PlaypoolRules`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath

from athc.fbpro98_play import (
    CategoryLabels,
    InvalidPlayFileError,
    OffensiveCategory,
    PlayCategory,
    PlayFile,
    read_play,
)
from athc.playpool.model import (
    DefensiveFront,
    DefensivePlay,
    OffensivePlay,
    PassLogic,
    Play,
    PlayPool,
    SpecialTeamsPlay,
)
from athc.playpool.rules import (
    SECTION_QB_RUN,
    SECTION_ROLLOUT,
    SECTION_TIMED,
    FilenameFilter,
    PlaypoolRules,
    StrPath,
)

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


def _warn(pool: PlayPool, message: str) -> None:
    """Keep a problem on the pool as an issue; the reader never logs."""
    pool.issues.append(message)


def _add(
    pool: PlayPool, play: OffensivePlay | DefensivePlay | SpecialTeamsPlay
) -> None:
    if pool.find_by_name(play.name) is not None:
        _warn(pool, f"Duplicate play name '{play.name}'; last loaded wins")
    pool.add(play)


def _offensive(
    rules: PlaypoolRules, name: str, play_file: PlayFile, *, screen: bool
) -> OffensivePlay:
    category = play_file.category
    is_run = category.is_run
    is_pass = category.is_pass
    qb_draw = is_run and rules.qb_draw.matches(name)
    rollout = is_pass and rules.rollout.matches(name)
    pass_logic: PassLogic | None = None
    if is_pass:
        pass_logic = (
            PassLogic.TIMED if rules.timed.matches(name) else PassLogic.CHECK_RECEIVERS
        )
    return OffensivePlay(
        name=name,
        play_file=play_file,
        screen=screen,
        rollout=rollout,
        qb_draw=qb_draw,
        pass_logic=pass_logic,
    )


def _read_play_file(
    pool: PlayPool, file_path: Path, rules: PlaypoolRules, labels: CategoryLabels
) -> None:
    """Parse one .ply, classify it from its file and folders, and add it to
    `pool`; an invalid or unreadable file is skipped and noted as an issue."""
    try:
        play_file = read_play(file_path)
    except InvalidPlayFileError as exc:
        _warn(pool, f"Skipping invalid play file: {exc}")
        return
    except OSError as exc:
        _warn(pool, f"Skipping unreadable play file: {exc}")
        return

    name = file_path.stem
    rel = file_path.relative_to(pool.root_dir)
    info = _folder_info(rel.parent.parts, _file_side(play_file), labels)
    for message in _warnings(info, play_file, rel.as_posix()):
        _warn(pool, message)

    if play_file.is_special_teams:
        _add(pool, SpecialTeamsPlay(name=name, play_file=play_file))
    elif play_file.is_offensive:
        _add(pool, _offensive(rules, name, play_file, screen=info.screen))
    else:
        _add(
            pool,
            DefensivePlay(name=name, play_file=play_file, defensive_front=info.front),
        )


def read_play_pool(
    root_dir: StrPath,
    *,
    rules: PlaypoolRules | None = None,
    labels: CategoryLabels | None = None,
) -> PlayPool:
    """Scan `root_dir` for .ply files, in sorted path order, and classify them;
    invalid and unreadable files are skipped with a warning. With duplicate
    names the last in that order wins.

    Each play's side and category come from the file itself. With no `rules`,
    filename-derived attributes stay off; with no `labels`, no folder name means
    a category (the fixed side, screen and front folders still apply).
    """
    pool = PlayPool(root_dir)
    rules = rules if rules is not None else PlaypoolRules()
    labels = labels if labels is not None else CategoryLabels()
    for file_path in sorted(pool.root_dir.glob("**/*.ply")):
        _read_play_file(pool, file_path, rules, labels)
    return pool


def rule_warnings(pool: PlayPool, rules: PlaypoolRules) -> list[str]:
    """What is wrong with the exact play names a rules file lists under `include`
    / `exclude`, checked against `pool`: a name not in the pool; a name whose
    play the section cannot apply to (a run play under a pass attribute, a pass
    play under [QBRun], a defensive or special-teams play anywhere); a name under
    both `include` and `exclude` of one section (the veto wins). One line each,
    in section order then by name. The reader applies the rules regardless; the
    patterns (`suffix_*`, `regex_*`) are not checked."""
    messages: list[str] = []
    sections: tuple[tuple[str, FilenameFilter, bool], ...] = (
        (SECTION_TIMED, rules.timed, False),
        (SECTION_ROLLOUT, rules.rollout, False),
        (SECTION_QB_RUN, rules.qb_draw, True),
    )
    for section, filter_, needs_run in sections:
        both = filter_.include & filter_.exclude
        for name in sorted(both):
            messages.append(
                f"[{section}] '{name}' is in both include and exclude; exclude wins"
            )
        for key, names in (("include", filter_.include), ("exclude", filter_.exclude)):
            for name in sorted(names - both):
                play = pool.find_by_name(name)
                if play is None:
                    messages.append(
                        f"[{section}] {key} '{name}' is not in the play pool"
                    )
                    continue
                kind = _wrong_kind(play, needs_run)
                if kind is not None:
                    messages.append(
                        f"[{section}] {key} '{name}' is a {kind} play; it has no effect"
                    )
    return messages


def _wrong_kind(play: Play, needs_run: bool) -> str | None:
    """What `play` is when a section needing a run (or pass) play cannot apply
    to it; None when it can."""
    if isinstance(play, SpecialTeamsPlay):
        return "special-teams"
    if isinstance(play, DefensivePlay):
        return "defensive"
    category = play.category
    if needs_run and not category.is_run:
        return "pass" if category.is_pass else category.long
    if not needs_run and not category.is_pass:
        return "run" if category.is_run else category.long
    return None


__all__ = ["folder_warnings", "read_play_pool", "rule_warnings"]
