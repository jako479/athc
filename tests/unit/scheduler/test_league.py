"""League structure built from standings keys: `<CONFERENCE>_<DIVISION>` keys
(a league with divisions) or conference names (a league without)."""

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
)

EASTERN = Conference("EASTERN")
WESTERN = Conference("WESTERN")
AFC = Conference("AFC")
NFC = Conference("NFC")
AFC_EAST = Division("AFC_EAST", AFC, 4)
AFC_WEST = Division("AFC_WEST", AFC, 5)
NFC_EAST = Division("NFC_EAST", NFC, 4)
NFC_WEST = Division("NFC_WEST", NFC, 5)


def _conferences(**overrides):
    standings = {"WESTERN": CONFERENCES_WEST, "EASTERN": CONFERENCES_EAST}
    standings.update(overrides)
    return build_league(standings, CONFERENCES_OVERALL, divisions=False)


def _divisional_standings() -> dict[str, tuple[str, ...]]:
    return {
        division.name: tuple(team.metro for team in order)
        for division, order in ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.division_standings.items()
    }


def _divisional(standings=None):
    overall = tuple(
        team.metro for team in ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.rankings.overall
    )
    return build_league(standings or _divisional_standings(), overall, divisions=True)


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


# --- League with divisions: structure comes from the standings keys ----------


def test_divisional_league_conferences_come_from_the_key_prefixes() -> None:
    league = _divisional()
    assert league.has_divisions
    assert league.conferences == (AFC, NFC)
    assert league.divisions == (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)


def test_divisional_league_division_sizes_come_from_the_file() -> None:
    standings = _divisional_standings()
    moved = standings["AFC_WEST"][-1]
    standings["AFC_WEST"] = standings["AFC_WEST"][:-1]
    standings["AFC_EAST"] = (*standings["AFC_EAST"], moved)
    league = _divisional(standings)
    sizes = {division.name: division.expected_size for division in league.divisions}
    assert sizes == {"AFC_EAST": 5, "AFC_WEST": 4, "NFC_EAST": 4, "NFC_WEST": 5}
    assert league.max_divisional_games_per_week == 8


def test_divisional_league_accepts_any_division_name() -> None:
    standings = _divisional_standings()
    standings["AFC_NORTH"] = standings.pop("AFC_EAST")
    league = _divisional(standings)
    assert [division.name for division in league.divisions] == [
        "AFC_NORTH",
        "AFC_WEST",
        "NFC_EAST",
        "NFC_WEST",
    ]


def test_divisional_league_rejects_a_key_without_a_conference() -> None:
    standings = _divisional_standings()
    standings["AFCEAST"] = standings.pop("AFC_EAST")
    with pytest.raises(ValueError, match="<CONFERENCE>_<DIVISION>"):
        _divisional(standings)


def test_divisional_league_rejects_an_empty_division() -> None:
    standings = _divisional_standings()
    standings["AFC_EAST"] = ()
    with pytest.raises(ValueError, match="no teams"):
        _divisional(standings)


def test_divisional_league_rejects_one_conference() -> None:
    standings = _divisional_standings()
    standings["AFC_NORTH"] = standings.pop("NFC_EAST")
    standings["AFC_SOUTH"] = standings.pop("NFC_WEST")
    with pytest.raises(
        ValueError, match=f"exactly {CONFERENCES_PER_LEAGUE} conferences"
    ):
        _divisional(standings)


def test_divisional_league_rejects_three_conferences() -> None:
    standings = _divisional_standings()
    standings["XFC_WEST"] = standings.pop("NFC_WEST")
    with pytest.raises(
        ValueError, match=f"exactly {CONFERENCES_PER_LEAGUE} conferences"
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
    assert divisions == sorted(divisions, key=lambda d: d.name if d else "")
    assert list(ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION.teams) == teams


def test_divisional_league_keeps_each_divisions_finish_order() -> None:
    standings = _divisional_standings()
    league = _divisional(standings)
    for division, order in league.division_standings.items():
        assert tuple(t.metro for t in order) == standings[division.name]


# --- League without divisions -------------------------------------------------


def test_conference_league_has_no_divisions() -> None:
    assert not CONFERENCES_LEAGUE.has_divisions
    assert CONFERENCES_LEAGUE.divisions == ()
    assert CONFERENCES_LEAGUE.division_standings == {}
    assert all(t.division is None for t in CONFERENCES_LEAGUE.teams)


def test_conference_league_conferences_are_sorted_by_name() -> None:
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
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        build_league(
            {"WESTERN": CONFERENCES_WEST}, CONFERENCES_OVERALL, divisions=False
        )


def test_conference_league_rejects_three_conferences() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        _conferences(EXTRA=("Nowhere",))


@pytest.mark.parametrize("size", [8, 10])
def test_conference_league_rejects_wrong_conference_size(size: int) -> None:
    west = CONFERENCES_WEST[:8] if size == 8 else (*CONFERENCES_WEST, "Nowhere")
    with pytest.raises(ValueError, match="exactly 9 teams"):
        _conferences(WESTERN=west)


def test_conference_league_rejects_duplicate_team() -> None:
    with pytest.raises(ValueError, match="Duplicate team"):
        _conferences(EASTERN=(*CONFERENCES_EAST[:8], "Michigan"))


def test_conference_league_rejects_overall_missing_a_team() -> None:
    with pytest.raises(ValueError, match="all 18 teams"):
        build_league(
            {"WESTERN": CONFERENCES_WEST, "EASTERN": CONFERENCES_EAST},
            CONFERENCES_OVERALL[:-1],
            divisions=False,
        )


def test_conference_league_ordered_teams_by_conference_then_metro() -> None:
    order = [t.metro for t in ordered_teams(CONFERENCES_LEAGUE.teams)]
    assert order == sorted(CONFERENCES_EAST) + sorted(CONFERENCES_WEST)
    assert list(CONFERENCES_LEAGUE.teams) == ordered_teams(CONFERENCES_LEAGUE.teams)
