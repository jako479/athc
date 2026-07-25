"""League structure: conferences, divisions, teams, and conference rankings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

TOTAL_TEAMS = 18
TEAMS_PER_CONFERENCE = 9


class Conference(Enum):
    AFC = "AFC"
    NFC = "NFC"


class Division(Enum):
    AFC_EAST = "AFC East"
    AFC_WEST = "AFC West"
    NFC_EAST = "NFC East"
    NFC_WEST = "NFC West"

    @property
    def conference(self) -> Conference:
        return _DIVISION_META[self].conference

    @property
    def expected_size(self) -> int:
        return _DIVISION_META[self].expected_size


@dataclass(frozen=True)
class _DivisionMeta:
    conference: Conference
    expected_size: int


_DIVISION_META: dict[Division, _DivisionMeta] = {
    Division.AFC_EAST: _DivisionMeta(Conference.AFC, 4),
    Division.AFC_WEST: _DivisionMeta(Conference.AFC, 5),
    Division.NFC_EAST: _DivisionMeta(Conference.NFC, 4),
    Division.NFC_WEST: _DivisionMeta(Conference.NFC, 5),
}

DIVISION_ORDER: tuple[Division, ...] = (
    Division.AFC_EAST,
    Division.AFC_WEST,
    Division.NFC_EAST,
    Division.NFC_WEST,
)
DIVISION_INDEX = {division: index for index, division in enumerate(DIVISION_ORDER)}


@dataclass(frozen=True)
class ConferenceRankings:
    """The overall 1-18 standings (`overall`) plus the per-conference 1-9 ranks
    (`afc`, `nfc`) derived from it."""

    afc: tuple[Team, ...]
    nfc: tuple[Team, ...]
    overall: tuple[Team, ...]

    def rank_of(self, team: Team) -> int:
        """Return 1-based conference rank."""
        ranking = self.afc if team.conference == Conference.AFC else self.nfc
        return ranking.index(team) + 1

    def overall_rank(self, team: Team) -> int:
        """Return 1-based overall rank (1-18)."""
        return self.overall.index(team) + 1


@dataclass(frozen=True)
class Team:
    metro: str
    division: Division

    @property
    def conference(self) -> Conference:
        return self.division.conference


def build_teams(divisions: Mapping[str, Sequence[str]]) -> tuple[Team, ...]:
    """Build the canonical teams tuple from division-keyed metro lists.

    Validates that all four divisions are present, that each has its expected
    size, and that no metro is duplicated. Teams are returned in division order,
    alphabetical within each division; the input line order (a division's finish)
    is kept separately in `division_standings`.
    """
    by_division: dict[Division, Sequence[str]] = {}
    for key, metros in divisions.items():
        try:
            division = Division[key]
        except KeyError as exc:
            valid = ", ".join(d.name for d in DIVISION_ORDER)
            raise ValueError(
                f"Unknown division key {key!r}; expected one of {valid}"
            ) from exc
        by_division[division] = metros

    missing = [d.name for d in DIVISION_ORDER if d.name not in divisions]
    if missing:
        raise ValueError(f"Missing divisions: {missing}")

    teams: list[Team] = []
    seen_metros: set[str] = set()

    for division in DIVISION_ORDER:
        metros = tuple(sorted(m.strip() for m in by_division[division] if m.strip()))
        if len(metros) != division.expected_size:
            raise ValueError(
                f"{division.name} must list exactly {division.expected_size} teams; "
                f"got {len(metros)}"
            )
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in divisions config: {metro}")
            teams.append(Team(metro=metro, division=division))
            seen_metros.add(metro)

    expected_teams = sum(d.expected_size for d in DIVISION_ORDER)
    if len(teams) != expected_teams:
        raise ValueError(
            f"Expected exactly {expected_teams} teams across all divisions, got "
            f"{len(teams)}"
        )
    return tuple(teams)


def team_by_metro(teams: Sequence[Team]) -> dict[str, Team]:
    return {team.metro: team for team in teams}


def lookup_team(teams: Sequence[Team], metro: str) -> Team:
    by_metro = team_by_metro(teams)
    if metro not in by_metro:
        raise ValueError(f"Unknown team: {metro!r}. Valid: {sorted(by_metro)}")
    return by_metro[metro]


def ordered_teams(teams: Sequence[Team]) -> list[Team]:
    return sorted(teams, key=lambda team: (DIVISION_INDEX[team.division], team.metro))


@dataclass(frozen=True)
class League:
    """Teams, the overall AFC/NFC standings (for strength-of-schedule math), and
    each division's previous-season finish order.

    `division_standings` is the previous season's regular-season divisional
    finish (best first), from `[DivisionStandings]` -- which also defines who is
    in each division.
    """

    teams: tuple[Team, ...]
    rankings: ConferenceRankings
    division_standings: Mapping[Division, tuple[Team, ...]]


def build_league(
    division_standings: Mapping[str, Sequence[str]],  # "AFC_EAST" -> finish order
    overall_ranking: Sequence[str],  # all 18 metros, best to worst (from [Standings])
) -> League:
    """Build a `League` from the per-division standings plus the overall 1-18
    standings.

    `[DivisionStandings]` is the single source of division membership: each
    division lists its teams in finish order (best first). The teams tuple is
    canonical (alphabetical within division); the finish order is kept in
    `division_standings`. Per-conference 1-9 ranks derive from the overall order.
    """
    teams = build_teams(division_standings)
    overall = tuple(lookup_team(teams, metro) for metro in overall_ranking)
    _validate_overall(overall, teams)
    afc = tuple(t for t in overall if t.conference == Conference.AFC)
    nfc = tuple(t for t in overall if t.conference == Conference.NFC)
    by_division = {
        Division[key]: tuple(lookup_team(teams, metro) for metro in metros)
        for key, metros in division_standings.items()
    }
    return League(
        teams=teams,
        rankings=ConferenceRankings(afc=afc, nfc=nfc, overall=overall),
        division_standings=by_division,
    )


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"Standings have duplicate teams: {duplicates}")
