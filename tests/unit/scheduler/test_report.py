from pathlib import Path
from statistics import mean

import pytest

from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_cpsat_builder import FixedCpsatMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.writers.report import (
    HtmlReportWriter,
    ScheduleReport,
    TeamScheduleReport,
    build_schedule_report,
)

from .conftest import SLOW_SOLVE_TIME_LIMIT


@pytest.mark.slow
def test_schedule_report_rows_match_recomputed_sos(league, tmp_path):
    # Build a plan and schedule, then validate every row's rank and SOS fields
    # against an independent computation.
    matchup_plan = FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
    ).build_matchup_plan()
    schedule = ScheduleBuilder(league.teams, SchedulerError).build_schedule(
        matchup_plan.matchups, seed=0, time_limit=SLOW_SOLVE_TIME_LIMIT
    )
    report = build_schedule_report(
        schedule=schedule,
        matchup_plan=matchup_plan,
        league=league,
        seed=0,
        config_path=Path("test-config.ini"),
        elapsed_time_seconds=0.0,
    )
    report_path = tmp_path / "report.html"
    HtmlReportWriter(str(report_path)).write(report)
    print(f"Schedule report: {report_path}")

    rows_by_team = {row.team: row for row in report.teams}
    overall = {t: league.rankings.overall_rank(t) for t in league.teams}
    conf = {t: league.rankings.rank_of(t) for t in league.teams}

    assert len(rows_by_team) == 18
    for team in league.teams:
        row = rows_by_team[team.metro]
        all_opps = [
            g.away if g.home == team else g.home for g in schedule.games_for(team)
        ]
        nc_opps = [o for o in all_opps if o.conference != team.conference]
        assert row.conference_rank == conf[team]
        assert row.overall_rank == overall[team]
        assert row.avg_sos == pytest.approx(mean(overall[o] for o in all_opps))
        assert row.avg_nonconference_sos == pytest.approx(
            mean(overall[o] for o in nc_opps)
        )
        assert row.avg_nonconference_sos_conf == pytest.approx(
            mean(conf[o] for o in nc_opps)
        )
        assert row.nonconference_game_ranks == ",".join(
            str(rank) for rank in sorted(conf[o] for o in set(nc_opps))
        )


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
    assert "fixed-place + CP-SAT" in HtmlReportWriter("unused").render(_sample_report())


def test_html_report_shows_difficulty_knob() -> None:
    rendered = HtmlReportWriter("unused").render(_sample_report())
    assert "Difficulty spread" in rendered


def test_html_report_has_new_columns_and_values() -> None:
    html = HtmlReportWriter("unused").render(_sample_report())
    for header in (
        "Overall Rank (1-18)",
        "Avg SOS (1-18)",
        "Avg NC SOS (1-18)",
        "Avg NC SOS (1-9)",
    ):
        assert header in html
    # Team leads, then Overall Rank, then Conf Rank.
    assert html.index(">Team<") < html.index("Overall Rank (1-18)")
    assert html.index("Overall Rank (1-18)") < html.index("Conf Rank (1-9)")
    assert "9.50" in html  # avg_sos
    assert "8.25" in html  # avg_nonconference_sos
    assert "4.50" in html  # avg_nonconference_sos_conf


def test_html_report_marks_sortable_headers() -> None:
    html = HtmlReportWriter("unused").render(_sample_report())
    assert 'data-sort="order"' in html  # Team restores original order
    assert 'data-sort="num"' in html  # numeric columns sort
    assert 'data-index="0"' in html  # rows carry their original position
    assert "<script>" in html  # sort behavior embedded
