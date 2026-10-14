"""`athc gameplan find-play` — find plays across .pln normal + custom-special slots."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    category_of,
    epilog,
    find_in_gameplan,
    is_one_file,
    path_option,
    require_key_path,
    scope,
)
from athc.config import resolve_league
from athc.console import console
from athc.errors import AthcError, error_line
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


@gameplan.command(
    name="find-play",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan find-play OR45RL01",
        "athc gameplan find-play OR45RL01 BCFGPAT --path plans -r",
    ),
)
@click.argument("play", nargs=-1, required=True, help="Plays to find (any case).")
@path_option("Game plans to search")
@click.option("-r", "--recursive", is_flag=True, help="Include subfolders.")
@team_option(TEAM_HELP)
@league_option
@click.pass_context
def find_play(
    ctx: click.Context,
    play: tuple[str, ...],
    path: str | None,
    recursive: bool,
    team: str | None,
    league: str | None,
) -> None:
    """Find plays by name in game plans.

    Lists each play's normal and special-teams slots in each game plan.
    """
    require_key_path(team, path)
    if league is not None:
        resolve_league(league)  # a league that does not exist fails first
    play_names = list(play)
    one_file = is_one_file(path)  # found or not: no tally
    collected = scope(path, team, league, recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    instances_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    files_hit_per_play: dict[str, int] = dict.fromkeys(play_names, 0)
    failed = len(collected.errors)

    for file in collected.files:
        try:
            gp = read_gameplan(str(file))
        except (AthcError, OSError) as error:
            console.fail(error_line(error))
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

    if not one_file:
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
