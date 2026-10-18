"""`athc gameplan replace-play` — swap one play for another across .pln files."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    build_pool,
    category_of,
    epilog,
    find_in_gameplan,
    format_violation,
    is_one_file,
    path_option,
    require_key_path,
    scope,
)
from athc.config import resolve_league
from athc.console import console
from athc.errors import AthcError, error_line, sentence
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    read_gameplan,
    write_gameplan,
)
from athc.fbpro98_play import CategoryLabels
from athc.gameplan import Rules, load_rules, validate_gameplan
from athc.gameplan.config import load_config
from athc.gameplan.writer import build_custom_play
from athc.playpool import PlayPool

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
        raise AthcError(sentence(str(error)), path) from error
    return updated, normal_hits, special_hits


@dataclass(frozen=True, slots=True)
class Skipped:
    """A replacement passed over in one game plan, each reason the rest of its
    `SKIP` line: `already in the game plan`, or `fails check: ...` once per
    violation the game plan would have with it."""

    name: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Picked:
    """What `pick_replacement` chose for one game plan. `updated` and `entry`
    are None when the play is not in it (no hits), no replacement fits, or
    the model `refused` a replacement for a slot (the file fails)."""

    updated: GamePlan | None
    entry: CustomPlayRef | None
    normal_hits: Hits
    special_hits: Hits
    skipped: tuple[Skipped, ...]
    refused: AthcError | None = None


def _already_in(gp: GamePlan, name: str, target: str) -> bool:
    """Whether `name` fills a slot of `gp` other than the play being replaced."""
    if name.casefold() == target.casefold():
        return False
    normal_hits, special_hits = find_in_gameplan(gp, name)
    return bool(normal_hits or special_hits)


def pick_replacement(
    gp: GamePlan,
    target: str,
    entries: Sequence[CustomPlayRef],
    rules: Rules,
    pool: PlayPool,
    path: Path | None = None,
) -> Picked:
    """Swap `target` for the first of `entries` that fits `gp`: not already in
    it, and the game plan then passes `check` (no violation at all). When the
    model refuses an entry for a slot (as in `replace_in_gameplan`) the
    search stops with that error in `refused`, the entry named in it when
    there are several, so a list's culprit is clear."""
    normal_hits, special_hits = find_in_gameplan(gp, target)
    if not normal_hits and not special_hits:
        return Picked(None, None, normal_hits, special_hits, ())
    skipped: list[Skipped] = []
    for entry in entries:
        if _already_in(gp, entry.name, target):
            skipped.append(Skipped(entry.name, ("already in the game plan",)))
            continue
        try:
            updated, normal_hits, special_hits = replace_in_gameplan(
                gp, target, entry, path
            )
        except AthcError as error:
            if len(entries) > 1:
                error = AthcError(f"'{entry.name}' does not fit: {error.reason}", path)
            return Picked(None, None, normal_hits, special_hits, tuple(skipped), error)
        violations = validate_gameplan(updated, rules, pool)
        if violations:
            reasons = tuple(f"fails check: {format_violation(v)}" for v in violations)
            skipped.append(Skipped(entry.name, reasons))
            continue
        return Picked(updated, entry, normal_hits, special_hits, tuple(skipped))
    return Picked(None, None, normal_hits, special_hits, tuple(skipped))


def _pool_entry(pool: PlayPool, name: str) -> CustomPlayRef:
    """The `.pln` entry for a replacement; AthcError when it is not in the pool."""
    record = pool.find_by_name(name)
    if record is None:
        raise AthcError(f"Replacement play '{name}' is not in the play pool.")
    return build_custom_play(record, pool.root_dir)


@gameplan.command(
    name="replace-play",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan replace-play OLDRUN NEWRUN",
        "athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r",
    ),
)
@click.argument("play", help="Play to replace (any case).")
@click.argument(
    "replacement",
    nargs=-1,
    required=True,
    help="Plays to put in its place, in order; each must be in the play pool.",
)
@path_option("Game plans to edit")
@click.option("-r", "--recursive", is_flag=True, help="Include subfolders.")
@team_option(TEAM_HELP)
@league_option
@click.pass_context
def replace_play(
    ctx: click.Context,
    play: str,
    replacement: tuple[str, ...],
    path: str | None,
    recursive: bool,
    team: str | None,
    league: str | None,
) -> None:
    """Replace one play with another in game plans.

    Each game plan gets the first REPLACEMENT not already in it with which it
    still passes 'athc gameplan check'; the others are backups, tried in order.
    """
    require_key_path(team, path)
    if league is not None:
        resolve_league(league)  # a league that does not exist fails first
    # A replacement listed again, in any case, is tried once, where it first
    # stands.
    first: dict[str, str] = {}
    for name in replacement:
        first.setdefault(name.casefold(), name)
    replacements = list(first.values())
    one_file = is_one_file(path)  # found or not: no tally
    # The team and the league files are read before the rules and the pool.
    collected = scope(path, team, league, recursive=recursive)
    config = load_config(league)
    rules = (
        load_rules(config.rule_files, labels=config.categories)
        if config.rule_files
        else Rules()
    )
    # The pool is built as `check` builds it, so the attributes the league rules
    # cap (rollout, QB run, timed, 2-DL) are the ones `check` sees.
    pool = build_pool(config.play_path, config.categories)
    entries = [_pool_entry(pool, name) for name in replacements]

    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    updated = replaced_total = not_replaced = 0
    failed = len(collected.errors)
    for file in collected.files:
        try:
            gp = read_gameplan(str(file))
            picked = pick_replacement(gp, play, entries, rules, pool, file)
            if picked.updated is not None:
                write_gameplan(picked.updated, file)
        except (AthcError, OSError) as error:
            console.fail(error_line(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(file))
            failed += 1
            continue
        for skipped in picked.skipped:
            for reason in skipped.reasons:
                console.skip(f"{file}: '{skipped.name}' {reason}")
        if picked.refused is not None:
            console.fail(str(picked.refused))
            failed += 1
            continue
        if not picked.normal_hits and not picked.special_hits:
            if one_file:  # a find-play-style miss; silent in a set
                console.result(f"{file}: '{play}' not found")
            continue
        if picked.entry is None:
            not_replaced += 1
            console.result(f"{file}: '{play}' not replaced, no valid replacement")
            continue
        updated += 1
        replaced_total += len(picked.normal_hits) + len(picked.special_hits)
        for line in format_replacement_lines(
            file,
            picked.normal_hits,
            picked.special_hits,
            picked.entry,
            config.categories,
        ):
            console.ok(line)

    if not one_file:
        console.print()
        names = ", ".join(f"'{name}'" for name in replacements)
        console.result(
            f"'{play}' -> {names}: replaced {replaced_total} instance(s) "
            f"in {updated} game plan(s), {failed} failed, {not_replaced} not replaced"
        )
    ctx.exit(2 if failed else 1 if replaced_total == 0 or not_replaced else 0)
