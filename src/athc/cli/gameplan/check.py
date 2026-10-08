"""`athc gameplan check` — validate .pln gameplans against league rules."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, collect_files, resolve_rules
from athc.fbpro98_gameplan import InvalidGamePlanError, read_gameplan
from athc.gameplan import Rules, Violation, validate_gameplan
from athc.gameplan.config import ConfigFileError, load_config
from athc.playpool import PlayPool

PROG = "athc gameplan check"
logger = logging.getLogger(__name__)


@gameplan.command(name="check", context_settings=CONTEXT_SETTINGS)
@click.argument("paths", nargs=-1, required=False, metavar="[path]...")
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories of a directory path.",
)
@league_option
@click.pass_context
def check(
    ctx: click.Context,
    paths: tuple[str, ...],
    recursive: bool,
    league: str | None,
) -> None:
    """Validate one or more .pln gameplans against the league's rules.

    Each path is a .pln file, a directory (top level, or the whole tree with -r),
    or a glob. With no path, the current directory is checked.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not paths:
        paths = (".",)
    files, path_errors = collect_files(paths, suffix=".pln", recursive=recursive)
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    try:
        config = load_config(league)
    except (ConfigFileError, ValueError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)

    rules = resolve_rules(
        config.rule_files, config.categories, prog=PROG, logger=logger
    )
    if rules is None:
        ctx.exit(2)
    pool = build_pool(
        config.play_path,
        config.playpool_rules,
        config.categories,
        prog=PROG,
        logger=logger,
    )
    if pool is None:
        ctx.exit(2)

    total = files_with_violations = total_violations = io_errors = 0
    for path in files:
        count, line = check_file(path, rules, pool)
        click.echo(line)
        total += 1
        if count < 0:
            io_errors += 1
        elif count > 0:
            files_with_violations += 1
            total_violations += count

    click.echo()
    click.echo(
        f"{total} file(s) checked, {total_violations} violation(s) "
        f"across {files_with_violations} file(s)."
    )
    if io_errors or path_errors:
        ctx.exit(2)
    ctx.exit(1 if total_violations else 0)


def check_file(path: Path, rules: Rules, pool: PlayPool) -> tuple[int, str]:
    """Return `(count, line)`; a parse/I/O error returns `(-1, error line)`."""
    try:
        gp = read_gameplan(str(path))
    except (OSError, InvalidGamePlanError, ValueError) as error:
        return -1, f"{path}: ERROR: {error}"
    violations = validate_gameplan(gp, rules, pool)
    side = "offense" if gp.is_offense else "defense"
    normal = sum(1 for p in gp.normal_plays if p is not None)
    summary = f"{side}, {normal} normal"
    if not violations:
        return 0, f"{path}: OK ({summary})"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_format_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _format_violation(v: Violation) -> str:
    prefix = f"[{v.category}] " if v.category else ""
    return f"{prefix}{v.message}"
