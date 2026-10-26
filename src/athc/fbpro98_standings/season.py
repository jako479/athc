"""One league file's season as numbers: each team's played regular-season
games and how far it went in the playoffs.

Teams are numbered 0..N-1 in file order (conference, division, team), the
order `LgeFile.teams` gives, and found by identity, so two teams that look
the same never mix.
"""

from __future__ import annotations

from dataclasses import dataclass

from athc.fbpro98_lge import Game, LgeFile, Team


@dataclass(frozen=True, slots=True)
class Result:
    """One played regular-season game, from one team's side."""

    opponent: int
    scored: int
    allowed: int
    division: bool
    """The opponent was in the team's division."""

    conference: bool
    """The opponent was in the team's conference."""

    @property
    def won(self) -> bool:
        return self.scored > self.allowed

    @property
    def lost(self) -> bool:
        return self.scored < self.allowed


@dataclass(frozen=True, slots=True)
class Season:
    """A season ready to rank."""

    teams: tuple[Team, ...]
    """The file's teams in file order: team N is at index N."""

    division_of: tuple[int, ...]
    """Each team's division, numbered from 0 in file order across
    conferences."""

    conference_of: tuple[int, ...]
    """Each team's conference, numbered from 0 in file order."""

    results: tuple[tuple[Result, ...], ...]
    """Each team's played regular-season games, in week order."""

    playoff_round: tuple[int, ...]
    """The playoff round each team went out in, counted from 1; one more than
    the last round for the champion; 0 with no playoff game."""

    champion: int | None
    """The last round's winner; None until that game is played."""

    runner_up: int | None
    """The last round's loser; None until that game is played."""

    def division_members(self, division: int) -> tuple[int, ...]:
        """The division's teams in file order."""
        return tuple(
            team for team, number in enumerate(self.division_of) if number == division
        )


def season_of(lge: LgeFile) -> Season:
    """The file's season: its regular-season games and playoff results."""
    teams = tuple(lge.teams)
    number = {id(team): index for index, team in enumerate(teams)}
    division_of: list[int] = []
    conference_of: list[int] = []
    division_number = 0
    for conference_number, conference in enumerate(lge.conferences):
        for division in conference.divisions:
            division_of += [division_number] * len(division.teams)
            conference_of += [conference_number] * len(division.teams)
            division_number += 1
    results: list[list[Result]] = [[] for _ in teams]
    for week in lge.weeks:
        for game in week:
            home, away = number[id(game.home)], number[id(game.away)]
            for team, other, scored, allowed in (
                (home, away, game.home_score, game.away_score),
                (away, home, game.away_score, game.home_score),
            ):
                results[team].append(
                    Result(
                        opponent=other,
                        scored=scored,
                        allowed=allowed,
                        division=division_of[team] == division_of[other],
                        conference=conference_of[team] == conference_of[other],
                    )
                )
    playoff_round = [0] * len(teams)
    for round_number, games in enumerate(lge.playoffs, 1):
        for game in games:
            winner, loser = _winner_and_loser(game, number)
            playoff_round[loser] = round_number
            # A later round overwrites an earlier one, so a bye costs nothing.
            playoff_round[winner] = round_number + 1
    champion = runner_up = None
    if lge.playoffs and lge.playoffs[-1]:
        champion, runner_up = _winner_and_loser(lge.playoffs[-1][0], number)
    return Season(
        teams=teams,
        division_of=tuple(division_of),
        conference_of=tuple(conference_of),
        results=tuple(tuple(games) for games in results),
        playoff_round=tuple(playoff_round),
        champion=champion,
        runner_up=runner_up,
    )


def _winner_and_loser(game: Game, number: dict[int, int]) -> tuple[int, int]:
    # A playoff game cannot end tied: the game plays overtime until it does not.
    home, away = number[id(game.home)], number[id(game.away)]
    return (home, away) if game.home_score > game.away_score else (away, home)
