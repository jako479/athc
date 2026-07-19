"""Build a scheduler-format HTML report for the REAL 2048 PNFL schedule.

The real schedule (as published at pnfl.biz) was not produced by athc's
scheduler, so this reuses the scheduler's report code to score it on the same
strength-of-schedule metrics. The sortable table is byte-identical to what
`athc generate-schedule` emits; only the header differs (honest provenance).

The three Scheduler-A matchup-construction columns -- Extra Opp / H2H Opp /
Last Played -- describe how Scheduler A picks non-conference games and have no
meaning for a human-built schedule, so they render as "-".

Run:  .venv\\Scripts\\python.exe research\\scheduler\\build_real_2048_report.py
"""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path

from athc.scheduler.config import load_league
from athc.scheduler.domain.league import Team, lookup_team
from athc.scheduler.domain.schedule import Game, Schedule, nonconference_games_for
from athc.scheduler.schedulers.types import MatchupPlan
from athc.scheduler.writers import report as report_mod
from athc.scheduler.writers.report import (
    HtmlReportWriter,
    build_schedule_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAGUE_PATH = REPO_ROOT / "release" / "2048.league.ini"
OUT_PATH = REPO_ROOT / "research" / "scheduler" / "reports" / "schedule_2048_real.html"
SOURCE_URL = "https://pnfl.biz/pnflstats/PNFL_schedules.htm"

# Real 2048 PNFL schedule, transcribed from SOURCE_URL. Lines are "Away @ Home"
# (scores dropped; they don't affect the report). Week headers set the week.
RAW_SCHEDULE = """
Week 1
Los Angeles @ Buffalo
Denver @ Minnesota
Las Vegas @ New England
Pittsburgh @ Cincinnati
Washington @ Jacksonville
New York @ Miami
Philadelphia @ Atlanta
Green Bay @ San Francisco
Seattle @ Chicago

Week 2
New England @ Buffalo
Jacksonville @ Pittsburgh
Los Angeles @ Chicago
Denver @ Miami
Cincinnati @ Las Vegas
Washington @ Philadelphia
Atlanta @ New York
San Francisco @ Minnesota
Seattle @ Green Bay

Week 3
Miami @ Buffalo
Jacksonville @ Los Angeles
Las Vegas @ Pittsburgh
Washington @ San Francisco
Atlanta @ Denver
Philadelphia @ New York
Minnesota @ New England
Green Bay @ Chicago
Seattle @ Cincinnati

Week 4
Miami @ Las Vegas
Buffalo @ Denver
Los Angeles @ Cincinnati
Pittsburgh @ New England
New York @ Jacksonville
Philadelphia @ Washington
Chicago @ Seattle
Minnesota @ Atlanta
San Francisco @ Green Bay

Week 5
Miami @ Minnesota
New England @ Jacksonville
Los Angeles @ Pittsburgh
Denver @ Washington
Atlanta @ Seattle
Philadelphia @ Las Vegas
Chicago @ New York
Green Bay @ Buffalo
San Francisco @ Cincinnati

Week 6
New England @ Philadelphia
Jacksonville @ Miami
Buffalo @ Atlanta
Las Vegas @ San Francisco
Cincinnati @ Los Angeles
Pittsburgh @ Denver
Washington @ New York
Chicago @ Green Bay
Seattle @ Minnesota

Week 7
Denver @ Jacksonville
Las Vegas @ Buffalo
Cincinnati @ Pittsburgh
Washington @ Los Angeles
Atlanta @ New England
New York @ San Francisco
Chicago @ Miami
Minnesota @ Philadelphia
Green Bay @ Seattle

Week 8
Miami @ Jacksonville
New England @ Denver
Buffalo @ Cincinnati
Los Angeles @ Las Vegas
Atlanta @ Green Bay
New York @ Washington
Philadelphia @ Seattle
Minnesota @ Chicago
San Francisco @ Pittsburgh

Week 9
New England @ Cincinnati
Jacksonville @ Philadelphia
Buffalo @ Miami
Pittsburgh @ Las Vegas
Chicago @ Denver
Minnesota @ Los Angeles
Green Bay @ Washington
San Francisco @ Atlanta
Seattle @ New York

Week 10
New England @ Miami
Denver @ Los Angeles
Cincinnati @ Jacksonville
Pittsburgh @ Buffalo
Atlanta @ Washington
New York @ Las Vegas
Philadelphia @ Chicago
Green Bay @ Minnesota
Seattle @ San Francisco

Week 11
Buffalo @ Jacksonville
Los Angeles @ New England
Las Vegas @ Seattle
Cincinnati @ Denver
Pittsburgh @ Green Bay
Washington @ Miami
Atlanta @ Chicago
New York @ Philadelphia
Minnesota @ San Francisco

Week 12
Miami @ Los Angeles
Jacksonville @ New England
Denver @ Las Vegas
Cincinnati @ Green Bay
Washington @ Minnesota
New York @ Atlanta
Philadelphia @ Pittsburgh
Chicago @ San Francisco
Seattle @ Buffalo

Week 13
Miami @ New England
Jacksonville @ Buffalo
Los Angeles @ Denver
Las Vegas @ Cincinnati
Pittsburgh @ Seattle
Washington @ Atlanta
Chicago @ Minnesota
Green Bay @ New York
San Francisco @ Philadelphia

Week 14
Miami @ Atlanta
New England @ Washington
Jacksonville @ Las Vegas
Buffalo @ New York
Denver @ Cincinnati
Pittsburgh @ Los Angeles
Philadelphia @ Green Bay
Minnesota @ Seattle
San Francisco @ Chicago

Week 15
Buffalo @ New England
Denver @ Pittsburgh
Las Vegas @ Los Angeles
Cincinnati @ Miami
Atlanta @ Philadelphia
New York @ Minnesota
Chicago @ Washington
Green Bay @ Jacksonville
San Francisco @ Seattle

Week 16
Miami @ Pittsburgh
New England @ Chicago
Jacksonville @ San Francisco
Buffalo @ Philadelphia
Los Angeles @ Atlanta
Las Vegas @ Denver
Cincinnati @ New York
Minnesota @ Green Bay
Seattle @ Washington
"""


def parse_games(teams: tuple[Team, ...]) -> list[Game]:
    games: list[Game] = []
    week = 0
    for line in RAW_SCHEDULE.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("week "):
            week = int(line.split()[1])
            continue
        away_metro, home_metro = (part.strip() for part in line.split("@"))
        away = lookup_team(teams, away_metro)
        home = lookup_team(teams, home_metro)
        games.append(Game(week=week, home=home, away=away))
    return games


def validate(schedule: Schedule, teams: tuple[Team, ...]) -> None:
    """Confirm the parsed games form a valid PNFL schedule. The report depends
    only on each team's opponent set, so passing this guarantees correct data."""
    assert len(schedule.games) == 144, f"expected 144 games, got {len(schedule.games)}"

    for team in teams:
        opponents = [
            g.away if g.home == team else g.home for g in schedule.games_for(team)
        ]
        assert len(opponents) == 16, f"{team.metro}: {len(opponents)} games, want 16"
        counts = Counter(opponents)

        divisional = [t for t in teams if t.division == team.division and t != team]
        for opp in divisional:
            assert counts[opp] == 2, (
                f"{team.metro} vs divisional {opp.metro}: {counts[opp]}x, want 2"
            )

        conference = [
            t
            for t in teams
            if t.conference == team.conference and t.division != team.division
        ]
        for opp in conference:
            assert counts[opp] == 1, (
                f"{team.metro} vs conference {opp.metro}: {counts[opp]}x, want 1"
            )

        nonconf = [t for t in teams if t.conference != team.conference]
        played_nc = [opp for opp in nonconf if counts[opp]]
        want_nc = nonconference_games_for(team.division)
        assert len(played_nc) == want_nc, (
            f"{team.metro}: {len(played_nc)} non-conf opponents, want {want_nc}"
        )
        for opp in played_nc:
            assert counts[opp] == 1, (
                f"{team.metro} vs non-conf {opp.metro}: {counts[opp]}x, want 1"
            )

        # Soft check: home/away balance (does not affect the report).
        home = sum(1 for g in schedule.games_for(team) if g.home == team)
        if home != 8:
            print(f"  note: {team.metro} hosts {home} games (8 expected)")


def render(report, info_lines: tuple[tuple[str, str], ...]) -> str:
    """Identical table to HtmlReportWriter, with a custom provenance header."""
    writer = HtmlReportWriter(OUT_PATH)
    info_html = "".join(
        f"<p><b>{escape(label)}:</b> {escape(value)}</p>" for label, value in info_lines
    )
    header_cells = "".join(
        report_mod._th(name, numeric, sort)
        for name, numeric, sort in report_mod._COLUMNS
    )
    body_rows = "".join(writer._row(i, team) for i, team in enumerate(report.teams))
    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'>",
            "<title>PNFL Schedule Report</title>",
            report_mod._STYLE,
            "</head><body>",
            "<h1>PNFL Schedule Report</h1>",
            info_html,
            f"<table><thead><tr>{header_cells}</tr></thead>",
            f"<tbody>{body_rows}</tbody></table>",
            report_mod._SCRIPT,
            "</body></html>",
            "",
        ]
    )


def main() -> None:
    league = load_league(LEAGUE_PATH)
    games = parse_games(league.teams)
    schedule = Schedule(games=tuple(games))
    validate(schedule, league.teams)

    report = build_schedule_report(
        schedule=schedule,
        matchup_plan=MatchupPlan(matchups=()),  # no scheduler-internal pairs
        league=league,
        history=None,
        seed=0,
        scheduler_kind="real",
        config_path="-",
        history_path="-",
        elapsed_time_seconds=0.0,
        command_line=None,
    )
    info_lines = (
        ("Schedule", "Real 2048 PNFL schedule (as played)"),
        ("Source", SOURCE_URL),
        ("Standings", "2047 final results (2048.league.ini)"),
        (
            "Note",
            "Extra Opp / H2H Opp / Last Played are Scheduler-A matchup-"
            "construction details and do not apply to a human-built schedule "
            '(shown as "-").',
        ),
    )
    OUT_PATH.write_text(render(report, info_lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(schedule.games)} games, validated)")


if __name__ == "__main__":
    main()
