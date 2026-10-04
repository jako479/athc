"""Parse a written `.txt` schedule and validate it against every scheduler rule.

One validator for every league: `validate_schedule` takes the schedule, its
league and its config and checks every rule that applies -- structural rules
always, divisional rules when the league has divisions, and the toggled or
configured rules when the config turns them on. Amounts and counts come from the
config and the league, never literals. Used by the golden regression test and by
the solved-schedule unit tests, independently of the solver.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from itertools import pairwise

from athc.scheduler.config import Phase2Config, SchedulerConfig, resolve_rivalries
from athc.scheduler.domain.league import League, Team, team_by_metro
from athc.scheduler.domain.schedule import GAMES_PER_WEEK, Game, Schedule
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup
from athc.scheduler.writers.report import build_schedule_report

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
    values match an independent recomputation."""
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
        all_opps = _opponents(schedule, team)
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


def _opponents(schedule: Schedule, team: Team) -> list[Team]:
    return [
        g.away if g.home == team else g.home
        for g in sorted(schedule.games_for(team), key=lambda g: g.week)
    ]


def _home_pattern(schedule: Schedule, team: Team, weeks: int) -> list[bool]:
    pattern = [False] * weeks
    for game in schedule.home_games_for(team):
        pattern[game.week - 1] = True
    return pattern


def _divisional_pattern(schedule: Schedule, team: Team, weeks: int) -> list[bool]:
    pattern = [False] * weeks
    for game in schedule.games_for(team):
        opponent = game.away if game.home == team else game.home
        if opponent.same_division(team):
            pattern[game.week - 1] = True
    return pattern


def _count_streaks_of(pattern: Sequence[bool], length: int) -> int:
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
        if opponent.same_division(team):
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
        and (g.away if g.home == team else g.home).same_division(team)
    )
    return opening == 2


def _is_five_team(team: Team) -> bool:
    # The model's size split: 5-team divisions take the five_team_* amounts,
    # every other size the four_team_* amounts.
    return team.division is not None and team.division.expected_size == 5


def validate_schedule(
    schedule: Schedule, league: League, config: SchedulerConfig, *, season: int
) -> None:
    """Assert `schedule` obeys every rule that applies to `league` under
    `config`. Raises AssertionError on any violation."""
    weeks = config.league.weeks
    amounts = config.phase2
    teams = league.teams

    _validate_structure(schedule, teams, weeks)
    _validate_inventory(schedule, league, weeks)
    _validate_home_balance(schedule, league, weeks)
    _validate_home_away_sequencing(schedule, teams, weeks, amounts)
    _validate_opening_weeks(schedule, league, amounts)
    _validate_conference_sequence(schedule, league, amounts)
    _validate_rivalry_week(schedule, league, config, weeks, season)
    if league.has_divisions:
        _validate_no_back_to_back(schedule)
        _validate_divisional_sequencing(schedule, league, weeks, amounts)
        _validate_divisional_league_caps(schedule, teams, weeks, amounts)
        _validate_season_ending(schedule, league, weeks, amounts)


def _validate_structure(
    schedule: Schedule, teams: tuple[Team, ...], weeks: int
) -> None:
    assert len(schedule.games) == weeks * GAMES_PER_WEEK, (
        f"expected {weeks * GAMES_PER_WEEK} games, got {len(schedule.games)}"
    )
    for week in range(1, weeks + 1):
        week_games = [g for g in schedule.games if g.week == week]
        assert len(week_games) == GAMES_PER_WEEK, (
            f"week {week}: expected {GAMES_PER_WEEK} games, got {len(week_games)}"
        )
    for game in schedule.games:
        assert game.home != game.away, f"team plays itself in week {game.week}"
    for team in teams:
        played = schedule.games_for(team)
        assert len(played) == weeks, (
            f"{team.metro}: expected {weeks} games, got {len(played)}"
        )
        week_counts = Counter(g.week for g in played)
        for week in range(1, weeks + 1):
            assert week_counts[week] == 1, (
                f"{team.metro}: expected exactly 1 game in week {week}"
            )
        assert len(schedule.home_games_for(team)) == weeks // 2, (
            f"{team.metro}: expected {weeks // 2} home games"
        )


def _validate_inventory(schedule: Schedule, league: League, weeks: int) -> None:
    teams = league.teams
    pair_counts: Counter = Counter()
    for game in schedule.games:
        pair_counts[make_matchup(game.home, game.away)] += 1

    for i, team_a in enumerate(teams):
        for team_b in teams[i + 1 :]:
            pair = make_matchup(team_a, team_b)
            if team_a.same_division(team_b):
                meetings = schedule.games_between(team_a, team_b)
                assert len(meetings) == 2, (
                    f"{team_a.metro}/{team_b.metro}: expected 2 divisional meetings"
                )
                assert sum(1 for g in meetings if g.home == team_a) == 1, (
                    f"{team_a.metro}/{team_b.metro}: {team_a.metro} must host once"
                )
            elif team_a.conference == team_b.conference:
                assert pair_counts[pair] == 1, (
                    f"{team_a.metro}/{team_b.metro}: expected 1 conference game"
                )
            else:
                assert pair_counts[pair] <= 1, (
                    f"{team_a.metro}/{team_b.metro}: non-conference pair met twice"
                )

    # The same-place rule: each division place meets the same place in every
    # other-conference division that has that place.
    for division, order in league.division_standings.items():
        for other, other_order in league.division_standings.items():
            if other.conference == division.conference:
                continue
            for place, team in enumerate(order):
                if place < len(other_order):
                    rival = other_order[place]
                    assert pair_counts[make_matchup(team, rival)] == 1, (
                        f"{team.metro}/{rival.metro}: same-place game missing"
                    )

    for team in teams:
        nonconf = [
            g
            for g in schedule.games_for(team)
            if g.home.conference != g.away.conference
        ]
        expected = league.nonconference_games(team, weeks)
        assert len(nonconf) == expected, (
            f"{team.metro}: expected {expected} non-conference games, got {len(nonconf)}"
        )


def _validate_home_balance(schedule: Schedule, league: League, weeks: int) -> None:
    # Each team hosts half its conference games and half its non-conference
    # games (the odd game either way).
    for team in league.teams:
        conference = len(league.conference_opponents(team))
        nonconference = league.nonconference_games(team, weeks)
        conf_home = sum(
            1
            for g in schedule.home_games_for(team)
            if g.away.conference == team.conference and not g.away.same_division(team)
        )
        nonconf_home = sum(
            1
            for g in schedule.home_games_for(team)
            if g.away.conference != team.conference
        )
        assert conference // 2 <= conf_home <= (conference + 1) // 2, (
            f"{team.metro}: {conf_home} conference home games of {conference}"
        )
        assert nonconference // 2 <= nonconf_home <= (nonconference + 1) // 2, (
            f"{team.metro}: {nonconf_home} non-conference home games of {nonconference}"
        )


def _validate_home_away_sequencing(
    schedule: Schedule, teams: tuple[Team, ...], weeks: int, amounts: Phase2Config
) -> None:
    cap = amounts.max_consecutive_home_or_away
    for team in teams:
        home = _home_pattern(schedule, team, weeks)
        away = [not h for h in home]

        for start in range(weeks - cap):
            window = slice(start, start + cap + 1)
            assert sum(home[window]) <= cap, (
                f"{team.metro}: >{cap} straight home from week {start + 1}"
            )
            assert sum(away[window]) <= cap, (
                f"{team.metro}: >{cap} straight away from week {start + 1}"
            )

        if amounts.require_home_balance_per_six_weeks:
            for start in range(weeks - 5):
                window_home = sum(home[start : start + 6])
                assert (
                    amounts.min_home_per_six_weeks
                    <= window_home
                    <= amounts.max_home_per_six_weeks
                ), (
                    f"{team.metro} weeks {start + 1}-{start + 6}: {window_home} home "
                    f"games outside [{amounts.min_home_per_six_weeks}, "
                    f"{amounts.max_home_per_six_weeks}]"
                )

        if amounts.require_mixed_home_away_at_season_ends:
            assert 1 <= sum(home[:3]) <= 2, (
                f"{team.metro}: 3-game home/away streak to start the season"
            )
            assert 1 <= sum(home[-3:]) <= 2, (
                f"{team.metro}: 3-game home/away streak to end the season"
            )

        if amounts.require_home_away_streak_caps:
            total_streaks = _count_streaks_of(home, 3) + _count_streaks_of(away, 3)
            assert total_streaks <= amounts.max_three_game_home_away_streaks, (
                f"{team.metro}: {total_streaks} total 3-game home/away streaks"
            )

    if amounts.require_home_away_streak_caps:
        home_streak = away_streak = 0
        for team in teams:
            home = _home_pattern(schedule, team, weeks)
            home_streak += _count_streaks_of(home, 3) >= 1
            away_streak += _count_streaks_of([not h for h in home], 3) >= 1
        assert home_streak <= amounts.max_teams_with_home_streak, (
            f"{home_streak} teams with a 3-game home streak"
        )
        assert away_streak <= amounts.max_teams_with_away_streak, (
            f"{away_streak} teams with a 3-game away streak"
        )


def _validate_opening_weeks(
    schedule: Schedule, league: League, amounts: Phase2Config
) -> None:
    # Weeks 1..N hold no same-conference game.
    opening = amounts.opening_nonconference_weeks
    for game in schedule.games:
        if game.week <= opening:
            assert game.home.conference != game.away.conference, (
                f"week {game.week}: same-conference game in the opening weeks"
            )


def _validate_conference_sequence(
    schedule: Schedule, league: League, amounts: Phase2Config
) -> None:
    # Along a team's conference games only: no cap + 1 straight home or away.
    cap = amounts.max_consecutive_conference_home_or_away
    if cap == 0:
        return
    for team in league.teams:
        venues = [
            g.home == team
            for g in sorted(schedule.games_for(team), key=lambda g: g.week)
            if g.home.conference == g.away.conference
        ]
        for start in range(len(venues) - cap):
            assert len(set(venues[start : start + cap + 1])) == 2, (
                f"{team.metro}: >{cap} straight conference games at the same venue"
            )


def _validate_rivalry_week(
    schedule: Schedule,
    league: League,
    config: SchedulerConfig,
    weeks: int,
    season: int,
) -> None:
    rivalries = resolve_rivalries(league, config.rivalries)
    if not rivalries:
        return
    final = [g for g in schedule.games if g.week == weeks]
    assert {make_matchup(g.home, g.away) for g in final} == {
        make_matchup(a, b) for a, b in rivalries
    }, "the final week is not exactly the rivalry pairs"
    if config.rivalries.rotate_home_by_season:
        hosts = {g.home for g in final}
        expected = {first if season % 2 == 0 else second for first, second in rivalries}
        assert hosts == expected, f"season {season}: wrong rival hosts"


def _validate_no_back_to_back(schedule: Schedule) -> None:
    pair_weeks: dict = {}
    for game in schedule.games:
        pair_weeks.setdefault(make_matchup(game.home, game.away), []).append(game.week)
    for pair, pair_week_list in pair_weeks.items():
        ordered = sorted(pair_week_list)
        for first, second in pairwise(ordered):
            assert second - first > 1, (
                f"{pair[0].metro}/{pair[1].metro}: back-to-back weeks {first}, {second}"
            )


def _validate_divisional_sequencing(
    schedule: Schedule, league: League, weeks: int, amounts: Phase2Config
) -> None:
    cap = amounts.max_consecutive_divisional
    for team in league.teams:
        pattern = _divisional_pattern(schedule, team, weeks)

        for start in range(weeks - cap):
            assert sum(pattern[start : start + cap + 1]) <= cap, (
                f"{team.metro}: >{cap} straight divisional from week {start + 1}"
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

        if _is_five_team(team):
            for start in range(weeks - 8):
                count = sum(pattern[start : start + 9])
                assert count <= amounts.five_team_max_divisional_in_9, (
                    f"{team.metro} weeks {start + 1}-{start + 9}: {count} divisional "
                    f"in 9-game span"
                )
            windows = (
                (5, amounts.five_team_max_divisional_first_5),
                (6, amounts.five_team_max_divisional_first_6),
                (8, amounts.five_team_max_divisional_first_8),
                (10, amounts.five_team_max_divisional_first_10),
            )
        else:
            if team.division is not None and team.division.expected_size == 4:
                for start in range(weeks - 6):
                    count = sum(pattern[start : start + 7])
                    assert count <= amounts.four_team_max_divisional_in_7, (
                        f"{team.metro} weeks {start + 1}-{start + 7}: {count} "
                        f"divisional in 7-game span"
                    )
            windows = (
                (4, amounts.four_team_max_divisional_first_4),
                (8, amounts.four_team_max_divisional_first_8),
                (10, amounts.four_team_max_divisional_first_10),
            )
        for window, window_cap in windows:
            count = sum(pattern[:window])
            assert count <= window_cap, (
                f"{team.metro}: {count} divisional games in first {window} weeks "
                f"(cap {window_cap})"
            )

        non_interleaved = _non_interleaved_count(
            _divisional_meeting_weeks(schedule, team)
        )
        assert non_interleaved <= amounts.max_non_interleaved_divisional_opponents, (
            f"{team.metro}: {non_interleaved} non-interleaved divisional opponents"
        )

    opening = [t for t in league.teams if _opens_with_divisional_pair(schedule, t)]
    assert len(opening) <= amounts.max_teams_divisional_weeks_1_and_2, (
        f"{len(opening)} teams open weeks 1-2 both divisional"
    )
    five = sum(1 for t in opening if _is_five_team(t))
    four = len(opening) - five
    assert four <= amounts.four_team_max_teams_open_divisional_pair, (
        f"{four} four-team teams open weeks 1-2 both divisional"
    )
    assert five <= amounts.five_team_max_teams_open_divisional_pair, (
        f"{five} five-team teams open weeks 1-2 both divisional"
    )


def _validate_divisional_league_caps(
    schedule: Schedule, teams: tuple[Team, ...], weeks: int, amounts: Phase2Config
) -> None:
    div_streak = bunched = 0
    for team in teams:
        div_streak += (
            _count_streaks_of(_divisional_pattern(schedule, team, weeks), 3) >= 1
        )
        bunched += (
            _non_interleaved_count(_divisional_meeting_weeks(schedule, team)) >= 2
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
    schedule: Schedule, league: League, weeks: int, amounts: Phase2Config
) -> None:
    if amounts.require_final_week_divisional:
        final_divisional = sum(
            1
            for g in schedule.games
            if g.week == weeks and g.home.same_division(g.away)
        )
        assert final_divisional == league.max_divisional_games_per_week, (
            f"week {weeks}: {final_divisional} divisional games, "
            f"expected {league.max_divisional_games_per_week}"
        )
    if amounts.require_divisional_in_final_two_weeks:
        for team in league.teams:
            late = [g for g in schedule.games_for(team) if g.week in (weeks - 1, weeks)]
            assert any(
                (g.away if g.home == team else g.home).same_division(team) for g in late
            ), f"{team.metro}: no divisional game in the final 2 weeks"
