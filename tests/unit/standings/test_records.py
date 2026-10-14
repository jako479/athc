"""Each team's standings row from the regular-season games."""

from __future__ import annotations

import pytest

from athc.fbpro98_lge import LgeFile
from athc.standings import Row, Split, rows_of
from tests.unit.fbpro98_standings.leagues import build_league, real_lge, win

# A and B share a division; C is in A's conference, another division; D is in
# the other conference.
SHAPE = [[["A", "B"], ["C"]], [["D"]]]


def _row(lge: LgeFile, name: str) -> Row:
    team = next(team for team in lge.teams if team.name == name)
    return rows_of(lge)[id(team)]


def test_overall_counts_wins_losses_and_ties() -> None:
    lge = build_league(SHAPE, [win("A", "B"), ("A", 10, "C", 10), win("D", "A")])
    assert _row(lge, "A").overall == Split(1, 1, 1)


def test_home_and_away() -> None:
    # win() puts the winner at home: A wins at home, then loses at C.
    lge = build_league(SHAPE, [win("A", "B"), win("C", "A")])
    row = _row(lge, "A")
    assert row.home == Split(1, 0, 0)
    assert row.away == Split(0, 1, 0)


def test_division_and_conference() -> None:
    lge = build_league(SHAPE, [win("A", "B"), win("C", "A"), win("A", "D")])
    row = _row(lge, "A")
    assert row.division == Split(1, 0, 0)  # B only
    assert row.conference == Split(1, 1, 0)  # B and C, never D


def test_points_for_and_against() -> None:
    lge = build_league(SHAPE, [("A", 24, "B", 17), ("C", 30, "A", 3)])
    row = _row(lge, "A")
    assert (row.points_for, row.points_against) == (27, 47)


@pytest.mark.parametrize(
    ("games", "streak"),
    [
        ([win("B", "A"), win("A", "B"), win("A", "C")], "W2"),
        ([win("A", "B"), win("B", "A"), win("C", "A")], "L2"),
        ([win("A", "B"), ("A", 10, "C", 10)], "-"),
        ([win("A", "B"), ("A", 10, "C", 10), win("A", "D")], "W1"),
        ([], "-"),
    ],
    ids=["wins", "losses", "tie last", "tie ends the run", "no games"],
)
def test_streak(games: list[tuple[str, int, str, int]], streak: str) -> None:
    lge = build_league(SHAPE, games)
    assert _row(lge, "A").streak == streak


def test_playoff_games_not_counted() -> None:
    lge = build_league(SHAPE, [win("B", "A")], playoffs=[[win("A", "D")]])
    row = _row(lge, "A")
    assert row.overall == Split(0, 1, 0)
    assert (row.points_for, row.points_against) == (10, 20)
    assert row.streak == "L1"


def test_every_team_has_a_row() -> None:
    lge = build_league(SHAPE)
    assert {id(team) for team in lge.teams} == set(rows_of(lge))


@pytest.mark.parametrize(
    "filename",
    [
        "PNFL-2048-after-week16.lge",
        "PNFL-after-super-bowl.lge",
        "PNFL-before-week1.lge",
        "NFLPI97R.LGE",
    ],
)
def test_rows_match_the_file_records(filename: str) -> None:
    """The reader's own records count the same regular-season games."""
    lge = real_lge(filename)
    rows = rows_of(lge)
    for team in lge.teams:
        row = rows[id(team)]
        record = team.record
        assert (
            row.overall.wins,
            row.overall.losses,
            row.overall.ties,
            row.points_for,
            row.points_against,
        ) == (
            record.wins,
            record.losses,
            record.ties,
            record.points_for,
            record.points_against,
        ), team.name
