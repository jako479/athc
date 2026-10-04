"""Schedule report: per-team rows and the sortable HTML rendering.

The row test reads the shared solved schedule for every league case (slow);
the rendering tests need no solver.
"""

from __future__ import annotations

from athc.scheduler.writers.report import (
    HtmlReportWriter,
    ScheduleReport,
    TeamScheduleReport,
)
from tests.integration.schedule_validation import validate_report

from .conftest import Solved


def test_schedule_report_rows_match_recomputed_sos(solved: Solved) -> None:
    # Every row's rank and SOS fields against an independent computation.
    validate_report(solved.schedule, solved.league)


# --- HTML rendering (fast; no solver) ---------------------------------------


def _sample_report() -> ScheduleReport:
    row = TeamScheduleReport(
        team="Buffalo",
        conference_rank=1,
        overall_rank=2,
        schedule_rank=3,
        avg_sos=9.5,
        nonconference_rank=4,
        avg_nonconference_sos=8.25,
        avg_nonconference_sos_conf=4.5,
        nonconference_game_ranks="1,4,6,7,8",
        nonconference_opponents=("Atlanta", "Chicago"),
    )
    return ScheduleReport(
        seed=7,
        config_path="c.ini",
        elapsed_time_seconds=1.5,
        teams=(row,),
        command_line="athc generate-schedule",
    )


def test_html_report_shows_scheduler_description() -> None:
    assert "two-phase CP-SAT" in HtmlReportWriter("unused", league_name="Test").render(
        _sample_report()
    )


def test_html_report_title_carries_the_league_name() -> None:
    html = HtmlReportWriter("unused", league_name="Test").render(_sample_report())
    assert "<title>Test Schedule Report</title>" in html
    assert "<h1>Test Schedule Report</h1>" in html


def test_html_report_shows_difficulty_knob() -> None:
    rendered = HtmlReportWriter("unused", league_name="Test").render(_sample_report())
    assert "Difficulty spread" in rendered


def test_html_report_has_new_columns_and_values() -> None:
    html = HtmlReportWriter("unused", league_name="Test").render(_sample_report())
    for header in (
        "Overall Rank (1-18)",
        "Avg SOS (1-18)",
        "Avg NC SOS (1-18)",
        "Avg NC SOS (1-9)",
    ):
        assert header in html
    # Team leads, then Overall Rank. Conf Rank sits right after Avg NC SOS (1-18),
    # as the first 1-9 column.
    assert html.index(">Team<") < html.index("Overall Rank (1-18)")
    assert html.index("Avg NC SOS (1-18)") < html.index("Conf Rank (1-9)")
    assert html.index("Conf Rank (1-9)") < html.index("Avg NC SOS (1-9)")
    assert "9.50" in html  # avg_sos
    assert "8.25" in html  # avg_nonconference_sos
    assert "4.50" in html  # avg_nonconference_sos_conf


def test_html_report_marks_sortable_headers() -> None:
    html = HtmlReportWriter("unused", league_name="Test").render(_sample_report())
    assert 'data-sort="order"' in html  # Team restores original order
    assert 'data-sort="num"' in html  # numeric columns sort
    assert 'data-index="0"' in html  # rows carry their original position
    assert "<script>" in html  # sort behavior embedded
