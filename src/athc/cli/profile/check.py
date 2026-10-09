"""`athc profile check` — validate .prf files against league rules."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.profile import profile
from athc.cli.profile._common import collect_files, load_rules_or_raise
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_profile import read_profile
from athc.profile import ProfileRules, Violation, validate_profile
from athc.profile.config import load_config


@profile.command(name="check", context_settings=CONTEXT_SETTINGS)
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
    """Validate one or more .prf coaching profiles against the league's rules.

    Each path is a .prf file, a directory (top level, or the whole tree with -r),
    or a glob. With no path, the current directory is checked.
    """
    if not paths:
        paths = (".",)
    config = load_config(league)
    rules = load_rules_or_raise(config.rule_files)

    collected = collect_files(paths, suffix=".prf", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    findings = 0
    failed = len(collected.errors)
    for path in collected.files:
        try:
            count, line = check_file(path, rules)
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


def check_file(path: Path, rules: ProfileRules) -> tuple[int, str]:
    """Return `(count, line)`: the file's report, headline first; a clean file
    gives `(0, "<path>: <side>, FG range <n>")`. A file that cannot be read
    raises the reader's error; the loop catches per item."""
    prof = read_profile(path)
    violations = validate_profile(prof, rules)
    side = "offense" if prof.is_offense else "defense"
    summary = f"{side}, FG range {prof.field_goal_range}"
    if not violations:
        return 0, f"{path}: {summary}"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_format_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _format_violation(v: Violation) -> str:
    prefix = (
        f"[situation {v.situation_number}] " if v.situation_number is not None else ""
    )
    return f"{prefix}{v.message}"
