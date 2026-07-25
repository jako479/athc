"""Parse a written `.txt` schedule and validate it against every scheduler rule.

Used by the golden regression test to confirm the frozen schedule is a legal
PNFL schedule (not just byte-identical to a blob). Every rule the CP-SAT model
enforces -- both the hard-coded structure and the `Phase2Config`-tunable
amounts -- is re-checked here independently of the solver.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from athc.scheduler.config import Phase2Config
from athc.scheduler.domain.league import (
    Division,
    League,
    Team,
    team_by_metro,
)
from athc.scheduler.domain.schedule import (
    GAMES_PER_WEEK,
    HOME_GAMES_PER_TEAM,
    NUM_WEEKS,
    WEEK_16_DIVISIONAL_GAMES,
    Game,
    Schedule,
    nonconference_games_for,
)
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup
from athc.scheduler.writers.report import build_schedule_report

FIVE_TEAM_DIVISIONS = (Division.AFC_WEST, Division.NFC_WEST)
FOUR_TEAM_DIVISIONS = (Division.AFC_EAST, Division.NFC_EAST)

# Must match HtmlScheduleWriter's week-by-week column width.
_HTML_COL_WIDTH = 42


def parse_schedule_txt(text: str, league: League) -> Schedule:
    """Parse the `Week N` / `away#home` text format back into a `Schedule`.

    Metros are resolved against `league`, so an unknown or malformed line is a
    hard error rather than a silently dropped game.
    """
    by_metro = team_by_metro(league.teams)
    games: list[Game] = []
    week: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Week "):
            week = int(line.removeprefix("Week ").strip())
            continue
        if week is None:
            raise ValueError(f"Game line before any 'Week' header: {line!r}")
        away_metro, sep, home_metro = line.partition("#")
        if sep != "#":
            raise ValueError(f"Malformed game line (expected 'away#home'): {line!r}")
        games.append(
            Game(
                week=week,
                home=_resolve(by_metro, home_metro),
                away=_resolve(by_metro, away_metro),
            )
        )
    return Schedule(games=tuple(games))


def parse_schedule_html(html: str, league: League) -> Schedule:
    """Parse the HTML schedule's week-by-week section back into a `Schedule`.

    Confirms the HTML writer encodes the same games as the text writer. Reads
    only the week-by-week block (two columns, `away at home` per cell); the
    team-by-team block that follows is redundant.
    """
    by_metro = team_by_metro(league.teams)
    pre = html.split("<body><pre>", 1)[1].split("</pre>", 1)[0]
    week_block = pre.split("League Schedule by team", 1)[0]  # drop team-by-team

    games: list[Game] = []
    left_week: int | None = None
    right_week: int | None = None
    for line in week_block.splitlines():
        headers = re.findall(r"<b>Week (\d+)</b>", line)
        if headers:  # e.g. "Week 3 ... Week 4" column pair
            left_week = int(headers[0])
            right_week = int(headers[1]) if len(headers) > 1 else None
            continue
        if "<" in line or " at " not in line:  # nav / title / blank
            continue
        left, right = line[:_HTML_COL_WIDTH].strip(), line[_HTML_COL_WIDTH:].strip()
        if left:
            games.append(_html_game(left, left_week, by_metro))
        if right:
            games.append(_html_game(right, right_week, by_metro))
    return Schedule(games=tuple(games))


def _html_game(cell: str, week: int | None, by_metro: dict[str, Team]) -> Game:
    if week is None:
        raise ValueError(f"Game cell {cell!r} with no week header")
    away, sep, home = cell.partition(" at ")
    if sep != " at ":
        raise ValueError(f"Malformed HTML game cell: {cell!r}")
    return Game(week=week, home=_resolve(by_metro, home), away=_resolve(by_metro, away))


def game_keys(schedule: Schedule) -> set[tuple[int, str, str]]:
    return {(g.week, g.home.metro, g.away.metro) for g in schedule.games}


def validate_report(schedule: Schedule, league: League) -> None:
    """Build the report from `schedule` and assert every row's ranks and SOS
    values match an independent recomputation (mirrors the report unit test)."""
    report = build_schedule_report(
        schedule=schedule,
        matchup_plan=MatchupPlan(matchups=()),  # unused by the builder
        league=league,
        seed=0,
        config_path="test",
        elapsed_time_seconds=0.0,
    )
    rows = {row.team: row for row in report.teams}
    overall = {t: league.rankings.overall_rank(t) for t in league.teams}
    conf = {t: league.rankings.rank_of(t) for t in league.teams}

    assert len(rows) == len(league.teams), "report is missing team rows"
    for team in league.teams:
        row = rows[team.metro]
        all_opps = [
            g.away if g.home == team else g.home for g in schedule.games_for(team)
        ]
        nc_opps = [o for o in all_opps if o.conference != team.conference]
        assert row.conference_rank == conf[team], team.metro
        assert row.overall_rank == overall[team], team.metro
        assert math.isclose(row.avg_sos, _mean(overall[o] for o in all_opps)), (
            team.metro
        )
        assert math.isclose(
            row.avg_nonconference_sos, _mean(overall[o] for o in nc_opps)
        ), team.metro
        assert math.isclose(
            row.avg_nonconference_sos_conf, _mean(conf[o] for o in nc_opps)
        ), team.metro
        assert row.nonconference_game_ranks == ",".join(
            str(rank) for rank in sorted(conf[o] for o in set(nc_opps))
        ), team.metro
        assert row.nonconference_opponents == tuple(
            sorted(o.metro for o in set(nc_opps))
        ), team.metro


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def _resolve(by_metro: dict[str, Team], metro: str) -> Team:
    team = by_metro.get(metro.strip())
    if team is None:
        raise ValueError(f"Unknown team in schedule: {metro!r}")
    return team


def _home_pattern(schedule: Schedule, team: Team) -> list[bool]:
    pattern = [False] * NUM_WEEKS
    for game in schedule.home_games_for(team):
        pattern[game.week - 1] = True
    return pattern


def _divisional_pattern(schedule: Schedule, team: Team) -> list[bool]:
    pattern = [False] * NUM_WEEKS
    for game in schedule.games_for(team):
        opponent = game.away if game.home == team else game.home
        if opponent.division == team.division:
            pattern[game.week - 1] = True
    return pattern


def _count_streaks_of(pattern: list[bool], length: int) -> int:
    # Number of maximal runs of True with length >= `length`.
    count = 0
    run = 0
    for value in pattern:
        if value:
            run += 1
        else:
            if run >= length:
                count += 1
            run = 0
    if run >= length:
        count += 1
    return count


def _divisional_meeting_weeks(schedule: Schedule, team: Team) -> dict[Team, list[int]]:
    weeks: dict[Team, list[int]] = {}
    for game in schedule.games_for(team):
        opponent = game.away if game.home == team else game.home
        if opponent.division == team.division:
            weeks.setdefault(opponent, []).append(game.week)
    return weeks


def _non_interleaved_count(weeks_by_opp: dict[Team, list[int]]) -> int:
    non_interleaved = 0
    for opponent, weeks in weeks_by_opp.items():
        first, second = sorted(weeks)
        has_between = any(
            first < other < second
            for other_opp, other_weeks in weeks_by_opp.items()
            if other_opp != opponent
            for other in other_weeks
        )
        if not has_between:
            non_interleaved += 1
    return non_interleaved


def _opens_with_divisional_pair(schedule: Schedule, team: Team) -> bool:
    opening = sum(
        1
        for g in schedule.games_for(team)
        if g.week in (1, 2)
        and (g.away if g.home == team else g.home).division == team.division
    )
    return opening == 2


def validate_schedule(
    schedule: Schedule, league: League, amounts: Phase2Config | None = None
) -> None:
    """Assert `schedule` obeys every PNFL rule. Raises AssertionError on any
    violation. `amounts` supplies the configurable caps (defaults if omitted)."""
    amounts = amounts or Phase2Config()
    teams = league.teams

    _validate_structure(schedule, teams)
    _validate_inventory(schedule, teams)
    _validate_home_away_sequencing(schedule, teams, amounts)
    _validate_divisional_sequencing(schedule, teams, amounts)
    _validate_home_balance(schedule, teams)
    _validate_league_wide_caps(schedule, teams, amounts)
    _validate_season_ending(schedule, teams, amounts)


def _validate_structure(schedule: Schedule, teams: tuple[Team, ...]) -> None:
    assert len(schedule.games) == NUM_WEEKS * GAMES_PER_WEEK, (
        f"expected {NUM_WEEKS * GAMES_PER_WEEK} games, got {len(schedule.games)}"
    )
    for week in range(1, NUM_WEEKS + 1):
        week_games = [g for g in schedule.games if g.week == week]
        assert len(week_games) == GAMES_PER_WEEK, (
            f"week {week}: expected {GAMES_PER_WEEK} games, got {len(week_games)}"
        )
    for game in schedule.games:
        assert game.home != game.away, f"team plays itself in week {game.week}"
    for team in teams:
        played = schedule.games_for(team)
        assert len(played) == NUM_WEEKS, (
            f"{team.metro}: expected {NUM_WEEKS} games, got {len(played)}"
        )
        week_counts = Counter(g.week for g in played)
        for week in range(1, NUM_WEEKS + 1):
            assert week_counts[week] == 1, (
                f"{team.metro}: expected exactly 1 game in week {week}"
            )
        assert len(schedule.home_games_for(team)) == HOME_GAMES_PER_TEAM, (
            f"{team.metro}: expected {HOME_GAMES_PER_TEAM} home games"
        )


def _validate_inventory(schedule: Schedule, teams: tuple[Team, ...]) -> None:
    pair_counts: Counter = Counter()
    for game in schedule.games:
        pair_counts[make_matchup(game.home, game.away)] += 1

    for i, team_a in enumerate(teams):
        for team_b in teams[i + 1 :]:
            pair = make_matchup(team_a, team_b)
            if team_a.division == team_b.division:
                meetings = schedule.games_between(team_a, team_b)
                assert len(meetings) == 2, (
                    f"{team_a.metro}/{team_b.metro}: expected 2 divisional meetings"
                )
                assert sum(1 for g in meetings if g.home == team_a) == 1, (
                    f"{team_a.metro}/{team_b.metro}: {team_a.metro} must host once"
                )
                assert sum(1 for g in meetings if g.home == team_b) == 1, (
                    f"{team_a.metro}/{team_b.metro}: {team_b.metro} must host once"
                )
            elif team_a.conference == team_b.conference:
                assert pair_counts[pair] == 1, (
                    f"{team_a.metro}/{team_b.metro}: expected 1 conference game"
                )

    for team in teams:
        nonconf = [
            g
            for g in schedule.games_for(team)
            if g.home.conference != g.away.conference
        ]
        expected = nonconference_games_for(team.division)
        assert len(nonconf) == expected, (
            f"{team.metro}: expected {expected} non-conference games, got {len(nonconf)}"
        )


def _validate_home_away_sequencing(
    schedule: Schedule, teams: tuple[Team, ...], amounts: Phase2Config
) -> None:
    for team in teams:
        home = _home_pattern(schedule, team)
        away = [not h for h in home]

        for start in range(NUM_WEEKS - 3):
            assert (
                sum(home[start : start + 4]) <= amounts.max_consecutive_home_or_away
            ), (
                f"{team.metro}: >{amounts.max_consecutive_home_or_away} straight home "
                f"from week {start + 1}"
            )
            assert (
                sum(away[start : start + 4]) <= amounts.max_consecutive_home_or_away
            ), (
                f"{team.metro}: >{amounts.max_consecutive_home_or_away} straight away "
                f"from week {start + 1}"
            )

        for start in range(NUM_WEEKS - 5):
            window = sum(home[start : start + 6])
            assert (
                amounts.min_home_per_six_weeks
                <= window
                <= amounts.max_home_per_six_weeks
            ), (
                f"{team.metro} weeks {start + 1}-{start + 6}: {window} home games "
                f"outside [{amounts.min_home_per_six_weeks}, "
                f"{amounts.max_home_per_six_weeks}]"
            )

        assert 1 <= sum(home[:3]) <= 2, (
            f"{team.metro}: 3-game home/away streak to start the season"
        )
        assert 1 <= sum(home[-3:]) <= 2, (
            f"{team.metro}: 3-game home/away streak to end the season"
        )

        total_streaks = _count_streaks_of(home, 3) + _count_streaks_of(away, 3)
        assert total_streaks <= amounts.max_three_game_home_away_streaks, (
            f"{team.metro}: {total_streaks} total 3-game home/away streaks"
        )


def _validate_divisional_sequencing(
    schedule: Schedule, teams: tuple[Team, ...], amounts: Phase2Config
) -> None:
    for team in teams:
        pattern = _divisional_pattern(schedule, team)

        for start in range(NUM_WEEKS - 3):
            assert (
                sum(pattern[start : start + 4]) <= amounts.max_consecutive_divisional
            ), (
                f"{team.metro}: >{amounts.max_consecutive_divisional} straight "
                f"divisional from week {start + 1}"
            )

        assert sum(pattern[:3]) <= 2, (
            f"{team.metro}: 3 straight divisional games to start the season"
        )
        assert sum(pattern[-3:]) <= 2, (
            f"{team.metro}: 3 straight divisional games to end the season"
        )

        assert (
            _count_streaks_of(pattern, 3) <= amounts.max_three_game_divisional_streaks
        ), f"{team.metro}: too many 3-game divisional streaks"

        if team.division in FIVE_TEAM_DIVISIONS:
            for start in range(NUM_WEEKS - 8):
                count = sum(pattern[start : start + 9])
                assert count <= amounts.five_team_max_divisional_in_9, (
                    f"{team.metro} weeks {start + 1}-{start + 9}: {count} divisional "
                    f"in 9-game span"
                )
            windows = (
                (6, amounts.five_team_max_divisional_first_6),
                (8, amounts.five_team_max_divisional_first_8),
                (10, amounts.five_team_max_divisional_first_10),
            )
        else:
            for start in range(NUM_WEEKS - 6):
                count = sum(pattern[start : start + 7])
                assert count <= amounts.four_team_max_divisional_in_7, (
                    f"{team.metro} weeks {start + 1}-{start + 7}: {count} divisional "
                    f"in 7-game span"
                )
            windows = (
                (4, amounts.four_team_max_divisional_first_4),
                (8, amounts.four_team_max_divisional_first_8),
                (10, amounts.four_team_max_divisional_first_10),
            )
        for window, cap in windows:
            count = sum(pattern[:window])
            assert count <= cap, (
                f"{team.metro}: {count} divisional games in first {window} weeks (cap {cap})"
            )

        non_interleaved = _non_interleaved_count(
            _divisional_meeting_weeks(schedule, team)
        )
        assert non_interleaved <= amounts.max_non_interleaved_divisional_opponents, (
            f"{team.metro}: {non_interleaved} non-interleaved divisional opponents"
        )

    opening = [t for t in teams if _opens_with_divisional_pair(schedule, t)]
    assert len(opening) <= amounts.max_teams_divisional_weeks_1_and_2, (
        f"{len(opening)} teams open weeks 1-2 both divisional"
    )
    four = sum(1 for t in opening if t.division in FOUR_TEAM_DIVISIONS)
    five = sum(1 for t in opening if t.division in FIVE_TEAM_DIVISIONS)
    assert four <= amounts.four_team_max_teams_open_divisional_pair, (
        f"{four} four-team teams open weeks 1-2 both divisional"
    )
    assert five <= amounts.five_team_max_teams_open_divisional_pair, (
        f"{five} five-team teams open weeks 1-2 both divisional"
    )


def _validate_home_balance(schedule: Schedule, teams: tuple[Team, ...]) -> None:
    for team in teams:
        conf_games = [
            g
            for g in schedule.games_for(team)
            if g.home.conference == g.away.conference
            and g.home.division != g.away.division
        ]
        conf_home = sum(1 for g in conf_games if g.home == team)
        nonconf_home = sum(
            1
            for g in schedule.home_games_for(team)
            if g.away.conference != team.conference
        )
        if team.division in FIVE_TEAM_DIVISIONS:
            assert conf_home == 2, (
                f"{team.metro}: expected 2 conference home games, got {conf_home}"
            )
            assert nonconf_home == 2, (
                f"{team.metro}: expected 2 non-conference home games, got {nonconf_home}"
            )
        else:
            assert 2 <= conf_home <= 3, (
                f"{team.metro}: {conf_home} conference home games outside [2, 3]"
            )
            assert 2 <= nonconf_home <= 3, (
                f"{team.metro}: {nonconf_home} non-conference home games outside [2, 3]"
            )

    for division in FOUR_TEAM_DIVISIONS:
        div_teams = [t for t in teams if t.division == division]
        conf_home = sorted(
            sum(
                1
                for g in schedule.home_games_for(team)
                if g.away.conference == team.conference
                and g.away.division != team.division
            )
            for team in div_teams
        )
        nonconf_home = sorted(
            sum(
                1
                for g in schedule.home_games_for(team)
                if g.away.conference != team.conference
            )
            for team in div_teams
        )
        assert conf_home == [2, 2, 3, 3], (
            f"{division.name}: conference home split {conf_home}, expected [2, 2, 3, 3]"
        )
        assert nonconf_home == [2, 2, 3, 3], (
            f"{division.name}: non-conference home split {nonconf_home}, "
            f"expected [2, 2, 3, 3]"
        )


def _validate_league_wide_caps(
    schedule: Schedule, teams: tuple[Team, ...], amounts: Phase2Config
) -> None:
    home_streak = away_streak = div_streak = bunched = 0
    for team in teams:
        home = _home_pattern(schedule, team)
        away = [not h for h in home]
        home_streak += _count_streaks_of(home, 3) >= 1
        away_streak += _count_streaks_of(away, 3) >= 1
        div_streak += _count_streaks_of(_divisional_pattern(schedule, team), 3) >= 1
        bunched += (
            _non_interleaved_count(_divisional_meeting_weeks(schedule, team)) >= 2
        )
    assert home_streak <= amounts.max_teams_with_home_streak, (
        f"{home_streak} teams with a 3-game home streak"
    )
    assert away_streak <= amounts.max_teams_with_away_streak, (
        f"{away_streak} teams with a 3-game away streak"
    )
    assert div_streak <= amounts.max_teams_with_divisional_streak, (
        f"{div_streak} teams with a 3-game divisional streak"
    )
    assert bunched <= amounts.max_teams_with_two_bunched_rivals, (
        f"{bunched} teams with 2 non-interleaved rivals"
    )

    meeting_weeks: dict = {}
    for game in schedule.games:
        meeting_weeks.setdefault(make_matchup(game.home, game.away), []).append(
            game.week
        )
    close = sum(
        1 for w in meeting_weeks.values() if len(w) == 2 and abs(w[0] - w[1]) <= 2
    )
    assert close <= amounts.max_close_rematches, (
        f"{close} rematches within a 3-week span"
    )


def _validate_season_ending(
    schedule: Schedule, teams: tuple[Team, ...], amounts: Phase2Config
) -> None:
    if amounts.require_final_week_divisional:
        final_divisional = sum(
            1
            for g in schedule.games
            if g.week == NUM_WEEKS and g.home.division == g.away.division
        )
        assert final_divisional == WEEK_16_DIVISIONAL_GAMES, (
            f"week {NUM_WEEKS}: {final_divisional} divisional games, "
            f"expected {WEEK_16_DIVISIONAL_GAMES}"
        )
    if amounts.require_divisional_in_final_two_weeks:
        for team in teams:
            late = [
                g
                for g in schedule.games_for(team)
                if g.week in (NUM_WEEKS - 1, NUM_WEEKS)
            ]
            assert any(
                (g.away if g.home == team else g.home).division == team.division
                for g in late
            ), f"{team.metro}: no divisional game in the final 2 weeks"
