"""`athc gameplan set-specials` — set special-teams slots of one or many .pln."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import click

from athc.cli import league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    build_pool,
    collect_files,
    make_backup,
    parse_play_list,
)
from athc.fbpro98_gameplan import (
    GamePlan,
    InvalidGamePlanError,
    read_gameplan,
    write_gameplan,
)
from athc.gameplan.config import ConfigFileError, load_config
from athc.gameplan.writer import InvalidPlayInputError, apply_special_plays
from athc.playpool import PlayPool

PROG = "athc gameplan set-specials"
logger = logging.getLogger(__name__)
SPECIAL_COUNT = GamePlan.NUMBER_SPECIAL_CATEGORIES


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


def _update_one(
    path: Path, lines: Sequence[str], pool: PlayPool, *, no_backup: bool
) -> tuple[str, str]:
    """Apply the special list to one .pln. Returns `(status, message)`."""
    try:
        gp = read_gameplan(str(path))
        updated = apply_special_plays(gp, lines, pool)
    except InvalidPlayInputError as error:
        return "failed", error.violations[0] if error.violations else "invalid input"
    except (OSError, InvalidGamePlanError, ValueError) as error:
        return "failed", str(error)
    backup = None if no_backup else make_backup(path)
    write_gameplan(updated, path)
    count = sum(1 for p in updated.custom_special_plays if p is not None)
    tail = "" if backup is None else f"; backup {backup.name}"
    return "updated", f"{count} special play(s){tail}"


@gameplan.command(name="set-specials")
@click.argument("target", type=click.Path(path_type=Path))
@click.argument("input_path", required=False, type=click.Path(path_type=Path))
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when TARGET is a directory.",
)
@click.option(
    "--stdin", "use_stdin", is_flag=True, help="Read the play list from stdin."
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
@click.option(
    "--playpool-rules",
    "playpool_rules",
    type=click.Path(path_type=Path),
    default=None,
    help="Playpool rules TOML (overrides the league's PlayPoolRules).",
)
@league_option
@click.pass_context
def set_specials(
    ctx: click.Context,
    target: Path,
    input_path: Path | None,
    recursive: bool,
    use_stdin: bool,
    no_backup: bool,
    play_path: Path | None,
    playpool_rules: Path | None,
    league: str | None,
) -> None:
    """Set the custom special-teams plays of TARGET from a play list (file or --stdin).

    TARGET is a .pln file or a directory (top level, or the tree with -r). Files of the
    wrong side are skipped silently (offense .pln are even-sized, defense odd). Merge
    semantics: unlisted special categories are preserved. A timestamped .bak is written
    next to each updated file (unless --no-backup). Exit 0 = all updated, 1 = some
    failed, 2 = setup error.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if use_stdin and input_path is not None:
        raise click.UsageError("provide either INPUT_PATH or --stdin, not both")
    if not use_stdin and input_path is None:
        raise click.UsageError("INPUT_PATH is required (or pass --stdin)")

    try:
        if use_stdin:
            text = sys.stdin.read()
        else:
            assert input_path is not None
            text = input_path.read_text(encoding="utf-8")
        lines = parse_play_list(text)
        if len(lines) > SPECIAL_COUNT:
            logger.error(
                "%s: input has %d play(s), max is %d", PROG, len(lines), SPECIAL_COUNT
            )
            ctx.exit(2)
        config = load_config(
            league,
            play_path=play_path,
            playpool_rules=playpool_rules,
        )
    except (ConfigFileError, ValueError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)

    pool = build_pool(config.play_path, config.playpool_rules, prog=PROG, logger=logger)
    if pool is None:
        ctx.exit(2)

    input_errors = validate_special_input(lines, pool)
    if input_errors:
        for err in input_errors:
            logger.error("%s: %s", PROG, err)
        ctx.exit(2)

    side = _determine_side(pool, lines)
    files, path_errors = collect_files(
        [str(target)], suffix=".pln", recursive=recursive
    )
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    updated = failed = 0
    for path in files:
        if not _matches_side(path, side):
            continue
        status, message = _update_one(path, lines, pool, no_backup=no_backup)
        click.echo(f"{path}: {status} ({message})")
        if status == "updated":
            updated += 1
        else:
            failed += 1

    click.echo()
    click.echo(
        f"{updated + failed} file(s) processed; {updated} updated, {failed} failed."
    )
    ctx.exit(1 if failed else 0)
