"""The tie-break steps.

Each step gives every level team a value, higher is better, or None when it
does not apply to these teams; the ranking then skips it. Values are exact
(`Fraction`), so equal records compare equal.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from fractions import Fraction
from typing import Literal, Protocol

from athc.fbpro98_standings.season import Result, Season

Value = Fraction | int
Values = Mapping[int, Value]


class Context(Protocol):
    """What a step may look at besides the level teams."""

    season: Season

    def division_order(self, division: int) -> tuple[int, ...]:
        """The season's division, in its standings by the same method."""
        ...


Step = Callable[[Sequence[int], Context], Values | None]


def percentage(results: Iterable[Result]) -> Fraction:
    """W-L-T percentage, a tie counting half a win; 0 with no game."""
    games = tuple(results)
    if not games:
        return Fraction(0)
    points = sum(2 if game.won else 0 if game.lost else 1 for game in games)
    return Fraction(points, 2 * len(games))


def win_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in every game."""
    results = context.season.results
    return {team: percentage(results[team]) for team in group}


def head_to_head(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in the games among the level teams only."""
    results = context.season.results
    level = set(group)
    return {
        team: percentage(game for game in results[team] if game.opponent in level)
        for team in group
    }


def head_to_head_sweep(group: Sequence[int], context: Context) -> Values | None:
    """Two teams: head-to-head. Three or more: only a team that beat every
    other level team, or lost to every one, is placed, first or last."""
    if len(group) == 2:
        return head_to_head(group, context)
    results = context.season.results
    for team in group:
        others = set(group) - {team}
        games = [game for game in results[team] if game.opponent in others]
        if {game.opponent for game in games} != others:
            continue
        if all(game.won for game in games):
            return {other: int(other == team) for other in group}
        if all(game.lost for game in games):
            return {other: -int(other == team) for other in group}
    return None


def division_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in division games."""
    results = context.season.results
    return {
        team: percentage(game for game in results[team] if game.division)
        for team in group
    }


def conference_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in conference games."""
    results = context.season.results
    return {
        team: percentage(game for game in results[team] if game.conference)
        for team in group
    }


def _common_opponents(group: Sequence[int], context: Context) -> set[int]:
    results = context.season.results
    opponents = [{game.opponent for game in results[team]} for team in group]
    return opponents[0].intersection(*opponents[1:])


def common_games(minimum: int) -> Step:
    """W-L-T % against the opponents every level team played; skipped when a
    team played fewer than `minimum` such games."""

    def step(group: Sequence[int], context: Context) -> Values | None:
        common = _common_opponents(group, context)
        results = context.season.results
        games = {
            team: [game for game in results[team] if game.opponent in common]
            for team in group
        }
        if any(len(played) < minimum for played in games.values()):
            return None
        return {team: percentage(played) for team, played in games.items()}

    return step


def common_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points against the opponents every level team played."""
    common = _common_opponents(group, context)
    results = context.season.results
    return {
        team: sum(
            game.scored - game.allowed
            for game in results[team]
            if game.opponent in common
        )
        for team in group
    }


def strength_of_victory(group: Sequence[int], context: Context) -> Values:
    """Combined W-L-T % of the teams beaten, every win counted."""
    results = context.season.results
    return {
        team: percentage(
            beaten
            for game in results[team]
            if game.won
            for beaten in results[game.opponent]
        )
        for team in group
    }


def strength_of_schedule(each_opponent_once: bool) -> Step:
    """Combined W-L-T % of the opponents, tougher higher: each opponent once
    (the game's manual), or every game counted (the NFL's)."""

    def step(group: Sequence[int], context: Context) -> Values:
        results = context.season.results
        values: dict[int, Value] = {}
        for team in group:
            opponents = [game.opponent for game in results[team]]
            if each_opponent_once:
                opponents = list(dict.fromkeys(opponents))
            values[team] = percentage(
                game for opponent in opponents for game in results[opponent]
            )
        return values

    return step


def combined_ranking(scope: Literal["conference", "league"]) -> Step:
    """A team's rank in points scored plus its rank in points allowed, among
    its conference's or the league's teams; lower is better, and equal
    values share a rank."""

    def step(group: Sequence[int], context: Context) -> Values:
        season = context.season
        scored = [sum(game.scored for game in games) for games in season.results]
        allowed = [sum(game.allowed for game in games) for games in season.results]
        values: dict[int, Value] = {}
        for team in group:
            pool = [
                other
                for other in range(len(season.teams))
                if scope == "league"
                or season.conference_of[other] == season.conference_of[team]
            ]
            scored_rank = sum(scored[other] > scored[team] for other in pool)
            allowed_rank = sum(allowed[other] < allowed[team] for other in pool)
            values[team] = -(scored_rank + allowed_rank)
        return values

    return step


def net_points(group: Sequence[int], context: Context) -> Values:
    """Points for minus points against, in every game."""
    results = context.season.results
    return {
        team: sum(game.scored - game.allowed for game in results[team])
        for team in group
    }


def division_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points in division games."""
    results = context.season.results
    return {
        team: sum(game.scored - game.allowed for game in results[team] if game.division)
        for team in group
    }


def conference_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points in conference games."""
    results = context.season.results
    return {
        team: sum(
            game.scored - game.allowed for game in results[team] if game.conference
        )
        for team in group
    }


def division_finish(group: Sequence[int], context: Context) -> Values | None:
    """Level teams all of one division keep their order in its standings;
    skipped for teams of different divisions."""
    divisions = {context.season.division_of[team] for team in group}
    if len(divisions) != 1:
        return None
    order = context.division_order(divisions.pop())
    return {team: -order.index(team) for team in group}


def playoff_round(group: Sequence[int], context: Context) -> Values:
    """The playoff round reached; the champion highest."""
    season = context.season
    return {team: season.playoff_round[team] for team in group}


def champion_then_runner_up(group: Sequence[int], context: Context) -> Values:
    """The champion first, the Super Bowl loser second, every other team
    level."""
    season = context.season
    return {
        team: 2 if team == season.champion else 1 if team == season.runner_up else 0
        for team in group
    }
