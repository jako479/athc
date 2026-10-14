"""Match the previous season's teams to the current season's: by name, with
the team moves for the teams whose name changed. A team that only changed
division needs nothing; the current file says where it is."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from athc.fbpro98_lge import LgeFile, Team
from athc.fbpro98_standings.errors import StandingsError


def match(
    previous: LgeFile, current: LgeFile, team_moves: Mapping[str, str]
) -> tuple[int, ...]:
    """For each current team, in file order, its previous-season team's index
    in `previous.teams`.

    Raises:
        StandingsError: a team name repeats in either file; a team move names
            a team not in the previous file, a name not in the current file,
            a name another previous-season team keeps, or a name another move
            already took; a team of one file has no match in the other.
    """
    previous_by_name = _by_name(previous.teams, "previous")
    current_by_name = _by_name(current.teams, "current")
    taken: dict[str, str] = {}
    for old, new in team_moves.items():
        if old not in previous_by_name:
            raise StandingsError(f"Team move {old}: Not a team in the previous file.")
        if new not in current_by_name:
            raise StandingsError(
                f"Team move {old}: {new} is not a team in the current file."
            )
        # Another previous-season team keeps that name, unless it moves too.
        if new in previous_by_name and new not in team_moves:
            raise StandingsError(
                f"Team move {old}: Another team in the previous file is named {new}."
            )
        if new in taken:
            raise StandingsError(
                f"Team move {old}: {new} is also the new name of {taken[new]}."
            )
        taken[new] = old
    new_names = {old: team_moves.get(old, old) for old in previous_by_name}
    missing = [old for old, new in new_names.items() if new not in current_by_name]
    if missing:
        raise StandingsError(
            f"Team(s) not in the current file: {', '.join(missing)}. "
            "List each team whose name changed in the team moves."
        )
    matched = set(new_names.values())
    extra = [name for name in current_by_name if name not in matched]
    if extra:
        raise StandingsError(f"Team(s) not in the previous file: {', '.join(extra)}.")
    old_of = {new: old for old, new in new_names.items()}
    return tuple(previous_by_name[old_of[team.name]] for team in current.teams)


def _by_name(teams: Sequence[Team], which: str) -> dict[str, int]:
    by_name: dict[str, int] = {}
    for number, team in enumerate(teams):
        if team.name in by_name:
            raise StandingsError(f"Team name repeats in the {which} file: {team.name}.")
        by_name[team.name] = number
    return by_name
