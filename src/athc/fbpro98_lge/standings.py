"""Rank teams the way the game orders a finished season's standings.

Won-lost-tied percentage first, then the manual's tie-breakers (page 129)
among the teams still level: head-to-head, division record, conference
record, net points in division games, net points in all games, strength of
schedule (the opponents' combined record, each opponent once). Net touchdowns
and the coin toss are not in the file, so teams level after all that keep
their given (file) order. Once a step separates some of a level group, the
teams it placed and the rest are each ranked again from the first step.

Works on team numbers, so the reader can rank before the model exists.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Result:
    """One played regular-season game, from one team's side."""

    opponent: int
    scored: int
    allowed: int
    division: bool
    """The opponent is in the team's division."""

    conference: bool
    """The opponent is in the team's conference."""


# Team number -> its results, for every team (an empty sequence for one with
# no game).
Season = Mapping[int, Sequence[Result]]


def season_from_games(
    games: Iterable[tuple[int, int, int, int]],
    division_of: Mapping[int, int],
    conference_of: Mapping[int, int],
) -> dict[int, list[Result]]:
    """Each team's results from (home, home score, away, away score) games;
    `division_of` and `conference_of` map every team number to its division
    and conference."""
    season: dict[int, list[Result]] = {number: [] for number in division_of}
    for home, home_score, away, away_score in games:
        for team, other, scored, allowed in (
            (home, away, home_score, away_score),
            (away, home, away_score, home_score),
        ):
            season[team].append(
                Result(
                    opponent=other,
                    scored=scored,
                    allowed=allowed,
                    division=division_of[team] == division_of[other],
                    conference=conference_of[team] == conference_of[other],
                )
            )
    return season


def percentage(results: Sequence[Result]) -> Fraction:
    """Won-lost-tied percentage, a tie counting half a win; 0 with no game."""
    if not results:
        return Fraction(0)
    points = sum(
        2 if r.scored > r.allowed else 1 if r.scored == r.allowed else 0
        for r in results
    )
    return Fraction(points, 2 * len(results))


def rank(teams: Sequence[int], season: Season) -> tuple[int, ...]:
    """`teams` best first: percentage, then the tie-breakers among the teams
    level with each other, then the given order."""
    ordered: list[int] = []
    remaining = sorted(teams, key=lambda team: -percentage(season[team]))
    while remaining:
        level = percentage(season[remaining[0]])
        group = [team for team in remaining if percentage(season[team]) == level]
        ordered += _break(group, season)
        remaining = remaining[len(group) :]
    return tuple(ordered)


def _break(group: list[int], season: Season) -> list[int]:
    if len(group) == 1:
        return group
    for step in _STEPS:
        values = {team: step(team, group, season) for team in group}
        best = max(values.values())
        winners = [team for team in group if values[team] == best]
        if len(winners) < len(group):
            rest = [team for team in group if values[team] != best]
            return _break(winners, season) + _break(rest, season)
    return group


def _head_to_head(team: int, group: list[int], season: Season) -> Fraction:
    others = set(group) - {team}
    return percentage([r for r in season[team] if r.opponent in others])


def _division(team: int, group: list[int], season: Season) -> Fraction:
    return percentage([r for r in season[team] if r.division])


def _conference(team: int, group: list[int], season: Season) -> Fraction:
    return percentage([r for r in season[team] if r.conference])


def _division_net_points(team: int, group: list[int], season: Season) -> int:
    return sum(r.scored - r.allowed for r in season[team] if r.division)


def _net_points(team: int, group: list[int], season: Season) -> int:
    return sum(r.scored - r.allowed for r in season[team])


def _strength_of_schedule(team: int, group: list[int], season: Season) -> Fraction:
    # Each opponent once, however often they met.
    opponents = dict.fromkeys(r.opponent for r in season[team])
    return percentage([r for opponent in opponents for r in season[opponent]])


_Step = Callable[[int, list[int], Season], Fraction | int]
_STEPS: tuple[_Step, ...] = (
    _head_to_head,
    _division,
    _conference,
    _division_net_points,
    _net_points,
    _strength_of_schedule,
)
