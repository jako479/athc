"""`athc profile check` — validate .prf files against league rules."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli.profile import profile
from athc.cli.profile._common import collect_files, resolve_rules
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
from athc.fbpro98_profile import (
    InvalidProfileError,
    UnsupportedProfileError,
    read_profile,
)
from athc.profile import (
    CompatIssue,
    CompatWarning,
    ProfileRules,
    Violation,
    check_gameplan_compatibility,
    gameplan_extra_categories,
    validate_profile,
)
from athc.profile.config import ConfigFileError, load_config

PROG = "athc profile check"
logger = logging.getLogger(__name__)


@profile.command(name="check")
@click.argument("paths", nargs=-1, required=True, metavar="PATH...")
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories of a directory PATH.",
)
@click.option(
    "--rules",
    "rule_overrides",
    type=click.Path(path_type=Path),
    multiple=True,
    help="Rules TOML file; repeat to layer multiple. Overrides config.",
)
@click.option(
    "--gameplan",
    "gameplan_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Also check each profile's play categories are covered by this .pln "
    "gameplan, and warn about gameplan categories the profile never uses "
    "(same side only).",
)
@click.pass_context
def check(
    ctx: click.Context,
    paths: tuple[str, ...],
    recursive: bool,
    rule_overrides: tuple[Path, ...],
    gameplan_path: Path | None,
) -> None:
    """Validate one or more .prf coaching profiles against the configured rules.

    Each PATH is a .prf file, a directory (top level, or the whole tree with -r),
    or a glob. With --gameplan, each profile is also checked for play-category
    coverage against that .pln (offense with offense, defense with defense), and
    gameplan categories the profile never uses are reported as warnings (these do
    not affect the exit code).
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    files, path_errors = collect_files(paths, suffix=".prf", recursive=recursive)
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    try:
        config = load_config(rule_files=list(rule_overrides) or None)
    except ConfigFileError as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)

    rules = resolve_rules(config.rule_files, prog=PROG, logger=logger)
    if rules is None:
        ctx.exit(2)

    gameplan = None
    if gameplan_path is not None:
        gameplan = load_gameplan(gameplan_path)
        if gameplan is None:
            ctx.exit(2)

    total = files_with_violations = total_violations = io_errors = 0
    for path in files:
        count, line = check_file(path, rules, gameplan)
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


def load_gameplan(path: Path) -> GamePlan | None:
    """Read the --gameplan .pln; log and return None on a bad path or parse error."""
    if path.suffix.lower() != ".pln":
        logger.error("%s: not a .pln file: %s", PROG, path)
        return None
    try:
        return read_gameplan(str(path))
    except (OSError, InvalidGamePlanError) as error:
        logger.error("%s: %s", PROG, error)
        return None


def check_file(
    path: Path, rules: ProfileRules, gameplan: GamePlan | None = None
) -> tuple[int, str]:
    """Return `(count, line)`; a parse/I/O error or side mismatch returns
    `(-1, error line)`. With a gameplan, `count` also includes compatibility
    issues and the head line reports them; gameplan categories the profile never
    uses are appended as warnings that do not count toward `count`."""
    try:
        prof = read_profile(str(path))
    except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
        return -1, f"{path}: ERROR: {error}"
    violations = validate_profile(prof, rules)
    side = "offense" if prof.is_offense else "defense"
    summary = f"{side}, FG range {prof.field_goal_range}"

    if gameplan is None:
        return _render(path, violations, summary)

    if prof.is_offense != gameplan.is_offense:
        gp_side = "offense" if gameplan.is_offense else "defense"
        return -1, (
            f"{path}: ERROR: profile is {side} but gameplan is {gp_side}; "
            f"sides must match"
        )
    issues = check_gameplan_compatibility(prof, gameplan)
    warnings = gameplan_extra_categories(prof, gameplan)
    return _render_with_compat(path, violations, issues, warnings, summary)


def _render(
    path: Path, violations: tuple[Violation, ...], summary: str
) -> tuple[int, str]:
    if not violations:
        return 0, f"{path}: OK ({summary})"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_format_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _render_with_compat(
    path: Path,
    violations: tuple[Violation, ...],
    issues: tuple[CompatIssue, ...],
    warnings: tuple[CompatWarning, ...],
    summary: str,
) -> tuple[int, str]:
    """Render the gameplan report. `count` excludes warnings, which are
    informational and do not affect the exit code."""
    total = len(violations) + len(issues)
    if total == 0 and not warnings:
        return 0, f"{path}: OK ({summary}; gameplan compatible)"
    if total == 0:
        head = f"{path}: OK ({summary}; gameplan compatible)"
    else:
        head = (
            f"{path}: {len(violations)} violation(s), "
            f"{len(issues)} gameplan issue(s) ({summary})"
        )
    if warnings:
        head += f"; {len(warnings)} gameplan warning(s)"
    lines = [head]
    lines.extend(f"  {_format_violation(v)}" for v in violations)
    lines.extend(f"  gameplan: {issue.message}" for issue in issues)
    lines.extend(f"  gameplan warning: {w.message}" for w in warnings)
    return total, "\n".join(lines)


def _format_violation(v: Violation) -> str:
    prefix = (
        f"[situation {v.situation_number}] " if v.situation_number is not None else ""
    )
    return f"{prefix}{v.message}"
