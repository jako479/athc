"""Phase-1 inventory tests for the rank-only MatchupBuilder (Scheduler B)."""

from __future__ import annotations

from collections import Counter
from itertools import pairwise

import pytest

from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.domain.league import Division, League, Team
from athc.scheduler.schedulers.matchup_builder import MatchupBuilder, difficulty_target
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup

from ..conftest import HISTORY_PATH


@pytest.fixture(scope="session")
def rank_only_matchup_plan(league: League) -> MatchupPlan:
    return MatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        history=NonConfHistory.load(HISTORY_PATH),
    ).build_matchup_plan()


def _team_counts(matchups) -> Counter[Team]:
    counts: Counter[Team] = Counter()
    for i, j in matchups:
        counts[i] += 1
        counts[j] += 1
    return counts


def _nonconference_degree(team: Team, matchups) -> int:
    return sum(
        1 for i, j in matchups if team in (i, j) and i.conference != j.conference
    )


def test_rank_only_inventory_has_expected_total_counts(
    rank_only_matchup_plan, league
) -> None:
    matchups = rank_only_matchup_plan.matchups
    assert len(matchups) == 144
    team_counts = _team_counts(matchups)
    for team in league.teams:
        assert team_counts[team] == 16, (
            f"{team.metro}: wrong total game count in phase-1 inventory"
        )


def test_rank_only_inventory_has_expected_divisional_and_conference_counts(
    rank_only_matchup_plan, league
) -> None:
    pair_counts = Counter(rank_only_matchup_plan.matchups)
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


def test_rank_only_inventory_assigns_expected_nonconference_degree(
    rank_only_matchup_plan, league
) -> None:
    for team in league.teams:
        expected = 5 if team.division in (Division.AFC_EAST, Division.NFC_EAST) else 4
        actual = _nonconference_degree(team, rank_only_matchup_plan.matchups)
        assert actual == expected, f"{team.metro}: wrong non-conference degree"


def test_rank_only_inventory_uses_canonical_pair_ordering(
    rank_only_matchup_plan,
) -> None:
    assert all(i.metro < j.metro for i, j in rank_only_matchup_plan.matchups)


def test_rank_only_gives_each_team_a_top_and_bottom_half_opponent(
    rank_only_matchup_plan, league
) -> None:
    for team in league.teams:
        opp_ranks = [
            league.rankings.rank_of(j if i == team else i)
            for i, j in rank_only_matchup_plan.matchups
            if team in (i, j) and i.conference != j.conference
        ]
        assert any(r <= 5 for r in opp_ranks), (
            f"{team.metro}: no top-half non-conference opponent"
        )
        assert any(r >= 5 for r in opp_ranks), (
            f"{team.metro}: no bottom-half non-conference opponent"
        )


def test_rank_only_inventory_is_deterministic(league) -> None:
    def build() -> Counter:
        return Counter(
            MatchupBuilder(
                teams=league.teams,
                rankings=league.rankings,
                history=NonConfHistory.load(HISTORY_PATH),
            )
            .build_matchup_plan()
            .matchups
        )

    assert build() == build()


def _avg_opponent_rank(team: Team, matchups, rankings) -> float:
    games = 5 if team.division in (Division.AFC_EAST, Division.NFC_EAST) else 4
    total = sum(
        rankings.overall_rank(j if i == team else i)
        for i, j in matchups
        if team in (i, j) and i.conference != j.conference
    )
    return total / games


def test_difficulty_target_curve() -> None:
    # Sine on a slope (spread 3.19, amplitude 0.30): monotonic and symmetric about
    # 9.5; the wave pulls the ends just inside the 6.31/12.69 trend.
    assert difficulty_target(1) == pytest.approx(6.42, abs=0.01)
    assert difficulty_target(18) == pytest.approx(12.58, abs=0.01)
    targets = [difficulty_target(r) for r in range(1, 19)]
    assert targets == sorted(targets)
    for r in range(1, 19):
        assert round(difficulty_target(r) + difficulty_target(19 - r), 9) == 19.0
    # Soft-staircase: the top pair sits closer together than a mid-table riser.
    assert difficulty_target(2) - difficulty_target(1) < difficulty_target(
        6
    ) - difficulty_target(5)
    # amplitude 0 -> plain straight line: equal steps between adjacent ranks.
    flat = [difficulty_target(r, amplitude=0) for r in range(1, 19)]
    steps = [round(b - a, 9) for a, b in pairwise(flat)]
    assert len(set(steps)) == 1


def test_rank_only_difficulty_is_near_curve_target(
    rank_only_matchup_plan, league
) -> None:
    # Soft target (minimax): each team lands close to its curve target. The target
    # is not a hard cap, so a team may sit a little past it -- we only require it
    # stay within ~1.5 ranks (measured worst across the test leagues is ~1.2).
    for team in league.teams:
        avg = _avg_opponent_rank(team, rank_only_matchup_plan.matchups, league.rankings)
        target = difficulty_target(league.rankings.overall_rank(team))
        assert abs(avg - target) <= 1.5, (
            f"{team.metro}: avg opponent rank {avg:.2f} far from target {target:.2f}"
        )


def test_rank_only_orders_difficulty_by_rank(rank_only_matchup_plan, league) -> None:
    matchups = rank_only_matchup_plan.matchups
    overall = league.rankings.overall
    top = _avg_opponent_rank(overall[0], matchups, league.rankings)
    bottom = _avg_opponent_rank(overall[-1], matchups, league.rankings)
    assert top < bottom, "top seed should get a tougher slate than the bottom seed"
