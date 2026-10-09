"""`athc profile copy` — copy selected fields from a source .prf into targets."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS
from athc.cli.profile import profile
from athc.cli.profile._common import collect_files, named_file
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_profile import read_profile, write_profile
from athc.profile.writer import ProfileWriter

# CLI flag dest -> summary label, in display order.
_FLAG_LABELS = {
    "copy_stop_clock": "stop-clock",
    "copy_sub_percent": "sub-percent",
    "copy_field_goal_range": "field-goal-range",
    "copy_fourth_down": "fourth-down",
    "copy_goal_line": "goal-line",
    "copy_pat_logic": "pat-logic",
}


@profile.command(name="copy", context_settings=CONTEXT_SETTINGS)
@click.argument("source", metavar="source", type=click.Path(path_type=Path))
@click.argument("target", metavar="target", type=click.Path(path_type=Path))
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when target is a directory.",
)
@click.option(
    "--stop-clock",
    "copy_stop_clock",
    is_flag=True,
    help="Copy the stop-clock flag for every situation.",
)
@click.option(
    "--sub-percent",
    "copy_sub_percent",
    is_flag=True,
    help="Copy all substitution percentages.",
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
    help="Copy every goal-line situation (inside DEF 5 or OFF 5).",
)
@click.option(
    "--pat-logic",
    "copy_pat_logic",
    is_flag=True,
    help="Copy the PAT play-calling table (all 60 situations).",
)
@click.pass_context
def copy(
    ctx: click.Context,
    source: Path,
    target: Path,
    recursive: bool,
    **flags: bool,
) -> None:
    """Copy selected fields from the source .prf into one or more target .prf files.

    target is a .prf file or a directory (top level, or the whole tree with -r).
    Files of the wrong side (offense vs defense) are skipped. At least one copy
    flag is required.
    """
    if not any(flags.values()):
        raise click.UsageError(
            "at least one copy option is required "
            "(--stop-clock, --sub-percent, --field-goal-range, "
            "--fourth-down, --goal-line, --pat-logic)"
        )
    side = "offense" if read_profile(named_file(source)).is_offense else "defense"

    collected = collect_files([str(target)], suffix=".prf", recursive=recursive)
    for line in collected.errors:
        console.fail(line)
    for line in collected.warnings:
        console.warn(line)

    other_side = "defense" if side == "offense" else "offense"
    source_resolved = source.resolve()
    updated = skipped = 0
    failed = len(collected.errors)
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
            result = ProfileWriter(source, path).apply(**flags)
            write_profile(result, str(path))
        except (AthcError, OSError) as error:
            console.fail(str(error))
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
