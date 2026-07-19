"""Phase-1 inventory tests for the FixedCpsatMatchupBuilder (Scheduler C).

Scheduler C fixes two non-conference games per team by division place (5ths
one), then one CP-SAT solve picks the rest along the c_spread line. These
tests build the plan directly (no week placement), so they run in the fast
suite.
"""

from __future__ import annotations

from collections import Counter

import pytest

from athc.scheduler.domain.league import Division, League, Team, build_league
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_cpsat_builder import (
    FIXED_NONCONF_PLACE_OPPONENTS,
    FixedCpsatMatchupBuilder,
    _validate_fixed_place_table,
    difficulty_target,
)
from athc.scheduler.schedulers.types import MatchupPlan, make_matchup

from ..conftest import _DIVISIONS


@pytest.fixture(scope="session")
def fixed_cpsat_matchup_plan(league: League) -> MatchupPlan:
    return FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
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


def _place_pairs_from(league: League) -> set:
    """The 17 fixed pairs the place table implies for `league`'s standings."""
    standings = league.division_standings
    assert standings is not None
    team_at = {
        (division, index + 1): team
        for division, order in standings.items()
        for index, team in enumerate(order)
    }
    return {
        make_matchup(team_at[slot], team_at[opp])
        for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
        for opp in opponents
    }


def _avg_opponent_conf_rank(team: Team, matchups, rankings) -> float:
    games = 5 if team.division in (Division.AFC_EAST, Division.NFC_EAST) else 4
    total = sum(
        rankings.rank_of(j if i == team else i)
        for i, j in matchups
        if team in (i, j) and i.conference != j.conference
    )
    return total / games


def test_inventory_has_expected_total_counts(fixed_cpsat_matchup_plan, league):
    matchups = fixed_cpsat_matchup_plan.matchups
    assert len(matchups) == 144
    team_counts = _team_counts(matchups)
    for team in league.teams:
        assert team_counts[team] == 16, (
            f"{team.metro}: wrong total number of games in phase-1 inventory"
        )


def test_inventory_has_expected_divisional_and_conference_counts(
    fixed_cpsat_matchup_plan, league
):
    pair_counts = Counter(fixed_cpsat_matchup_plan.matchups)
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
                    f"{team_a.metro}/{team_b.metro}: non-conference pair at most once"
                )


def test_inventory_assigns_expected_nonconference_degree(
    fixed_cpsat_matchup_plan, league
):
    for team in league.teams:
        expected = 5 if team.division in (Division.AFC_EAST, Division.NFC_EAST) else 4
        actual = len(_nonconference_opponents(team, fixed_cpsat_matchup_plan.matchups))
        assert actual == expected, f"{team.metro}: wrong non-conference degree"


def test_inventory_contains_fixed_place_table_pairs(fixed_cpsat_matchup_plan, league):
    expected = _place_pairs_from(league)
    assert expected <= set(fixed_cpsat_matchup_plan.matchups)
    assert fixed_cpsat_matchup_plan.fixed_nonconference_pairs == expected


def test_inventory_records_fixed_pairs_per_team(fixed_cpsat_matchup_plan, league):
    # 16 teams x 2 fixed + 2 fifth-place teams x 1, halved = 17 pairs.
    fixed = fixed_cpsat_matchup_plan.fixed_nonconference_pairs
    assert len(fixed) == 17
    assert fixed <= set(fixed_cpsat_matchup_plan.matchups)
    standings = league.division_standings
    fifth_place = {standings[Division.AFC_WEST][4], standings[Division.NFC_WEST][4]}
    fixed_degree = _team_counts(fixed)
    for team in league.teams:
        expected = 1 if team in fifth_place else 2
        assert fixed_degree[team] == expected, f"{team.metro}: wrong fixed count"


def test_inventory_uses_canonical_pair_ordering(fixed_cpsat_matchup_plan):
    assert all(i.metro < j.metro for i, j in fixed_cpsat_matchup_plan.matchups)


def test_gives_each_team_a_top_and_bottom_half_opponent(
    fixed_cpsat_matchup_plan, league
):
    for team in league.teams:
        opp_ranks = [
            league.rankings.rank_of(j if i == team else i)
            for i, j in fixed_cpsat_matchup_plan.matchups
            if team in (i, j) and i.conference != j.conference
        ]
        assert any(r <= 5 for r in opp_ranks), (
            f"{team.metro}: no top-half non-conference opponent"
        )
        assert any(r >= 5 for r in opp_ranks), (
            f"{team.metro}: no bottom-half non-conference opponent"
        )


def test_inventory_is_deterministic(league) -> None:
    def build() -> Counter:
        return Counter(
            FixedCpsatMatchupBuilder(
                teams=league.teams,
                rankings=league.rankings,
                division_standings=league.division_standings,
            )
            .build_matchup_plan()
            .matchups
        )

    assert build() == build()


# ---------------------------------------------------------------------------
# Difficulty line
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("c_spread", [0.0, 1.8, 2.5])
def test_difficulty_is_near_line_target(league, c_spread) -> None:
    # Soft target; worst observed across leagues and spreads is 0.75, allow 1.0.
    plan = FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
        c_spread=c_spread,
    ).build_matchup_plan()
    for team in league.teams:
        avg = _avg_opponent_conf_rank(team, plan.matchups, league.rankings)
        target = difficulty_target(league.rankings.rank_of(team), c_spread)
        assert abs(avg - target) <= 1.0, (
            f"{team.metro}: avg opponent rank {avg:.2f} far from target {target:.2f}"
        )


def test_orders_difficulty_by_conference_rank(fixed_cpsat_matchup_plan, league) -> None:
    matchups = fixed_cpsat_matchup_plan.matchups
    for ranked in (league.rankings.afc, league.rankings.nfc):
        top = _avg_opponent_conf_rank(ranked[0], matchups, league.rankings)
        bottom = _avg_opponent_conf_rank(ranked[-1], matchups, league.rankings)
        assert top < bottom, "top seed should get a tougher slate than the bottom seed"


def test_difficulty_target_line() -> None:
    # Linear on conference rank 1-9: default tilt 1.8, symmetric about 5.
    assert difficulty_target(1) == pytest.approx(3.2)
    assert difficulty_target(5) == 5.0
    assert difficulty_target(9) == pytest.approx(6.8)
    assert difficulty_target(1, c_spread=2.5) == 2.5
    for rank in range(1, 10):
        assert difficulty_target(rank, c_spread=0.0) == 5.0
        assert difficulty_target(rank) + difficulty_target(10 - rank) == pytest.approx(
            10.0
        )
    targets = [difficulty_target(r) for r in range(1, 10)]
    assert targets == sorted(targets)


# ---------------------------------------------------------------------------
# The fixed place table itself
# ---------------------------------------------------------------------------


def test_place_table_covers_every_division_place() -> None:
    expected_slots = {
        (division, place)
        for division in Division
        for place in range(1, division.expected_size + 1)
    }
    assert set(FIXED_NONCONF_PLACE_OPPONENTS) == expected_slots


def test_place_table_is_symmetric_and_cross_conference() -> None:
    for (division, place), opponents in FIXED_NONCONF_PLACE_OPPONENTS.items():
        assert len(set(opponents)) == len(opponents)
        for opp_division, opp_place in opponents:
            assert opp_division.conference != division.conference
            assert (division, place) in FIXED_NONCONF_PLACE_OPPONENTS[
                opp_division, opp_place
            ]


def test_place_table_defines_17_unique_pairs() -> None:
    pairs = {
        frozenset({slot, opp})
        for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
        for opp in opponents
    }
    assert len(pairs) == 17


def test_place_table_is_same_place_only() -> None:
    # Places 1-4: both same-place finishers, nothing else. 5ths: each other.
    for division in Division:
        for place in range(1, 5):
            opponents = set(FIXED_NONCONF_PLACE_OPPONENTS[division, place])
            expected = {
                (other, place)
                for other in Division
                if other.conference != division.conference
            }
            assert opponents == expected, f"{division.name} place {place}"
    assert FIXED_NONCONF_PLACE_OPPONENTS[Division.AFC_WEST, 5] == (
        (Division.NFC_WEST, 5),
    )
    assert FIXED_NONCONF_PLACE_OPPONENTS[Division.NFC_WEST, 5] == (
        (Division.AFC_WEST, 5),
    )


@pytest.mark.parametrize(
    "bad_table",
    [
        pytest.param({(Division.AFC_EAST, 1): ()}, id="missing-slots"),
        pytest.param(
            {
                slot: (*opponents, (Division.NFC_EAST, 3))
                if slot == (Division.AFC_EAST, 1)
                else opponents
                for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
            },
            id="wrong-count",
        ),
        pytest.param(
            {
                slot: ((Division.NFC_EAST, 3), (Division.NFC_WEST, 3))
                if slot == (Division.AFC_EAST, 1)
                else opponents
                for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
            },
            id="asymmetric",
        ),
        pytest.param(
            {
                slot: ((Division.AFC_WEST, 1), *opponents[1:])
                if slot == (Division.AFC_EAST, 1)
                else opponents
                for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
            },
            id="same-conference",
        ),
    ],
)
def test_place_table_validation_rejects_invalid_table(monkeypatch, bad_table) -> None:
    monkeypatch.setattr(
        "athc.scheduler.schedulers.fixed_cpsat_builder.FIXED_NONCONF_PLACE_OPPONENTS",
        bad_table,
    )
    with pytest.raises(SchedulerError):
        _validate_fixed_place_table()


# ---------------------------------------------------------------------------
# Division standings drive the fixed pairs (not conference rank)
# ---------------------------------------------------------------------------


def test_fixed_pairs_follow_division_standings_not_rank() -> None:
    # Jacksonville is 7th in the AFC by rank but 1st in its division standings,
    # so its fixed games are vs the two other-conference division winners.
    afc = (
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
    nfc = (
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
    overall = [team for pair in zip(afc, nfc, strict=True) for team in pair]
    standings = {
        "AFC_EAST": ("Jacksonville", "New England", "Miami", "Buffalo"),
        "AFC_WEST": ("Cincinnati", "Pittsburgh", "Denver", "Los Angeles", "Las Vegas"),
        "NFC_EAST": ("Washington", "Atlanta", "New York", "Philadelphia"),
        "NFC_WEST": ("Chicago", "Minnesota", "San Francisco", "Green Bay", "Seattle"),
    }
    league = build_league(_DIVISIONS, overall, division_standings=standings)
    plan = FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=league.division_standings,
    ).build_matchup_plan()
    assert plan.fixed_nonconference_pairs == _place_pairs_from(league)
    jacksonville = next(t for t in league.teams if t.metro == "Jacksonville")
    fixed_opponents = {
        j if i == jacksonville else i
        for i, j in plan.fixed_nonconference_pairs
        if jacksonville in (i, j)
    }
    assert {t.metro for t in fixed_opponents} == {"Washington", "Chicago"}


def test_builder_errors_without_division_standings(league) -> None:
    builder = FixedCpsatMatchupBuilder(
        teams=league.teams,
        rankings=league.rankings,
        division_standings=None,
    )
    with pytest.raises(SchedulerError, match="DivisionStandings"):
        builder.build_matchup_plan()
