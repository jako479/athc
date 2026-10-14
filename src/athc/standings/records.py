"""Each team's standings row, from one league file's regular-season games."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from athc.fbpro98_lge import LgeFile, Team


@dataclass(frozen=True, slots=True)
class Split:
    """Wins, losses and ties in some of a team's games."""

    wins: int
    losses: int
    ties: int


@dataclass(frozen=True, slots=True)
class Row:
    """One team's standings values, from its regular-season games."""

    team: Team
    overall: Split
    home: Split
    away: Split
    division: Split
    """Against the team's own division."""

    conference: Split
    """Against the team's own conference."""

    points_for: int
    points_against: int
    streak: str
    """`W3`, `L2`: the run of wins or losses ending with the latest game; `-`
    when the latest game was a tie or none was played."""


@dataclass(frozen=True, slots=True)
class _Game:
    """One played regular-season game, from one team's side."""

    scored: int
    allowed: int
    home: bool
    division: bool
    conference: bool


def rows_of(lge: LgeFile) -> dict[int, Row]:
    """Each team's row, keyed by `id(team)`: teams are found by identity, so
    two teams that look the same never mix."""
    division_of: dict[int, int] = {}
    conference_of: dict[int, int] = {}
    division_number = 0
    for conference_number, conference in enumerate(lge.conferences):
        for division in conference.divisions:
            for team in division.teams:
                division_of[id(team)] = division_number
                conference_of[id(team)] = conference_number
            division_number += 1
    games: dict[int, list[_Game]] = {id(team): [] for team in lge.teams}
    for week in lge.weeks:
        for game in week:
            home, away = id(game.home), id(game.away)
            division = division_of[home] == division_of[away]
            conference = conference_of[home] == conference_of[away]
            games[home].append(
                _Game(
                    scored=game.home_score,
                    allowed=game.away_score,
                    home=True,
                    division=division,
                    conference=conference,
                )
            )
            games[away].append(
                _Game(
                    scored=game.away_score,
                    allowed=game.home_score,
                    home=False,
                    division=division,
                    conference=conference,
                )
            )
    return {id(team): _row(team, games[id(team)]) for team in lge.teams}


def _row(team: Team, games: list[_Game]) -> Row:
    return Row(
        team=team,
        overall=_split(games),
        home=_split(game for game in games if game.home),
        away=_split(game for game in games if not game.home),
        division=_split(game for game in games if game.division),
        conference=_split(game for game in games if game.conference),
        points_for=sum(game.scored for game in games),
        points_against=sum(game.allowed for game in games),
        streak=_streak(games),
    )


def _split(games: Iterable[_Game]) -> Split:
    wins = losses = ties = 0
    for game in games:
        if game.scored > game.allowed:
            wins += 1
        elif game.scored < game.allowed:
            losses += 1
        else:
            ties += 1
    return Split(wins, losses, ties)


def _streak(games: list[_Game]) -> str:
    # The games are in week order, so the latest is last.
    if not games or games[-1].scored == games[-1].allowed:
        return "-"
    won = games[-1].scored > games[-1].allowed
    run = 0
    for game in reversed(games):
        if game.scored == game.allowed or (game.scored > game.allowed) != won:
            break
        run += 1
    return f"{'W' if won else 'L'}{run}"
