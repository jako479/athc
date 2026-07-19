"""`athc gameplan find-play` — find plays across .pln normal + custom-special slots."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import collect_files, find_in_gameplan
from athc.fbpro98_gameplan import InvalidGamePlanError, PlayRef, read_gameplan
from athc.fbpro98_play import resolve_category

PROG = "athc gameplan find-play"
logger = logging.getLogger(__name__)


def _normal_slot_label(index: int) -> str:
    """Game-grid coord for a 0-based normal slot: slot 0 -> `1-1`, slot 63 -> `16-4`."""
    return f"{index // 4 + 1}-{index % 4 + 1}"


def _join_slots(labels: Sequence[str]) -> str:
    """Join slot labels in English: 1 -> `A`, 2 -> `A and B`, 3+ -> `A, B, and C`."""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _category_name(play: PlayRef) -> str:
    """Long game category name for a play, from its category bytes."""
    return resolve_category(
        play.play_category, play.special_category, play.user_category
    ).long


def _short_category(play: PlayRef) -> str:
    """Short game category label for a play (e.g. `RL`), from its category bytes."""
    return resolve_category(
        play.play_category, play.special_category, play.user_category
    ).short


def format_hit_line(
    path: Path,
    play_name: str,
    normal_hits: Sequence[tuple[int, PlayRef]],
    special_hits: Sequence[tuple[int, PlayRef]],
) -> str:
    """Compose the one-line hit summary for a single play in a single gameplan.
    Normal hits: `'NAME' (short-cat) [G-C][G-C]` (slots bracketed at the end).
    Special hits keep the long category and `in special slot N` wording."""
    parts: list[str] = []
    if normal_hits:
        slots = "".join(f"[{_normal_slot_label(i)}]" for i, _ in normal_hits)
        parts.append(f"'{play_name}' ({_short_category(normal_hits[0][1])}) {slots}")
    if special_hits:
        labels = [str(n) for n, _ in special_hits]
        section = "special slot" if len(labels) == 1 else "special slots"
        category = _category_name(special_hits[0][1])
        parts.append(f"'{play_name}' ({category}) in {section} {_join_slots(labels)}")
    return f"{path}: {'; '.join(parts)}"


@gameplan.command(name="find-play")
@click.argument("args", nargs=-1, required=True, metavar="PLAY... PATH")
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when PATH is a directory.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="In directory/tree mode, also report files missing a requested play.",
)
@click.pass_context
def find_play(
    ctx: click.Context, args: tuple[str, ...], recursive: bool, verbose: bool
) -> None:
    """Find one or more plays by name across .pln files (normal + custom-special slots).

    PLAY... are one or more case-insensitive names; PATH is a .pln file or a directory
    (top level, or the whole tree with -r). Hits show the slot(s) and game category.
    Single file: a miss prints 'not found'. Directory/tree: misses are silent unless
    --verbose, and a per-play summary is appended.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(args) < 2:
        raise click.UsageError("need one or more PLAY names followed by a PATH")
    *play_names, path = args

    files, path_errors = collect_files([path], suffix=".pln", recursive=recursive)
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    single_file = Path(path).is_file()
    instances_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    files_hit_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    io_errors = 0

    for file in files:
        try:
            gp = read_gameplan(str(file))
        except (OSError, InvalidGamePlanError, ValueError) as error:
            click.echo(f"{file}: ERROR: {error}")
            io_errors += 1
            continue
        for play_name in play_names:
            normal_hits, special_hits = find_in_gameplan(gp, play_name)
            hit_count = len(normal_hits) + len(special_hits)
            if hit_count > 0:
                instances_per_play[play_name] += hit_count
                files_hit_per_play[play_name] += 1
                click.echo(format_hit_line(file, play_name, normal_hits, special_hits))
            elif single_file or verbose:
                click.echo(f"{file}: '{play_name}' not found")

    if not single_file:
        click.echo()
        for play_name in play_names:
            click.echo(
                f"'{play_name}': Found {instances_per_play[play_name]} instance(s) "
                f"in {files_hit_per_play[play_name]} gameplan(s)."
            )

    if io_errors or path_errors:
        ctx.exit(2)
    ctx.exit(0 if all(c > 0 for c in files_hit_per_play.values()) else 1)
