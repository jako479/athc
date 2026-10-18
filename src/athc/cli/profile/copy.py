"""`athc profile copy` — copy selected fields from a source .prf into targets."""

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
    one_profile,
    team_profiles,
)
from athc.console import console
from athc.errors import AthcError, error_line
from athc.fbpro98_profile import read_profile, write_profile
from athc.profile.writer import ProfileWriter

# CLI flag dest -> summary label, in display order. The writer's keyword names
# the substitutions flag `copy_sub_percent`.
_FLAG_LABELS = {
    "copy_stop_clock": "stop-clock",
    "copy_sub_percent": "substitutions",
    "copy_field_goal_range": "field-goal-range",
    "copy_fourth_down": "fourth-down",
    "copy_goal_line": "goal-line",
    "copy_pat_logic": "pat-logic",
}

# Windows' `copy` words for a file copied onto itself.
_ONTO_ITSELF = "The file cannot be copied onto itself."


@profile.command(
    name="copy",
    context_settings=CONTEXT_SETTINGS,
    epilog=epilog(
        "athc profile copy off1 off2 --stop-clock --substitutions",
        "athc profile copy new.prf off1 off2 --substitutions",
    ),
)
@click.argument("source", help="Profile to copy from: a .prf file or a profile key.")
@click.argument(
    "target",
    nargs=-1,
    required=True,
    help="Profiles to copy into: .prf files, folders, wildcards or profile keys.",
)
@click.option("-r", "--recursive", is_flag=True, help="Include subfolders.")
@click.option(
    "--stop-clock",
    "copy_stop_clock",
    is_flag=True,
    help="Copy the stop-clock setting of every situation.",
)
@click.option(
    "--substitutions",
    "copy_sub_percent",
    is_flag=True,
    help="Copy the substitution percentages.",
)
@click.option(
    "--field-goal-range",
    "copy_field_goal_range",
    is_flag=True,
    help="Copy the field-goal range.",
)
@click.option(
    "--fourth-down",
    "copy_fourth_down",
    is_flag=True,
    help="Copy every 4th-down situation.",
)
@click.option(
    "--goal-line",
    "copy_goal_line",
    is_flag=True,
    help="Copy every goal-line situation (inside the 5).",
)
@click.option(
    "--pat-logic",
    "copy_pat_logic",
    is_flag=True,
    help="Copy the PAT table (60 situations).",
)
@team_option(TEAM_HELP)
@league_option
@click.pass_context
def copy(
    ctx: click.Context,
    source: str,
    target: tuple[str, ...],
    recursive: bool,
    team: str | None,
    league: str | None,
    **flags: bool,
) -> None:
    """Copy settings from one profile to others.

    Targets of the other side are skipped; run 'athc profile check' afterward.
    """
    if not any(flags.values()):
        raise click.UsageError(
            "At least one copy option is required "
            "(--stop-clock, --substitutions, --field-goal-range, "
            "--fourth-down, --goal-line, --pat-logic)."
        )
    profiles = team_profiles((source, *target), team=team, league=league)
    source_path = one_profile(source, profiles)
    source_resolved = source_path.resolve()
    expanded = expand_names(target, profiles)
    # The source as the one file named is refused, as Windows' `copy` does; in
    # a bulk copy (more targets, a folder, a wildcard) it is only skipped.
    if len(target) == 1 and expanded.paths:
        only = Path(expanded.paths[0])
        if only.is_file() and only.resolve() == source_resolved:
            raise AthcError(_ONTO_ITSELF, only)
    side = "offense" if read_profile(source_path).is_offense else "defense"

    collected = collect_files(expanded.paths, suffix=".prf", recursive=recursive)
    errors = [*expanded.errors, *collected.errors]
    for line in errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    other_side = "defense" if side == "offense" else "offense"
    updated = skipped = 0
    failed = len(errors)
    for path in collected.files:
        if path.resolve() == source_resolved:
            skipped += 1
            console.skip(f"{path}: the source profile")
            continue
        if not _matches_side(path, side):
            skipped += 1
            console.skip(f"{path}: {other_side} profile")
            continue
        try:
            result = ProfileWriter(source_path, path).apply(**flags)
            write_profile(result, str(path))
        except (AthcError, OSError) as error:
            console.fail(error_line(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(str(path))
            failed += 1
            continue
        updated += 1
        console.ok(f"{path}: updated ({_flag_summary(flags)})")

    console.print()
    console.result(
        f"{len(collected.files)} file(s) processed, {updated} updated, "
        f"{skipped} skipped, {failed} failed"
    )
    ctx.exit(2 if failed else 0)


def _matches_side(path: Path, side: str) -> bool:
    """A `.prf`'s file-size parity marks its side: offense even, defense odd."""
    even = path.stat().st_size % 2 == 0
    return even if side == "offense" else not even


def _flag_summary(flags: dict[str, bool]) -> str:
    return ", ".join(label for key, label in _FLAG_LABELS.items() if flags.get(key))
