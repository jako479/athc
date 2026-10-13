"""League structure: conferences, divisions, teams, and conference rankings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

TOTAL_TEAMS = 18
TEAMS_PER_CONFERENCE = 9
CONFERENCES_PER_LEAGUE = 2


@dataclass(frozen=True, slots=True)
class Conference:
    number: int
    """1-based position in the league file: the identity and the sort key,
    since a name may be empty or repeat (the PNFL's are both empty)."""

    name: str


@dataclass(frozen=True, slots=True)
class Division:
    number: int
    """1-based position in the league file, counted across conferences."""

    name: str
    conference: Conference
    expected_size: int


@dataclass(frozen=True, slots=True)
class Team:
    metro: str
    conference: Conference
    division: Division | None = None  # None in a league without divisions

    def __post_init__(self) -> None:
        if self.division is not None and self.division.conference != self.conference:
            raise ValueError(
                f"{self.metro}: division {self.division.name} is not in conference "
                f"{_label(self.conference)}"
            )

    def same_division(self, other: Team) -> bool:
        """Whether both teams share a division. Division-less teams never do --
        a bare `division == division` would call every such pair divisional."""
        return self.division is not None and self.division == other.division


# A rivalry as listed in the rules file: the first team hosts in even seasons.
RivalryPair = tuple[Team, Team]


@dataclass(frozen=True, slots=True)
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


def _label(conference: Conference) -> str:
    # For messages: the name, or the position when the league file names none.
    return conference.name or f"Conference {conference.number}"


def _division_number(team: Team) -> int:
    return team.division.number if team.division is not None else 0


def ordered_teams(teams: Sequence[Team]) -> list[Team]:
    """Canonical order: conference, division (both by file position), metro."""
    return sorted(
        teams, key=lambda t: (t.conference.number, _division_number(t), t.metro)
    )


def team_by_metro(teams: Sequence[Team]) -> dict[str, Team]:
    return {team.metro: team for team in teams}


def lookup_team(teams: Sequence[Team], metro: str) -> Team:
    by_metro = team_by_metro(teams)
    if metro not in by_metro:
        valid = ", ".join(sorted(by_metro))
        raise ValueError(f"Unknown team: {metro!r}. Valid: {valid}")
    return by_metro[metro]


@dataclass(frozen=True, slots=True)
class League:
    """Teams in canonical order, the two conferences (by file position), the
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
        return tuple(sorted(self.division_standings, key=lambda d: d.number))

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
    teams: Sequence[Team],
    overall: Sequence[Team],
    division_standings: Mapping[Division, Sequence[Team]] | None = None,
) -> League:
    """Check and assemble a `League`: `teams` in any order, `overall` the 1-18
    finish, `division_standings` each division's finish order (None for a
    league without divisions).

    Raises ValueError: a metro twice; not exactly two conferences; a conference
    without nine teams; `overall` not every team exactly once; with
    `division_standings`, a team without a division, a division whose finish
    is not exactly its members once, a division without a finish, or a
    division whose `expected_size` is not its member count; without it, a team
    that has a division.
    """
    ordered = tuple(ordered_teams(teams))
    seen: set[str] = set()
    for team in ordered:
        if team.metro in seen:
            raise ValueError(f"Duplicate team: {team.metro}")
        seen.add(team.metro)
    conferences = tuple(sorted({t.conference for t in ordered}, key=lambda c: c.number))
    if len(conferences) != CONFERENCES_PER_LEAGUE:
        raise ValueError(
            f"Expected exactly {CONFERENCES_PER_LEAGUE} conferences, "
            f"got {len(conferences)}"
        )
    for conference in conferences:
        size = sum(1 for team in ordered if team.conference == conference)
        if size != TEAMS_PER_CONFERENCE:
            raise ValueError(
                f"{_label(conference)} must have exactly {TEAMS_PER_CONFERENCE} "
                f"teams; got {size}"
            )
    ranking = tuple(overall)
    _validate_overall(ranking, ordered)
    finish = _validate_divisions(ordered, division_standings)
    by_conference = {
        conference: tuple(t for t in ranking if t.conference == conference)
        for conference in conferences
    }
    return League(
        teams=ordered,
        conferences=conferences,
        rankings=ConferenceRankings(by_conference=by_conference, overall=ranking),
        division_standings=finish,
    )


def _validate_overall(ranking: tuple[Team, ...], teams: tuple[Team, ...]) -> None:
    if len(ranking) != len(teams):
        raise ValueError(
            f"Overall standings must list all {len(teams)} teams; got {len(ranking)}"
        )
    if len(set(ranking)) != len(ranking):
        duplicates = sorted({t.metro for t in ranking if ranking.count(t) > 1})
        raise ValueError(
            f"Overall standings have duplicate teams: {', '.join(duplicates)}"
        )
    strangers = [t.metro for t in ranking if t not in teams]
    if strangers:
        raise ValueError(
            f"Overall standings name a team not in the league: {', '.join(strangers)}"
        )


def _validate_divisions(
    teams: tuple[Team, ...],
    division_standings: Mapping[Division, Sequence[Team]] | None,
) -> dict[Division, tuple[Team, ...]]:
    if division_standings is None:
        placed = [t.metro for t in teams if t.division is not None]
        if placed:
            raise ValueError(f"Division finish missing for: {', '.join(placed)}")
        return {}
    loose = [t.metro for t in teams if t.division is None]
    if loose:
        raise ValueError(f"No division for: {', '.join(loose)}")
    finish: dict[Division, tuple[Team, ...]] = {}
    for division in sorted(
        {t.division for t in teams if t.division}, key=lambda d: d.number
    ):
        members = tuple(t for t in teams if t.division == division)
        if division.expected_size != len(members):
            raise ValueError(
                f"{division.name} has {len(members)} teams, "
                f"not {division.expected_size}"
            )
        if division not in division_standings:
            raise ValueError(f"No finish order for {division.name}")
        order = tuple(division_standings[division])
        if len(order) != len(set(order)) or set(order) != set(members):
            raise ValueError(
                f"{division.name} finish must list its {len(members)} teams once; "
                f"got {', '.join(t.metro for t in order)}"
            )
        finish[division] = order
    return finish
