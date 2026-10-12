"""Tests for athc.fbpro98_lge.model."""

import dataclasses

import pytest

from athc.fbpro98_lge import Conference, Division, LgeFile, Record, Team

NO_GAMES = Record(wins=0, losses=0, ties=0, points_for=0, points_against=0)


def _team(name: str, record: tuple[int, int, int, int, int]) -> Team:
    return Team(name=name, nickname="", record=Record(*record))


def _names(teams: tuple[Team, ...]) -> tuple[str, ...]:
    return tuple(team.name for team in teams)


def test_nested_access():
    team = Team(name="Denver", nickname="Broncos", record=NO_GAMES)
    division = Division(name="West", teams=(team,))
    lge = LgeFile(conferences=(Conference(name="AFC", divisions=(division,)),))
    assert lge.conferences[0].name == "AFC"
    assert lge.conferences[0].divisions[0].name == "West"
    assert lge.conferences[0].divisions[0].teams[0].nickname == "Broncos"


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
    team = Team(name=name, nickname=nickname, record=NO_GAMES)
    assert team.official_name == official_name


def test_frozen():
    team = Team(name="Denver", nickname="Broncos", record=NO_GAMES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        team.name = "Dallas"  # type: ignore[misc]


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


def test_division_standings_rank_by_win_percentage_counting_ties_as_half():
    teams = (
        _team("8-7-1", (8, 7, 1, 0, 0)),
        _team("9-7", (9, 7, 0, 0, 0)),
        _team("9-6-1", (9, 6, 1, 0, 0)),
    )
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("9-6-1", "9-7", "8-7-1")


def test_equal_win_percentage_ranked_by_point_differential():
    teams = (_team("8-8", (8, 8, 0, 300, 297)), _team("7-7-2", (7, 7, 2, 300, 290)))
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("7-7-2", "8-8")


def test_level_teams_keep_file_order():
    teams = (_team("first", (8, 8, 0, 300, 300)), _team("second", (8, 8, 0, 310, 310)))
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("first", "second")


def test_conference_standings_rank_across_divisions():
    east = Division(
        name="East",
        teams=(_team("A", (4, 2, 0, 0, 0)), _team("B", (2, 4, 0, 0, 0))),
    )
    west = Division(
        name="West",
        teams=(_team("C", (6, 0, 0, 0, 0)), _team("D", (3, 3, 0, 0, 0))),
    )
    conference = Conference(name="AFC", divisions=(east, west))
    assert _names(conference.standings) == ("C", "A", "D", "B")
