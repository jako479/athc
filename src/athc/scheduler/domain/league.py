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
    """Per-conference 1-9 standings (`afc`, `nfc`). `overall` is the overall 1-18
    order when the league supplies one (from `[Standings]`); the new two-phase-rank
    scheduler needs it, while the old fixed-matchup scheduler uses only the 1-9
    conference ranks. A `[ConferenceRanking]` league has no overall order."""

    afc: tuple[Team, ...]
    nfc: tuple[Team, ...]
    overall: tuple[Team, ...] | None = None

    def rank_of(self, team: Team) -> int:
        """Return 1-based conference rank."""
        ranking = self.afc if team.conference == Conference.AFC else self.nfc
        return ranking.index(team) + 1

    def overall_rank(self, team: Team) -> int:
        """Return 1-based overall rank (1-18). Requires overall standings."""
        if self.overall is None:
            raise ValueError(
                "league has no overall standings; add a [Standings] list to "
                "league.ini, or use the fixed-matchup scheduler"
            )
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
    """Teams plus the AFC/NFC standings used for strength-of-schedule math."""

    teams: tuple[Team, ...]
    rankings: ConferenceRankings


def build_league(
    divisions: Mapping[str, Sequence[str]],  # section-name ("AFCEast") -> team metros
    overall_ranking: Sequence[str] | None = None,  # all 18 metros, best to worst
    afc_ranking: Sequence[str] | None = None,  # ranked AFC metros, 1-9
    nfc_ranking: Sequence[str] | None = None,  # ranked NFC metros, 1-9
) -> League:
    """Build a `League` from a division map plus a ranking.

    Pass an overall 1-18 list (`[Standings]`), per-conference 1-9 lists
    (`[ConferenceRanking]`), or both. With both, the overall order is kept for the
    new scheduler and the *explicit* conference order for the old (playoff seeding
    can differ from overall record). With only overall, the conference order is
    derived from it; with only conference, there is no overall order.
    """
    teams = build_teams(divisions)

    overall: tuple[Team, ...] | None = None
    if overall_ranking is not None:
        overall = tuple(lookup_team(teams, metro) for metro in overall_ranking)
        _validate_overall(overall, teams)

    if afc_ranking is not None and nfc_ranking is not None:
        afc = tuple(lookup_team(teams, metro) for metro in afc_ranking)
        nfc = tuple(lookup_team(teams, metro) for metro in nfc_ranking)
        _validate_conference(afc, Conference.AFC)
        _validate_conference(nfc, Conference.NFC)
    elif overall is not None:
        afc = tuple(t for t in overall if t.conference == Conference.AFC)
        nfc = tuple(t for t in overall if t.conference == Conference.NFC)
    else:
        raise ValueError("a league needs an overall or per-conference ranking")

    return League(
        teams=teams, rankings=ConferenceRankings(afc=afc, nfc=nfc, overall=overall)
    )


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"Standings have duplicate teams: {duplicates}")


def _validate_conference(ranking: tuple[Team, ...], conference: Conference) -> None:
    label = conference.value
    if len(ranking) != TEAMS_PER_CONFERENCE:
        raise ValueError(
            f"{label} ranking must have {TEAMS_PER_CONFERENCE} teams; got "
            f"{len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"{label} ranking has duplicate teams: {duplicates}")
    wrong_conf = [t.metro for t in ranking if t.conference != conference]
    if wrong_conf:
        raise ValueError(
            f"{label} ranking contains teams from wrong conference: "
            f"{sorted(wrong_conf)}"
        )
