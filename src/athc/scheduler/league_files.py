"""Build the scheduler's League from two league files.

The upcoming season's `.lge` gives the conferences, divisions and team names;
the previous season's gives the standings: each team's regular-season record,
its opponents (for strength of schedule) and the playoff results. Teams are
matched by name, with the season's `[renames]` for the ones that moved.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

from athc.errors import ConfigFileError, sentence
from athc.fbpro98_lge import LgeFile, Record, ranked, read_lge
from athc.fbpro98_lge import Team as LgeTeam
from athc.scheduler.domain.league import (
    Conference,
    Division,
    League,
    Team,
    build_league,
)
from athc.scheduler.schedulers.errors import SchedulerError

StrPath = str | PathLike[str]


def load_league(
    league: str,
    previous_dir: StrPath,
    upcoming_dir: StrPath,
    renames: Mapping[str, str],
    *,
    season: int,
    rules_path: Path,
) -> League:
    """Read `<league>.lge` from both folders and build the League for `season`.

    Args:
        league: League name; each folder's `<league>.lge` is read.
        previous_dir: Folder holding the previous season's league files.
        upcoming_dir: Folder holding the upcoming season's league files.
        renames: Each renamed team's previous name -> its new name.
        season: The season being scheduled; names the `[renames]` table.
        rules_path: The `scheduler.toml` the renames came from, for errors.

    Raises:
        OSError: A file cannot be opened or read.
        InvalidLgeError: A file is not a valid `.lge`.
        SchedulerError: The previous season is not finished; a team name
            repeats in a file; a team of one file has no match in the other; a
            playoff game is tied; or the league is not two conferences of nine.
        ConfigFileError: A rename names a team neither file has, or a name
            another previous-season team keeps.
    """
    previous_path = Path(previous_dir) / f"{league}.lge"
    upcoming_path = Path(upcoming_dir) / f"{league}.lge"
    return league_from_files(
        read_lge(league, previous_dir),
        read_lge(league, upcoming_dir),
        renames,
        season=season,
        previous_path=previous_path,
        upcoming_path=upcoming_path,
        rules_path=rules_path,
    )


def league_from_files(
    previous: LgeFile,
    upcoming: LgeFile,
    renames: Mapping[str, str],
    *,
    season: int,
    previous_path: Path,
    upcoming_path: Path,
    rules_path: Path,
) -> League:
    """`load_league` on files already read; the paths only name them in
    errors."""
    if previous.unplayed_games:
        raise SchedulerError(
            f"Season not finished: {previous.unplayed_games} game(s) not played.",
            previous_path,
        )
    previous_teams = _teams(previous)
    previous_by_name = _by_name(previous_teams, previous_path)
    upcoming_by_name = _by_name(_teams(upcoming), upcoming_path)
    table = f"[renames.{season}]"
    for old, new in renames.items():
        if old not in previous_by_name:
            raise ConfigFileError(
                f"{table} {old}: Not a team in {previous_path}.", rules_path
            )
        if new not in upcoming_by_name:
            raise ConfigFileError(
                f"{table} {old}: Not a team in {upcoming_path}.", rules_path
            )
        # Another previous-season team keeps that name, unless it is renamed too.
        if new in previous_by_name and new not in renames:
            raise ConfigFileError(
                f"{table} {old}: Another team in {previous_path} is named {new}.",
                rules_path,
            )
    # Previous name -> upcoming name, for every previous-season team.
    new_names = {old: renames.get(old, old) for old in previous_by_name}
    missing = [old for old, new in new_names.items() if new not in upcoming_by_name]
    if missing:
        raise SchedulerError(
            f"Team(s) not in {upcoming_path}: {', '.join(missing)}. "
            f"List renamed teams under {table} in {rules_path}.",
            previous_path,
        )
    matched = set(new_names.values())
    extra = [name for name in upcoming_by_name if name not in matched]
    if extra:
        raise SchedulerError(
            f"Team(s) not in {previous_path}: {', '.join(extra)}.", upcoming_path
        )
    previous_of = {new: previous_by_name[old] for old, new in new_names.items()}
    # Previous-file order, the last tiebreak everywhere.
    position = {team.name: index for index, team in enumerate(previous_teams)}

    # The upcoming file's structure. One division per conference is the
    # scheduler's league without divisions.
    has_divisions = any(len(c.divisions) > 1 for c in upcoming.conferences)
    teams: dict[str, Team] = {}
    finish: dict[Division, list[Team]] = {}
    number = 0
    for index, lge_conference in enumerate(upcoming.conferences, 1):
        conference = Conference(index, lge_conference.name)
        for lge_division in lge_conference.divisions:
            number += 1
            division = (
                Division(number, lge_division.name, conference, len(lge_division.teams))
                if has_divisions
                else None
            )
            members = [Team(t.name, conference, division) for t in lge_division.teams]
            teams.update((member.metro, member) for member in members)
            if division is not None:
                # Its members ranked by the previous season as it stood (the
                # game's tie-breakers under the previous divisions), with the
                # previous-file order last.
                previous_members = sorted(
                    (previous_of[m.metro] for m in members),
                    key=lambda t: position[t.name],
                )
                finish[division] = [
                    teams[new_names[t.name]] for t in ranked(previous, previous_members)
                ]

    tiers = _playoff_finish(previous, previous_path)
    strength = _strength_of_schedule(previous, previous_teams)
    order = sorted(
        previous_teams,
        key=lambda t: (
            -tiers.get(t.name, 0),
            -t.record.win_percentage,
            -strength[t.name],
            -t.record.point_differential,
            position[t.name],
        ),
    )
    overall = [teams[new_names[t.name]] for t in order]
    try:
        return build_league(list(teams.values()), overall, finish or None)
    except ValueError as error:
        raise SchedulerError(sentence(str(error)), upcoming_path) from error


def _teams(lge: LgeFile) -> list[LgeTeam]:
    return list(lge.teams)


def _by_name(teams: list[LgeTeam], path: Path) -> dict[str, LgeTeam]:
    by_name: dict[str, LgeTeam] = {}
    for team in teams:
        if team.name in by_name:
            raise SchedulerError(f"Team name repeats: {team.name}.", path)
        by_name[team.name] = team
    return by_name


def _playoff_finish(previous: LgeFile, path: Path) -> dict[str, int]:
    """Each team's playoff finish by name: the round it went out in, one more
    for the team that won the last round; absent for a team that played none.
    A later round overwrites an earlier one, so a bye costs nothing."""
    finish: dict[str, int] = {}
    for round_number, games in enumerate(previous.playoffs, 1):
        for game in games:
            if game.winner is None or game.loser is None:
                raise SchedulerError(
                    f"Playoff round {round_number}: Tied game, "
                    f"{game.home.name} {game.home_score}, "
                    f"{game.away.name} {game.away_score}.",
                    path,
                )
            finish[game.loser.name] = round_number
            finish[game.winner.name] = round_number + 1
    return finish


def _strength_of_schedule(previous: LgeFile, teams: list[LgeTeam]) -> dict[str, float]:
    """Each team's opponents' combined regular-season record, as a win
    percentage (a tie half a win); 0.0 for a team with no game."""
    opponents: dict[str, list[Record]] = defaultdict(list)
    for week in previous.weeks:
        for game in week:
            opponents[game.home.name].append(game.away.record)
            opponents[game.away.name].append(game.home.record)
    strength: dict[str, float] = {}
    for team in teams:
        records = opponents.get(team.name, [])
        games = sum(record.games for record in records)
        wins = sum(record.wins + record.ties / 2 for record in records)
        strength[team.name] = wins / games if games else 0.0
    return strength
