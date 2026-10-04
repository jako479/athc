"""Phase-1 matchup inventory for every league: structure, the same-place pairs,
cross-conference rivalries, and the difficulty line.

The phase-1 solve is fast at spread 2.5, so these run in the default suite;
proving the flat line (spread 0.0) optimal on the conference league takes about
30 s, so that case is `slow`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import pytest

from athc.scheduler.config import resolve_rivalries
from athc.scheduler.domain.league import League, Team, build_league
from athc.scheduler.domain.schedule import GAMES_PER_WEEK
from athc.scheduler.schedulers.matchup_builder import MatchupBuilder, difficulty_target
from athc.scheduler.schedulers.types import (
    Matchup,
    MatchupPlan,
    Matchups,
    make_matchup,
)

from .conftest import MATCHUP_CASES, LeagueCase

FAST_SPREAD = 2.5
TOP_HALF = 5  # conference ranks 1-5 are the top half, 5-9 the bottom half


def _weeks(case: LeagueCase) -> int:
    return case.config.league.weeks


def _builder(case: LeagueCase, spread: float = FAST_SPREAD, weeks: int | None = None):
    return MatchupBuilder(
        case.league,
        weeks=weeks or _weeks(case),
        rivalries=resolve_rivalries(case.league, case.config.rivalries),
        spread=spread,
    )


@pytest.fixture(scope="module")
def plan(matchup_case: LeagueCase) -> MatchupPlan:
    return _builder(matchup_case).build_matchup_plan()


def _team_counts(matchups: Iterable[Matchup]) -> Counter[Team]:
    return Counter(team for pair in matchups for team in pair)


def _nonconference_opponents(team: Team, matchups: Matchups) -> list[Team]:
    return [
        j if i == team else i
        for i, j in matchups
        if team in (i, j) and i.conference != j.conference
    ]


def _expected_same_place_pairs(league: League) -> set:
    """Each division place vs the same place in every other-conference division
    that has that place, computed independently of the builder."""
    standings = league.division_standings
    pairs = set()
    for division, order in standings.items():
        for other, other_order in standings.items():
            if other.conference == division.conference:
                continue
            for place, team in enumerate(order):
                if place < len(other_order):
                    pairs.add(make_matchup(team, other_order[place]))
    return pairs


def _expected_fixed_pairs(case: LeagueCase) -> set:
    rivalries = resolve_rivalries(case.league, case.config.rivalries)
    cross = {make_matchup(a, b) for a, b in rivalries if a.conference != b.conference}
    return _expected_same_place_pairs(case.league) | cross


def _avg_opponent_conf_rank(team: Team, matchups: Matchups, league: League) -> float:
    ranks = [
        league.rankings.rank_of(o) for o in _nonconference_opponents(team, matchups)
    ]
    return sum(ranks) / len(ranks)


# --- Structure ----------------------------------------------------------------


def test_inventory_totals(plan: MatchupPlan, matchup_case: LeagueCase) -> None:
    weeks = _weeks(matchup_case)
    assert len(plan.matchups) == weeks * GAMES_PER_WEEK
    counts = _team_counts(plan.matchups)
    assert all(counts[team] == weeks for team in matchup_case.league.teams)


def test_divisional_twice_conference_once_nonconference_at_most_once(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    pair_counts = Counter(plan.matchups)
    teams = matchup_case.league.teams
    for i, a in enumerate(teams):
        for b in teams[i + 1 :]:
            pair = make_matchup(a, b)
            if a.same_division(b):
                assert pair_counts[pair] == 2, (a.metro, b.metro)
            elif a.conference == b.conference:
                assert pair_counts[pair] == 1, (a.metro, b.metro)
            else:
                assert pair_counts[pair] <= 1, (a.metro, b.metro)


def test_nonconference_degree_matches_the_league(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    league = matchup_case.league
    for team in league.teams:
        opponents = _nonconference_opponents(team, plan.matchups)
        expected = league.nonconference_games(team, _weeks(matchup_case))
        assert len(opponents) == len(set(opponents)) == expected, team.metro


def test_inventory_uses_canonical_pair_ordering(plan: MatchupPlan) -> None:
    assert all(i.metro < j.metro for i, j in plan.matchups)


def test_inventory_is_deterministic(matchup_case: LeagueCase) -> None:
    first = Counter(_builder(matchup_case).build_matchup_plan().matchups)
    second = Counter(_builder(matchup_case).build_matchup_plan().matchups)
    assert first == second


@pytest.mark.parametrize(
    "case",
    [c for c in MATCHUP_CASES if not c.league.has_divisions],
    ids=lambda c: c.id,
)
def test_fewer_weeks_give_fewer_nonconference_games(case: LeagueCase) -> None:
    # Without same-place pairs every non-conference slot is the solver's, so
    # the inventory shrinks with the weeks (with divisions the fixed pairs and
    # the top/bottom-half guard need the full slate).
    weeks = _weeks(case) - 2
    plan = _builder(case, weeks=weeks).build_matchup_plan()
    assert len(plan.matchups) == weeks * GAMES_PER_WEEK
    for team in case.league.teams:
        expected = case.league.nonconference_games(team, weeks)
        assert len(_nonconference_opponents(team, plan.matchups)) == expected


# --- Fixed non-conference games: same-place pairs and cross-conference rivalries


def test_fixed_pairs_are_same_place_pairs_and_cross_rivalries(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    expected = _expected_fixed_pairs(matchup_case)
    assert plan.fixed_nonconference_pairs == expected
    assert expected <= set(plan.matchups)


def test_same_place_pairs_match_the_divisions(matchup_case: LeagueCase) -> None:
    pairs = _builder(matchup_case)._same_place_pairs()
    assert pairs == _expected_same_place_pairs(matchup_case.league)
    assert all(a.conference != b.conference for a, b in pairs)


@pytest.mark.parametrize(
    "case", [c for c in MATCHUP_CASES if c.league.has_divisions], ids=lambda c: c.id
)
def test_same_place_pair_count_for_two_4_and_two_5_team_divisions(
    case: LeagueCase,
) -> None:
    # Places 1-4 pair across both other-conference divisions (16 pairs); the
    # two 5th places have only each other (1 pair).
    assert len(_builder(case)._same_place_pairs()) == 17


def test_fixed_pair_degree_follows_the_places(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    league = matchup_case.league
    cross_rivals = {
        team
        for a, b in resolve_rivalries(league, matchup_case.config.rivalries)
        if a.conference != b.conference
        for team in (a, b)
    }
    degree = _team_counts(plan.fixed_nonconference_pairs)
    for division, order in league.division_standings.items():
        for place, team in enumerate(order):
            expected = sum(
                1
                for other, other_order in league.division_standings.items()
                if other.conference != division.conference and place < len(other_order)
            )
            assert degree[team] == expected + (team in cross_rivals), team.metro
    if not league.has_divisions:
        for team in league.teams:
            assert degree[team] == (1 if team in cross_rivals else 0), team.metro


def test_fixed_pairs_follow_division_standings_not_rank() -> None:
    # Jacksonville is 7th in its conference by rank but 1st in its division
    # standings, so its fixed games are vs the two other-conference 1st places.
    first = (
        "New England",
        "Cincinnati",
        "Pittsburgh",
        "Denver",
        "Miami",
        "Buffalo",
        "Jacksonville",
        "Los Angeles",
        "Las Vegas",
    )
    second = (
        "Washington",
        "Chicago",
        "Minnesota",
        "San Francisco",
        "Atlanta",
        "New York",
        "Philadelphia",
        "Green Bay",
        "Seattle",
    )
    overall = [team for pair in zip(first, second, strict=True) for team in pair]
    standings = {
        "AFC_EAST": ("Jacksonville", "New England", "Miami", "Buffalo"),
        "AFC_WEST": ("Cincinnati", "Pittsburgh", "Denver", "Los Angeles", "Las Vegas"),
        "NFC_EAST": ("Washington", "Atlanta", "New York", "Philadelphia"),
        "NFC_WEST": ("Chicago", "Minnesota", "San Francisco", "Green Bay", "Seattle"),
    }
    league = build_league(standings, overall, divisions=True)
    plan = MatchupBuilder(league).build_matchup_plan()
    assert plan.fixed_nonconference_pairs == _expected_same_place_pairs(league)
    jacksonville = next(t for t in league.teams if t.metro == "Jacksonville")
    fixed_opponents = {
        j if i == jacksonville else i
        for i, j in plan.fixed_nonconference_pairs
        if jacksonville in (i, j)
    }
    assert {t.metro for t in fixed_opponents} == {"Washington", "Chicago"}


# --- Difficulty line ----------------------------------------------------------


def test_each_team_draws_a_top_and_bottom_half_opponent(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    league = matchup_case.league
    for team in league.teams:
        ranks = [
            league.rankings.rank_of(o)
            for o in _nonconference_opponents(team, plan.matchups)
        ]
        assert any(r <= TOP_HALF for r in ranks), team.metro
        assert any(r >= TOP_HALF for r in ranks), team.metro


def _spread_cases():
    for case in MATCHUP_CASES:
        for spread in (0.0, 1.8, 2.5):
            slow = spread == 0.0 and not case.league.has_divisions
            yield pytest.param(
                case,
                spread,
                id=f"{case.id}-spread-{spread}",
                marks=[pytest.mark.slow] if slow else [],
            )


@pytest.mark.parametrize(("case", "spread"), list(_spread_cases()))
def test_difficulty_is_near_line_target(case: LeagueCase, spread: float) -> None:
    # Soft target; worst observed miss across leagues and spreads is 0.75.
    plan = _builder(case, spread=spread).build_matchup_plan()
    for team in case.league.teams:
        avg = _avg_opponent_conf_rank(team, plan.matchups, case.league)
        target = difficulty_target(case.league.rankings.rank_of(team), spread)
        assert abs(avg - target) <= 1.0, (
            f"{team.metro}: avg opponent rank {avg:.2f} far from target {target:.2f}"
        )


def test_orders_difficulty_by_conference_rank(
    plan: MatchupPlan, matchup_case: LeagueCase
) -> None:
    league = matchup_case.league
    for conference in league.conferences:
        ranked = league.rankings.ranked(conference)
        top = _avg_opponent_conf_rank(ranked[0], plan.matchups, league)
        bottom = _avg_opponent_conf_rank(ranked[-1], plan.matchups, league)
        assert top < bottom, "top seed should get a tougher slate than the bottom seed"


def test_difficulty_target_line() -> None:
    # Linear on conference rank 1-9: default tilt 2.5, symmetric about 5.
    assert difficulty_target(1) == 2.5
    assert difficulty_target(5) == 5.0
    assert difficulty_target(9) == 7.5
    assert difficulty_target(1, spread=1.8) == pytest.approx(3.2)
    for rank in range(1, 10):
        assert difficulty_target(rank, spread=0.0) == 5.0
        assert difficulty_target(rank) + difficulty_target(10 - rank) == pytest.approx(
            10.0
        )
    targets = [difficulty_target(r) for r in range(1, 10)]
    assert targets == sorted(targets)
