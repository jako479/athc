"""`athc gameplan find-play` — find plays across .pln normal + custom-special slots."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    category_of,
    collect_files,
    find_in_gameplan,
    is_glob,
)
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import PlayRef, read_gameplan


def _normal_slot_label(index: int) -> str:
    """Game-grid coord for a 0-based normal slot: slot 0 -> `1-1`, slot 63 -> `16-4`."""
    return f"{index // 4 + 1}-{index % 4 + 1}"


def format_hit_line(
    path: Path,
    play_name: str,
    normal_hits: Sequence[tuple[int, PlayRef]],
    special_hits: Sequence[tuple[int, PlayRef]],
) -> str:
    """Compose the one-line hit summary for a single play in a single gameplan.
    Normal hits: `'NAME' found in slots G-C, G-C` (`slot` when there is one).
    Special hits: `'NAME' found in special slot N (long-cat)`; never plural, since a
    play's special category fixes its one special slot."""
    parts: list[str] = []
    if normal_hits:
        section = "slot" if len(normal_hits) == 1 else "slots"
        slots = ", ".join(_normal_slot_label(i) for i, _ in normal_hits)
        parts.append(f"'{play_name}' found in {section} {slots}")
    for number, play in special_hits:
        parts.append(
            f"'{play_name}' found in special slot {number} ({category_of(play).long})"
        )
    return f"{path}: {'; '.join(parts)}"


@gameplan.command(name="find-play", context_settings=CONTEXT_SETTINGS)
@click.argument("args", nargs=-1, required=True, metavar="play... [path]")
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when path is a directory.",
)
@click.pass_context
def find_play(ctx: click.Context, args: tuple[str, ...], recursive: bool) -> None:
    """Find one or more plays by name across .pln files (normal + custom-special slots).

    play... are one or more case-insensitive names; path is a .pln file or a directory
    (top level, or the whole tree with -r), never a wildcard. A single argument is
    a play searched in the current directory; with two or more, the last is always
    the path. Hits show the slot(s); special hits also show the game category.
    Each file missing a play prints 'not found'. Directory/tree: a per-play summary
    is appended.
    """
    if len(args) == 1:
        play_names, path = list(args), "."
    else:
        *play_names, path = args
    if is_glob(path):
        raise click.UsageError(
            "path must be a .pln file or a directory; wildcards are not supported"
        )

    collected = collect_files([path], suffix=".pln", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    single_path = not Path(path).is_dir()  # one file, found or not: no tally
    instances_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    files_hit_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    failed = len(collected.errors)

    for file in collected.files:
        try:
            gp = read_gameplan(str(file))
        except (AthcError, OSError) as error:
            console.fail(str(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(file))
            failed += 1
            continue
        for play_name in play_names:
            normal_hits, special_hits = find_in_gameplan(gp, play_name)
            hit_count = len(normal_hits) + len(special_hits)
            if hit_count > 0:
                instances_per_play[play_name] += hit_count
                files_hit_per_play[play_name] += 1
                console.result(
                    format_hit_line(file, play_name, normal_hits, special_hits)
                )
            else:
                console.result(f"{file}: '{play_name}' not found")

    if not single_path:
        console.print()
        for play_name in play_names:
            console.result(
                f"'{play_name}': found {instances_per_play[play_name]} instance(s) "
                f"in {files_hit_per_play[play_name]} gameplan(s)"
            )

    if failed:
        ctx.exit(2)
    # Like grep: success when any play was found anywhere.
    ctx.exit(0 if any(c > 0 for c in files_hit_per_play.values()) else 1)
