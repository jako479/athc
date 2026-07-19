"""`athc profile copy` — copy selected fields from a source .prf into targets."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from athc.cli.profile import profile
from athc.cli.profile._common import collect_files, make_backup
from athc.fbpro98_profile import (
    InvalidProfileError,
    UnsupportedProfileError,
    read_profile,
    write_profile,
)
from athc.profile.writer import ProfileTypeMismatchError, ProfileWriter

PROG = "athc profile copy"
logger = logging.getLogger(__name__)

# CLI flag dest -> summary label, in display order.
_FLAG_LABELS = {
    "copy_stop_clock": "stop-clock",
    "copy_sub_percent": "sub-percent",
    "copy_field_goal_range": "field-goal-range",
    "copy_fourth_down": "fourth-down",
    "copy_goal_line": "goal-line",
}


@profile.command(name="copy")
@click.argument("source", metavar="SRC.prf", type=click.Path(path_type=Path))
@click.argument("target", metavar="TARGET", type=click.Path(path_type=Path))
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories when TARGET is a directory.",
)
@click.option(
    "--no-backup", is_flag=True, help="Do not create a .bak copy before writing."
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
@click.pass_context
def copy(
    ctx: click.Context,
    source: Path,
    target: Path,
    recursive: bool,
    no_backup: bool,
    **flags: bool,
) -> None:
    """Copy selected fields from SRC.prf into one or more TARGET .prf files.

    TARGET is a .prf file or a directory (top level, or the whole tree with -r).
    Files of the wrong side (offense vs defense) are skipped. A timestamped .bak
    is made next to each target before it is written (suppress with --no-backup).
    At least one copy flag is required.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if not any(flags.values()):
        raise click.UsageError(
            "at least one copy option is required "
            "(--stop-clock, --sub-percent, --field-goal-range, "
            "--fourth-down, --goal-line)"
        )

    try:
        side = "offense" if read_profile(str(source)).is_offense else "defense"
    except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)

    files, path_errors = collect_files(
        [str(target)], suffix=".prf", recursive=recursive
    )
    for error in path_errors:
        logger.error("%s: %s", PROG, error)
    if not files:
        ctx.exit(2)

    source_resolved = source.resolve()
    updated = failed = 0
    for path in files:
        if not _matches_side(path, side) or path.resolve() == source_resolved:
            continue
        status, message = _copy_one(source, path, flags, no_backup=no_backup)
        click.echo(f"{path}: {status} ({message})")
        if status == "updated":
            updated += 1
        else:
            failed += 1

    click.echo()
    click.echo(
        f"{updated + failed} file(s) processed; {updated} updated, {failed} failed."
    )
    ctx.exit(0 if failed == 0 else 1)


def _matches_side(path: Path, side: str) -> bool:
    """A `.prf`'s file-size parity marks its side: offense even, defense odd."""
    even = path.stat().st_size % 2 == 0
    return even if side == "offense" else not even


def _copy_one(
    source: Path, target: Path, flags: dict[str, bool], *, no_backup: bool
) -> tuple[str, str]:
    """Return `(status, message)` where status is `updated` or `failed`."""
    try:
        result = ProfileWriter(source, target).apply(**flags)
        backup = None if no_backup else make_backup(target)
        write_profile(result, str(target))
    except ProfileTypeMismatchError as error:
        return "failed", str(error)
    except (InvalidProfileError, UnsupportedProfileError, OSError) as error:
        return "failed", str(error)
    suffix = "" if backup is None else f"; backup {backup.name}"
    return "updated", f"{_flag_summary(flags)}{suffix}"


def _flag_summary(flags: dict[str, bool]) -> str:
    return ", ".join(label for key, label in _FLAG_LABELS.items() if flags.get(key))
