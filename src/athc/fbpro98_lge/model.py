"""In-memory data model for FbPro98 .lge league files.

The league's conferences, their divisions and the divisions' teams, nested the
way the file's chunk tree is, in file order, each team with its record.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
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


def _ranked(teams: Iterable[Team]) -> tuple[Team, ...]:
    # sorted() is stable, so teams still level stay in file order.
    return tuple(
        sorted(
            teams,
            key=lambda team: (
                -team.record.win_percentage,
                -team.record.point_differential,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class Division:
    """One division and its teams, in file order."""

    name: str
    teams: tuple[Team, ...]

    @property
    def standings(self) -> tuple[Team, ...]:
        """Its teams, best first: win percentage, then point differential,
        then file order."""
        return _ranked(self.teams)


@dataclass(frozen=True, slots=True)
class Conference:
    """One conference and its divisions, in file order."""

    name: str
    divisions: tuple[Division, ...]

    @property
    def standings(self) -> tuple[Team, ...]:
        """Every team in its divisions, best first, ranked as
        `Division.standings`."""
        return _ranked(team for division in self.divisions for team in division.teams)


@dataclass(frozen=True, slots=True)
class LgeFile:
    """The parts of a league's `.lge` file this library reads."""

    conferences: tuple[Conference, ...]
    """In file order. Walking conferences, divisions and teams in order gives
    team numbers 1..N, which key the other league files (see specs/lge.md)."""
