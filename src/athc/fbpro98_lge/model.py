"""In-memory data model for FbPro98 .lge league files.

The league's conferences, their divisions and the divisions' teams, nested the
way the file's chunk tree is, in file order, each team with its record and its
roster; each division's and conference's standings; and the played games, by
regular-season week and by playoff round. Mutable classes, edited by
assignment; `LgeFile.validate()` checks the roster rules the spec states
before a write or after an edit (the reader does not call it).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from athc.fbpro98_lge._standings import rank, season_from_games
from athc.fbpro98_lge.schema import (
    ROSTER_ASSIGNED_SLOTS,
    ROSTER_CAMP_GROUPS,
    ROSTER_CAMP_RATINGS,
    ROSTER_INJURED_RESERVE_SLOTS,
    ROSTER_OPEN_ACTIVE_SLOTS,
    ROSTER_OPEN_INACTIVE_SLOTS,
    ROSTER_PERMUTATION_SIZE,
    ROSTER_UNKNOWN_SIZE,
)

CAMP_PERCENT_MAX = 100
"""A training camp percentage's limit, and a camp row's total's."""

_U8_MAX = 0xFF
_U16_MAX = 0xFFFF


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
class RosterPlayer:
    """A player on a roster: which player, with the jersey number the roster
    gives them."""

    player_id: int
    """The `.pyr` player id, 1-65535."""

    jersey: int
    """Jersey number."""


@dataclass(slots=True)
class Roster:
    """One team's roster chunk, decoded (docs/formats/lge.md section 6): its
    63 slots by status, as the game's roster screen groups them, each list in
    slot order with `None` for an empty slot."""

    team_number: int
    """The chunk's own team number, in clear; it keys the mask."""

    assigned: list[RosterPlayer | None]
    """The 34 Assigned slots ("A" on the roster screen): the depth chart."""

    open_active: list[RosterPlayer | None]
    """The 12 Open Active slots ("O")."""

    open_inactive: list[RosterPlayer | None]
    """The 7 Open Inactive slots ("I")."""

    injured_reserve: list[RosterPlayer | None]
    """The 10 Injured Reserve slots ("IF")."""

    permutation: bytes
    """The 10 bytes at 0xBD, as read; a permutation of 0-9 in every sampled
    file, meaning unknown."""

    training_camp: list[list[int]]
    """The Training Camp screen: one row per position group in the screen's
    order (QB, RB, REC, OL, DL, LB, DB, P/K), each row one percentage per
    rating in `.pyr` order (AC, AG, DI, EN, HA, IN, SP, ST); all zero for a
    team never set up."""

    unknown: bytes
    """The 60 bytes at 0x107, as read; the same in every sampled team."""

    @property
    def players(self) -> list[RosterPlayer]:
        """Every player, in slot order: assigned, open active, open inactive,
        then injured reserve."""
        return [
            player
            for group in (
                self.assigned,
                self.open_active,
                self.open_inactive,
                self.injured_reserve,
            )
            for player in group
            if player is not None
        ]


@dataclass(slots=True)
class Team:
    """One team's names, as on the game's Team Settings screen, its record
    and its roster."""

    name: str
    """The "Team Name", e.g. `Denver`."""

    nickname: str
    """The "Nickname", e.g. `Broncos`."""

    record: Record
    """Regular-season record."""

    roster: Roster
    """The team's roster chunk."""

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

    def team_of(self, player_id: int) -> Team | None:
        """The team whose roster holds `player_id`, the first in file order;
        None when no roster does."""
        for team in self.teams:
            if any(player.player_id == player_id for player in team.roster.players):
                return team
        return None

    def validate(self) -> None:
        """Check every roster rule the spec states, so a roster can be written
        back; the names and games are not checked. The reader does not call
        it: a file's roster fields are fixed-size, so only the training camp
        percentages could fail, and a tool that never looks at rosters should
        not be refused its league over them (whether the game would refuse
        such a file is untested; no sampled file has one).

        Raises:
            ValueError: On the first rule broken, in file order; the message
                names the team by its file-order number, then the place as the
                game's screens name it (status groups and slots counted from
                1, camp groups and ratings), then the field and the rule as a
                sentence without its period (`team 5: roster: Assigned slot 4:
                player_id: Must be 1-65535, got 65536`).
        """
        for number, team in enumerate(self.teams, 1):
            _check_roster(f"team {number}: roster", team.roster)


def _check_roster(label: str, roster: Roster) -> None:
    _check_range(f"{label}: team_number", roster.team_number, _U16_MAX)
    groups = (
        ("Assigned", roster.assigned, ROSTER_ASSIGNED_SLOTS),
        ("Open Active", roster.open_active, ROSTER_OPEN_ACTIVE_SLOTS),
        ("Open Inactive", roster.open_inactive, ROSTER_OPEN_INACTIVE_SLOTS),
        ("Injured Reserve", roster.injured_reserve, ROSTER_INJURED_RESERVE_SLOTS),
    )
    for name, group, size in groups:
        if len(group) != size:
            raise ValueError(f"{label}: {name}: Must be {size} slots, got {len(group)}")
        for slot, player in enumerate(group, 1):
            if player is None:
                continue
            place = f"{label}: {name} slot {slot}"
            _check_range(f"{place}: player_id", player.player_id, _U16_MAX, low=1)
            _check_range(f"{place}: jersey", player.jersey, _U8_MAX)
    _check_length(f"{label}: permutation", roster.permutation, ROSTER_PERMUTATION_SIZE)
    camp = roster.training_camp
    camp_label = f"{label}: training camp"
    if len(camp) != len(ROSTER_CAMP_GROUPS):
        raise ValueError(
            f"{camp_label}: Must be {len(ROSTER_CAMP_GROUPS)} rows, got {len(camp)}"
        )
    columns = len(ROSTER_CAMP_RATINGS)
    for group_name, row in zip(ROSTER_CAMP_GROUPS, camp, strict=True):
        row_label = f"{camp_label}: {group_name}"
        if len(row) != columns:
            raise ValueError(f"{row_label}: Must be {columns} values, got {len(row)}")
        for rating, value in zip(ROSTER_CAMP_RATINGS, row, strict=True):
            _check_range(f"{row_label}: {rating}", value, CAMP_PERCENT_MAX)
        if sum(row) > CAMP_PERCENT_MAX:
            raise ValueError(
                f"{row_label}: Must total at most {CAMP_PERCENT_MAX}, got {sum(row)}"
            )
    _check_length(f"{label}: unknown", roster.unknown, ROSTER_UNKNOWN_SIZE)


def _check_range(location: str, value: int, limit: int, low: int = 0) -> None:
    if not low <= value <= limit:
        raise ValueError(f"{location}: Must be {low}-{limit}, got {value}")


def _check_length(location: str, value: bytes, size: int) -> None:
    if len(value) != size:
        raise ValueError(f"{location}: Must be {size} bytes, got {len(value)}")


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
