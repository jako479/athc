"""`athc gameplan check` — check .pln game plans against the league's rules."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import (
    TEAM_HELP,
    build_pool,
    collect_entries,
    epilog,
    format_violation,
    load_rules_or_raise,
    require_a_key,
)
from athc.config import resolve_league
from athc.console import console
from athc.errors import AthcError, error_line
from athc.fbpro98_gameplan import read_gameplan
from athc.gameplan import Rules, validate_gameplan
from athc.gameplan.config import load_config
from athc.playpool import PlayPool


@gameplan.command(
    name="check",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc gameplan check",
        "athc gameplan check off1",
        "athc gameplan check plans -r",
    ),
)
@click.argument(
    "path",
    nargs=-1,
    help=(
        ".pln files, folders, wildcards or game plan keys (default: current folder)."
    ),
)
@click.option("-r", "--recursive", is_flag=True, help="Include subfolders.")
@team_option(TEAM_HELP)
@league_option
@click.pass_context
def check(
    ctx: click.Context,
    path: tuple[str, ...],
    recursive: bool,
    team: str | None,
    league: str | None,
) -> None:
    """Check game plans against the league's rules.

    To check game plans with their profiles, run 'athc check-ppp'.
    """
    require_a_key(team, path)
    if league is not None:
        resolve_league(league)  # a league that does not exist fails first
    # A key reads the team and the league files before the rules and the pool.
    collected = collect_entries(path or (".",), team, league, recursive=recursive)
    config = load_config(league)
    rules = load_rules_or_raise(config.rule_files, config.categories)
    pool = build_pool(config.play_path, config.categories)

    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    findings = 0
    failed = len(collected.errors)
    for file in collected.files:
        try:
            count, line = check_file(file, rules, pool)
        except (AthcError, OSError) as error:
            console.fail(error_line(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(file))
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
    lines.extend(f"  {format_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)
