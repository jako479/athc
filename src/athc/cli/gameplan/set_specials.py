"""`athc gameplan set-specials` — set special-teams slots of one or many .pln."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    build_pool,
    collect_files,
    named_file,
    parse_play_list,
)
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from athc.gameplan.config import load_config
from athc.gameplan.writer import InvalidPlayInputError, apply_special_plays
from athc.playpool import PlayPool

SPECIAL_COUNT = len(GamePlan.CUSTOM_SPECIAL_CATEGORIES)


def validate_special_input(lines: Sequence[str], pool: PlayPool) -> list[str]:
    """Per-line errors: duplicate name, non-special play, duplicate special category.
    Names missing from the pool are left for the per-file pass to report."""
    errors: list[str] = []
    seen_names: dict[str, int] = {}
    seen_categories: dict[int, str] = {}
    for i, name in enumerate(lines, start=1):
        upper = name.upper()
        if upper in seen_names:
            errors.append(
                f"line {i}: duplicate play '{name}' "
                f"(already on line {seen_names[upper]})"
            )
            continue
        seen_names[upper] = i
        record = pool.find_by_name(name)
        if record is None:
            continue
        if not record.play_file.is_special_teams:
            errors.append(
                f"line {i}: '{name}' is not a special teams play; use set-normals"
            )
            continue
        cat = record.play_file.special_category
        if cat in seen_categories:
            errors.append(
                f"line {i}: '{name}' targets special category {cat}, "
                f"already filled by '{seen_categories[cat]}'"
            )
            continue
        seen_categories[cat] = name
    return errors


def _matches_side(path: Path, side: str | None) -> bool:
    """`offense` = even file size, `defense` = odd. `side=None` accepts everything."""
    if side is None:
        return True
    size = path.stat().st_size
    return size % 2 == 0 if side == "offense" else size % 2 == 1


def _determine_side(pool: PlayPool, lines: Sequence[str]) -> str | None:
    """Infer side from the first resolvable special play; None if none resolve."""
    for name in lines:
        record = pool.find_by_name(name)
        if record is not None and record.play_file.is_special_teams:
            if record.play_file.is_offensive:
                return "offense"
            if record.play_file.is_defensive:
                return "defense"
    return None


@gameplan.command(name="set-specials", context_settings=CONTEXT_SETTINGS)
@click.argument("target", metavar="path", type=click.Path(path_type=Path))
@click.argument(
    "input_path",
    metavar="input_file",
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when path is a directory.",
)
@league_option
@click.pass_context
def set_specials(
    ctx: click.Context,
    target: Path,
    input_path: Path,
    recursive: bool,
    league: str | None,
) -> None:
    """Set the custom special-teams plays of path from the play list in input_file.

    path is a .pln file or a directory (top level, or the tree with -r); an
    input_file of `-` reads the list from the console. Files of the wrong side are
    skipped (offense .pln are even-sized, defense odd). Merge semantics: unlisted
    special categories are preserved. The league's play pool resolves names.
    """
    if str(input_path) == "-":
        text = sys.stdin.read()
        source = ""  # a list from the console has no file to name
    else:
        text = named_file(input_path).read_text(encoding="utf-8")
        source = f"{input_path} "
    lines = parse_play_list(text)
    if len(lines) > SPECIAL_COUNT:
        raise AthcError(f"input has {len(lines)} play(s), max is {SPECIAL_COUNT}")
    config = load_config(league, rule_files=())  # no gameplan rules needed
    pool = build_pool(config.play_path, config.playpool_rules, config.categories)

    input_errors = validate_special_input(lines, pool)
    if input_errors:
        for err in input_errors:
            console.fail(f"{source}{err}")
        ctx.exit(2)

    side = _determine_side(pool, lines)
    collected = collect_files([str(target)], suffix=".pln", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    other_side = "defense" if side == "offense" else "offense"
    updated = skipped = 0
    failed = len(collected.errors)
    for path in collected.files:
        if not _matches_side(path, side):
            skipped += 1
            console.skip(f"{path}: {other_side} gameplan")
            continue
        try:
            gp = read_gameplan(str(path))
            new_gp = apply_special_plays(gp, lines, pool)
            write_gameplan(new_gp, path)
        except InvalidPlayInputError as error:
            for violation in error.violations:
                console.fail(f"{path}: {violation}")
            failed += 1
            continue
        except (AthcError, OSError) as error:
            console.fail(str(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(path))
            failed += 1
            continue
        updated += 1
        count = sum(1 for p in new_gp.custom_special_plays if p is not None)
        console.ok(f"{path}: updated ({count} special play(s))")

    console.print()
    console.result(
        f"{len(collected.files)} file(s) processed, {updated} updated, "
        f"{skipped} skipped, {failed} failed"
    )
    ctx.exit(2 if failed else 0)
