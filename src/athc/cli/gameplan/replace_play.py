"""`athc gameplan replace-play` — swap one play for another across .pln files."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    build_pool,
    category_of,
    collect_files,
    find_in_gameplan,
    format_violation,
    is_glob,
)
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


def _is_path(arg: str) -> bool:
    """Whether the last argument names the files, not a play: an existing file
    or folder (first, so a folder named like a play is the folder), a name
    with a folder separator, a `.pln` name, or a wildcard. Play names are
    plain file stems with none of these."""
    return (
        Path(arg).exists()
        or "/" in arg
        or "\\" in arg
        or arg.casefold().endswith(".pln")
        or is_glob(arg)
    )


def split_args(args: Sequence[str]) -> tuple[str, list[str], str | None]:
    """`play replacement... [path]` -> `(play, replacements, path)`, path None
    when the last argument is a play; a replacement listed again, in any case,
    is dropped. UsageError without a replacement."""
    if not args:
        raise click.UsageError("Missing argument 'play'.")
    play, *rest = args
    path = rest.pop() if rest and _is_path(rest[-1]) else None
    if not rest:
        raise click.UsageError("Missing argument 'replacement'.")
    seen: set[str] = set()
    replacements: list[str] = []
    for name in rest:
        if name.casefold() not in seen:
            seen.add(name.casefold())
            replacements.append(name)
    return play, replacements, path


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
    `SKIP` line: `already in the gameplan`, or `fails check: ...` once per
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
            skipped.append(Skipped(entry.name, ("already in the gameplan",)))
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
        raise AthcError(f"Replacement play '{name}' not found in the play pool.")
    return build_custom_play(record, pool.root_dir)


@gameplan.command(name="replace-play", context_settings=CONTEXT_SETTINGS)
@click.argument("args", nargs=-1, required=True, metavar="play replacement... [path]")
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
    args: tuple[str, ...],
    recursive: bool,
    league: str | None,
) -> None:
    """Replace every instance of play with the first replacement that fits.

    play and each replacement are single, case-insensitive names; the
    replacements are tried in order, each a backup for the one before it.
    path is a .pln file, a directory (top level, or the whole tree with -r) or
    a wildcard, the current directory when left out; the last name counts as
    the path when it is an existing file or folder, or has a \\ or /, a .pln
    ending or a wildcard. In each gameplan the first replacement not already
    in it, with which the gameplan passes `check`, is used.
    Every replacement must exist in the league's play pool; play need not (it
    may already be gone). Normal and custom-special slots are searched.
    """
    play, replacements, path = split_args(args)
    target = path or "."
    config = load_config(league)
    rules = (
        load_rules(config.rule_files, labels=config.categories)
        if config.rule_files
        else Rules()
    )
    # The pool is built as `check` builds it, so the attributes the league rules
    # cap (rollout, QB run, timed, 2-DL) are the ones `check` sees.
    pool = build_pool(config.play_path, config.categories, config.league_file)
    entries = [_pool_entry(pool, name) for name in replacements]

    collected = collect_files([target], suffix=".pln", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    # One file, found or not: no tally. A wildcard can match many files, so it
    # counts as a folder.
    single_path = not (Path(target).is_dir() or is_glob(target))
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
            if single_path:  # a find-play-style miss; silent in a directory
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

    if not single_path:
        console.print()
        names = ", ".join(f"'{name}'" for name in replacements)
        console.result(
            f"'{play}' -> {names}: replaced {replaced_total} instance(s) "
            f"in {updated} gameplan(s), {failed} failed, {not_replaced} not replaced"
        )
    ctx.exit(2 if failed else 1 if replaced_total == 0 or not_replaced else 0)
