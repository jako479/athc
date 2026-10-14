"""Leagues for the fbpro98_standings tests.

`build_league` makes an `LgeFile` in code from a shape of team names and the
games by name; `win` writes one game. `real_lge` reads a real `.lge` from the
fbpro98_lge or integration test data. Records stay at zero: the library works
from the games, never from `Team.record`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from athc.fbpro98_lge import (
    Conference,
    Division,
    Game,
    LgeFile,
    Record,
    Team,
    parse_lge,
)

TESTS = Path(__file__).resolve().parents[2]
DATA_DIRS = (TESTS / "unit" / "fbpro98_lge" / "data", TESTS / "integration" / "data")
NO_GAMES = Record(0, 0, 0, 0, 0)

# Conferences, each a list of divisions, each a list of team names.
Shape = Sequence[Sequence[Sequence[str]]]
# Home team, home score, away team, away score.
Played = tuple[str, int, str, int]


def win(winner: str, loser: str, by: int = 10) -> Played:
    """A game the first team won by `by` points, at home."""
    return (winner, 10 + by, loser, 10)


def build_league(
    shape: Shape,
    games: Sequence[Played] = (),
    playoffs: Sequence[Sequence[Played]] = (),
) -> LgeFile:
    """Conferences `C1`.. and divisions `D1`.. in file order; one
    regular-season week per game; one playoff round per inner list."""
    teams = {
        name: Team(name=name, nickname="", record=NO_GAMES)
        for conference in shape
        for division in conference
        for name in division
    }
    conferences: list[Conference] = []
    count = 0
    for conference_number, conference in enumerate(shape, 1):
        divisions: list[Division] = []
        for division_names in conference:
            count += 1
            members = tuple(teams[name] for name in division_names)
            divisions.append(
                Division(name=f"D{count}", teams=members, standings=members)
            )
        members = tuple(team for division in divisions for team in division.teams)
        conferences.append(
            Conference(
                name=f"C{conference_number}",
                divisions=tuple(divisions),
                standings=members,
            )
        )

    def game(played: Played) -> Game:
        home, home_score, away, away_score = played
        return Game(teams[home], home_score, teams[away], away_score)

    return LgeFile(
        conferences=tuple(conferences),
        weeks=tuple((game(played),) for played in games),
        playoffs=tuple(
            tuple(game(played) for played in games_in_round)
            for games_in_round in playoffs
        ),
    )


def real_lge(filename: str) -> LgeFile:
    """A real `.lge` from the test data folders."""
    for folder in DATA_DIRS:
        path = folder / filename
        if path.exists():
            return parse_lge(path.read_bytes(), path)
    raise FileNotFoundError(filename)


def names(teams: Sequence[Team]) -> tuple[str, ...]:
    return tuple(team.name for team in teams)
