"""League structure: both formats (divisions / conferences only)."""

from __future__ import annotations

import pytest

from athc.scheduler.domain.league import (
    AFC,
    AFC_EAST,
    AFC_WEST,
    NFC,
    NFC_EAST,
    NFC_WEST,
    Conference,
    Team,
    build_conference_league,
    build_league,
    ordered_teams,
)

from .conftest import LEAGUE_5_SLOTS, PCFL_EAST, PCFL_LEAGUE, PCFL_OVERALL, PCFL_WEST

EASTERN = Conference("EASTERN")
WESTERN = Conference("WESTERN")


def _pcfl(**overrides):
    standings = {"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}
    standings.update(overrides)
    return build_conference_league(standings, PCFL_OVERALL)


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


# --- Conference-only league ---------------------------------------------------


def test_conference_league_has_no_divisions() -> None:
    assert not PCFL_LEAGUE.has_divisions
    assert PCFL_LEAGUE.divisions == ()
    assert PCFL_LEAGUE.division_standings == {}
    assert all(t.division is None for t in PCFL_LEAGUE.teams)


def test_conference_league_conferences_are_sorted_by_name() -> None:
    assert PCFL_LEAGUE.conferences == (EASTERN, WESTERN)


def test_conference_league_opponent_classes() -> None:
    team = next(t for t in PCFL_LEAGUE.teams if t.metro == "Michigan")
    assert PCFL_LEAGUE.divisional_opponents(team) == ()
    conference = PCFL_LEAGUE.conference_opponents(team)
    assert len(conference) == 8
    assert all(t.conference == WESTERN and t != team for t in conference)
    assert PCFL_LEAGUE.same_conference_opponents(team) == conference
    assert PCFL_LEAGUE.structural_games(team) == 8
    assert PCFL_LEAGUE.nonconference_games(team, 12) == 4
    assert PCFL_LEAGUE.max_divisional_games_per_week == 0


def test_conference_league_ranks_derive_from_overall_order() -> None:
    texas = next(t for t in PCFL_LEAGUE.teams if t.metro == "Texas")
    notre_dame = next(t for t in PCFL_LEAGUE.teams if t.metro == "Notre Dame")
    assert PCFL_LEAGUE.rankings.overall_rank(texas) == 1
    assert PCFL_LEAGUE.rankings.rank_of(texas) == 1
    assert PCFL_LEAGUE.rankings.overall_rank(notre_dame) == 3
    assert PCFL_LEAGUE.rankings.rank_of(notre_dame) == 1
    assert PCFL_LEAGUE.rankings.ranked(WESTERN)[0] == notre_dame


def test_conference_league_rejects_one_conference() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        build_conference_league({"WESTERN": PCFL_WEST}, PCFL_OVERALL)


def test_conference_league_rejects_three_conferences() -> None:
    with pytest.raises(ValueError, match="exactly 2 conferences"):
        _pcfl(EXTRA=("Nowhere",))


@pytest.mark.parametrize("size", [8, 10])
def test_conference_league_rejects_wrong_conference_size(size: int) -> None:
    west = PCFL_WEST[:8] if size == 8 else (*PCFL_WEST, "Nowhere")
    with pytest.raises(ValueError, match="exactly 9 teams"):
        _pcfl(WESTERN=west)


def test_conference_league_rejects_duplicate_team() -> None:
    with pytest.raises(ValueError, match="Duplicate team"):
        _pcfl(EASTERN=(*PCFL_EAST[:8], "Michigan"))


def test_conference_league_rejects_overall_missing_a_team() -> None:
    with pytest.raises(ValueError, match="all 18 teams"):
        build_conference_league(
            {"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}, PCFL_OVERALL[:-1]
        )


def test_conference_league_ordered_teams_by_conference_then_metro() -> None:
    order = [t.metro for t in ordered_teams(PCFL_LEAGUE.teams)]
    assert order == sorted(PCFL_EAST) + sorted(PCFL_WEST)
    assert list(PCFL_LEAGUE.teams) == ordered_teams(PCFL_LEAGUE.teams)


# --- Divisional league (PNFL) -------------------------------------------------


def test_divisional_league_structure() -> None:
    league = LEAGUE_5_SLOTS
    assert league.has_divisions
    assert league.conferences == (AFC, NFC)
    assert league.divisions == (AFC_EAST, AFC_WEST, NFC_EAST, NFC_WEST)
    assert league.max_divisional_games_per_week == 8
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
    teams = ordered_teams(LEAGUE_5_SLOTS.teams)
    divisions = [t.division for t in teams]
    assert divisions == sorted(divisions, key=lambda d: d.name if d else "")
    assert list(LEAGUE_5_SLOTS.teams) == teams


def test_build_league_rejects_mixed_conference_keys() -> None:
    with pytest.raises(ValueError, match="Unknown division key"):
        build_league({"WESTERN": PCFL_WEST, "EASTERN": PCFL_EAST}, PCFL_OVERALL)
