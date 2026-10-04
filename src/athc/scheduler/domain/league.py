"""League structure: conferences, divisions, teams, and conference rankings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

TOTAL_TEAMS = 18
TEAMS_PER_CONFERENCE = 9
CONFERENCES_PER_LEAGUE = 2


@dataclass(frozen=True)
class Conference:
    name: str


@dataclass(frozen=True)
class Division:
    name: str
    conference: Conference
    expected_size: int


AFC = Conference("AFC")
NFC = Conference("NFC")
AFC_EAST = Division("AFC_EAST", AFC, 4)
AFC_WEST = Division("AFC_WEST", AFC, 5)
NFC_EAST = Division("NFC_EAST", NFC, 4)
NFC_WEST = Division("NFC_WEST", NFC, 5)

# The PNFL's divisions in canonical order, keyed by their [DivisionStandings] names.
PNFL_DIVISIONS: tuple[Division, ...] = (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)
PNFL_DIVISIONS_BY_NAME: dict[str, Division] = {d.name: d for d in PNFL_DIVISIONS}


@dataclass(frozen=True)
class Team:
    metro: str
    conference: Conference
    division: Division | None = None  # None in a league without divisions

    def __post_init__(self) -> None:
        if self.division is not None and self.division.conference != self.conference:
            raise ValueError(
                f"{self.metro}: division {self.division.name} is not in conference "
                f"{self.conference.name}"
            )

    def same_division(self, other: Team) -> bool:
        """Whether both teams share a division. Division-less teams never do --
        a bare `division == division` would call every such pair divisional."""
        return self.division is not None and self.division == other.division


# A rivalry as listed in the rules file: the first team hosts in even seasons.
RivalryPair = tuple[Team, Team]


@dataclass(frozen=True)
class ConferenceRankings:
    """The overall 1-18 standings (`overall`) plus the per-conference 1-9 ranks
    derived from it."""

    by_conference: Mapping[Conference, tuple[Team, ...]]
    overall: tuple[Team, ...]

    def ranked(self, conference: Conference) -> tuple[Team, ...]:
        return self.by_conference[conference]

    def rank_of(self, team: Team) -> int:
        """Return 1-based conference rank."""
        return self.by_conference[team.conference].index(team) + 1

    def overall_rank(self, team: Team) -> int:
        """Return 1-based overall rank (1-18)."""
        return self.overall.index(team) + 1


def _division_name(team: Team) -> str:
    return team.division.name if team.division is not None else ""


def ordered_teams(teams: Sequence[Team]) -> list[Team]:
    """Canonical order: conference name, division name, metro."""
    return sorted(teams, key=lambda t: (t.conference.name, _division_name(t), t.metro))


def build_teams(divisions: Mapping[str, Sequence[str]]) -> tuple[Team, ...]:
    """Build the PNFL teams tuple from division-keyed metro lists.

    Validates that all four divisions are present, that each has its expected
    size, and that no metro is duplicated. Teams are returned in canonical order
    (division, then metro); the input line order (a division's finish) is kept
    separately in `division_standings`.
    """
    by_division: dict[Division, Sequence[str]] = {}
    for key, metros in divisions.items():
        division = PNFL_DIVISIONS_BY_NAME.get(key)
        if division is None:
            valid = ", ".join(d.name for d in PNFL_DIVISIONS)
            raise ValueError(f"Unknown division key {key!r}; expected one of {valid}")
        by_division[division] = metros

    missing = [d.name for d in PNFL_DIVISIONS if d.name not in divisions]
    if missing:
        raise ValueError(f"Missing divisions: {missing}")

    teams: list[Team] = []
    seen_metros: set[str] = set()
    for division in PNFL_DIVISIONS:
        metros = tuple(sorted(m.strip() for m in by_division[division] if m.strip()))
        if len(metros) != division.expected_size:
            raise ValueError(
                f"{division.name} must list exactly {division.expected_size} teams; "
                f"got {len(metros)}"
            )
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in divisions config: {metro}")
            teams.append(
                Team(metro=metro, conference=division.conference, division=division)
            )
            seen_metros.add(metro)

    expected_teams = sum(d.expected_size for d in PNFL_DIVISIONS)
    if len(teams) != expected_teams:
        raise ValueError(
            f"Expected exactly {expected_teams} teams across all divisions, got "
            f"{len(teams)}"
        )
    return tuple(teams)


def build_conference_teams(
    conferences: Mapping[str, Sequence[str]],
) -> tuple[Team, ...]:
    """Build a division-less teams tuple from conference-keyed metro lists: exactly
    two conferences of nine, no metro twice. Canonical order: conference name,
    then metro."""
    if len(conferences) != CONFERENCES_PER_LEAGUE:
        raise ValueError(
            f"Expected exactly {CONFERENCES_PER_LEAGUE} conferences, got "
            f"{len(conferences)}: {sorted(conferences)}"
        )
    teams: list[Team] = []
    seen_metros: set[str] = set()
    for name in sorted(conferences):
        conference = Conference(name)
        metros = tuple(sorted(m.strip() for m in conferences[name] if m.strip()))
        if len(metros) != TEAMS_PER_CONFERENCE:
            raise ValueError(
                f"{name} must list exactly {TEAMS_PER_CONFERENCE} teams; "
                f"got {len(metros)}"
            )
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in conferences config: {metro}")
            teams.append(Team(metro=metro, conference=conference))
            seen_metros.add(metro)
    return tuple(teams)


def team_by_metro(teams: Sequence[Team]) -> dict[str, Team]:
    return {team.metro: team for team in teams}


def lookup_team(teams: Sequence[Team], metro: str) -> Team:
    by_metro = team_by_metro(teams)
    if metro not in by_metro:
        raise ValueError(f"Unknown team: {metro!r}. Valid: {sorted(by_metro)}")
    return by_metro[metro]


@dataclass(frozen=True)
class League:
    """Teams in canonical order, the two conferences (sorted by name), the
    standings-derived rankings, and each division's previous-season finish
    order (empty for a league without divisions)."""

    teams: tuple[Team, ...]
    conferences: tuple[Conference, ...]
    rankings: ConferenceRankings
    division_standings: Mapping[Division, tuple[Team, ...]]

    @property
    def has_divisions(self) -> bool:
        return self.teams[0].division is not None

    @property
    def divisions(self) -> tuple[Division, ...]:
        return tuple(sorted(self.division_standings, key=lambda d: d.name))

    @property
    def max_divisional_games_per_week(self) -> int:
        """Divisional games one week can hold (each odd division strands a team)."""
        return sum(d.expected_size // 2 for d in self.divisions)

    def divisional_opponents(self, team: Team) -> tuple[Team, ...]:
        return tuple(t for t in self.teams if t != team and team.same_division(t))

    def conference_opponents(self, team: Team) -> tuple[Team, ...]:
        """Same conference, outside the division (the whole conference when there
        are no divisions)."""
        return tuple(
            t
            for t in self.teams
            if t != team
            and t.conference == team.conference
            and not team.same_division(t)
        )

    def same_conference_opponents(self, team: Team) -> tuple[Team, ...]:
        return tuple(
            t for t in self.teams if t != team and t.conference == team.conference
        )

    def structural_games(self, team: Team) -> int:
        """Games fixed by structure: every divisional rival twice, the rest of
        the conference once."""
        return 2 * len(self.divisional_opponents(team)) + len(
            self.conference_opponents(team)
        )

    def nonconference_games(self, team: Team, weeks: int) -> int:
        return weeks - self.structural_games(team)


def build_league(
    division_standings: Mapping[str, Sequence[str]],  # "AFC_EAST" -> finish order
    overall_ranking: Sequence[str],  # all 18 metros, best to worst
) -> League:
    """Build a PNFL-style `League`: `[DivisionStandings]` defines membership and
    each division's finish order; `[OverallStandings]` gives the 1-18 order."""
    teams = build_teams(division_standings)
    by_division = {
        PNFL_DIVISIONS_BY_NAME[key]: tuple(
            lookup_team(teams, metro) for metro in metros
        )
        for key, metros in division_standings.items()
    }
    return _finish_league(teams, overall_ranking, by_division)


def build_conference_league(
    conference_standings: Mapping[str, Sequence[str]],  # "WESTERN" -> finish order
    overall_ranking: Sequence[str],
) -> League:
    """Build a division-less `League`: `[ConferenceStandings]` defines the two
    conferences; `[OverallStandings]` gives the 1-18 order."""
    teams = build_conference_teams(conference_standings)
    return _finish_league(teams, overall_ranking, {})


def _finish_league(
    teams: tuple[Team, ...],
    overall_ranking: Sequence[str],
    division_standings: Mapping[Division, tuple[Team, ...]],
) -> League:
    overall = tuple(lookup_team(teams, metro) for metro in overall_ranking)
    _validate_overall(overall, teams)
    conferences = tuple(sorted({t.conference for t in teams}, key=lambda c: c.name))
    by_conference = {
        conference: tuple(t for t in overall if t.conference == conference)
        for conference in conferences
    }
    return League(
        teams=teams,
        conferences=conferences,
        rankings=ConferenceRankings(by_conference=by_conference, overall=overall),
        division_standings=division_standings,
    )


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Overall standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(f"Overall standings have duplicate teams: {duplicates}")
