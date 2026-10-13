"""League structure built from conference, division and team objects; the
conferences and divisions go by file position, not name."""

from __future__ import annotations

import pytest

from athc.scheduler.domain.league import (
    CONFERENCES_PER_LEAGUE,
    TEAMS_PER_CONFERENCE,
    Conference,
    Division,
    Team,
    build_league,
    ordered_teams,
)

from .conftest import (
    CONFERENCES_EAST,
    CONFERENCES_LEAGUE,
    CONFERENCES_OVERALL,
    CONFERENCES_WEST,
    ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION,
    league_from_tables,
)

EASTERN = Conference(1, "EASTERN")
WESTERN = Conference(2, "WESTERN")
AFC = Conference(1, "AFC")
NFC = Conference(2, "NFC")
AFC_EAST = Division(1, "AFC_EAST", AFC, 4)
AFC_WEST = Division(2, "AFC_WEST", AFC, 5)
NFC_EAST = Division(3, "NFC_EAST", NFC, 4)
NFC_WEST = Division(4, "NFC_WEST", NFC, 5)


def _conferences(**overrides):
    standings = {"EASTERN": CONFERENCES_EAST, "WESTERN": CONFERENCES_WEST}
    standings.update(overrides)
    return league_from_tables(standings, CONFERENCES_OVERALL, divisions=False)


def _divisional_standings() -> dict[str, tuple[str, ...]]:
    return {
        division.name: tuple(team.metro for team in order)
        for division, order in ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.division_standings.items()
    }


def _overall() -> tuple[str, ...]:
    return tuple(
        team.metro for team in ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.rankings.overall
    )


def _divisional(standings=None):
    return league_from_tables(
        standings or _divisional_standings(), _overall(), divisions=True
    )


def _teams(league) -> dict[str, Team]:
    return {team.metro: team for team in league.teams}


# --- Team ---------------------------------------------------------------------


def test_team_division_must_belong_to_its_conference() -> None:
    with pytest.raises(ValueError, match="AFC_EAST"):
        Team("Nowhere", NFC, AFC_EAST)


def test_same_division_is_false_for_division_less_teams() -> None:
    a = Team("A", WESTERN)
    b = Team("B", WESTERN)
    assert not a.same_division(b)


def test_same_division_compares_divisions() -> None:
    a = Team("A", AFC, AFC_EAST)
    b = Team("B", AFC, AFC_EAST)
    c = Team("C", AFC, AFC_WEST)
    assert a.same_division(b)
    assert not a.same_division(c)


# --- Identity and order by position --------------------------------------------


def test_conferences_with_the_same_name_stay_distinct() -> None:
    # The PNFL's conference names are empty; each conference's divisions
    # are "East" and "West".
    first, second = Conference(1, ""), Conference(2, "")
    assert first != second
    assert Division(1, "East", first, 4) != Division(3, "East", second, 4)


def test_league_orders_conferences_and_divisions_by_number_not_name() -> None:
    zulu, alpha = Conference(1, "Zulu"), Conference(2, "Alpha")
    standings = {
        Division(1, "Z late", zulu, 5): [f"Z{i}" for i in range(5)],
        Division(2, "Z early", zulu, 4): [f"Z{i}" for i in range(5, 9)],
        Division(3, "A late", alpha, 5): [f"A{i}" for i in range(5)],
        Division(4, "A early", alpha, 4): [f"A{i}" for i in range(5, 9)],
    }
    finish = {
        division: tuple(Team(metro, division.conference, division) for metro in metros)
        for division, metros in standings.items()
    }
    teams = [team for order in finish.values() for team in order]
    league = build_league(teams, teams, finish)
    assert league.conferences == (zulu, alpha)
    assert [d.name for d in league.divisions] == [
        "Z late",
        "Z early",
        "A late",
        "A early",
    ]
    assert [t.metro for t in league.teams[:9]] == sorted(
        [f"Z{i}" for i in range(5)]
    ) + sorted([f"Z{i}" for i in range(5, 9)])


# --- League with divisions ----------------------------------------------------


def test_divisional_league_structure_comes_from_the_objects() -> None:
    league = _divisional()
    assert league.has_divisions
    assert league.conferences == (AFC, NFC)
    assert league.divisions == (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)


def test_divisional_league_division_sizes_come_from_the_members() -> None:
    standings = _divisional_standings()
    moved = standings["AFC_WEST"][-1]
    standings["AFC_WEST"] = standings["AFC_WEST"][:-1]
    standings["AFC_EAST"] = (*standings["AFC_EAST"], moved)
    league = _divisional(standings)
    sizes = {division.name: division.expected_size for division in league.divisions}
    assert sizes == {"AFC_EAST": 5, "AFC_WEST": 4, "NFC_EAST": 4, "NFC_WEST": 5}
    assert league.max_divisional_games_per_week == 8


def test_divisional_league_rejects_an_empty_division() -> None:
    standings = _divisional_standings()
    standings["AFC_EAST"] = ()
    with pytest.raises(ValueError, match="AFC must have exactly 9 teams; got 5"):
        _divisional(standings)


def test_divisional_league_rejects_one_conference() -> None:
    standings = _divisional_standings()
    standings["AFC_NORTH"] = standings.pop("NFC_EAST")
    standings["AFC_SOUTH"] = standings.pop("NFC_WEST")
    with pytest.raises(
        ValueError, match=f"exactly {CONFERENCES_PER_LEAGUE} conferences, got 1"
    ):
        _divisional(standings)


def test_divisional_league_rejects_three_conferences() -> None:
    standings = _divisional_standings()
    standings["XFC_WEST"] = standings.pop("NFC_WEST")
    with pytest.raises(
        ValueError, match=f"exactly {CONFERENCES_PER_LEAGUE} conferences, got 3"
    ):
        _divisional(standings)


def test_divisional_league_rejects_wrong_conference_sizes() -> None:
    # Move a team across conferences: AFC 8, NFC 10.
    standings = _divisional_standings()
    moved = standings["AFC_WEST"][-1]
    standings["AFC_WEST"] = standings["AFC_WEST"][:-1]
    standings["NFC_WEST"] = (*standings["NFC_WEST"], moved)
    with pytest.raises(ValueError, match=f"exactly {TEAMS_PER_CONFERENCE} teams"):
        _divisional(standings)


def test_divisional_league_rejects_duplicate_team() -> None:
    standings = _divisional_standings()
    standings["AFC_EAST"] = (*standings["AFC_EAST"][:-1], standings["AFC_WEST"][0])
    with pytest.raises(ValueError, match="Duplicate team"):
        _divisional(standings)


def test_divisional_league_structure() -> None:
    league = ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION
    four = next(t for t in league.teams if t.division == AFC_EAST)
    five = next(t for t in league.teams if t.division == AFC_WEST)
    assert len(league.divisional_opponents(four)) == 3
    assert len(league.conference_opponents(four)) == 5
    assert len(league.same_conference_opponents(four)) == 8
    assert league.structural_games(four) == 11
    assert league.nonconference_games(four, 16) == 5
    assert len(league.divisional_opponents(five)) == 4
    assert len(league.conference_opponents(five)) == 4
    assert league.structural_games(five) == 12
    assert league.nonconference_games(five, 16) == 4


def test_divisional_league_ordered_teams_by_division_then_metro() -> None:
    teams = ordered_teams(ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.teams)
    divisions = [t.division for t in teams]
    assert divisions == sorted(divisions, key=lambda d: d.number if d else 0)
    assert list(ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.teams) == teams


def test_divisional_league_keeps_each_divisions_finish_order() -> None:
    standings = _divisional_standings()
    league = _divisional(standings)
    for division, order in league.division_standings.items():
        assert tuple(t.metro for t in order) == standings[division.name]


# --- build_league: overall and division finish checks -------------------------


def test_build_league_rejects_overall_missing_a_team() -> None:
    league = _divisional()
    with pytest.raises(ValueError, match="all 18 teams; got 17"):
        build_league(
            league.teams, league.rankings.overall[:-1], league.division_standings
        )


def test_build_league_rejects_overall_duplicate() -> None:
    league = _divisional()
    overall = (*league.rankings.overall[:-1], league.rankings.overall[0])
    with pytest.raises(ValueError, match="duplicate teams: New England"):
        build_league(league.teams, overall, league.division_standings)


def test_build_league_rejects_overall_naming_a_team_not_in_the_league() -> None:
    league = _divisional()
    stranger = Team("Nowhere", AFC, AFC_EAST)
    overall = (*league.rankings.overall[:-1], stranger)
    with pytest.raises(ValueError, match="not in the league: Nowhere"):
        build_league(league.teams, overall, league.division_standings)


def test_build_league_rejects_a_division_finish_that_is_not_its_members() -> None:
    league = _divisional()
    finish = dict(league.division_standings)
    east = finish[AFC_EAST]
    finish[AFC_EAST] = (east[0], east[0], *east[2:])  # one team twice, one missing
    with pytest.raises(ValueError, match="AFC_EAST finish must list its 4 teams once"):
        build_league(league.teams, league.rankings.overall, finish)


def test_build_league_rejects_a_division_without_a_finish_order() -> None:
    league = _divisional()
    finish = {d: o for d, o in league.division_standings.items() if d != NFC_WEST}
    with pytest.raises(ValueError, match="No finish order for NFC_WEST"):
        build_league(league.teams, league.rankings.overall, finish)


def test_build_league_rejects_a_team_without_a_division_in_a_divisional_league() -> (
    None
):
    league = _divisional()
    teams = _teams(league)
    loose = Team("Buffalo", AFC)  # same metro, no division
    others = [t for t in league.teams if t.metro != "Buffalo"]
    overall = [loose if t.metro == "Buffalo" else t for t in league.rankings.overall]
    finish = {
        d: tuple(loose if t.metro == "Buffalo" else t for t in o)
        for d, o in league.division_standings.items()
    }
    with pytest.raises(ValueError, match="No division for: Buffalo"):
        build_league([*others, loose], overall, finish)
    assert teams["Buffalo"].division == AFC_EAST


def test_build_league_rejects_a_division_in_a_league_without_divisions() -> None:
    league = _divisional()
    with pytest.raises(ValueError, match="Division finish missing for: "):
        build_league(league.teams, league.rankings.overall)


def test_build_league_rejects_a_wrong_expected_size() -> None:
    league = _divisional()
    wrong = Division(1, "AFC_EAST", AFC, 5)
    teams = [
        Team(t.metro, t.conference, wrong if t.division == AFC_EAST else t.division)
        for t in league.teams
    ]
    by_metro = {t.metro: t for t in teams}
    overall = [by_metro[t.metro] for t in league.rankings.overall]
    finish = {
        (wrong if d == AFC_EAST else d): tuple(by_metro[t.metro] for t in o)
        for d, o in league.division_standings.items()
    }
    with pytest.raises(ValueError, match="AFC_EAST has 4 teams, not 5"):
        build_league(teams, overall, finish)


# --- League without divisions -------------------------------------------------


def test_conference_league_has_no_divisions() -> None:
    assert not CONFERENCES_LEAGUE.has_divisions
    assert CONFERENCES_LEAGUE.divisions == ()
    assert CONFERENCES_LEAGUE.division_standings == {}
    assert all(t.division is None for t in CONFERENCES_LEAGUE.teams)


def test_conference_league_conferences_are_in_position_order() -> None:
    assert CONFERENCES_LEAGUE.conferences == (EASTERN, WESTERN)


def test_conference_league_opponent_classes() -> None:
    team = next(t for t in CONFERENCES_LEAGUE.teams if t.metro == "Michigan")
    assert CONFERENCES_LEAGUE.divisional_opponents(team) == ()
    conference = CONFERENCES_LEAGUE.conference_opponents(team)
    assert len(conference) == 8
    assert all(t.conference == WESTERN and t != team for t in conference)
    assert CONFERENCES_LEAGUE.same_conference_opponents(team) == conference
    assert CONFERENCES_LEAGUE.structural_games(team) == 8
    assert CONFERENCES_LEAGUE.nonconference_games(team, 12) == 4
    assert CONFERENCES_LEAGUE.max_divisional_games_per_week == 0


def test_conference_league_ranks_derive_from_overall_order() -> None:
    texas = next(t for t in CONFERENCES_LEAGUE.teams if t.metro == "Texas")
    notre_dame = next(t for t in CONFERENCES_LEAGUE.teams if t.metro == "Notre Dame")
    assert CONFERENCES_LEAGUE.rankings.overall_rank(texas) == 1
    assert CONFERENCES_LEAGUE.rankings.rank_of(texas) == 1
    assert CONFERENCES_LEAGUE.rankings.overall_rank(notre_dame) == 3
    assert CONFERENCES_LEAGUE.rankings.rank_of(notre_dame) == 1
    assert CONFERENCES_LEAGUE.rankings.ranked(WESTERN)[0] == notre_dame


def test_conference_league_rejects_one_conference() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences, got 1"):
        league_from_tables(
            {"WESTERN": CONFERENCES_WEST}, CONFERENCES_OVERALL, divisions=False
        )


def test_conference_league_rejects_three_conferences() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences, got 3"):
        _conferences(EXTRA=("Nowhere",))


@pytest.mark.parametrize("size", [8, 10])
def test_conference_league_rejects_wrong_conference_size(size: int) -> None:
    west = CONFERENCES_WEST[:8] if size == 8 else (*CONFERENCES_WEST, "Nowhere")
    with pytest.raises(
        ValueError, match=f"WESTERN must have exactly 9 teams; got {size}"
    ):
        _conferences(WESTERN=west)


def test_conference_league_rejects_duplicate_team() -> None:
    with pytest.raises(ValueError, match="Duplicate team: Michigan"):
        _conferences(EASTERN=(*CONFERENCES_EAST[:8], "Michigan"))


def test_conference_league_ordered_teams_by_conference_then_metro() -> None:
    order = [t.metro for t in ordered_teams(CONFERENCES_LEAGUE.teams)]
    assert order == sorted(CONFERENCES_EAST) + sorted(CONFERENCES_WEST)
    assert list(CONFERENCES_LEAGUE.teams) == ordered_teams(CONFERENCES_LEAGUE.teams)


def test_unnamed_conference_errors_go_by_number() -> None:
    first, second = Conference(1, ""), Conference(2, "")
    teams = [Team(f"A{i}", first) for i in range(8)] + [
        Team(f"B{i}", second) for i in range(10)
    ]
    with pytest.raises(
        ValueError, match="Conference 1 must have exactly 9 teams; got 8"
    ):
        build_league(teams, teams)
