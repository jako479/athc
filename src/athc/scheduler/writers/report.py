"""Schedule report builder + sortable HTML report writer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape
from os import PathLike
from pathlib import Path

from athc.scheduler.config import DEFAULT_DIFFICULTY_SPREAD
from athc.scheduler.domain.league import League, Team, ordered_teams
from athc.scheduler.domain.schedule import Schedule
from athc.scheduler.schedulers.types import SCHEDULER_DESCRIPTION, MatchupPlan

StrPath = str | PathLike[str]


@dataclass(frozen=True)
class TeamScheduleReport:
    team: str
    conference_rank: int  # 1-9
    overall_rank: int  # 1-18, previous season's final ranking
    schedule_rank: int  # 1-18 ordering by total opponent strength
    avg_sos: float  # average opponent overall rank (1-18), full schedule
    nonconference_rank: int  # 1-18 ordering by non-conference strength
    avg_nonconference_sos: float  # average non-conf opponent overall rank (1-18)
    avg_nonconference_sos_conf: float  # average non-conf opponent conference rank (1-9)
    nonconference_game_ranks: str  # conference ranks (1-9) of non-conf opponents
    nonconference_opponents: tuple[str, ...]


@dataclass(frozen=True)
class ScheduleReport:
    seed: int
    config_path: str
    elapsed_time_seconds: float
    teams: tuple[TeamScheduleReport, ...]
    command_line: str | None = None
    difficulty_spread: float = DEFAULT_DIFFICULTY_SPREAD


def _opponents(schedule: Schedule, team: Team) -> list[Team]:
    """All opponents over the team's 16 games (divisional opponents appear twice)."""
    return [(g.away if g.home == team else g.home) for g in schedule.games_for(team)]


def _nonconference_opponents(schedule: Schedule, team: Team) -> tuple[Team, ...]:
    opponents = {
        opp for opp in _opponents(schedule, team) if opp.conference != team.conference
    }
    return tuple(sorted(opponents, key=lambda opponent: opponent.metro))


def _mean(values: Sequence[int]) -> float:
    return sum(values) / len(values)


def _ordering(teams: Sequence[Team], score: Callable[[Team], float]) -> dict[Team, int]:
    ordered = sorted(teams, key=lambda team: (score(team), team.metro))
    return {team: idx + 1 for idx, team in enumerate(ordered)}


def build_schedule_report(
    *,
    schedule: Schedule,
    matchup_plan: MatchupPlan,
    league: League,
    seed: int,
    config_path: StrPath,
    elapsed_time_seconds: float,
    command_line: str | None = None,
    difficulty_spread: float = DEFAULT_DIFFICULTY_SPREAD,
) -> ScheduleReport:
    """Compute per-team schedule-strength rows and return a structured report."""
    conf_rank = {team: league.rankings.rank_of(team) for team in league.teams}
    overall_rank = {team: league.rankings.overall_rank(team) for team in league.teams}

    nonconf = {team: _nonconference_opponents(schedule, team) for team in league.teams}
    nc_conf_avg = {
        team: _mean([conf_rank[opp] for opp in nonconf[team]]) for team in league.teams
    }
    # Orderings keep the conference-rank basis (unchanged); the SOS averages below
    # use the overall 1-18 scale, to compare against the difficulty curve.
    schedule_rank = _ordering(
        league.teams,
        lambda team: sum(conf_rank[opp] for opp in _opponents(schedule, team)),
    )
    nonconference_rank = _ordering(league.teams, lambda team: nc_conf_avg[team])

    rows: list[TeamScheduleReport] = []
    for team in ordered_teams(league.teams):
        opponents = nonconf[team]
        nonconference_game_ranks = ",".join(
            str(rank) for rank in sorted(conf_rank[opp] for opp in opponents)
        )
        rows.append(
            TeamScheduleReport(
                team=team.metro,
                conference_rank=conf_rank[team],
                overall_rank=overall_rank[team],
                schedule_rank=schedule_rank[team],
                avg_sos=_mean(
                    [overall_rank[opp] for opp in _opponents(schedule, team)]
                ),
                nonconference_rank=nonconference_rank[team],
                avg_nonconference_sos=_mean([overall_rank[opp] for opp in opponents]),
                avg_nonconference_sos_conf=nc_conf_avg[team],
                nonconference_game_ranks=nonconference_game_ranks,
                nonconference_opponents=tuple(opp.metro for opp in opponents),
            )
        )

    return ScheduleReport(
        seed=seed,
        command_line=command_line,
        config_path=str(config_path),
        elapsed_time_seconds=elapsed_time_seconds,
        teams=tuple(rows),
        difficulty_spread=difficulty_spread,
    )


# Column = (header, numeric?, sort-kind). sort-kind None = not sortable; "order"
# restores the original row order. Columns are grouped by scope.
_Column = tuple[str, bool, str | None]
_COLUMNS: tuple[_Column, ...] = (
    ("Team", False, "order"),
    ("Overall Rank (1-18)", True, "num"),
    ("Conf Rank (1-9)", True, "num"),
    ("Sched Rank (1-18)", True, "num"),
    ("Avg SOS (1-18)", True, "num"),
    ("NC Rank (1-18)", True, "num"),
    ("Avg NC SOS (1-18)", True, "num"),
    ("Avg NC SOS (1-9)", True, "num"),
    ("NC Game Ranks (1-9)", False, None),
    ("Non-Conference Opponents", False, None),
)

_STYLE = """\
<style>
body { font-family: sans-serif; margin: 1rem; }
table { border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 2px 8px; }
th { background: #eee; text-align: left; }
th[data-sort] { cursor: pointer; }
td.num { text-align: right; }
</style>"""

# Click a header to sort; the Team header restores the original row order.
_SCRIPT = """\
<script>
function sortTable(table, col, kind) {
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const th = table.tHead.rows[0].cells[col];
  const asc = kind === "order" || th.getAttribute("data-dir") !== "asc";
  for (const c of table.tHead.rows[0].cells) c.removeAttribute("data-dir");
  th.setAttribute("data-dir", asc ? "asc" : "desc");
  const cell = (r) => r.cells[col].textContent;
  rows.sort((a, b) => {
    let x, y;
    if (kind === "order") { x = +a.dataset.index; y = +b.dataset.index; }
    else if (kind === "num") { x = parseFloat(cell(a)); y = parseFloat(cell(b)); }
    else { x = cell(a); y = cell(b); }
    return x < y ? (asc ? -1 : 1) : x > y ? (asc ? 1 : -1) : 0;
  });
  for (const r of rows) tbody.appendChild(r);
}
document.addEventListener("DOMContentLoaded", () => {
  for (const th of document.querySelectorAll("th[data-sort]")) {
    th.addEventListener("click", () =>
      sortTable(th.closest("table"), th.cellIndex, th.getAttribute("data-sort")));
  }
});
</script>"""


@dataclass(frozen=True)
class HtmlReportWriter:
    """Render a `ScheduleReport` as a sortable HTML table to `path`."""

    path: StrPath

    def write(self, report: ScheduleReport) -> None:
        Path(self.path).write_text(self.render(report), encoding="utf-8")

    def render(self, report: ScheduleReport) -> str:
        info_rows = [
            ("Scheduler", SCHEDULER_DESCRIPTION),
            ("Difficulty spread", f"{report.difficulty_spread:g}"),
        ]
        info_rows += [
            ("Seed", str(report.seed)),
            ("Command line", report.command_line or "-"),
            ("Config path", report.config_path or "-"),
            ("Elapsed (s)", f"{report.elapsed_time_seconds:.3f}"),
        ]
        info = tuple(info_rows)
        info_html = "".join(
            f"<p><b>{escape(label)}:</b> {escape(value)}</p>" for label, value in info
        )
        header_cells = "".join(
            _th(name, numeric, sort) for name, numeric, sort in _COLUMNS
        )
        body_rows = "".join(
            self._row(index, team) for index, team in enumerate(report.teams)
        )
        return "\n".join(
            [
                "<!DOCTYPE html>",
                "<html><head><meta charset='utf-8'>",
                "<title>PNFL Schedule Report</title>",
                _STYLE,
                "</head><body>",
                "<h1>PNFL Schedule Report</h1>",
                info_html,
                f"<table><thead><tr>{header_cells}</tr></thead>",
                f"<tbody>{body_rows}</tbody></table>",
                _SCRIPT,
                "</body></html>",
                "",
            ]
        )

    def _row(self, index: int, team: TeamScheduleReport) -> str:
        values = (
            team.team,
            str(team.overall_rank),
            str(team.conference_rank),
            str(team.schedule_rank),
            f"{team.avg_sos:.2f}",
            str(team.nonconference_rank),
            f"{team.avg_nonconference_sos:.2f}",
            f"{team.avg_nonconference_sos_conf:.2f}",
            team.nonconference_game_ranks,
            ", ".join(team.nonconference_opponents),
        )
        cells = "".join(
            f'<td class="num">{escape(value)}</td>'
            if numeric
            else f"<td>{escape(value)}</td>"
            for (_, numeric, _), value in zip(_COLUMNS, values, strict=True)
        )
        return f'<tr data-index="{index}">{cells}</tr>'


def _th(name: str, numeric: bool, sort: str | None) -> str:
    attrs = ""
    if sort:
        attrs += f' data-sort="{sort}"'
    if numeric:
        attrs += ' class="num"'
    return f"<th{attrs}>{escape(name)}</th>"
