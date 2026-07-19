"""Excel workbook construction for PDB exports.

Owns the xlsxwriter lifecycle, defines worksheet layouts (columns, headers,
formats, named ranges), and renders rows handed in by the orchestrator. Knows
nothing about PDB or play pools beyond a play's category + a few attributes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import xlsxwriter
from xlsxwriter.worksheet import Worksheet

from athc.pdbtoexcel.config import CategoryOrder, Config, get_runtime_path
from athc.pdbtoexcel.pdb import PLAY_DATA
from athc.playpool import DefensivePlay, OffensivePlay, Play


@dataclass
class _WorksheetState:
    worksheet: Worksheet
    rows: int = 1


# xlsxwriter.format.Format has no type stubs; use Any to avoid false errors.
@dataclass
class _Formats:
    text: Any
    avg: Any
    percent_0: Any
    percent_1: Any
    center: Any
    options_normal: Any
    options_header: Any
    options_header2: Any
    options_option: Any
    options_note: Any


class ExcelPdbWorkbook:
    """Builds the workbook: layouts, row writers, formats, named ranges, VBA."""

    def __init__(
        self,
        config: Config,
        category_order: CategoryOrder,
        filename,
        perform_calculations,
        offense_slot_count: int = 0,
        defense_slot_count: int = 0,
    ):
        self.config = config
        self.category_order = category_order
        self.filename = Path(filename)
        self.macros_are_enabled = self.filename.suffix.lower() == ".xlsm"
        self.show_percentages = perform_calculations and config.calculate_percentages
        self.offense_slot_count = offense_slot_count
        self.defense_slot_count = defense_slot_count

    @staticmethod
    def _slot_options(slot_count: int, slot_index: int) -> dict | None:
        """xlsxwriter column options to hide slots not backed by a gameplan.

        slot_index is 1 or 2 (1-based). 0 gameplans hides both; 1 hides only
        Slot-2; 2 keeps both visible.
        """
        if slot_count < slot_index:
            return {"hidden": True}
        return None

    def __enter__(self):
        self.filename.parent.mkdir(exist_ok=True)

        self.workbook = xlsxwriter.Workbook(self.filename)
        self.fmt = self._create_formats()
        self._create_options_worksheet()
        self.run = self._create_run_worksheet()
        self.pass_ = self._create_pass_worksheet()
        self.def_ = self._create_def_worksheet()
        self.tendencies = self._create_tendencies_worksheet()

        self.run_categories: _WorksheetState | None = None
        self.pass_categories: _WorksheetState | None = None
        self.def_categories: _WorksheetState | None = None
        if self.config.include_category_worksheets:
            self.run_categories = self._create_run_categories_worksheet()
            self.pass_categories = self._create_pass_categories_worksheet()
            self.def_categories = self._create_def_categories_worksheet()

        return self

    def __exit__(self, *args):
        if self.workbook:
            if self.macros_are_enabled:
                self._add_conditional_format()
                if self.config.include_category_worksheets:
                    self.workbook.add_vba_project(
                        str(get_runtime_path("vbaProject_categories.bin"))
                    )
                else:
                    self.workbook.add_vba_project(
                        str(get_runtime_path("vbaProject.bin"))
                    )
            self.workbook.close()

    # -- Public API -----------------------------------------------------------

    def add_play(self, play_data, play_slots, play_record):
        if play_data.play_type == PLAY_DATA.PLAY_TYPE.RUN:
            self._add_run_play(play_data, play_slots, play_record)
        elif play_data.play_type == PLAY_DATA.PLAY_TYPE.PASS:
            self._add_pass_play(play_data, play_slots, play_record)
        elif play_data.play_type == PLAY_DATA.PLAY_TYPE.DEFENSE:
            self._add_defense_play(play_data, play_slots, play_record)

    def add_category(self, team_category, category_data):
        if category_data.play_type == PLAY_DATA.PLAY_TYPE.RUN:
            self._add_run_category(team_category, category_data)
        elif category_data.play_type == PLAY_DATA.PLAY_TYPE.PASS:
            self._add_pass_category(team_category, category_data)
        elif category_data.play_type == PLAY_DATA.PLAY_TYPE.DEFENSE:
            self._add_defense_category(team_category, category_data)

    def add_tendency(self, t):
        team = t.team_name.decode("ASCII")
        downs = [
            ("First", "first_down"),
            ("Second", "second_down"),
            ("Third", "third_down"),
            ("Fourth", "fourth_down"),
        ]
        buckets = [
            ("0-1", t.run_zero_to_one, t.pass_zero_to_one),
            ("2-5", t.run_two_to_five, t.pass_two_to_five),
            ("6-10", t.run_six_to_ten, t.pass_six_to_ten),
            ("10+", t.run_ten_plus, t.pass_ten_plus),
        ]
        for down_label, down_attr in downs:
            for bucket_label, run_data, pass_data in buckets:
                row_data = [
                    team,
                    f"{down_label} and {bucket_label}",
                    getattr(run_data, down_attr),
                    getattr(pass_data, down_attr),
                ]
                self.tendencies.worksheet.write_row(self.tendencies.rows, 0, row_data)
                self.tendencies.rows += 1

    # -- Worksheet creation ---------------------------------------------------

    def _create_formats(self) -> _Formats:
        return _Formats(
            text=self.workbook.add_format({"num_format": "@"}),
            avg=self.workbook.add_format({"num_format": "0.0"}),
            percent_0=self.workbook.add_format({"num_format": "0%"}),
            percent_1=self.workbook.add_format({"num_format": "0.0%"}),
            center=self.workbook.add_format({"align": "center"}),
            options_normal=self.workbook.add_format({"font_size": 10}),
            options_header=self.workbook.add_format(
                {"bg_color": "#FABF8F", "bold": True, "font_size": 10}
            ),
            options_header2=self.workbook.add_format(
                {"bg_color": "#FDE9D9", "bold": True, "font_size": 10}
            ),
            options_option=self.workbook.add_format(
                {
                    "bg_color": "#FFFF00",
                    "bold": True,
                    "font_size": 10,
                    "border": 2,
                    "border_color": "black",
                }
            ),
            options_note=self.workbook.add_format(
                {"bg_color": "#FDE9D9", "bold": True, "font_size": 8}
            ),
        )

    def _create_options_worksheet(self) -> None:
        ws = self.workbook.add_worksheet("Options")
        ws.set_vba_name("wsOptions")
        ws.set_column(0, 16383, None, self.fmt.options_normal)
        ws.set_column_pixels(0, 0, 6)
        # OPTIONS
        ws.write_row(0, 1, ["OPTIONS"] + [""] * 4, self.fmt.options_header)
        ws.write_row(
            1, 1, ["Highlight Selected Row"] + [""] * 4, self.fmt.options_header2
        )
        ws.data_validation(2, 1, 2, 1, {"validate": "list", "source": ["Yes", "No"]})
        ws.write(2, 1, "Yes", self.fmt.options_option)
        ws.write_row(
            2,
            2,
            ["""      (when "Yes", hold [Ctrl] to paste data)"""] + [""] * 3,
            self.fmt.options_note,
        )
        # CATEGORY ORDER
        ws.set_column_pixels(7, 9, 81)
        ws.write_row(0, 7, ["CATEGORY ORDER", "", ""], self.fmt.options_header)
        ws.write_row(1, 7, ["RUN", "PASS", "DEFENSE"], self.fmt.options_header2)
        ws.write_column(2, 7, self.category_order[PLAY_DATA.PLAY_TYPE.RUN])
        ws.write_column(2, 8, self.category_order[PLAY_DATA.PLAY_TYPE.PASS])
        ws.write_column(2, 9, self.category_order[PLAY_DATA.PLAY_TYPE.DEFENSE])
        # NOTES
        ws.write_row(0, 11, ["NOTES"] + [""] * 9, self.fmt.options_header)
        note = (
            "1. Play data columns (attempts, yards, etc.) utilize bi-directional sort; "
            "All other columns sort in ascending order only."
        )
        ws.write(1, 11, note)
        note = (
            "2. Built-in columns can be sorted by double-clicking anywhere in the "
            "column (i.e. double-click does not invoke data editor)."
        )
        ws.write(2, 11, note)
        note = (
            "3. Sort user-added columns by double-clicking populated column header "
            "(retains double-click to invoke data editor)."
        )
        ws.write(3, 11, note)
        # Named ranges
        run_last = 2 + len(self.category_order[PLAY_DATA.PLAY_TYPE.RUN])
        pass_last = 2 + len(self.category_order[PLAY_DATA.PLAY_TYPE.PASS])
        def_last = 2 + len(self.category_order[PLAY_DATA.PLAY_TYPE.DEFENSE])
        self.workbook.define_name("HighlightSelectedRow", "=Options!$B$3")
        self.workbook.define_name("RunCategoryOrder", f"=Options!$H$3:$H${run_last}")
        self.workbook.define_name("PassCategoryOrder", f"=Options!$I$3:$I${pass_last}")
        self.workbook.define_name(
            "DefenseCategoryOrder", f"=Options!$J$3:$J${def_last}"
        )

    def _create_run_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Run Plays")
        ws.set_vba_name("wsRunPlays")
        header = [
            "Team",
            "Category",
            "Slot 1",
            "Slot 2",
            "Play",
            "Type",
            "Rushes",
            "Yards",
            "Avg",
            "Fumbles",
            "TD",
        ]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 80)
        ws.set_column_pixels(
            2, 2, 57, self.fmt.text, self._slot_options(self.offense_slot_count, 1)
        )
        ws.set_column_pixels(
            3, 3, 57, self.fmt.text, self._slot_options(self.offense_slot_count, 2)
        )
        ws.set_column_pixels(4, 4, 100)
        ws.set_column_pixels(5, 5, 59)
        ws.set_column_pixels(8, 8, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(10, "Fumble %")
            ws.set_column_pixels(10, 10, 68, self.fmt.percent_1)
            header.insert(12, "TD %")
            ws.set_column_pixels(12, 12, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:D1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_pass_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Pass Plays")
        ws.set_vba_name("wsPassPlays")
        header = [
            "Team",
            "Category",
            "Slot 1",
            "Slot 2",
            "Play",
            "Type",
            "Comp",
            "Att",
            "Comp %",
            "Yards",
            "Y/Comp",
            "Y/Att",
            "Fumbles",
            "Int",
            "Sacks",
            "TD",
        ]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 80)
        ws.set_column_pixels(
            2, 2, 57, self.fmt.text, self._slot_options(self.offense_slot_count, 1)
        )
        ws.set_column_pixels(
            3, 3, 57, self.fmt.text, self._slot_options(self.offense_slot_count, 2)
        )
        ws.set_column_pixels(4, 4, 100)
        ws.set_column_pixels(5, 5, 49)
        ws.set_column_pixels(8, 8, None, self.fmt.percent_0)
        ws.set_column_pixels(10, 10, None, self.fmt.avg)
        ws.set_column_pixels(11, 11, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(14, "Int %")
            ws.set_column_pixels(14, 14, None, self.fmt.percent_1)
            header.insert(16, "Sack %")
            ws.set_column_pixels(16, 16, None, self.fmt.percent_1)
            header.insert(18, "TD %")
            ws.set_column_pixels(18, 18, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:D1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_def_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Def Plays")
        ws.set_vba_name("wsDefPlays")
        header = [
            "Team",
            "Category",
            "Slot 1",
            "Slot 2",
            "Play",
            "Type",
            "Calls",
            "Yards",
            "Avg",
            "vs Run",
            "Yards",
            "Avg",
            "vs Pass",
            "Yards",
            "Avg",
            "Fumbles",
            "Int",
            "Sacks",
            "TD/Def",
            "TD/Off",
        ]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 100)
        ws.set_column_pixels(
            2, 2, 57, self.fmt.text, self._slot_options(self.defense_slot_count, 1)
        )
        ws.set_column_pixels(
            3, 3, 57, self.fmt.text, self._slot_options(self.defense_slot_count, 2)
        )
        ws.set_column_pixels(4, 4, 100)
        ws.set_column_pixels(5, 5, 37)
        ws.set_column_pixels(8, 8, None, self.fmt.avg)
        ws.set_column_pixels(11, 11, None, self.fmt.avg)
        ws.set_column_pixels(14, 14, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(17, "Int %")
            ws.set_column_pixels(17, 17, None, self.fmt.percent_1)
            header.insert(19, "Sack %")
            ws.set_column_pixels(19, 19, None, self.fmt.percent_1)
            header.insert(22, "TD/Off %")
            ws.set_column_pixels(22, 22, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:D1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_tendencies_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Tendencies")
        ws.set_vba_name("wsTendencies")
        header = ["Team", "Situation", "Runs", "Passes"]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 125)
        ws.set_column_pixels(2, 2, 56)
        ws.set_column_pixels(3, 3, 56)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:B1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_run_categories_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Run Categories")
        ws.set_vba_name("wsRunCategories")
        header = ["Team", "Category", "Rushes", "Yards", "Avg", "Fumbles", "TD"]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 80)
        ws.set_column_pixels(4, 4, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(6, "Fumble %")
            ws.set_column_pixels(6, 6, 68, self.fmt.percent_1)
            header.insert(8, "TD %")
            ws.set_column_pixels(8, 8, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:B1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_pass_categories_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Pass Categories")
        ws.set_vba_name("wsPassCategories")
        header = [
            "Team",
            "Category",
            "Comp",
            "Att",
            "Comp %",
            "Yards",
            "Y/Comp",
            "Y/Att",
            "Fumbles",
            "Int",
            "Sacks",
            "TD",
        ]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 80)
        ws.set_column_pixels(4, 4, None, self.fmt.percent_0)
        ws.set_column_pixels(6, 6, None, self.fmt.avg)
        ws.set_column_pixels(7, 7, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(10, "Int %")
            ws.set_column_pixels(10, 10, None, self.fmt.percent_1)
            header.insert(12, "Sack %")
            ws.set_column_pixels(12, 12, None, self.fmt.percent_1)
            header.insert(14, "TD %")
            ws.set_column_pixels(14, 14, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:B1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    def _create_def_categories_worksheet(self) -> _WorksheetState:
        ws = self.workbook.add_worksheet("Def Categories")
        ws.set_vba_name("wsDefCategories")
        header = [
            "Team",
            "Category",
            "Calls",
            "Yards",
            "Avg",
            "vs Run",
            "Yards",
            "Avg",
            "vs Pass",
            "Yards",
            "Avg",
            "Fumbles",
            "Int",
            "Sacks",
            "TD/Def",
            "TD/Off",
        ]
        ws.set_column_pixels(0, 0, 115)
        ws.set_column_pixels(1, 1, 100)
        ws.set_column_pixels(4, 4, None, self.fmt.avg)
        ws.set_column_pixels(7, 7, None, self.fmt.avg)
        ws.set_column_pixels(10, 10, None, self.fmt.avg)
        if self.show_percentages:
            header.insert(13, "Int %")
            ws.set_column_pixels(13, 13, None, self.fmt.percent_1)
            header.insert(15, "Sack %")
            ws.set_column_pixels(15, 15, None, self.fmt.percent_1)
            header.insert(18, "TD/Off %")
            ws.set_column_pixels(18, 18, None, self.fmt.percent_1)
        ws.write_row(0, 0, header)
        ws.freeze_panes(1, 0)
        ws.autofilter("A1:B1")  # pyright: ignore[reportCallIssue]
        return _WorksheetState(ws)

    # -- Row writers ----------------------------------------------------------

    def _add_run_play(self, play_data, play_slots, play_record: Play):
        play_type = (
            "QB draw"
            if isinstance(play_record, OffensivePlay) and play_record.qb_draw
            else ""
        )

        avg = (
            int(play_data.total_yards) / int(play_data.play_count)
            if play_data.play_count > 0
            else 0.0
        )

        slot_1, slot_2 = play_slots
        row_data = [
            play_data.team_name.decode("ASCII"),
            play_record.category.long,
            slot_1,
            slot_2,
            play_data.play_name.decode("ASCII"),
            play_type,
            play_data.play_count,
            play_data.total_yards,
            round(avg, 1),
            play_data.fumbles,
            play_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                10, round(int(play_data.fumbles) / int(play_data.play_count), 3)
            )
            row_data.insert(
                12,
                round(int(play_data.touchdowns_offense) / int(play_data.play_count), 3),
            )

        self.run.worksheet.write_row(self.run.rows, 0, row_data)
        self.run.rows += 1

    def _add_pass_play(self, play_data, play_slots, play_record: Play):
        play_type = (
            "Screen"
            if isinstance(play_record, OffensivePlay) and play_record.screen
            else ""
        )

        play_count = int(play_data.play_count)
        sacks = int(play_data.sacks)
        att = (
            play_count - sacks
            if self.config.exclude_sacks_from_pass_attempts
            else play_count
        )

        avg_per_completion = (
            int(play_data.total_yards) / int(play_data.completions)
            if play_data.completions > 0
            else 0.0
        )
        avg_per_attempt = int(play_data.total_yards) / att if att > 0 else 0.0

        slot_1, slot_2 = play_slots
        row_data = [
            play_data.team_name.decode("ASCII"),
            play_record.category.long,
            slot_1,
            slot_2,
            play_data.play_name.decode("ASCII"),
            play_type,
            play_data.completions,
            att,
            round(int(play_data.completions) / att, 2) if att > 0 else 0,
            play_data.total_yards,
            round(avg_per_completion, 1),
            round(avg_per_attempt, 1),
            play_data.fumbles,
            play_data.interceptions,
            play_data.sacks,
            play_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                14, round(int(play_data.interceptions) / att, 3) if att > 0 else 0
            )
            row_data.insert(16, round(sacks / play_count, 3) if play_count > 0 else 0)
            row_data.insert(
                18,
                round(int(play_data.touchdowns_offense) / play_count, 3)
                if play_count > 0
                else 0,
            )

        self.pass_.worksheet.write_row(self.pass_.rows, 0, row_data)
        self.pass_.rows += 1

    def _add_defense_play(self, play_data, play_slots, play_record: Play):
        front = (
            play_record.defensive_front
            if isinstance(play_record, DefensivePlay)
            else None
        )
        play_type = front.value if front else ""

        rush_avg = (
            int(play_data.rush_yards_allowed) / int(play_data.run_plays_against)
            if play_data.run_plays_against > 0
            else 0.0
        )
        pass_avg = (
            int(play_data.pass_yards_allowed) / int(play_data.pass_plays_against)
            if play_data.pass_plays_against > 0
            else 0.0
        )

        # Calls / Yards / Avg: combined run + pass defense. Not stored in the
        # PDB -- derived by summing the run and pass columns for the play.
        total_calls = int(play_data.run_plays_against) + int(
            play_data.pass_plays_against
        )
        total_yards = int(play_data.rush_yards_allowed) + int(
            play_data.pass_yards_allowed
        )
        total_avg = total_yards / total_calls if total_calls > 0 else 0.0

        slot_1, slot_2 = play_slots
        row_data = [
            play_data.team_name.decode("ASCII"),
            play_record.category.long,
            slot_1,
            slot_2,
            play_data.play_name.decode("ASCII"),
            play_type,
            total_calls,
            total_yards,
            round(total_avg, 1),
            play_data.run_plays_against,
            play_data.rush_yards_allowed,
            round(rush_avg, 1),
            play_data.pass_plays_against,
            play_data.pass_yards_allowed,
            round(pass_avg, 1),
            play_data.fumbles,
            play_data.interceptions,
            play_data.sacks,
            play_data.touchdowns_defense,
            play_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                17,
                round(
                    int(play_data.interceptions) / int(play_data.pass_plays_against), 3
                )
                if play_data.pass_plays_against > 0
                else 0,
            )
            row_data.insert(
                19,
                round(int(play_data.sacks) / int(play_data.pass_plays_against), 3)
                if play_data.pass_plays_against > 0
                else 0,
            )
            row_data.insert(
                22,
                round(int(play_data.touchdowns_offense) / total_calls, 3)
                if total_calls > 0
                else 0,
            )

        self.def_.worksheet.write_row(self.def_.rows, 0, row_data)
        self.def_.rows += 1

    def _add_run_category(self, team_category, category_data):
        avg = (
            int(category_data.total_yards) / int(category_data.play_count)
            if category_data.play_count > 0
            else 0.0
        )

        row_data = [
            team_category[0],
            team_category[1],
            category_data.play_count,
            category_data.total_yards,
            round(avg, 1),
            category_data.fumbles,
            category_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                6, round(int(category_data.fumbles) / int(category_data.play_count), 3)
            )
            row_data.insert(
                8,
                round(
                    int(category_data.touchdowns_offense)
                    / int(category_data.play_count),
                    3,
                ),
            )

        assert self.run_categories is not None
        self.run_categories.worksheet.write_row(self.run_categories.rows, 0, row_data)
        self.run_categories.rows += 1

    def _add_pass_category(self, team_category, category_data):
        play_count = int(category_data.play_count)
        sacks = int(category_data.sacks)
        exclude_sacks = self.config.exclude_sacks_from_pass_attempts
        att = play_count - sacks if exclude_sacks else play_count

        avg_per_completion = (
            int(category_data.total_yards) / int(category_data.completions)
            if category_data.completions > 0
            else 0.0
        )
        avg_per_attempt = int(category_data.total_yards) / att if att > 0 else 0.0

        row_data = [
            team_category[0],
            team_category[1],
            category_data.completions,
            att,
            round(int(category_data.completions) / att, 2) if att > 0 else 0,
            category_data.total_yards,
            round(avg_per_completion, 1),
            round(avg_per_attempt, 1),
            category_data.fumbles,
            category_data.interceptions,
            category_data.sacks,
            category_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                10, round(int(category_data.interceptions) / att, 3) if att > 0 else 0
            )
            if exclude_sacks:
                sack_pct = round(sacks / play_count, 3) if play_count > 0 else 0
            else:
                sack_pct = (
                    round(sacks / (play_count + sacks), 3)
                    if (play_count + sacks) > 0
                    else 0
                )
            row_data.insert(12, sack_pct)
            row_data.insert(
                14,
                round(int(category_data.touchdowns_offense) / play_count, 3)
                if play_count > 0
                else 0,
            )

        assert self.pass_categories is not None
        self.pass_categories.worksheet.write_row(self.pass_categories.rows, 0, row_data)
        self.pass_categories.rows += 1

    def _add_defense_category(self, team_category, category_data):
        total_calls = int(category_data.run_plays_against) + int(
            category_data.pass_plays_against
        )
        total_yards = int(category_data.rush_yards_allowed) + int(
            category_data.pass_yards_allowed
        )
        total_avg = total_yards / total_calls if total_calls > 0 else 0.0
        rush_avg = (
            int(category_data.rush_yards_allowed) / int(category_data.run_plays_against)
            if category_data.run_plays_against > 0
            else 0.0
        )
        pass_avg = (
            int(category_data.pass_yards_allowed)
            / int(category_data.pass_plays_against)
            if category_data.pass_plays_against > 0
            else 0.0
        )

        row_data = [
            team_category[0],
            team_category[1],
            total_calls,
            total_yards,
            round(total_avg, 1),
            category_data.run_plays_against,
            category_data.rush_yards_allowed,
            round(rush_avg, 1),
            category_data.pass_plays_against,
            category_data.pass_yards_allowed,
            round(pass_avg, 1),
            category_data.fumbles,
            category_data.interceptions,
            category_data.sacks,
            category_data.touchdowns_defense,
            category_data.touchdowns_offense,
        ]

        if self.show_percentages:
            row_data.insert(
                13,
                round(
                    int(category_data.interceptions)
                    / int(category_data.pass_plays_against),
                    3,
                )
                if category_data.pass_plays_against > 0
                else 0,
            )
            row_data.insert(
                15,
                round(
                    int(category_data.sacks) / int(category_data.pass_plays_against), 3
                )
                if category_data.pass_plays_against > 0
                else 0,
            )
            row_data.insert(
                18,
                round(int(category_data.touchdowns_offense) / total_calls, 3)
                if total_calls > 0
                else 0,
            )

        assert self.def_categories is not None
        self.def_categories.worksheet.write_row(self.def_categories.rows, 0, row_data)
        self.def_categories.rows += 1

    # -- Conditional formatting -----------------------------------------------

    def _add_conditional_format(self):
        border_format = self.workbook.add_format()
        border_format.set_border_color("#0000FF")
        border_format.set_top(1)
        border_format.set_bottom(1)

        formula = {
            "type": "formula",
            "criteria": (
                '=AND(CELL("row")=ROW(), INDIRECT("HighlightSelectedRow")="Yes")'
            ),
            "format": border_format,
        }

        sheets: list[_WorksheetState] = [
            self.run,
            self.pass_,
            self.def_,
            self.tendencies,
        ]
        if self.config.include_category_worksheets:
            assert self.run_categories is not None
            assert self.pass_categories is not None
            assert self.def_categories is not None
            sheets.extend(
                [self.run_categories, self.pass_categories, self.def_categories]
            )

        for state in sheets:
            state.worksheet.conditional_format(1, 0, 1048575, 16383, formula)
