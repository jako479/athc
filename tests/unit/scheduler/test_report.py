from pathlib import Path
from statistics import mean

import pytest

from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_matchup_builder import FixedMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.writers.report import (
    HtmlReportWriter,
    ScheduleReport,
    TeamScheduleReport,
    build_schedule_report,
)

from .conftest import (
    HISTORY_PATH,
    LEAGUE_5_SLOTS,
    LEAGUE_6_SLOTS,
    LEAGUE_7_SLOTS,
    SLOW_SOLVE_TIME_LIMIT,
)

# Golden values for the existing (conference-rank-basis) fields. The new SOS
# averages are solver-dependent, so they're checked by recomputation below.
EXPECTED_ROWS = {
    "5-free-slots": {
        "Buffalo": {
            "conference_rank": 6,
            "schedule_rank": 3,
            "nonconference_rank": 10,
            "extra_opponent": "Philadelphia",
            "history_opponent": "Washington",
            "history_last_played": "2047",
            "nonconference_game_ranks": "1,4,6,7,8",
        },
        "Denver": {
            "conference_rank": 4,
            "schedule_rank": 18,
            "nonconference_rank": 12,
            "extra_opponent": "-",
            "history_opponent": "Seattle",
            "history_last_played": "2045",
            "nonconference_game_ranks": "2,4,6,9",
        },
    },
    "6-free-slots": {
        "Buffalo": {
            "conference_rank": 5,
            "schedule_rank": 1,
            "nonconference_rank": 5,
            "extra_opponent": "Washington",
            "history_opponent": "Minnesota",
            "history_last_played": "2047",
            "nonconference_game_ranks": "1,3,4,5,7",
        },
        "Denver": {
            "conference_rank": 7,
            "schedule_rank": 9,
            "nonconference_rank": 13,
            "extra_opponent": "-",
            "history_opponent": "Chicago",
            "history_last_played": "2047",
            "nonconference_game_ranks": "2,5,7,9",
        },
    },
    "7-free-slots": {
        "Buffalo": {
            "conference_rank": 4,
            "schedule_rank": 6,
            "nonconference_rank": 10,
            "extra_opponent": "Atlanta",
            "history_opponent": "Seattle",
            "history_last_played": "2047",
            "nonconference_game_ranks": "2,3,4,6,9",
        },
        "Denver": {
            "conference_rank": 7,
            "schedule_rank": 12,
            "nonconference_rank": 13,
            "extra_opponent": "-",
            "history_opponent": "Chicago",
            "history_last_played": "2047",
            "nonconference_game_ranks": "2,5,7,9",
        },
    },
}


def _league_id(league) -> str:
    if league is LEAGUE_5_SLOTS:
        return "5-free-slots"
    if league is LEAGUE_6_SLOTS:
        return "6-free-slots"
    if league is LEAGUE_7_SLOTS:
        return "7-free-slots"
    raise AssertionError(f"Unexpected league fixture: {league}")


@pytest.mark.slow
def test_schedule_report_rows_for_one_four_team_and_one_five_team_division(
    league, tmp_path
):
    # Report rows are Scheduler A-specific, so build that scheduler's plan and
    # schedule directly rather than the default (Scheduler B) fixtures.
    history = NonConfHistory.load(HISTORY_PATH)
    matchup_plan = FixedMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=history,
    ).build_matchup_plan()
    schedule = ScheduleBuilder(league.teams, SchedulerError).build_schedule(
        matchup_plan.matchups, seed=0, time_limit=SLOW_SOLVE_TIME_LIMIT
    )
    report = build_schedule_report(
        schedule=schedule,
        matchup_plan=matchup_plan,
        league=league,
        history=history,
        seed=0,
        scheduler_kind="A",
        config_path=Path("test-config.ini"),
        history_path=Path("test-history.json"),
        elapsed_time_seconds=0.0,
    )
    report_path = tmp_path / "report.html"
    HtmlReportWriter(str(report_path)).write(report)
    print(f"Schedule report: {report_path}")

    rows_by_team = {row.team: row for row in report.teams}
    teams_by_metro = {t.metro: t for t in league.teams}
    overall = {t: league.rankings.overall_rank(t) for t in league.teams}
    conf = {t: league.rankings.rank_of(t) for t in league.teams}

    for team_name, expected in EXPECTED_ROWS[_league_id(league)].items():
        row = rows_by_team[team_name]
        for field, value in expected.items():
            assert getattr(row, field) == value, (team_name, field)

        # New SOS fields: validate against an independent computation.
        team = teams_by_metro[team_name]
        all_opps = [
            g.away if g.home == team else g.home for g in schedule.games_for(team)
        ]
        nc_opps = [o for o in all_opps if o.conference != team.conference]
        assert row.overall_rank == overall[team]
        assert row.avg_sos == pytest.approx(mean(overall[o] for o in all_opps))
        assert row.avg_nonconference_sos == pytest.approx(
            mean(overall[o] for o in nc_opps)
        )
        assert row.avg_nonconference_sos_conf == pytest.approx(
            mean(conf[o] for o in nc_opps)
        )


# --- HTML rendering (fast; no solver) ---------------------------------------


def _sample_report(
    scheduler_kind: str = "A",
    *,
    difficulty_amplitude: float = 0.3,
    difficulty_period: float = 8.0,
) -> ScheduleReport:
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
        extra_opponent="Philadelphia",
        history_opponent="Washington",
        history_last_played="2047",
        nonconference_opponents=("Atlanta", "Chicago"),
    )
    return ScheduleReport(
        seed=7,
        scheduler_kind=scheduler_kind,
        config_path="c.ini",
        history_path="h.json",
        elapsed_time_seconds=1.5,
        teams=(row,),
        command_line="athc generate-schedule",
        difficulty_amplitude=difficulty_amplitude,
        difficulty_period=difficulty_period,
    )


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("A", "Scheduler A (fixed-rank)"),
        ("B", "Scheduler B (full CP-SAT)"),
        ("C", "Scheduler C (fixed-place + CP-SAT)"),
        ("D", "Scheduler D (fixed-place + CP-SAT, free-only)"),
    ],
)
def test_html_report_shows_scheduler_display_name(kind: str, label: str) -> None:
    assert label in HtmlReportWriter("unused").render(_sample_report(kind))


def test_html_report_shows_difficulty_knobs_per_scheduler() -> None:
    # B shows its curve knobs (a/t); C shows c_spread; D shows d_spread; A none.
    b = HtmlReportWriter("unused").render(
        _sample_report("B", difficulty_amplitude=0.3, difficulty_period=8.0)
    )
    assert "amplitude (a)" in b and "period (t)" in b
    assert "c_spread" not in b and "d_spread" not in b
    c = HtmlReportWriter("unused").render(_sample_report("C"))
    assert "c_spread" in c and "d_spread" not in c
    assert "amplitude (a)" not in c and "period (t)" not in c
    d = HtmlReportWriter("unused").render(_sample_report("D"))
    assert "d_spread" in d and "c_spread" not in d
    assert "amplitude (a)" not in d and "period (t)" not in d
    a = HtmlReportWriter("unused").render(_sample_report("A"))
    assert "amplitude (a)" not in a and "period (t)" not in a
    assert "c_spread" not in a and "d_spread" not in a


def test_html_report_has_new_columns_and_values() -> None:
    html = HtmlReportWriter("unused").render(_sample_report())
    for header in (
        "Prev Rank (1-18)",
        "Avg SOS (1-18)",
        "Avg NC SOS (1-18)",
        "Avg NC SOS (1-9)",
    ):
        assert header in html
    assert "9.50" in html  # avg_sos
    assert "8.25" in html  # avg_nonconference_sos
    assert "4.50" in html  # avg_nonconference_sos_conf


def test_html_report_marks_sortable_headers() -> None:
    html = HtmlReportWriter("unused").render(_sample_report())
    assert 'data-sort="order"' in html  # Team restores original order
    assert 'data-sort="num"' in html  # numeric columns sort
    assert 'data-index="0"' in html  # rows carry their original position
    assert "<script>" in html  # sort behavior embedded
