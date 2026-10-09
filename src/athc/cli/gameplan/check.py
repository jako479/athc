"""`athc gameplan check` — validate .pln gameplans against league rules."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, collect_files, load_rules_or_raise
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import read_gameplan
from athc.gameplan import Rules, Violation, validate_gameplan
from athc.gameplan.config import load_config
from athc.playpool import PlayPool


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
    if not paths:
        paths = (".",)
    config = load_config(league)
    rules = load_rules_or_raise(config.rule_files, config.categories)
    pool = build_pool(config.play_path, config.playpool_rules, config.categories)

    collected = collect_files(paths, suffix=".pln", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    findings = 0
    failed = len(collected.errors)
    for path in collected.files:
        try:
            count, line = check_file(path, rules, pool)
        except (AthcError, OSError) as error:
            console.fail(str(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(path))
            failed += 1
            continue
        if count > 0:
            findings += 1
            head, *details = line.split("\n")
            console.result(head)
            for detail in details:
                console.print(detail)
        else:
            console.ok(line)

    console.print()
    console.result(
        f"{len(collected.files)} file(s) checked, {findings} with violations, "
        f"{failed} failed"
    )
    ctx.exit(2 if failed else 1 if findings else 0)


def check_file(path: Path, rules: Rules, pool: PlayPool) -> tuple[int, str]:
    """Return `(count, line)`: the file's report, headline first; a clean file
    gives `(0, "<path>: <side>, <n> normal")`. A file that cannot be read
    raises the reader's error; the loop catches per item."""
    gp = read_gameplan(path)
    violations = validate_gameplan(gp, rules, pool)
    side = "offense" if gp.is_offense else "defense"
    normal = sum(1 for p in gp.normal_plays if p is not None)
    summary = f"{side}, {normal} normal"
    if not violations:
        return 0, f"{path}: {summary}"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_format_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _format_violation(v: Violation) -> str:
    prefix = f"[{v.category}] " if v.category else ""
    return f"{prefix}{v.message}"
