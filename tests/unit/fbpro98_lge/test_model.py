"""Tests for athc.fbpro98_lge.model: the model's own logic, and
`LgeFile.validate()` on models built in Python, each rule at its limit and
one past it."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_lge import (
    Conference,
    Division,
    Game,
    LgeFile,
    Record,
    Roster,
    RosterPlayer,
    Team,
    ranked,
)

NO_GAMES = Record(wins=0, losses=0, ties=0, points_for=0, points_against=0)


def _roster(team_number: int = 1, **overrides: object) -> Roster:
    """A valid, empty roster: the four status groups at the screen's sizes
    with every slot empty, every camp percentage 0."""
    roster = Roster(
        team_number=team_number,
        assigned=[None] * 34,
        open_active=[None] * 12,
        open_inactive=[None] * 7,
        injured_reserve=[None] * 10,
        permutation=bytes(10),
        training_camp=[[0] * 8 for _ in range(8)],
        unknown=bytes(60),
    )
    for name, value in overrides.items():
        setattr(roster, name, value)
    return roster


def _team(name: str, record: tuple[int, int, int, int, int]) -> Team:
    return Team(name=name, nickname="", record=Record(*record), roster=_roster())


def _file(*rosters: Roster) -> LgeFile:
    """One conference and division of teams T1, T2, ..., one per roster."""
    teams = [
        Team(name=f"T{number}", nickname="", record=NO_GAMES, roster=roster)
        for number, roster in enumerate(rosters, 1)
    ]
    division = Division(name="D1", teams=teams, standings=list(teams))
    conference = Conference(name="C1", divisions=[division], standings=list(teams))
    return LgeFile(conferences=[conference])


def _names(teams: list[Team]) -> list[str]:
    return [team.name for team in teams]


def _rejects(lge: LgeFile, message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        lge.validate()


def test_teams_walks_conferences_divisions_and_teams_in_order():
    a, b, c, d = (_team(name, (0, 0, 0, 0, 0)) for name in "abcd")
    east = Division(name="East", teams=[a], standings=[a])
    west = Division(name="West", teams=[b, c], standings=[b, c])
    south = Division(name="South", teams=[d], standings=[d])
    lge = LgeFile(
        conferences=[
            Conference(name="AFC", divisions=[east, west], standings=[a, b, c]),
            Conference(name="NFC", divisions=[south], standings=[d]),
        ]
    )
    assert lge.teams == [a, b, c, d]


def test_lge_is_edited_by_assignment():
    lge, loser, winner = _one_game()
    loser.record.wins = 9
    loser.roster.injured_reserve[9] = RosterPlayer(player_id=4242, jersey=1)
    lge.conferences[0].divisions[0].teams.remove(winner)
    assert lge.teams == [loser]
    assert lge.teams[0].record.wins == 9
    assert lge.teams[0].roster.players == [RosterPlayer(player_id=4242, jersey=1)]


@pytest.mark.parametrize(
    ("name", "nickname", "official_name"),
    [
        ("Denver", "Broncos", "Denver Broncos"),
        ("Denver", "", "Denver"),
        ("", "Broncos", "Broncos"),
        ("", "", ""),
    ],
)
def test_official_name(name: str, nickname: str, official_name: str):
    team = Team(name=name, nickname=nickname, record=NO_GAMES, roster=_roster())
    assert team.official_name == official_name


@pytest.mark.parametrize(
    ("record", "games", "win_percentage", "point_differential"),
    [
        ((5, 1, 0, 164, 112), 6, 5 / 6, 52),
        ((9, 6, 1, 362, 323), 16, 9.5 / 16, 39),
        ((0, 0, 1, 10, 10), 1, 0.5, 0),
        ((0, 0, 0, 0, 0), 0, 0.0, 0),
    ],
)
def test_record_totals(
    record: tuple[int, int, int, int, int],
    games: int,
    win_percentage: float,
    point_differential: int,
):
    totals = Record(*record)
    assert totals.games == games
    assert totals.win_percentage == win_percentage
    assert totals.point_differential == point_differential


def _one_game() -> tuple[LgeFile, Team, Team]:
    """Two teams, one game played and one week recorded: the loser is listed
    first in the file."""
    loser = _team("loser", (0, 1, 0, 10, 20))
    winner = _team("winner", (1, 0, 0, 20, 10))
    division = Division(name="East", teams=[loser, winner], standings=[])
    conference = Conference(name="AFC", divisions=[division], standings=[])
    game = Game(home=winner, home_score=20, away=loser, away_score=10)
    return LgeFile(conferences=[conference], weeks=[[game]]), loser, winner


def test_ranked_orders_from_the_files_games_not_the_records():
    lge, loser, winner = _one_game()
    assert _names(ranked(lge, [loser, winner])) == ["winner", "loser"]


def test_ranked_defaults_to_every_team_of_the_file():
    lge, _, _ = _one_game()
    assert _names(ranked(lge)) == ["winner", "loser"]


def test_ranked_with_no_teams_is_empty():
    lge, _, _ = _one_game()
    assert ranked(lge, []) == []


@pytest.mark.parametrize(
    ("home_score", "away_score", "winner", "loser"),
    [(21, 14, "home", "away"), (14, 21, "away", "home"), (10, 10, None, None)],
)
def test_game_winner_and_loser(
    home_score: int, away_score: int, winner: str | None, loser: str | None
):
    teams = {
        "home": _team("home", (0, 0, 0, 0, 0)),
        "away": _team("away", (0, 0, 0, 0, 0)),
    }
    game = Game(
        home=teams["home"],
        home_score=home_score,
        away=teams["away"],
        away_score=away_score,
    )
    assert game.winner is (teams[winner] if winner else None)
    assert game.loser is (teams[loser] if loser else None)


# --- rosters ---


def test_players_lists_the_filled_slots_in_slot_order():
    roster = _roster()
    roster.injured_reserve[9] = RosterPlayer(14, 4)
    roster.open_inactive[0] = RosterPlayer(13, 3)
    roster.open_active[11] = RosterPlayer(12, 2)
    roster.assigned[0] = RosterPlayer(11, 1)
    assert roster.players == [
        RosterPlayer(11, 1),
        RosterPlayer(12, 2),
        RosterPlayer(13, 3),
        RosterPlayer(14, 4),
    ]


def test_team_of_finds_the_first_team_in_file_order():
    first, second = _roster(), _roster(2)
    first.assigned[5] = RosterPlayer(7, 1)
    second.assigned[0] = RosterPlayer(7, 1)
    second.open_active[1] = RosterPlayer(8, 2)
    lge = _file(first, second)
    assert lge.team_of(7) is lge.teams[0]
    assert lge.team_of(8) is lge.teams[1]


@pytest.mark.parametrize("player_id", [0, 99999])
def test_team_of_unknown_or_empty_id_is_none(player_id: int):
    roster = _roster()
    roster.assigned[0] = RosterPlayer(1, 1)
    assert _file(roster).team_of(player_id) is None


# --- validate() ---


def test_valid_file_passes():
    _file(_roster(), _roster(2)).validate()


def test_file_without_teams_passes():
    LgeFile(conferences=[]).validate()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("team_number", 0),
        ("team_number", 65535),
        ("permutation", bytes(10)),
        ("unknown", bytes(60)),
    ],
)
def test_roster_field_at_its_limit_accepted(field: str, value: object):
    roster = _roster()
    setattr(roster, field, value)
    _file(roster).validate()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("team_number", 65536, "team_number: Must be 0-65535, got 65536"),
        ("team_number", -1, "team_number: Must be 0-65535, got -1"),
        ("permutation", bytes(9), "permutation: Must be 10 bytes, got 9"),
        ("permutation", bytes(11), "permutation: Must be 10 bytes, got 11"),
        ("unknown", bytes(59), "unknown: Must be 60 bytes, got 59"),
        ("unknown", bytes(61), "unknown: Must be 60 bytes, got 61"),
        ("training_camp", [[0] * 8] * 7, "training camp: Must be 8 rows, got 7"),
        ("training_camp", [[0] * 8] * 9, "training camp: Must be 8 rows, got 9"),
    ],
)
def test_roster_field_past_its_limit_rejected(field: str, value: object, message: str):
    roster = _roster()
    setattr(roster, field, value)
    _rejects(_file(roster), f"team 1: roster: {message}")


@pytest.mark.parametrize(
    ("group", "name", "size"),
    [
        ("assigned", "Assigned", 34),
        ("open_active", "Open Active", 12),
        ("open_inactive", "Open Inactive", 7),
        ("injured_reserve", "Injured Reserve", 10),
    ],
)
@pytest.mark.parametrize("off", [-1, 1])
def test_group_size_off_by_one_rejected(group: str, name: str, size: int, off: int):
    # Each group at its size is the valid roster every other test builds.
    roster = _roster()
    setattr(roster, group, [None] * (size + off))
    _rejects(
        _file(roster),
        f"team 1: roster: {name}: Must be {size} slots, got {size + off}",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("player_id", 1), ("player_id", 65535), ("jersey", 0), ("jersey", 255)],
)
def test_player_field_at_its_limit_accepted(field: str, value: int):
    player = RosterPlayer(player_id=1, jersey=0)
    setattr(player, field, value)
    roster = _roster()
    roster.assigned[0] = player
    _file(roster).validate()


@pytest.mark.parametrize(
    ("group", "index", "place", "field", "value", "message"),
    [
        ("assigned", 0, "Assigned slot 1", "player_id", 0, "Must be 1-65535, got 0"),
        (
            "assigned",
            0,
            "Assigned slot 1",
            "player_id",
            65536,
            "Must be 1-65535, got 65536",
        ),
        ("assigned", 0, "Assigned slot 1", "jersey", 256, "Must be 0-255, got 256"),
        ("assigned", 0, "Assigned slot 1", "jersey", -1, "Must be 0-255, got -1"),
        (
            "injured_reserve",
            9,
            "Injured Reserve slot 10",
            "jersey",
            256,
            "Must be 0-255, got 256",
        ),
    ],
)
def test_player_field_past_its_limit_rejected(
    group: str, index: int, place: str, field: str, value: int, message: str
):
    # Slots are counted from 1 in messages, as the spec counts them.
    player = RosterPlayer(player_id=1, jersey=0)
    setattr(player, field, value)
    roster = _roster()
    getattr(roster, group)[index] = player
    _rejects(_file(roster), f"team 1: roster: {place}: {field}: {message}")


@pytest.mark.parametrize("values", [7, 9])
def test_camp_row_length_off_by_one_rejected(values: int):
    # Camp rows and columns are named as the Training Camp screen names them.
    roster = _roster()
    roster.training_camp[0] = [0] * values
    _rejects(
        _file(roster),
        f"team 1: roster: training camp: QB: Must be 8 values, got {values}",
    )


def test_camp_byte_at_its_limit_accepted():
    roster = _roster()
    roster.training_camp[7][7] = 100
    _file(roster).validate()


@pytest.mark.parametrize("value", [101, -1])
def test_camp_byte_past_its_limit_rejected(value: int):
    roster = _roster()
    roster.training_camp[7][7] = value
    _rejects(
        _file(roster),
        f"team 1: roster: training camp: P/K: ST: Must be 0-100, got {value}",
    )


def test_camp_row_total_at_its_limit_accepted():
    roster = _roster()
    roster.training_camp[0] = [13] * 7 + [9]
    _file(roster).validate()


def test_camp_row_total_past_its_limit_rejected():
    roster = _roster()
    roster.training_camp[0] = [13] * 7 + [10]
    _rejects(
        _file(roster),
        "team 1: roster: training camp: QB: Must total at most 100, got 101",
    )


def test_problem_in_a_later_team_names_that_team():
    # Named by its position in the file, not by the roster's own number.
    _rejects(
        _file(_roster(), _roster(7, assigned=[])),
        "team 2: roster: Assigned: Must be 34 slots, got 0",
    )


def test_first_problem_in_file_order_reported():
    _rejects(
        _file(_roster(unknown=bytes(59)), _roster(2, assigned=[])),
        "team 1: roster: unknown: Must be 60 bytes, got 59",
    )
