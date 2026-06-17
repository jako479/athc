"""`athc gameplan find-play` — find plays across .pln normal + custom-special slots."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import collect_files
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, Play, read_gameplan
from athc.fbpro98_play.model import (
    DEFENSIVE_CATEGORIES,
    OFFENSIVE_CATEGORIES,
    SPECIAL_TEAMS_DEFENSIVE_CATEGORIES,
    SPECIAL_TEAMS_OFFENSIVE_CATEGORIES,
)

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


def _is_offense_side(play: Play) -> bool:
    """Bit 0 of `play_category`: odd = offense / kicking, even = defense / receiving."""
    return play.play_category % 2 == 1


def _normal_category_name(play: Play) -> str | None:
    """Game category for a normal play; bits 7-6 of `user_category` are intra-category
    variation and are masked off before the lookup. None for unmapped codes."""
    table = OFFENSIVE_CATEGORIES if _is_offense_side(play) else DEFENSIVE_CATEGORIES
    return table.get(play.user_category & 0x3F)


def _special_category_name(play: Play) -> str | None:
    """Game category for a custom special play (e.g. `Field Goal/PAT`)."""
    table = (
        SPECIAL_TEAMS_OFFENSIVE_CATEGORIES
        if _is_offense_side(play)
        else SPECIAL_TEAMS_DEFENSIVE_CATEGORIES
    )
    return table.get(play.special_category)


def find_in_gameplan(
    gp: GamePlan, play_name: str
) -> tuple[list[tuple[int, Play]], list[tuple[int, Play]]]:
    """Case-insensitive name match -> `(normal_hits, special_hits)`. Stock specials and
    clock plays are skipped. Special slot numbers are 1-based."""
    target = play_name.casefold()
    normal_hits: list[tuple[int, Play]] = [
        (i, p)
        for i, p in enumerate(gp.normal_plays)
        if p is not None and p.name.casefold() == target
    ]
    special_hits: list[tuple[int, Play]] = [
        (i + 1, p)
        for i, p in enumerate(gp.custom_special_plays)
        if p is not None and p.name.casefold() == target
    ]
    return normal_hits, special_hits


def format_hit_line(
    path: Path,
    play_name: str,
    normal_hits: Sequence[tuple[int, Play]],
    special_hits: Sequence[tuple[int, Play]],
) -> str:
    """Compose the one-line hit summary for a single play in a single gameplan."""
    parts: list[str] = []
    if normal_hits:
        labels = [_normal_slot_label(i) for i, _ in normal_hits]
        section = "normal slot" if len(labels) == 1 else "normal slots"
        category = _normal_category_name(normal_hits[0][1])
        suffix = f" ({category})" if category else ""
        parts.append(f"'{play_name}'{suffix} in {section} {_join_slots(labels)}")
    if special_hits:
        labels = [str(n) for n, _ in special_hits]
        section = "special slot" if len(labels) == 1 else "special slots"
        category = _special_category_name(special_hits[0][1])
        suffix = f" ({category})" if category else ""
        parts.append(f"'{play_name}'{suffix} in {section} {_join_slots(labels)}")
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
    --verbose, and a per-play summary is appended. Exit 0 = every play hit somewhere,
    1 = a play missed everywhere, 2 = I/O error.
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
