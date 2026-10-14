"""Standings: a league's teams ranked by one tie-break method."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from itertools import groupby

from athc.fbpro98_lge import Conference, Division, LgeFile, Team
from athc.fbpro98_standings.methods import (
    METHODS,
    RULES,
    Method,
    MethodRules,
    Rules,
)
from athc.fbpro98_standings.moves import match
from athc.fbpro98_standings.season import Season, season_of
from athc.fbpro98_standings.steps import Value


class Standings:
    """A league's standings by one tie-break method.

    With only `current`, ranks the current file's season as played so far.
    With `previous` too, ranks the previous file's season, as played under its
    own divisions, and answers for the current file's divisions, conferences
    and teams; `team_moves` maps each team whose name changed from its
    previous name to its current one. `seed` makes the coin toss repeatable.

    Raises:
        ValueError: an unknown method; `team_moves` without `previous`.
        StandingsError: the two files and the team moves do not fit together.
    """

    def __init__(
        self,
        current: LgeFile,
        previous: LgeFile | None = None,
        team_moves: Mapping[str, str] | None = None,
        *,
        method: Method,
        seed: int | None = None,
    ) -> None:
        if method not in METHODS:
            raise ValueError(f"Unknown method: {method!r}. Valid: {', '.join(METHODS)}")
        if team_moves and previous is None:
            raise ValueError("team_moves needs the previous season's file.")
        self._current = current
        self._number = {id(team): number for number, team in enumerate(current.teams)}
        self._ranked_of: tuple[int, ...]
        if previous is None:
            self._ranked_of = tuple(range(len(current.teams)))
            season = season_of(current)
        else:
            self._ranked_of = match(previous, current, team_moves or {})
            season = season_of(previous)
        self._current_of = {
            ranked: number for number, ranked in enumerate(self._ranked_of)
        }
        self._ranker = _Ranker(season, RULES[method], seed)

    def division(self, division: Division) -> tuple[Team, ...]:
        """The division's teams, best first.

        Raises:
            ValueError: not a division of the current file.
        """
        if not any(
            known is division
            for conference in self._current.conferences
            for known in conference.divisions
        ):
            raise ValueError(f"Not a division of the current file: {division.name!r}.")
        return self._teams(self._ranker.division(self._ranked(division.teams)))

    def conference(self, conference: Conference) -> tuple[Team, ...]:
        """The conference's teams, best first.

        Raises:
            ValueError: not a conference of the current file.
        """
        if not any(known is conference for known in self._current.conferences):
            raise ValueError(
                f"Not a conference of the current file: {conference.name!r}."
            )
        teams = [team for division in conference.divisions for team in division.teams]
        return self._teams(self._ranker.conference(self._ranked(teams)))

    def league(self) -> tuple[Team, ...]:
        """Every team, in final order."""
        return self._teams(self._ranker.league())

    def _ranked(self, teams: Iterable[Team]) -> tuple[int, ...]:
        # The current teams' numbers in the season being ranked.
        return tuple(self._ranked_of[self._number[id(team)]] for team in teams)

    def _teams(self, numbers: Iterable[int]) -> tuple[Team, ...]:
        teams = self._current.teams
        return tuple(teams[self._current_of[number]] for number in numbers)


class _Ranker:
    """Orders one season's teams, by their numbers in it, by one method.
    Every answer is kept, so the same question gets the same answer."""

    def __init__(self, season: Season, method: MethodRules, seed: int | None) -> None:
        self.season = season
        self._method = method
        self._answers: dict[tuple[str, tuple[int, ...]], tuple[int, ...]] = {}
        # The coin is tossed once: one random order of every team, so every
        # request breaks a last tie the same way and a seed repeats it.
        teams = list(range(len(season.teams)))
        random.Random(seed).shuffle(teams)
        self._coin = {team: place for place, team in enumerate(teams)}

    def division(self, teams: Iterable[int]) -> tuple[int, ...]:
        rules = self._method.division
        return self._kept("division", teams, lambda group: self._order(group, rules))

    def conference(self, teams: Iterable[int]) -> tuple[int, ...]:
        rules = self._method.conference
        if rules is None:
            members = set(teams)
            return tuple(team for team in self.league() if team in members)
        return self._kept(
            "conference", teams, lambda group: self._winners_first(group, rules)
        )

    def league(self) -> tuple[int, ...]:
        rules = self._method.league
        return self._kept(
            "league",
            range(len(self.season.teams)),
            lambda group: self._order(group, rules),
        )

    def division_order(self, division: int) -> tuple[int, ...]:
        """One of the season's own divisions, by the division rules."""
        return self.division(self.season.division_members(division))

    def _kept(
        self,
        kind: str,
        teams: Iterable[int],
        rank: Callable[[list[int]], tuple[int, ...]],
    ) -> tuple[int, ...]:
        group = sorted(teams)
        key = (kind, tuple(group))
        if key not in self._answers:
            self._answers[key] = rank(group)
        return self._answers[key]

    def _winners_first(self, teams: list[int], rules: Rules) -> tuple[int, ...]:
        winners = {
            self.division_order(division)[0]
            for division in set(self.season.division_of)
        }
        first = [team for team in teams if team in winners]
        rest = [team for team in teams if team not in winners]
        return self._order(first, rules) + self._order(rest, rules)

    def _order(self, teams: list[int], rules: Rules) -> tuple[int, ...]:
        """Sort by the sort steps, then break each level group."""
        values = [
            value for step in rules.sort if (value := step(teams, self)) is not None
        ]

        def key(team: int) -> tuple[Value, ...]:
            return tuple(-value[team] for value in values)

        ordered: list[int] = []
        for _, level in groupby(sorted(teams, key=key), key=key):
            ordered += self._break(list(level), rules)
        return tuple(ordered)

    def _break(self, group: list[int], rules: Rules) -> list[int]:
        """Orders one level group: one team at a time (the NFL), or by
        regrouping (the game)."""
        if len(group) == 1:
            return group
        if not rules.one_advances:
            return self._regroup(group, rules)
        ordered: list[int] = []
        rest = list(group)
        while rest:
            best = self._best(rest, rules)
            ordered.append(best)
            rest.remove(best)
        return ordered

    def _regroup(self, group: list[int], rules: Rules) -> list[int]:
        """The first tie-breaker that separates the group places its best
        teams; they and the rest are each ranked again from the first one.
        Level after every tie-breaker: the coin toss."""
        if len(group) == 1:
            return group
        for step in rules.breakers:
            values = step(group, self)
            if values is None:
                continue
            best = max(values.values())
            top = [team for team in group if values[team] == best]
            if len(top) < len(group):
                rest = [team for team in group if values[team] != best]
                return self._regroup(top, rules) + self._regroup(rest, rules)
        return self._toss(group)

    def _best(self, group: list[int], rules: Rules) -> int:
        """The single best team of a level group. A step that drops some teams
        sends the rest back to the first tie-breaker; level after every one,
        the coin toss."""
        candidates = list(group)
        while len(candidates) > 1:
            candidates, narrowed = self._narrow(candidates, rules)
            if narrowed is not rules:
                return self._best(candidates, narrowed)
            for step in rules.breakers:
                values = step(candidates, self)
                if values is None:
                    continue
                best = max(values.values())
                top = [team for team in candidates if values[team] == best]
                if len(top) < len(candidates):
                    candidates = top
                    break
            else:
                return self._toss(candidates)[0]
        return candidates[0]

    def _narrow(self, group: list[int], rules: Rules) -> tuple[list[int], Rules]:
        """The NFL's rule for teams of different divisions. Teams of one
        division use the division rules; in league standings, teams of one
        conference use the conference rules. Otherwise only each division's
        best goes on, and in league standings only each conference's best of
        those."""
        if not rules.by_division_first:
            return group, rules
        season = self.season
        method = self._method
        if len({season.division_of[team] for team in group}) == 1:
            return group, method.division
        conference = method.conference
        if rules is method.league and conference is not None:
            if len({season.conference_of[team] for team in group}) == 1:
                return group, conference
            group = self._best_of_each(group, season.division_of, method.division)
            return self._best_of_each(group, season.conference_of, conference), rules
        return self._best_of_each(group, season.division_of, method.division), rules

    def _best_of_each(
        self, group: list[int], part_of: Sequence[int], rules: Rules
    ) -> list[int]:
        """The best team of each division (or conference) in the group."""
        parts: dict[int, list[int]] = {}
        for team in group:
            parts.setdefault(part_of[team], []).append(team)
        return sorted(self._break(members, rules)[0] for members in parts.values())

    def _toss(self, group: list[int]) -> list[int]:
        """The level teams in the coin's order."""
        return sorted(group, key=self._coin.__getitem__)
