"""The four standings views, on a small league built in code."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Record, Team
from athc.fbpro98_standings import Standings
from athc.standings import Split, View, difference, percentage, record, render

NO_GAMES = Record(0, 0, 0, 0, 0)

# Conference name -> division name -> teams as (name, nickname).
Shape = Sequence[tuple[str, Sequence[tuple[str, Sequence[tuple[str, str]]]]]]
# Home team, home score, away team, away score, by team name.
Played = tuple[str, int, str, int]


def _league(shape: Shape, games: Sequence[Played] = ()) -> LgeFile:
    """One regular-season week per game."""
    teams = {
        name: Team(name=name, nickname=nickname, record=NO_GAMES)
        for _, divisions in shape
        for _, members in divisions
        for name, nickname in members
    }
    conferences: list[Conference] = []
    for conference_name, divisions in shape:
        built: list[Division] = []
        for division_name, members in divisions:
            in_division = tuple(teams[name] for name, _ in members)
            built.append(Division(division_name, in_division, in_division))
        in_conference = tuple(team for division in built for team in division.teams)
        conferences.append(Conference(conference_name, tuple(built), in_conference))
    weeks = tuple(
        (Game(teams[home], home_score, teams[away], away_score),)
        for home, home_score, away, away_score in games
    )
    return LgeFile(conferences=tuple(conferences), weeks=weeks)


# Two unnamed conferences; each has one two-team division and one one-team
# division, in opposite order, so the game view pads the shorter block.
SHAPE: Shape = [
    (
        "",
        [
            ("East", [("Miami", "Dolphins"), ("Buffalo", "Bills")]),
            ("West", [("Denver", "Broncos")]),
        ],
    ),
    (
        "",
        [
            ("East", [("Dallas", "Cowboys")]),
            ("West", [("Seattle", "Seahawks"), ("Chicago", "Bears")]),
        ],
    ),
]
GAMES: list[Played] = [
    ("Miami", 24, "Buffalo", 17),
    ("Chicago", 7, "Miami", 21),
    ("Seattle", 27, "Chicago", 10),
    ("Buffalo", 20, "Dallas", 13),
    ("Denver", 14, "Chicago", 3),
    ("Miami", 30, "Seattle", 20),
    ("Seattle", 17, "Buffalo", 16),
    ("Chicago", 6, "Buffalo", 28),
    ("Dallas", 10, "Denver", 10),
]
HEADER = "W  L  T    PCT   HOME   AWAY  DIV  CONF  PF  PA  DIFF  STRK"


def _render(view: View, lge: LgeFile | None = None) -> list[str]:
    lge = lge or _league(SHAPE, GAMES)
    return render(view, lge, Standings(lge, method="scheduler"), "PNFL")


def test_game_view() -> None:
    assert _render("game") == [
        "AFC EAST  W  L  T  PF  PA    NFC EAST  W  L  T  PF  PA",
        "Miami     3  0  0  75  44    Dallas    0  1  1  23  30",
        "Buffalo   2  2  0  81  60",
        "",
        "AFC WEST  W  L  T  PF  PA    NFC WEST  W  L  T  PF  PA",
        "Denver    1  0  1  24  13    Seattle   2  1  0  64  56",
        " " * 29 + "Chicago   0  4  0  26  90",
    ]


def test_league_view() -> None:
    assert _render("league") == [
        "PNFL",
        " " * 21 + HEADER,
        "1  Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "2  Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "3  Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "4  Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "5  Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "6  Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_conference_view() -> None:
    assert _render("conference") == [
        "AFC",
        " " * 21 + HEADER,
        "1  Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "2  Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "3  Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "",
        "NFC",
        " " * 21 + HEADER,
        "1  Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "2  Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "3  Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_division_view() -> None:
    assert _render("division") == [
        "AFC",
        "AFC EAST          " + HEADER,
        "Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "AFC WEST          " + HEADER,
        "Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "",
        "NFC",
        "NFC EAST          " + HEADER,
        "Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "NFC WEST          " + HEADER,
        "Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_game_view_one_conference() -> None:
    """A named conference keeps its name; one conference is one column."""
    lge = _league([("Big", [("North", [("A", "")]), ("South", [("B", "")])])])
    assert _render("game", lge) == [
        "BIG NORTH  W  L  T  PF  PA",
        "A          0  0  0   0   0",
        "",
        "BIG SOUTH  W  L  T  PF  PA",
        "B          0  0  0   0   0",
    ]


@pytest.mark.parametrize(
    ("split", "text"),
    [
        (Split(0, 0, 0), ".000"),
        (Split(0, 3, 0), ".000"),
        (Split(1, 1, 0), ".500"),
        (Split(0, 0, 1), ".500"),
        (Split(2, 1, 0), ".667"),
        (Split(1, 2, 0), ".333"),
        (Split(13, 3, 0), ".813"),
        (Split(9, 7, 0), ".563"),
        (Split(3, 0, 0), "1.000"),
    ],
    ids=[
        "no games",
        "no wins",
        "half",
        "a tie is half a win",
        "above a half rounds up",
        "below a half rounds down",
        "a half rounds up",
        "another half rounds up",
        "all wins",
    ],
)
def test_percentage(split: Split, text: str) -> None:
    assert percentage(split) == text


@pytest.mark.parametrize(
    ("split", "text"),
    [(Split(2, 1, 0), "2-1"), (Split(0, 1, 1), "0-1-1"), (Split(0, 0, 0), "0-0")],
    ids=["no ties", "ties", "no games"],
)
def test_record(split: Split, text: str) -> None:
    assert record(split) == text


@pytest.mark.parametrize(
    ("points_for", "points_against", "text"),
    [(164, 141, "+23"), (104, 112, "-8"), (10, 10, "0")],
    ids=["ahead", "behind", "even"],
)
def test_difference(points_for: int, points_against: int, text: str) -> None:
    assert difference(points_for, points_against) == text
