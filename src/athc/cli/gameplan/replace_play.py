"""`athc gameplan replace-play` — swap one play for another across .pln files."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    build_pool,
    category_of,
    collect_files,
    find_in_gameplan,
)
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    read_gameplan,
    write_gameplan,
)
from athc.fbpro98_play import CategoryLabels
from athc.gameplan.config import load_config
from athc.gameplan.writer import build_custom_play

Hits = list[tuple[int, PlayRef]]


def _label(play: PlayRef, labels: CategoryLabels) -> str:
    """The league's label for a slot's play category (e.g. `RL`); game name when
    the league has none (`Field Goal/PAT`)."""
    return labels.label(category_of(play))


def _slot_label(index: int) -> str:
    """Game-grid coord for a 0-based normal slot: 0 -> `1-1`, 63 -> `16-4`."""
    return f"{index // 4 + 1}-{index % 4 + 1}"


def format_replacement_lines(
    path: Path,
    normal_hits: Hits,
    special_hits: Hits,
    entry: CustomPlayRef,
    labels: CategoryLabels,
) -> list[str]:
    """Lines for the replaced play. Normal hits collapse to one line, slots bracketed
    in order at the end: `<file>: 'OLD' (cat) replaced with 'NEW' (cat) [1-3][4-2]`
    (a play can fill many normal slots). Special: `<file>: Replaced 'OLD' (cat) in
    special slot N with 'NEW' (cat)` (a play fills only one special slot)."""
    new = f"'{entry.name}' ({_label(entry, labels)})"
    lines: list[str] = []
    if normal_hits:
        slots = "".join(f"[{_slot_label(i)}]" for i, _ in normal_hits)
        old = normal_hits[0][1]  # same play in every hit; first is representative
        old_desc = f"'{old.name}' ({_label(old, labels)})"
        lines.append(f"{path}: {old_desc} replaced with {new} {slots}")
    lines += [
        f"{path}: Replaced '{old.name}' ({_label(old, labels)}) in special slot {n} "
        f"with {new}"
        for n, old in special_hits
    ]
    return lines


def replace_in_gameplan(
    gp: GamePlan, target: str, entry: CustomPlayRef, path: Path | None = None
) -> tuple[GamePlan, Hits, Hits]:
    """Replace every occurrence of `target` (case-insensitive, across normal +
    custom-special slots) with `entry`. Returns `(updated, normal_hits, special_hits)`;
    no hits leaves the gameplan unchanged. The GamePlan model validates the
    result; AthcError, naming `path` when given, when `entry` is wrong for a
    slot (wrong side, or a special-category that does not match the slot)."""
    normal_hits, special_hits = find_in_gameplan(gp, target)
    if not normal_hits and not special_hits:
        return gp, normal_hits, special_hits
    normals = list(gp.normal_plays)
    for i, _ in normal_hits:
        normals[i] = entry
    specials = list(gp.special_plays)
    for category, _ in special_hits:
        specials[category - 1] = replace(specials[category - 1], custom=entry)
    try:
        updated = replace(
            gp, normal_plays=tuple(normals), special_plays=tuple(specials)
        )
    except ValueError as error:  # the model refused the entry for a slot
        raise AthcError(str(error), path) from error
    return updated, normal_hits, special_hits


@gameplan.command(name="replace-play", context_settings=CONTEXT_SETTINGS)
@click.argument("play", metavar="play")
@click.argument("replacement", metavar="replacement")
@click.argument("path", metavar="path", type=click.Path(path_type=Path))
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when path is a directory.",
)
@league_option
@click.pass_context
def replace_play(
    ctx: click.Context,
    play: str,
    replacement: str,
    path: Path,
    recursive: bool,
    league: str | None,
) -> None:
    """Replace every instance of play with replacement across .pln files.

    play and replacement are single, case-insensitive names (unlike find-play, only
    one play); path is a .pln file or a directory (top level, or the whole tree with
    -r). replacement must exist in the league's play pool; play need not (it may
    already be gone). Normal and custom-special slots are searched. Rules are not
    checked; run `check` afterward to validate.
    """
    # Pool needs no playpool rules: replace-play uses each play's category bytes, not
    # the filename-derived attributes those rules add.
    config = load_config(league, rule_files=())
    pool = build_pool(config.play_path, None, config.categories)
    record = pool.find_by_name(replacement)
    if record is None:
        raise AthcError(f"replacement play '{replacement}' not found in the play pool")
    entry = build_custom_play(record, pool.root_dir)

    collected = collect_files([str(path)], suffix=".pln", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    single_path = not Path(path).is_dir()  # one file, found or not: no tally
    updated = replaced_total = 0
    failed = len(collected.errors)
    for file in collected.files:
        try:
            gp = read_gameplan(str(file))
            new_gp, normal_hits, special_hits = replace_in_gameplan(
                gp, play, entry, file
            )
            count = len(normal_hits) + len(special_hits)
            if count:
                write_gameplan(new_gp, file)
        except (AthcError, OSError) as error:
            console.fail(str(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(file))
            failed += 1
            continue
        if count == 0:
            if single_path:  # a find-play-style miss; silent in a directory
                console.result(f"{file}: '{play}' not found")
            continue
        updated += 1
        replaced_total += count
        for line in format_replacement_lines(
            file, normal_hits, special_hits, entry, config.categories
        ):
            console.ok(line)

    if not single_path:
        console.print()
        console.result(
            f"'{play}' -> '{replacement}': replaced {replaced_total} instance(s) "
            f"in {updated} gameplan(s), {failed} failed"
        )
    ctx.exit(2 if failed else 1 if replaced_total == 0 else 0)
