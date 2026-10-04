"""Phase-1 inventory for a league without divisions (the PCFL)."""

from __future__ import annotations

from collections import Counter

import pytest

from athc.scheduler.config import RivalriesConfig, resolve_rivalries
from athc.scheduler.schedulers.fixed_cpsat_builder import (
    FixedCpsatMatchupBuilder,
    difficulty_target,
)
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup

from ..conftest import PCFL_LEAGUE, PCFL_RIVALRIES

RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))


# The flat line (spread 0.0, the PCFL default) takes ~30 s to prove its minimax
# optimum; spread 2.5 takes well under a second. The inventory's structural
# rules do not depend on the spread, so the shared plan uses 2.5 and only the
# flat-line target case is slow.
FAST_SPREAD = 2.5


def _plan(spread: float = FAST_SPREAD, weeks: int = 12) -> MatchupPlan:
    return FixedCpsatMatchupBuilder(
        PCFL_LEAGUE, weeks=weeks, rivalries=RIVALRIES, spread=spread
    ).build_matchup_plan()


@pytest.fixture(scope="module")
def plan() -> MatchupPlan:
    return _plan()


def _nonconference(team, matchups):
    return [
        (j if i == team else i)
        for i, j in matchups
        if team in (i, j) and i.conference != j.conference
    ]


def test_inventory_totals(plan) -> None:
    assert len(plan.matchups) == 12 * 9
    counts = Counter(t for pair in plan.matchups for t in pair)
    assert all(counts[t] == 12 for t in PCFL_LEAGUE.teams)


def test_every_conference_pair_once_and_no_divisional_repeats(plan) -> None:
    pair_counts = Counter(plan.matchups)
    for i, a in enumerate(PCFL_LEAGUE.teams):
        for b in PCFL_LEAGUE.teams[i + 1 :]:
            expected = 1 if a.conference == b.conference else None
            if expected is not None:
                assert pair_counts[make_matchup(a, b)] == 1, (a.metro, b.metro)
            else:
                assert pair_counts[make_matchup(a, b)] <= 1, (a.metro, b.metro)


def test_every_team_has_four_distinct_nonconference_opponents(plan) -> None:
    for team in PCFL_LEAGUE.teams:
        opponents = _nonconference(team, plan.matchups)
        assert len(opponents) == 4 and len(set(opponents)) == 4, team.metro


def test_cross_conference_rivalry_is_fixed(plan) -> None:
    oklahoma_texas = {
        make_matchup(a, b) for a, b in RIVALRIES if a.conference != b.conference
    }
    assert len(oklahoma_texas) == 1
    assert plan.fixed_nonconference_pairs == frozenset(oklahoma_texas)
    assert oklahoma_texas <= set(plan.matchups)


def test_each_team_draws_a_top_and_bottom_half_opponent(plan) -> None:
    for team in PCFL_LEAGUE.teams:
        ranks = [
            PCFL_LEAGUE.rankings.rank_of(o) for o in _nonconference(team, plan.matchups)
        ]
        assert any(r <= 5 for r in ranks) and any(r >= 5 for r in ranks), team.metro


@pytest.mark.parametrize(
    "spread",
    [pytest.param(0.0, marks=pytest.mark.slow, id="flat"), pytest.param(2.5, id="max")],
)
def test_difficulty_is_near_line_target(spread: float) -> None:
    plan = _plan(spread=spread)
    for team in PCFL_LEAGUE.teams:
        ranks = [
            PCFL_LEAGUE.rankings.rank_of(o) for o in _nonconference(team, plan.matchups)
        ]
        target = difficulty_target(PCFL_LEAGUE.rankings.rank_of(team), spread)
        assert abs(sum(ranks) / 4 - target) <= 1.0, team.metro


def test_inventory_is_deterministic() -> None:
    assert Counter(_plan().matchups) == Counter(_plan().matchups)


def test_ten_week_season_gives_two_nonconference_games() -> None:
    plan = _plan(weeks=10)
    assert len(plan.matchups) == 90
    for team in PCFL_LEAGUE.teams:
        assert len(_nonconference(team, plan.matchups)) == 2, team.metro
