from collections import Counter

import pytest

from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.domain.league import Conference, Division, League, Team
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_matchup_builder import (
    FIXED_NONCONF_RANK_OPPONENTS,
    FixedMatchupBuilder,
    _pseudo_inverse_target_rank,
    _validate_fixed_rank_table,
)
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup

from ..conftest import HISTORY_PATH, TEST_SEASON


@pytest.fixture(scope="session")
def fixed_matchup_plan(league: League) -> MatchupPlan:
    return FixedMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=NonConfHistory.load(HISTORY_PATH),
        season=TEST_SEASON,
    ).build_matchup_plan()


def _team_counts(matchups) -> Counter[Team]:
    counts: Counter[Team] = Counter()
    for i, j in matchups:
        counts[i] += 1
        counts[j] += 1
    return counts


def _nonconference_opponents(team: Team, matchups) -> set[Team]:
    opponents: set[Team] = set()
    for i, j in matchups:
        if i == team and j.conference != team.conference:
            opponents.add(j)
        elif j == team and i.conference != team.conference:
            opponents.add(i)
    return opponents


def _expected_fixed_opponents(team: Team, league: League) -> set[Team]:
    other_ranked = (
        league.rankings.nfc
        if team.conference == Conference.AFC
        else league.rankings.afc
    )
    team_rank = league.rankings.rank_of(team)
    return {
        other_ranked[opp_rank - 1]
        for opp_rank in FIXED_NONCONF_RANK_OPPONENTS[team_rank]
    }


def test_phase_one_inventory_has_expected_total_counts(fixed_matchup_plan, league):
    matchups = fixed_matchup_plan.matchups
    pair_counts = Counter(matchups)
    team_counts = _team_counts(matchups)

    assert len(matchups) == 144
    assert sum(pair_counts.values()) == 144
    for team in league.teams:
        assert team_counts[team] == 16, (
            f"{team.metro}: wrong total number of games in phase-1 inventory"
        )


def test_phase_one_inventory_has_expected_divisional_and_conference_counts(
    fixed_matchup_plan, league
):
    pair_counts = Counter(fixed_matchup_plan.matchups)

    for i, team_a in enumerate(league.teams):
        for team_b in league.teams[i + 1 :]:
            pair = make_matchup(team_a, team_b)
            if team_a.division == team_b.division:
                assert pair_counts[pair] == 2, (
                    f"{team_a.metro}/{team_b.metro}: divisional pair should appear twice"
                )
            elif team_a.conference == team_b.conference:
                assert pair_counts[pair] == 1, (
                    f"{team_a.metro}/{team_b.metro}: conference pair should appear once"
                )
            else:
                assert pair_counts[pair] <= 1, (
                    f"{team_a.metro}/{team_b.metro}: non-conference pair should appear at most once"
                )


def test_phase_one_inventory_assigns_expected_nonconference_degree(
    fixed_matchup_plan, league
):
    for team in league.teams:
        expected = 5 if team.division in (Division.AFC_EAST, Division.NFC_EAST) else 4
        actual = len(_nonconference_opponents(team, fixed_matchup_plan.matchups))
        assert actual == expected, f"{team.metro}: wrong non-conference degree"


def test_phase_one_inventory_contains_fixed_rank_table_pairs(
    fixed_matchup_plan, league
):
    for team in league.teams:
        opponents = _nonconference_opponents(team, fixed_matchup_plan.matchups)
        expected_fixed = _expected_fixed_opponents(team, league)
        assert expected_fixed.issubset(opponents), (
            f"{team.metro}: missing one of the fixed rank-table opponents"
        )


def test_phase_one_inventory_adds_extra_east_sos_pairs(fixed_matchup_plan):
    # Four East teams per conference produces exactly 4 pairings (one per East team).
    assert len(fixed_matchup_plan.extra_nonconference_pairs) == 4


def test_phase_one_inventory_history_fills_remaining_nonconference_slots(
    fixed_matchup_plan, league
):
    east_divisions = {Division.AFC_EAST, Division.NFC_EAST}
    for team in league.teams:
        opponents = _nonconference_opponents(team, fixed_matchup_plan.matchups)
        fixed = _expected_fixed_opponents(team, league)
        extra = opponents - fixed
        expected_extra = 2 if team.division in east_divisions else 1
        assert len(extra) == expected_extra, (
            f"{team.metro}: wrong number of non-fixed non-conference opponents"
        )


def test_phase_one_inventory_uses_canonical_pair_ordering(fixed_matchup_plan):
    assert all(i.metro < j.metro for i, j in fixed_matchup_plan.matchups)


def test_pseudo_inverse_target_rank_matches_design() -> None:
    targets = {rank: _pseudo_inverse_target_rank(rank) for rank in range(1, 10)}
    assert targets == {1: 6, 2: 7, 3: 8, 4: 9, 5: 5, 6: 1, 7: 2, 8: 3, 9: 4}


def test_pseudo_inverse_rank_cost_penalizes_unfavorable_direction(league) -> None:
    builder = FixedMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=NonConfHistory.load(HISTORY_PATH),
        season=TEST_SEASON,
    )
    afc_top = league.rankings.afc[0]  # rank 1; target opponent rank is 6
    at_target = league.rankings.nfc[5]  # rank 6
    harder = league.rankings.nfc[4]  # rank 5 (tougher than target)
    easier = league.rankings.nfc[6]  # rank 7 (weaker than target)
    assert builder._pseudo_inverse_rank_cost(afc_top, at_target) == 0
    assert builder._pseudo_inverse_rank_cost(afc_top, harder) == 3  # 3x unfavorable
    assert builder._pseudo_inverse_rank_cost(afc_top, easier) == 1


def test_fixed_rank_table_validation_rejects_invalid_table(monkeypatch) -> None:
    monkeypatch.setattr(
        "athc.scheduler.schedulers.fixed_matchup_builder.FIXED_NONCONF_RANK_OPPONENTS",
        {1: (1, 2, 3)},
    )
    with pytest.raises(SchedulerError):
        _validate_fixed_rank_table()


def test_unbalanced_assignment_sides_raises(league) -> None:
    builder = FixedMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=NonConfHistory.load(HISTORY_PATH),
        season=TEST_SEASON,
    )
    teams = league.teams
    with pytest.raises(SchedulerError):
        builder._solve_exact_assignment(
            [teams[0]], [teams[1], teams[2]], lambda left, right: 0, set()
        )
