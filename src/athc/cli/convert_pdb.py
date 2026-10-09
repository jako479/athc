"""`athc convert-pdb` — build an Excel workbook from a WinLogStats PDB."""

from __future__ import annotations

from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli._files import named_file
from athc.console import console
from athc.pdbtoexcel.main import convert_pdb as run_conversion


def _ext(*extensions: str):
    """Click callback that rejects a path without one of `extensions`."""

    def callback(ctx: click.Context, param: click.Parameter, value):
        if value is None:
            return None
        paths = value if isinstance(value, tuple) else (value,)
        for path in paths:
            if Path(path).suffix.lower() not in extensions:
                raise click.BadParameter(
                    f"must have a {' or '.join(extensions)} extension", ctx, param
                )
        return value

    return callback


@click.command(name="convert-pdb", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.argument(
    "pdbfile",
    metavar="pdb_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pdb"),
)
@click.argument(
    "outputfile",
    metavar="output_file",
    type=click.Path(path_type=Path),
    callback=_ext(".xlsx", ".xlsm"),
)
@click.option(
    "-o",
    "--pln-off",
    metavar="pln_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="Offensive game plan (.pln).",
)
@click.option(
    "-o2",
    "--pln-off-2",
    metavar="pln_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="Second offensive game plan (.pln).",
)
@click.option(
    "-d",
    "--pln-def",
    metavar="pln_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="Defensive game plan (.pln).",
)
@click.option(
    "-d2",
    "--pln-def-2",
    metavar="pln_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="Second defensive game plan (.pln).",
)
@click.option(
    "--skip-calcs",
    is_flag=True,
    help="Omit the extra calculation (percentage) columns.",
)
@league_option
def convert_pdb(
    pdbfile: Path,
    outputfile: Path,
    pln_off: Path | None,
    pln_off_2: Path | None,
    pln_def: Path | None,
    pln_def_2: Path | None,
    skip_calcs: bool,
    league: str | None,
) -> None:
    """Create an Excel workbook from a WinLogStats PDB and optional game plans.

    pdb_file is a `.pdb`; output_file is `.xlsx` or `.xlsm` (`.xlsm` embeds sorting
    macros). Cross-reference up to two offensive (`-o`/`-o2`) and two defensive
    (`-d`/`-d2`) Front Page Sports Football Pro '98 game plans.
    """
    for path in (pdbfile, pln_off, pln_off_2, pln_def, pln_def_2):
        if path is not None:
            named_file(path)
    result = run_conversion(
        pdb_path=str(pdbfile),
        output_path=str(outputfile),
        league=league,
        pln_offense=str(pln_off) if pln_off else None,
        pln_offense_2=str(pln_off_2) if pln_off_2 else None,
        pln_defense=str(pln_def) if pln_def else None,
        pln_defense_2=str(pln_def_2) if pln_def_2 else None,
        skip_calcs=skip_calcs,
        progress=console.progress,
    )
    for warning in result.warnings:
        console.warn(warning)
    console.ok(f"{outputfile}: {result.plays} play(s)")
