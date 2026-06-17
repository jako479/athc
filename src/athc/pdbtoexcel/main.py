"""convert_pdb() orchestration: load config, build the workbook."""

from __future__ import annotations

from pathlib import Path

from athc.pdbtoexcel.config import load_config
from athc.pdbtoexcel.workbook_creator import PdbWorkbookCreator


def convert_pdb(
    *,
    pdb_path: str,
    output_path: str,
    pln_defense: str | None = None,
    pln_offense: str | None = None,
    pln_defense_2: str | None = None,
    pln_offense_2: str | None = None,
    play_path_override: str | None = None,
    playpool_rules_override: Path | None = None,
    skip_calcs: bool = False,
    skip_totals: bool = False,
) -> None:
    """Build an Excel workbook from a PDB and optional gameplan files."""
    config = load_config(
        play_path=play_path_override,
        playpool_rules=playpool_rules_override,
    )
    if not Path(config.play_path).is_dir():
        raise OSError(
            f"play path is not a directory: {config.play_path!r} "
            f"(set [convert-pdb] play_path in athc.ini or pass --play-path)"
        )
    calculate_totals = config.calculate_total_stats and not skip_totals

    creator = PdbWorkbookCreator.from_config(
        config,
        config.category_order,
        pdb_path,
        pln_defense,
        pln_offense,
        pln_defense_2,
        pln_offense_2,
    )
    creator.create_workbook(output_path, not skip_calcs, calculate_totals)
