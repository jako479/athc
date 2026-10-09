"""convert_pdb() orchestration: load config, build the workbook."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from athc.errors import ConfigFileError
from athc.pdbtoexcel.config import load_config
from athc.pdbtoexcel.workbook_creator import PdbWorkbookCreator


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """What a conversion produced: the play rows written and every warning met
    on the way (rules notices, play-pool issues, PDB and workbook notices), in
    the order they were found."""

    plays: int
    warnings: tuple[str, ...]


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
    progress: Callable[[str], None] | None = None,
) -> ConversionResult:
    """Build an Excel workbook from a PDB and optional gameplan files.

    `progress` hears each progress line; nothing is printed or logged here.
    """
    config = load_config(league)
    if not Path(config.play_path).is_dir():
        raise ConfigFileError(
            "play path is not a directory (set play_path in the league's league.toml)",
            config.play_path,
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
    plays = creator.create_workbook(
        output_path, not skip_calcs, calculate_totals=True, progress=progress
    )
    return ConversionResult(plays, tuple(creator.warnings))
