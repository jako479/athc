"""Orchestrates PDB -> Excel workbook creation.

Joins plays to the play pool, computes totals and category aggregates, sorts by
the league's category order, and dispatches rows to ExcelPdbWorkbook. Plays are
grouped by their category (from the play file), shown under the league's label.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from os import PathLike

from athc.fbpro98_gameplan import GamePlan, read_gameplan
from athc.fbpro98_play import PlayCategory
from athc.pdbtoexcel.config import Config
from athc.pdbtoexcel.excel_workbook import ExcelPdbWorkbook
from athc.pdbtoexcel.pdb import PDB, PLAY_DATA
from athc.playpool import (
    Play,
    PlayPool,
    load_rules,
    read_play_pool,
    rule_warnings,
)

StrPath = str | PathLike[str]

ResolvedPlay = tuple[PLAY_DATA, str, str, Play]


class PdbWorkbookCreator:
    """Reads a PDB, joins plays to the pool, writes via ExcelPdbWorkbook."""

    def __init__(
        self,
        config: Config,
        play_pool: PlayPool,
        pdb: PDB,
        pln_defense: GamePlan | None = None,
        pln_offense: GamePlan | None = None,
        pln_defense_2: GamePlan | None = None,
        pln_offense_2: GamePlan | None = None,
    ) -> None:
        self.config = config
        self.play_pool = play_pool
        self.pdb = pdb
        # Every notice met while reading the inputs and writing the workbook,
        # in order; the command decides how to show them.
        self.warnings: list[str] = []
        # Deleted plays match case-insensitively (the pool's names do too).
        self._deleted_upper = {name.upper() for name in config.deleted_plays}
        self.pln_defense = pln_defense
        self.pln_offense = pln_offense
        self.pln_defense_2 = pln_defense_2
        self.pln_offense_2 = pln_offense_2

    @classmethod
    def from_config(
        cls,
        config: Config,
        pdb_filename: StrPath,
        pln_def_filename: StrPath | None = None,
        pln_off_filename: StrPath | None = None,
        pln_def_filename_2: StrPath | None = None,
        pln_off_filename_2: StrPath | None = None,
    ) -> PdbWorkbookCreator:
        """Build all dependencies from file paths. Tests call `__init__` with fakes.

        The playpool rules' include / exclude names are checked against the pool
        once it is read; each problem, each play-pool issue and each PDB notice
        lands in the creator's `warnings`."""
        notices: list[str] = []
        if config.playpool_rules:
            rules = load_rules(config.playpool_rules)
            play_pool = read_play_pool(
                config.play_path, rules=rules, labels=config.categories
            )
            name = config.playpool_rules.name
            notices.extend(f"{name}: {m}" for m in rule_warnings(play_pool, rules))
        else:
            play_pool = read_play_pool(config.play_path, labels=config.categories)
        notices.extend(play_pool.issues)
        pdb = PDB(str(pdb_filename))
        notices.extend(pdb.warnings)
        pdb.convert_invalid_play_data(play_pool)
        creator = cls(
            config,
            play_pool,
            pdb,
            read_gameplan(pln_def_filename) if pln_def_filename else None,
            read_gameplan(pln_off_filename) if pln_off_filename else None,
            read_gameplan(pln_def_filename_2) if pln_def_filename_2 else None,
            read_gameplan(pln_off_filename_2) if pln_off_filename_2 else None,
        )
        creator.warnings.extend(notices)
        return creator

    def create_workbook(
        self,
        filename: StrPath,
        perform_calculations: bool,
        calculate_totals: bool,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> int:
        """Build the Excel workbook at `filename`; returns the play rows written.

        `perform_calculations=False` omits derived percentage columns.
        `calculate_totals=True` appends a "Total Stats" team summing all teams.
        `progress` hears each progress line; nothing is printed or logged here.
        """
        say = progress or (lambda _: None)
        say(f"Creating '{filename}'")
        self._warn_stale_deleted_plays()
        offense_slots = (1 if self.pln_offense else 0) + (
            1 if self.pln_offense_2 else 0
        )
        defense_slots = (1 if self.pln_defense else 0) + (
            1 if self.pln_defense_2 else 0
        )

        with ExcelPdbWorkbook(
            self.config, filename, perform_calculations, offense_slots, defense_slots
        ) as workbook:
            combined_plays: dict[bytes, PLAY_DATA] | None = (
                {} if calculate_totals else None
            )

            resolved_plays: list[ResolvedPlay] = list(self._iter_source_plays())
            if combined_plays is not None:
                for play_in_pdb, *_ in resolved_plays:
                    self._add_to_total_play(combined_plays, play_in_pdb)

            resolved_plays.sort(
                key=lambda x: (
                    x[0].team_name,
                    self._category_rank(x[3], x[0].play_type),
                    x[0].play_name,
                )
            )
            for play_in_pdb, play_name, _, play_record in resolved_plays:
                workbook.add_play(
                    play_in_pdb,
                    self._get_play_slots(play_in_pdb, play_name),
                    play_record,
                )

            if combined_plays is not None:
                self._add_total_plays(workbook, combined_plays)

            for tendency_data in self.pdb.tendencies:
                workbook.add_tendency(tendency_data)

            if self.config.include_category_worksheets:
                self._add_category_worksheets(
                    workbook, resolved_plays, calculate_totals
                )

        return len(resolved_plays)

    def _warn_stale_deleted_plays(self) -> None:
        """A `[deleted_plays]` entry that is still in the pool is stale; say so
        (its stats are skipped all the same)."""
        for name in sorted(self.config.deleted_plays):
            if self.play_pool.find_by_name(name) is not None:
                self.warnings.append(
                    f"'{name}' is listed in [deleted_plays] but is in the play "
                    "pool; its stats are skipped"
                )

    def _category_rank(self, play_record: Play, play_type: PLAY_DATA.PLAY_TYPE) -> int:
        return self.config.category_order[play_type].index(play_record.category)

    def _iter_tracked_plays(self) -> Iterator[PLAY_DATA]:
        for play_type in (
            PLAY_DATA.PLAY_TYPE.RUN,
            PLAY_DATA.PLAY_TYPE.PASS,
            PLAY_DATA.PLAY_TYPE.DEFENSE,
        ):
            yield from sorted(
                self.pdb.plays[play_type].values(), key=lambda x: x.team_name
            )

    def _iter_source_plays(self) -> Iterator[ResolvedPlay]:
        """Every exportable PDB stat line with its pool record. A deleted play is
        skipped quietly; a play missing from the pool is skipped with one
        warning per name, not per team."""
        missing: set[str] = set()
        for play_in_pdb in self._iter_tracked_plays():
            play_name = play_in_pdb.play_name.decode("ASCII")
            team_name = play_in_pdb.team_name.decode("ASCII")
            if play_name.upper() in self._deleted_upper:
                continue
            play_record = self.play_pool.find_by_name(play_name)
            if play_record is None:
                if play_name not in missing:
                    self.warnings.append(f"Play file not found for play '{play_name}'")
                    missing.add(play_name)
                continue
            if self._should_export(play_in_pdb, play_record):
                yield play_in_pdb, play_name, team_name, play_record

    def _should_export(self, play_in_pdb: PLAY_DATA, play_record: Play) -> bool:
        """Skip special-teams plays and any whose category is not in the league's
        order for its PDB play type (unlisted on purpose, or misclassified)."""
        if play_record.play_file.is_special_teams:
            return False
        return play_record.category in self.config.category_order[play_in_pdb.play_type]

    def _get_play_slots(
        self, play_in_pdb: PLAY_DATA, play_name: str
    ) -> tuple[str, str]:
        if play_in_pdb.play_type in (PLAY_DATA.PLAY_TYPE.RUN, PLAY_DATA.PLAY_TYPE.PASS):
            plan_1, plan_2 = self.pln_offense, self.pln_offense_2
        elif play_in_pdb.play_type == PLAY_DATA.PLAY_TYPE.DEFENSE:
            plan_1, plan_2 = self.pln_defense, self.pln_defense_2
        else:
            return ("", "")
        return (
            self._format_slot(self._find_slot(plan_1, play_name)) if plan_1 else "",
            self._format_slot(self._find_slot(plan_2, play_name)) if plan_2 else "",
        )

    @staticmethod
    def _find_slot(plan: GamePlan, play_name: str) -> int | None:
        target = play_name.casefold()
        for index, play in enumerate(plan.normal_plays):
            if play is not None and play.name.casefold() == target:
                return index
        return None

    @staticmethod
    def _format_slot(slot: int | None) -> str:
        if slot is None:
            return ""
        return f"{slot // 4 + 1}-{slot % 4 + 1}"

    def _add_total_plays(
        self, workbook: ExcelPdbWorkbook, combined_plays: dict[bytes, PLAY_DATA]
    ) -> None:
        plays_to_write: list[tuple[PLAY_DATA, Play]] = []
        for play_in_pdb in combined_plays.values():
            play_record = self.play_pool.find_by_name(
                play_in_pdb.play_name.decode("ASCII")
            )
            if play_record is not None and self._should_export(
                play_in_pdb, play_record
            ):
                plays_to_write.append((play_in_pdb, play_record))

        plays_to_write.sort(
            key=lambda x: (self._category_rank(x[1], x[0].play_type), x[0].play_name)
        )
        for play_in_pdb, play_record in plays_to_write:
            play_name = play_in_pdb.play_name.decode("ASCII")
            workbook.add_play(
                play_in_pdb, self._get_play_slots(play_in_pdb, play_name), play_record
            )

    def _add_category_worksheets(
        self,
        workbook: ExcelPdbWorkbook,
        resolved_plays: list[ResolvedPlay],
        calculate_totals: bool,
    ) -> None:
        team_categories: dict[tuple[str, PlayCategory], PLAY_DATA] = {}
        categories: dict[PlayCategory, PLAY_DATA] = {}
        for play_in_pdb, _, team_name, play_record in resolved_plays:
            category = play_record.category
            self._add_to_category(team_categories, play_in_pdb, (team_name, category))
            if calculate_totals:
                self._add_to_category(categories, play_in_pdb, category)

        label = self.config.categories.label
        for (team, category), category_data in team_categories.items():
            workbook.add_category((team, label(category)), category_data)
        if calculate_totals:
            ordered = sorted(
                categories.items(),
                key=lambda x: self.config.category_order[x[1].play_type].index(x[0]),
            )
            for category, category_data in ordered:
                workbook.add_category(("Total Stats", label(category)), category_data)

    @staticmethod
    def _add_to_total_play(
        combined_plays: dict[bytes, PLAY_DATA], play_in_pdb: PLAY_DATA
    ) -> None:
        combined = combined_plays.get(play_in_pdb.play_name)
        if combined is None:
            combined = PLAY_DATA()
            combined.play_type = play_in_pdb.play_type
            combined.team_name = b"Total Stats"
            combined.play_name = play_in_pdb.play_name
        combined += play_in_pdb
        combined_plays[play_in_pdb.play_name] = combined

    @staticmethod
    def _add_to_category(target, play_in_pdb: PLAY_DATA, key) -> None:
        data = target.get(key)
        if data is None:
            data = PLAY_DATA()
            data.play_type = play_in_pdb.play_type
        data += play_in_pdb
        target[key] = data
