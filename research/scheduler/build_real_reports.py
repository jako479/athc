"""Generate the 'real schedule' SOS report for seasons 2045-2047, identical in
format to the 2048 report (research/scheduler/build_real_2048_report.py).

Each season's schedule is imported from its sos_<year> module (the same verified
matchup data used to build the league.ini files); the league.ini supplies the
prior-season standings that drive the strength-of-schedule columns. The table is
rendered with the scheduler's own report code, so it is byte-identical in shape
to what `athc generate-schedule` emits.

Run: .venv\\Scripts\\python.exe research\\scheduler\\build_real_reports.py
"""

from __future__ import annotations

import contextlib
import io
import sys
from collections import Counter
from html import escape
from pathlib import Path

from athc.scheduler.config import load_league
from athc.scheduler.domain.league import Team
from athc.scheduler.domain.league import lookup_team
from athc.scheduler.domain.schedule import Game, Schedule, nonconference_games_for
from athc.scheduler.schedulers.types import MatchupPlan
from athc.scheduler.writers import report as report_mod
from athc.scheduler.writers.report import HtmlReportWriter, build_schedule_report

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
# The sos_<year> modules compute + print on import; silence that and keep only
# their (already validated) SCHEDULE text.
with contextlib.redirect_stdout(io.StringIO()):
    import sos_2045
    import sos_2046
    import sos_2047

SCHEDULES = {2045: sos_2045.SCHEDULE, 2046: sos_2046.SCHEDULE, 2047: sos_2047.SCHEDULE}
PRIOR = {2045: 2044, 2046: 2045, 2047: 2046}


# The scheduler's report dedupes non-conference opponents into a set, which
# under-counts a repeated matchup (the real 2046 schedule has Las Vegas/Green Bay
# playing twice). Override it to count games, not distinct opponents, so a repeat
# shows up twice across every NC column. No-op for the other seasons.
def _nonconf_games(schedule, team):
    opps = [
        o
        for o in report_mod._opponents(schedule, team)
        if o.conference != team.conference
    ]
    return tuple(sorted(opps, key=lambda o: o.metro))


report_mod._nonconference_opponents = _nonconf_games


def parse_games(teams: tuple[Team, ...], sched_text: str) -> list[Game]:
    games: list[Game] = []
    for week, line in enumerate(sched_text.strip().splitlines(), 1):
        for game in line.split("|"):
            game = game.strip()
            if not game:
                continue
            away, home = (t.strip() for t in game.split("@"))
            games.append(
                Game(
                    week=week,
                    home=lookup_team(teams, home),
                    away=lookup_team(teams, away),
                )
            )
    return games


def validate(schedule: Schedule, teams: tuple[Team, ...]) -> None:
    """Confirm a valid PNFL schedule; the report depends only on opponent sets,
    so passing this guarantees the data is right."""
    assert len(schedule.games) == 144, f"{len(schedule.games)} games, want 144"
    for team in teams:
        opps = [g.away if g.home == team else g.home for g in schedule.games_for(team)]
        assert len(opps) == 16, f"{team.metro}: {len(opps)} games"
        counts = Counter(opps)
        for opp in teams:
            if opp == team:
                continue
            if opp.division == team.division:
                assert counts[opp] == 2, f"{team.metro} vs {opp.metro}: want 2x"
            elif opp.conference == team.conference:
                assert counts[opp] == 1, f"{team.metro} vs {opp.metro}: want 1x"
        # Non-conference: enforce the game-count balance, but allow a repeated
        # opponent (the real 2046 schedule has Las Vegas/Green Bay home-and-home).
        nonconf_games = [o for o in opps if o.conference != team.conference]
        want = nonconference_games_for(team.division)
        assert len(nonconf_games) == want, (
            f"{team.metro}: {len(nonconf_games)} non-conf games, want {want}"
        )
        distinct = len(set(nonconf_games))
        if distinct != len(nonconf_games):
            print(
                f"  note: {team.metro} repeats a non-conf opponent "
                f"({len(nonconf_games)} games, {distinct} distinct)"
            )
        home = sum(1 for g in schedule.games_for(team) if g.home == team)
        if home != 8:
            print(f"  note: {team.metro} hosts {home} games (8 expected)")


def render(report, info_lines: tuple[tuple[str, str], ...], out_path: Path) -> str:
    writer = HtmlReportWriter(out_path)
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


def build(season: int) -> None:
    league = load_league(REPO_ROOT / "release" / f"{season}.league.ini")
    games = parse_games(league.teams, SCHEDULES[season])
    schedule = Schedule(games=tuple(games))
    validate(schedule, league.teams)
    report = build_schedule_report(
        schedule=schedule,
        matchup_plan=MatchupPlan(matchups=()),
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
        ("Schedule", f"Real {season} PNFL schedule (as played)"),
        ("Source", f"https://pnfl.biz/Seasons/{season}/{season}%20PNFL_schedules.htm"),
        ("Standings", f"{PRIOR[season]} final results ({season}.league.ini)"),
        (
            "Note",
            "Extra Opp / H2H Opp / Last Played are Scheduler-A matchup-"
            "construction details and do not apply to a human-built schedule "
            '(shown as "-").',
        ),
    )
    out = (
        REPO_ROOT
        / "research"
        / "scheduler"
        / "reports"
        / f"schedule_{season}_real.html"
    )
    out.write_text(render(report, info_lines, out), encoding="utf-8")
    print(f"Wrote {out.name} ({len(games)} games, validated)")


if __name__ == "__main__":
    for s in (2045, 2046, 2047):
        build(s)
