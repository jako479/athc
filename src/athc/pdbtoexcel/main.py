"""convert_pdb() orchestration: build the workbook from a loaded config."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from athc.errors import StrPath
from athc.fbpro98_gameplan import GamePlan
from athc.pdbtoexcel.config import Config
from athc.pdbtoexcel.workbook_creator import PdbWorkbookCreator


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """What a conversion produced: the play rows written and every warning met
    on the way (play-pool issues, PDB and workbook notices), in the order they
    were found."""

    plays: int
    warnings: tuple[str, ...]


def convert_pdb(
    *,
    config: Config,
    pdb_path: StrPath,
    output_path: StrPath,
    pln_offense: GamePlan | None = None,
    pln_offense_2: GamePlan | None = None,
    pln_defense: GamePlan | None = None,
    pln_defense_2: GamePlan | None = None,
    percentages: bool | None = None,
    progress: Callable[[str], None] | None = None,
) -> ConversionResult:
    """Build an Excel workbook from a PDB; each game plan given fills its Slot
    column, and a column with none is hidden.

    The caller loads `config` (its play pool folder checked). `percentages`
    shows or drops the percentage columns; None takes
    `config.calculate_percentages`. `progress` hears each progress line;
    nothing is printed or logged here.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    creator = PdbWorkbookCreator.from_config(
        config,
        pdb_path,
        pln_defense=pln_defense,
        pln_offense=pln_offense,
        pln_defense_2=pln_defense_2,
        pln_offense_2=pln_offense_2,
    )
    show_percentages = (
        config.calculate_percentages if percentages is None else percentages
    )
    plays = creator.create_workbook(
        output_path, show_percentages, calculate_totals=True, progress=progress
    )
    return ConversionResult(plays, tuple(creator.warnings))
