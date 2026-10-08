"""convert_pdb() orchestration: load config, build the workbook."""

from __future__ import annotations

from pathlib import Path

from athc.pdbtoexcel.config import load_config
from athc.pdbtoexcel.workbook_creator import PdbWorkbookCreator


def convert_pdb(
    *,
    pdb_path: str,
    output_path: str,
    league: str | None = None,
    pln_defense: str | None = None,
    pln_offense: str | None = None,
    pln_defense_2: str | None = None,
    pln_offense_2: str | None = None,
    skip_calcs: bool = False,
) -> None:
    """Build an Excel workbook from a PDB and optional gameplan files."""
    config = load_config(league)
    if not Path(config.play_path).is_dir():
        raise OSError(
            f"play path is not a directory: {config.play_path!r} "
            f"(set play_path in the league's league.toml)"
        )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    creator = PdbWorkbookCreator.from_config(
        config,
        pdb_path,
        pln_defense,
        pln_offense,
        pln_defense_2,
        pln_offense_2,
    )
    creator.create_workbook(output_path, not skip_calcs, calculate_totals=True)
