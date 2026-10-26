"""In-memory data model for FbPro98 .lge league files.

The league's conferences, their divisions and the divisions' teams, nested the
way the file's chunk tree is, in file order, each team with its record; each
division's and conference's standings; and the played games, by
regular-season week and by playoff round. Mutable classes, edited by
assignment.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from athc.fbpro98_lge._standings import rank, season_from_games


@dataclass(slots=True)
class Record:
    """A team's regular-season record from the games played so far."""

    wins: int
    losses: int
    ties: int
    points_for: int
    points_against: int

    @property
    def games(self) -> int:
        """Games played."""
        return self.wins + self.losses + self.ties

    @property
    def win_percentage(self) -> float:
        """Wins plus half the ties, over games played; 0.0 before any game."""
        if not self.games:
            return 0.0
        return (self.wins + self.ties / 2) / self.games

    @property
    def point_differential(self) -> int:
        """Points for minus points against."""
        return self.points_for - self.points_against


@dataclass(slots=True)
class Team:
    """One team's names, as on the game's Team Settings screen, and record."""

    name: str
    """The "Team Name", e.g. `Denver`."""

    nickname: str
    """The "Nickname", e.g. `Broncos`."""

    record: Record
    """Regular-season record."""

    @property
    def official_name(self) -> str:
        """Team name and nickname, e.g. `Denver Broncos`; just the one present
        when the other is empty."""
        return " ".join(part for part in (self.name, self.nickname) if part)


@dataclass(slots=True)
class Game:
    """One played game."""

    home: Team
    home_score: int
    away: Team
    away_score: int

    @property
    def winner(self) -> Team | None:
        """The team that scored more; None on a tie."""
        if self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self) -> Team | None:
        """The team that scored less; None on a tie."""
        if self.home_score == self.away_score:
            return None
        return self.away if self.home_score > self.away_score else self.home


@dataclass(slots=True)
class Division:
    """One division and its teams."""

    name: str

    teams: list[Team]
    """In file order."""

    standings: list[Team]
    """Its teams best first, the way the game orders a finished season:
    won-lost-tied percentage, then the manual's tie-breakers (see
    _standings.py), then file order."""


@dataclass(slots=True)
class Conference:
    """One conference and its divisions."""

    name: str

    divisions: list[Division]
    """In file order."""

    standings: list[Team]
    """Every team in its divisions, best first, ordered as
    `Division.standings`."""


@dataclass(slots=True)
class LgeFile:
    """The parts of a league's `.lge` file this library reads."""

    conferences: list[Conference]
    """In file order. Walking conferences, divisions and teams in order gives
    team numbers 1..N, which key the other league files (see docs/formats/lge.md)."""

    weeks: list[list[Game]] = field(default_factory=list)
    """The regular season: each week's played games, in file order."""

    playoffs: list[list[Game]] = field(default_factory=list)
    """The playoffs: each round's played games, in file order."""

    unplayed_games: int = 0
    """Regular-season and playoff games not played yet."""

    @property
    def teams(self) -> list[Team]:
        """Every team in file order: team N is at index N - 1."""
        return [
            team
            for conference in self.conferences
            for division in conference.divisions
            for team in division.teams
        ]


def ranked(lge: LgeFile, teams: Iterable[Team] | None = None) -> list[Team]:
    """`teams` (any of the file's own team objects; every team when None) best
    first, ordered as `Division.standings` from every regular-season game in
    the file, with the given order last."""
    every = lge.teams
    if teams is None:
        teams = every
    number_of = {id(team): number for number, team in enumerate(every, 1)}
    division_of: dict[int, int] = {}
    conference_of: dict[int, int] = {}
    number = division_number = 0
    for conference_number, conference in enumerate(lge.conferences, 1):
        for division in conference.divisions:
            division_number += 1
            for _ in division.teams:
                number += 1
                division_of[number] = division_number
                conference_of[number] = conference_number
    season = season_from_games(
        (
            (number_of[id(g.home)], g.home_score, number_of[id(g.away)], g.away_score)
            for week in lge.weeks
            for g in week
        ),
        division_of,
        conference_of,
    )
    order = rank([number_of[id(team)] for team in teams], season)
    return [every[number - 1] for number in order]
