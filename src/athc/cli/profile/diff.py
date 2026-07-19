"""`athc profile diff` — show differences between two .prf profiles.

Default report goes to stdout. `--output FILE` writes it instead, format inferred
from the extension: `.txt` (the stdout text) or `.csv` (one row per change).
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

import click

from athc.cli.profile import profile
from athc.fbpro98_profile import (
    InvalidProfileError,
    ProfileType,
    UnsupportedProfileError,
    read_profile,
)
from athc.profile import ProfileDiff, SituationChange, SlotChange, diff_profiles
from athc.profile.display import category_label

PROG = "athc profile diff"
logger = logging.getLogger(__name__)

_OUTPUT_FORMATS = ("csv", "txt")


@profile.command(name="diff")
@click.argument("a", metavar="A.prf", type=click.Path(path_type=Path))
@click.argument("b", metavar="B.prf", type=click.Path(path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    metavar="FILE",
    help=(
        "Write the report to FILE instead of stdout; "
        "format from the extension (.txt or .csv)."
    ),
)
@click.pass_context
def diff(ctx: click.Context, a: Path, b: Path, output: Path | None) -> None:
    """Show the differences between two .prf coaching profiles (same side only).

    Compares situations, PAT situations, substitution percentages, field-goal
    range, and audibles; only changed records are shown.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fmt = None
    if output is not None:
        fmt = _infer_format(output)
        if fmt is None:
            logger.error(
                "%s: %s: can't infer format from extension; use .txt or .csv",
                PROG,
                output,
            )
            ctx.exit(2)

    profiles = []
    for path in (a, b):
        try:
            profiles.append(read_profile(str(path)))
        except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
            logger.error("%s: %s: %s", PROG, path, error)
            ctx.exit(2)
    pa, pb = profiles
    if pa.profile_type != pb.profile_type:
        logger.error(
            "%s: cannot diff %s against %s (%s vs %s)",
            PROG,
            a,
            b,
            pa.profile_type.name,
            pb.profile_type.name,
        )
        ctx.exit(2)

    result = diff_profiles(pa, pb)
    if fmt is None:
        click.echo(render(result, str(a), str(b)))
    else:
        content = (
            render_csv(result, str(a), str(b))
            if fmt == "csv"
            else render(result, str(a), str(b)) + "\n"
        )
        try:
            output.write_bytes(content.encode("utf-8"))  # type: ignore[union-attr]
        except OSError as error:
            logger.error("%s: %s: %s", PROG, output, error)
            ctx.exit(2)
    ctx.exit(0 if result.is_empty else 1)


def render(result: ProfileDiff, a_name: str, b_name: str) -> str:
    """Render a `ProfileDiff` as the text report."""
    if result.is_empty:
        return f"{a_name} and {b_name} are identical."
    lines = [f"{a_name} -> {b_name}", ""]
    if result.profile:
        lines.append("[profile]")
        lines.extend(f"  {c.path}: {c.old} -> {c.new}" for c in result.profile)
        lines.append("")
    for header, changes in (("situations", result.situations), ("pat", result.pat)):
        if changes:
            lines.append(f"[{header}] {len(changes)} changed")
            lines.extend(
                f"  {_situation_line(c, result.profile_type)}" for c in changes
            )
            lines.append("")
    lines.append(_summary(result))
    return "\n".join(lines)


def _situation_line(c: SituationChange, profile_type: ProfileType) -> str:
    parts: list[str] = []
    if c.stop is not None:
        parts.append(f"stop {c.stop.old}->{c.stop.new}")
    parts.extend(_slot_text(s, profile_type) for s in c.slots)
    return f"#{c.number}  {c.label}  | {'  '.join(parts)}"


def _slot_text(s: SlotChange, profile_type: ProfileType) -> str:
    (old_code, old_wt), (new_code, new_wt) = s.old, s.new
    if old_code == new_code:  # weight-only change
        return f"{category_label(old_code, profile_type)} {old_wt}->{new_wt}"
    old_label = category_label(old_code, profile_type)
    new_label = category_label(new_code, profile_type)
    if (
        old_label == new_label
    ):  # same display, different code (defense pass direction) — show codes
        old_label, new_label = f"0x{old_code:02X}", f"0x{new_code:02X}"
    return f"{old_label} {old_wt} -> {new_label} {new_wt}"


def _summary(result: ProfileDiff) -> str:
    return (
        f"{len(result.situations)} situation(s), {len(result.pat)} PAT, "
        f"{len(result.profile)} profile field(s) differ."
    )


_CSV_COLUMNS = (
    "sit", "minutes", "down", "yards", "field", "spread", "stop_old", "stop_new",
    "slot1_old", "slot1_new", "slot2_old", "slot2_new", "slot3_old", "slot3_new",
)  # fmt: skip


def render_csv(result: ProfileDiff, a_name: str, b_name: str) -> str:
    """CSV: one row per change; whole-profile changes as a leading `#` block."""
    buf = io.StringIO()
    writer = csv.writer(buf)  # Excel-friendly \r\n line endings
    writer.writerow([f"# {a_name} -> {b_name}"])
    writer.writerows([f"# {c.path}: {c.old} -> {c.new}"] for c in result.profile)
    writer.writerow(_CSV_COLUMNS)
    writer.writerows(
        _csv_row(c, result.profile_type, pat=False) for c in result.situations
    )
    writer.writerows(_csv_row(c, result.profile_type, pat=True) for c in result.pat)
    return buf.getvalue()


def _csv_row(c: SituationChange, profile_type: ProfileType, *, pat: bool) -> list[str]:
    # Label tokens: situation = "min down yards field spread", PAT = "min spread".
    parts = c.label.split()
    if pat:
        sit, (minutes, spread), (down, yards, field) = (
            f"PAT {c.number}",
            parts,
            ("", "", ""),
        )
        stop_old = stop_new = ""
    else:
        sit, (minutes, down, yards, field, spread) = str(c.number), parts
        stop_old, stop_new = (c.stop.old, c.stop.new) if c.stop else ("", "")
    slots = ["", "", "", "", "", ""]
    for s in c.slots:
        slots[(s.slot - 1) * 2], slots[(s.slot - 1) * 2 + 1] = _slot_cells(
            s, profile_type
        )
    return [sit, minutes, down, yards, field, spread, stop_old, stop_new, *slots]


def _slot_cells(s: SlotChange, profile_type: ProfileType) -> tuple[str, str]:
    """`(old, new)` cells like `RM:8`; raw codes when both collapse to one label."""
    (old_code, old_wt), (new_code, new_wt) = s.old, s.new
    old_label = category_label(old_code, profile_type)
    new_label = category_label(new_code, profile_type)
    if (
        old_code != new_code and old_label == new_label
    ):  # defense pass direction — disambiguate
        old_label, new_label = f"0x{old_code:02X}", f"0x{new_code:02X}"
    return f"{old_label}:{old_wt}", f"{new_label}:{new_wt}"


def _infer_format(output: Path) -> str | None:
    """Infer `txt`/`csv` from `output`'s extension, or None if unrecognized."""
    fmt = output.suffix.lstrip(".").lower()
    return fmt if fmt in _OUTPUT_FORMATS else None
