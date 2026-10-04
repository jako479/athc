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


def _clean(metros: Sequence[str]) -> tuple[str, ...]:
    return tuple(m.strip() for m in metros if m.strip())


def build_teams(
    standings: Mapping[str, Sequence[str]], *, divisions: bool
) -> tuple[Team, ...]:
    """Build the teams tuple from standings-keyed metro lists.

    With `divisions`, each key is `<CONFERENCE>_<DIVISION>` (split on the first
    underscore) and the division's size is its line count; without, each key is
    a conference name. Exactly two conferences of nine, no metro twice. Teams are
    returned in canonical order (conference, division, metro); the input line
    order (a finish) is kept separately in `division_standings`.
    """
    conferences: dict[str, Conference] = {}
    teams: list[Team] = []
    seen_metros: set[str] = set()
    for key, raw in standings.items():
        metros = _clean(raw)
        if not metros:
            raise ValueError(f"{key} lists no teams")
        if divisions:
            conference_name, sep, division_name = key.partition("_")
            if not sep or not conference_name or not division_name:
                raise ValueError(
                    f"Division key {key!r} must be <CONFERENCE>_<DIVISION>"
                )
            conference = conferences.setdefault(
                conference_name, Conference(conference_name)
            )
            division: Division | None = Division(key, conference, len(metros))
        else:
            conference = conferences.setdefault(key, Conference(key))
            division = None
        for metro in metros:
            if metro in seen_metros:
                raise ValueError(f"Duplicate team in standings: {metro}")
            seen_metros.add(metro)
            teams.append(Team(metro=metro, conference=conference, division=division))

    if len(conferences) != CONFERENCES_PER_LEAGUE:
        raise ValueError(
            f"Expected exactly {CONFERENCES_PER_LEAGUE} conferences, got "
            f"{len(conferences)}: {sorted(conferences)}"
        )
    for conference in conferences.values():
        size = sum(1 for team in teams if team.conference == conference)
        if size != TEAMS_PER_CONFERENCE:
            raise ValueError(
                f"{conference.name} must have exactly {TEAMS_PER_CONFERENCE} teams; "
                f"got {size}"
            )
    return tuple(ordered_teams(teams))


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
    standings: Mapping[str, Sequence[str]],  # key -> finish order
    overall_ranking: Sequence[str],  # all 18 metros, best to worst
    *,
    divisions: bool,
) -> League:
    """Build a `League`: the standings section (`[DivisionStandings]` or
    `[ConferenceStandings]`) defines membership and each group's finish order;
    `[OverallStandings]` gives the 1-18 order."""
    teams = build_teams(standings, divisions=divisions)
    division_standings: dict[Division, tuple[Team, ...]] = {}
    if divisions:
        by_name = {t.division.name: t.division for t in teams if t.division}
        division_standings = {
            by_name[key]: tuple(lookup_team(teams, metro) for metro in _clean(metros))
            for key, metros in standings.items()
        }
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
