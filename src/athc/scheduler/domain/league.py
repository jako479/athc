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
    size, and that no metro is duplicated. Teams are returned in division order.
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
        metros = tuple(m.strip() for m in by_division[division] if m.strip())
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
    """Teams plus the AFC/NFC standings used for strength-of-schedule math.

    `division_standings` is the previous season's regular-season divisional
    finish (best first), from `[DivisionStandings]`.
    """

    teams: tuple[Team, ...]
    rankings: ConferenceRankings
    division_standings: Mapping[Division, tuple[Team, ...]] | None = None


def build_league(
    divisions: Mapping[str, Sequence[str]],  # section-name ("AFC_EAST") -> team metros
    overall_ranking: Sequence[str],  # all 18 metros, best to worst (from [Standings])
    division_standings: Mapping[str, Sequence[str]]
    | None = None,  # per-division finish
) -> League:
    """Build a `League` from a division map plus the overall 1-18 standings.

    The per-conference 1-9 ranks are derived from the overall order.
    """
    teams = build_teams(divisions)
    overall = tuple(lookup_team(teams, metro) for metro in overall_ranking)
    _validate_overall(overall, teams)
    afc = tuple(t for t in overall if t.conference == Conference.AFC)
    nfc = tuple(t for t in overall if t.conference == Conference.NFC)
    by_division = (
        _build_division_standings(division_standings, teams)
        if division_standings is not None
        else None
    )
    return League(
        teams=teams,
        rankings=ConferenceRankings(afc=afc, nfc=nfc, overall=overall),
        division_standings=by_division,
    )


def _build_division_standings(
    standings: Mapping[str, Sequence[str]], teams: tuple[Team, ...]
) -> dict[Division, tuple[Team, ...]]:
    """Validate and resolve `[DivisionStandings]`: every division, each listing
    exactly its own teams, best finish first."""
    by_division: dict[Division, tuple[Team, ...]] = {}
    for key, metros in standings.items():
        try:
            division = Division[key]
        except KeyError as exc:
            valid = ", ".join(d.name for d in DIVISION_ORDER)
            raise ValueError(
                f"Unknown division key {key!r} in division standings; "
                f"expected one of {valid}"
            ) from exc
        ordered = tuple(lookup_team(teams, metro) for metro in metros)
        if len(set(ordered)) != len(ordered):
            raise ValueError(f"{key} division standings list a team twice")
        expected = {t for t in teams if t.division == division}
        if set(ordered) != expected:
            raise ValueError(
                f"{key} division standings must list exactly that division's "
                f"{len(expected)} teams"
            )
        by_division[division] = ordered
    missing = [d.name for d in DIVISION_ORDER if d not in by_division]
    if missing:
        raise ValueError(f"Missing division standings: {missing}")
    return by_division


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"Standings have duplicate teams: {duplicates}")
