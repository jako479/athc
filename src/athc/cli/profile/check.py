"""`athc profile check` — check .prf files against the league's rules."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option, team_option
from athc.cli.profile import profile
from athc.cli.profile._common import (
    TEAM_HELP,
    collect_files,
    epilog,
    expand_names,
    load_rules_or_raise,
    team_profiles,
)
from athc.console import console
from athc.errors import AthcError, error_line
from athc.fbpro98_profile import read_profile
from athc.profile import ProfileRules, RuleViolation, validate_profile
from athc.profile.config import load_config


@profile.command(
    name="check",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc profile check",
        "athc profile check off2",
        "athc profile check drafts\\*OFF*.prf",
    ),
)
@click.argument(
    "path",
    nargs=-1,
    help=".prf files, folders, wildcards or profile keys (default: current folder).",
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
    """Check profiles against the league's rules.

    To check a profile with its game plan, run 'athc check-ppp'.
    """
    paths = path or (".",)
    profiles = team_profiles(paths, team=team, league=league)
    config = load_config(league)
    rules = load_rules_or_raise(config.rule_files, config.categories)

    expanded = expand_names(paths, profiles)
    collected = collect_files(expanded.paths, suffix=".prf", recursive=recursive)
    errors = [*expanded.errors, *collected.errors]
    for line in errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    findings = 0
    failed = len(errors)
    for file in collected.files:
        try:
            count, line = check_file(file, rules)
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


def _format_violation(v: RuleViolation) -> str:
    prefix = (
        f"[situation {v.situation_number}] " if v.situation_number is not None else ""
    )
    return f"{prefix}{v.message}"
