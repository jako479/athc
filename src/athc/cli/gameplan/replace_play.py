"""`athc gameplan replace-play` — swap one play for another across .pln files."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import click

from athc.cli import league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    build_pool,
    collect_files,
    find_in_gameplan,
    make_backup,
)
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    InvalidGamePlanError,
    PlayRef,
    read_gameplan,
    write_gameplan,
)
from athc.fbpro98_play import resolve_category
from athc.gameplan.config import ConfigFileError, load_config
from athc.gameplan.writer import build_custom_play

Hits = list[tuple[int, PlayRef]]

PROG = "athc gameplan replace-play"
logger = logging.getLogger(__name__)


def _short(play: PlayRef) -> str:
    """Short game-category label for a slot's play (e.g. `RL`, `Field Goal/PAT`)."""
    return resolve_category(
        play.play_category, play.special_category, play.user_category
    ).short


def _slot_label(index: int) -> str:
    """Game-grid coord for a 0-based normal slot: 0 -> `1-1`, 63 -> `16-4`."""
    return f"{index // 4 + 1}-{index % 4 + 1}"


def format_replacement_lines(
    path: Path, normal_hits: Hits, special_hits: Hits, entry: CustomPlayRef
) -> list[str]:
    """Lines for the replaced play. Normal hits collapse to one line, slots bracketed
    in order at the end: `<file>: 'OLD' (cat) replaced with 'NEW' (cat) [1-3][4-2]`
    (a play can fill many normal slots). Special: `<file>: Replaced 'OLD' (cat) in
    special slot N with 'NEW' (cat)` (a play fills only one special slot)."""
    new = f"'{entry.name}' ({_short(entry)})"
    lines: list[str] = []
    if normal_hits:
        slots = "".join(f"[{_slot_label(i)}]" for i, _ in normal_hits)
        old = normal_hits[0][1]  # same play in every hit; first is representative
        old_desc = f"'{old.name}' ({_short(old)})"
        lines.append(f"{path}: {old_desc} replaced with {new} {slots}")
    lines += [
        f"{path}: Replaced '{old.name}' ({_short(old)}) in special slot {n} with {new}"
        for n, old in special_hits
    ]
    return lines


def replace_in_gameplan(
    gp: GamePlan, target: str, entry: CustomPlayRef
) -> tuple[GamePlan, Hits, Hits]:
    """Replace every occurrence of `target` (case-insensitive, across normal +
    custom-special slots) with `entry`. Returns `(updated, normal_hits, special_hits)`;
    no hits leaves the gameplan unchanged. The GamePlan model validates the result,
    raising ValueError when `entry` is wrong for a slot (wrong side, or a
    special-category that does not match the slot)."""
    normal_hits, special_hits = find_in_gameplan(gp, target)
    if not normal_hits and not special_hits:
        return gp, normal_hits, special_hits
    normals = list(gp.normal_plays)
    for i, _ in normal_hits:
        normals[i] = entry
    specials = list(gp.special_plays)
    for category, _ in special_hits:
        specials[(category - 1) * 2] = entry  # custom slot for category = even index
    updated = replace(gp, normal_plays=tuple(normals), special_plays=tuple(specials))
    return updated, normal_hits, special_hits


def _replace_one(
    path: Path, target: str, entry: CustomPlayRef, *, no_backup: bool
) -> tuple[str, list[str], int]:
    """Apply the replacement to one .pln. Returns `(status, lines, count)`; status is
    'updated', 'absent', or 'failed', and `lines` are the stdout lines for it."""
    try:
        gp = read_gameplan(str(path))
        updated, normal_hits, special_hits = replace_in_gameplan(gp, target, entry)
    except (OSError, InvalidGamePlanError, ValueError) as error:
        return "failed", [f"{path}: failed ({error})"], 0
    count = len(normal_hits) + len(special_hits)
    if count == 0:
        return "absent", [], 0
    backup = None if no_backup else make_backup(path)
    write_gameplan(updated, path)
    lines = format_replacement_lines(path, normal_hits, special_hits, entry)
    if backup is not None:
        lines.append(f"{path}: backup {backup.name}")
    return "updated", lines, count


@gameplan.command(name="replace-play")
@click.argument("play")
@click.argument("replacement")
@click.argument("path", type=click.Path(path_type=Path))
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when PATH is a directory.",
)
@click.option(
    "--no-backup", is_flag=True, help="Do not create a .bak copy before writing."
)
@click.option(
    "--play-path",
    "play_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Play pool directory (overrides the league's PlayPath).",
)
@league_option
@click.pass_context
def replace_play(
    ctx: click.Context,
    play: str,
    replacement: str,
    path: Path,
    recursive: bool,
    no_backup: bool,
    play_path: Path | None,
    league: str | None,
) -> None:
    """Replace every instance of PLAY with REPLACEMENT across .pln files.

    PLAY and REPLACEMENT are single, case-insensitive names (unlike find-play, only
    one PLAY); PATH is a .pln file or a directory (top level, or the whole tree with
    -r). REPLACEMENT must exist in the play pool (--play-path or the league's
    PlayPath); PLAY need not (it may already be gone). Normal and custom-special slots
    are searched. A timestamped .bak is written next to each updated file (unless
    --no-backup). Rules are not checked; run `check` afterward to validate.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # Pool needs no playpool rules: replace-play uses each play's category bytes, not
    # the filename-derived attributes those rules add.
    try:
        config = load_config(league, play_path=play_path)
    except (ConfigFileError, ValueError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)

    pool = build_pool(config.play_path, None, prog=PROG, logger=logger)
    if pool is None:
        ctx.exit(2)

    record = pool.find_by_name(replacement)
    if record is None:
        logger.error(
            "%s: replacement play '%s' not found in the play pool", PROG, replacement
        )
        ctx.exit(2)
    entry = build_custom_play(record, pool.root_dir)

    files, path_errors = collect_files([str(path)], suffix=".pln", recursive=recursive)
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    single_file = Path(path).is_file()
    updated = failed = replaced_total = 0
    for file in files:
        status, lines, count = _replace_one(file, play, entry, no_backup=no_backup)
        for line in lines:
            click.echo(line)
        if status == "updated":
            updated += 1
            replaced_total += count
        elif status == "failed":
            failed += 1
        elif single_file:  # absent in single-file mode: a find-play-style miss
            click.echo(f"{file}: '{play}' not found")

    if not single_file:
        click.echo()
        click.echo(
            f"'{play}' -> '{replacement}': replaced {replaced_total} instance(s) "
            f"in {updated} gameplan(s); {failed} failed."
        )

    if failed:
        ctx.exit(1)
    ctx.exit(0 if replaced_total > 0 else 1)
