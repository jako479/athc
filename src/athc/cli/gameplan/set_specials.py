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
from athc.errors import AthcError, error_line
from athc.fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from athc.gameplan.config import load_config
from athc.gameplan.writer import (
    InvalidPlay,
    InvalidPlayListError,
    PlayLine,
    apply_special_plays,
)
from athc.playpool import PlayPool

SPECIAL_COUNT = len(GamePlan.CUSTOM_SPECIAL_CATEGORIES)


def validate_special_play_list(
    plays: Sequence[PlayLine], pool: PlayPool
) -> list[InvalidPlay]:
    """Per-line errors: duplicate name, non-special play, duplicate special category.
    Names missing from the pool are left for the per-file pass to report."""
    errors: list[InvalidPlay] = []
    seen_names: dict[str, int] = {}
    seen_categories: dict[int, str] = {}
    for play in plays:
        name = play.name
        upper = name.upper()
        if upper in seen_names:
            errors.append(
                InvalidPlay(
                    play.line,
                    f"Duplicate play '{name}' (already on line {seen_names[upper]}).",
                )
            )
            continue
        seen_names[upper] = play.line
        record = pool.find_by_name(name)
        if record is None:
            continue
        if not record.play_file.is_special_teams:
            errors.append(
                InvalidPlay(
                    play.line,
                    f"'{name}' is not a special teams play. Use set-normals.",
                )
            )
            continue
        cat = record.play_file.special_category
        if cat in seen_categories:
            errors.append(
                InvalidPlay(
                    play.line,
                    f"'{name}' targets special category {cat}, "
                    f"already filled by '{seen_categories[cat]}'.",
                )
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


def _determine_side(pool: PlayPool, plays: Sequence[PlayLine]) -> str | None:
    """Infer side from the first resolvable special play; None if none resolve."""
    for play in plays:
        record = pool.find_by_name(play.name)
        if record is not None and record.play_file.is_special_teams:
            if record.play_file.is_offensive:
                return "offense"
            if record.play_file.is_defensive:
                return "defense"
    return None


@gameplan.command(name="set-specials", context_settings=CONTEXT_SETTINGS)
@click.argument("target", metavar="path", type=click.Path(path_type=Path))
@click.argument(
    "play_list_path",
    metavar="play_list",
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
    play_list_path: Path,
    recursive: bool,
    league: str | None,
) -> None:
    """Set the custom special-teams plays of path from play_list.

    path is a .pln file or a directory (top level, or the tree with -r); a
    play_list of `-` reads the list from the console. Files of the wrong side are
    skipped (offense .pln are even-sized, defense odd). Merge semantics: unlisted
    special categories are preserved. The league's play pool resolves names.
    """
    from_console = str(play_list_path) == "-"
    if from_console:
        text = sys.stdin.read()
    else:
        text = named_file(play_list_path).read_text(encoding="utf-8-sig")
    # A list from the console has no file to name.
    source = "" if from_console else f"{play_list_path}: "
    where = "play list" if from_console else str(play_list_path)
    plays = parse_play_list(text)
    if len(plays) > SPECIAL_COUNT:
        raise AthcError(
            f"Too many plays ({len(plays)}). The most is {SPECIAL_COUNT}.",
            None if from_console else play_list_path,
        )
    config = load_config(league, rule_files=())  # no gameplan rules needed
    pool = build_pool(config.play_path, config.categories, config.league_file)

    invalid_plays = validate_special_play_list(plays, pool)
    if invalid_plays:
        for invalid in invalid_plays:
            console.fail(f"{source}line {invalid.line}: {invalid.reason}")
        ctx.exit(2)

    side = _determine_side(pool, plays)
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
            new_gp = apply_special_plays(gp, plays, pool)
            write_gameplan(new_gp, path)
        except InvalidPlayListError as error:
            # The line is the list's, so it goes last: after the .pln path it
            # would read as a line of the .pln.
            for invalid in error.invalid_plays:
                reason = invalid.reason.removesuffix(".")
                console.fail(f"{path}: {reason} ({where} line {invalid.line}).")
            failed += 1
            continue
        except (AthcError, OSError) as error:
            console.fail(error_line(error))
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
