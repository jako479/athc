"""`athc convert-pdb` — build an Excel workbook from a WinLogStats PDB."""

from __future__ import annotations

import logging
from pathlib import Path

import click
from xlsxwriter.exceptions import XlsxWriterException

from athc.pdbtoexcel.main import convert_pdb as run_conversion

PROG = "athc convert-pdb"
logger = logging.getLogger(__name__)


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


@click.command(name="convert-pdb")
@click.argument("pdbfile", type=click.Path(path_type=Path), callback=_ext(".pdb"))
@click.argument(
    "outputfile", type=click.Path(path_type=Path), callback=_ext(".xlsx", ".xlsm")
)
@click.option(
    "-o",
    "--pln-off",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="offensive game plan (.pln).",
)
@click.option(
    "-o2",
    "--pln-off-2",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="second offensive game plan (.pln).",
)
@click.option(
    "-d",
    "--pln-def",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="defensive game plan (.pln).",
)
@click.option(
    "-d2",
    "--pln-def-2",
    type=click.Path(path_type=Path),
    callback=_ext(".pln"),
    help="second defensive game plan (.pln).",
)
@click.option(
    "--play-path",
    type=click.Path(path_type=Path),
    help="play-files directory (overrides config play_path).",
)
@click.option(
    "--playpool-rules",
    type=click.Path(path_type=Path),
    callback=_ext(".toml"),
    help="playpool rules TOML for play tags (overrides config).",
)
@click.option(
    "--skip-calcs",
    is_flag=True,
    help="omit the extra calculation (percentage) columns.",
)
@click.option("--skip-totals", is_flag=True, help="omit the Total Stats team.")
@click.pass_context
def convert_pdb(
    ctx: click.Context,
    pdbfile: Path,
    outputfile: Path,
    pln_off: Path | None,
    pln_off_2: Path | None,
    pln_def: Path | None,
    pln_def_2: Path | None,
    play_path: Path | None,
    playpool_rules: Path | None,
    skip_calcs: bool,
    skip_totals: bool,
) -> None:
    """Create an Excel workbook from a WinLogStats PDB and optional FbPro 98 game plans.

    PDBFILE is a `.pdb`; OUTPUTFILE is `.xlsx` or `.xlsm` (`.xlsm` embeds sorting
    macros). Cross-reference up to two offensive (`-o`/`-o2`) and two defensive
    (`-d`/`-d2`) game plans. Exit 0 ok, 1 on an input/I/O error, 2 on usage.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    for path in (
        pdbfile,
        pln_off,
        pln_off_2,
        pln_def,
        pln_def_2,
        playpool_rules,
    ):
        if path is not None and not path.is_file():
            logger.error("%s: %s: file not found", PROG, path)
            ctx.exit(1)

    try:
        run_conversion(
            pdb_path=str(pdbfile),
            output_path=str(outputfile),
            pln_offense=str(pln_off) if pln_off else None,
            pln_offense_2=str(pln_off_2) if pln_off_2 else None,
            pln_defense=str(pln_def) if pln_def else None,
            pln_defense_2=str(pln_def_2) if pln_def_2 else None,
            play_path_override=str(play_path) if play_path else None,
            playpool_rules_override=playpool_rules,
            skip_calcs=skip_calcs,
            skip_totals=skip_totals,
        )
    except (OSError, ValueError, XlsxWriterException) as error:
        # ValueError covers InvalidPDBError / ConfigFileError / RulesFileError /
        # InvalidGamePlanError; report as one line rather than a traceback.
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
