"""Tests for athc.fbpro98_lge.model."""

import pytest

from athc.fbpro98_lge import (
    Conference,
    Division,
    Game,
    LgeFile,
    Record,
    Team,
    ranked,
)

NO_GAMES = Record(wins=0, losses=0, ties=0, points_for=0, points_against=0)


def _team(name: str, record: tuple[int, int, int, int, int]) -> Team:
    return Team(name=name, nickname="", record=Record(*record))


def _names(teams: tuple[Team, ...]) -> tuple[str, ...]:
    return tuple(team.name for team in teams)


def test_nested_access():
    team = Team(name="Denver", nickname="Broncos", record=NO_GAMES)
    division = Division(name="West", teams=(team,), standings=(team,))
    conference = Conference(name="AFC", divisions=(division,), standings=(team,))
    lge = LgeFile(conferences=(conference,))
    assert lge.conferences[0].name == "AFC"
    assert lge.conferences[0].divisions[0].name == "West"
    assert lge.conferences[0].divisions[0].teams[0].nickname == "Broncos"
    assert lge.teams == (team,)
    assert ranked(lge) == (team,)


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
    division = Division(name="East", teams=(loser, winner), standings=())
    conference = Conference(name="AFC", divisions=(division,), standings=())
    game = Game(home=winner, home_score=20, away=loser, away_score=10)
    return LgeFile(conferences=(conference,), weeks=((game,),)), loser, winner


def test_ranked_orders_from_the_files_games_not_the_records():
    lge, loser, winner = _one_game()
    assert _names(ranked(lge, (loser, winner))) == ("winner", "loser")


def test_ranked_defaults_to_every_team_of_the_file():
    lge, _, _ = _one_game()
    assert _names(ranked(lge)) == ("winner", "loser")


def test_ranked_with_no_teams_is_empty():
    lge, _, _ = _one_game()
    assert ranked(lge, ()) == ()


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
