"""Phase-2 ScheduleBuilder: inventory guards, rule gating, solver wiring.

Seed determinism and schedule correctness are covered end-to-end by the golden
regression test in tests/integration/test_generate_schedule.py; the PNFL model
itself is pinned by test_pnfl_model_fingerprint.py.
"""

from __future__ import annotations

import pytest

from athc.scheduler.config import (
    ConfigError,
    Phase2Config,
    RivalriesConfig,
    resolve_rivalries,
)
from athc.scheduler.domain.league import AFC, AFC_EAST, Team
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from athc.scheduler.schedulers.types import make_matchup

from .conftest import LEAGUE_5_SLOTS, PCFL_LEAGUE, PCFL_RIVALRIES


def _off_dict() -> dict[str, bool]:
    return {
        "require_home_balance_per_six_weeks": False,
        "require_home_away_streak_caps": False,
        "require_mixed_home_away_at_season_ends": False,
    }


PCFL_AMOUNTS = Phase2Config(**_off_dict())
RIVALRIES = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))


def _pcfl_model(amounts: Phase2Config = PCFL_AMOUNTS, **kwargs) -> ScheduleBuilder:
    builder = ScheduleBuilder(PCFL_LEAGUE, SchedulerError, amounts, weeks=12, **kwargs)
    builder._populate_model(matchups=[])
    return builder


def _counts(builder: ScheduleBuilder) -> tuple[int, int]:
    return len(builder.model.proto.variables), len(builder.model.proto.constraints)


def test_unknown_pair_in_inventory_raises() -> None:
    teams = LEAGUE_5_SLOTS.teams
    foreign = Team(metro="Nowhere", conference=AFC, division=AFC_EAST)
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([make_matchup(foreign, teams[0])], seed=0, time_limit=5)


def test_empty_inventory_is_infeasible() -> None:
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    with pytest.raises(SchedulerError):
        builder.build_schedule([], seed=0, time_limit=30)


def test_soft_objective_is_added_to_the_model() -> None:
    # Building the model (no solve) wires the soft objective: 8 metrics, each
    # with an over- and under-slack term -> 16 objective terms.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    builder._populate_model(matchups=[])
    assert len(builder.model.proto.objective.vars) == 16


def test_solver_is_configured_for_reproducible_parallel_search() -> None:
    # The worker count must reach the solver as a fixed interleave width (both
    # num_search_workers and interleave_batch_size), stopping on deterministic
    # time -- this is what keeps a seed reproducible across machines.
    builder = ScheduleBuilder(LEAGUE_5_SLOTS, SchedulerError)
    params = builder._make_solver(seed=3, time_limit=42.0, workers=5).parameters
    assert params.random_seed == 3
    assert params.num_search_workers == 5
    assert params.interleave_search is True
    assert params.interleave_batch_size == 5
    assert params.max_deterministic_time == 42.0


# --- Rule gating for a league without divisions -------------------------------


def test_league_without_divisions_has_no_divisional_model_parts() -> None:
    builder = _pcfl_model()
    assert len(builder.model.proto.objective.vars) == 0  # no soft objective
    names = [v.name for v in builder.model.proto.variables]
    assert not any(
        n.startswith(("d_", "s3d_", "has3", "open2div_", "gap_")) for n in names
    )
    assert builder.home_games_per_team == 6
    assert builder.num_weeks == 12


@pytest.mark.parametrize(
    "toggle",
    [
        "require_home_balance_per_six_weeks",
        "require_home_away_streak_caps",
        "require_mixed_home_away_at_season_ends",
    ],
)
def test_home_away_toggles_add_constraints_only_when_on(toggle: str) -> None:
    off = _counts(_pcfl_model())
    on = _counts(_pcfl_model(Phase2Config(**{**_off_dict(), toggle: True})))
    assert on[1] > off[1]


def test_streak_caps_off_with_divisions_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="require_home_away_streak_caps"):
        ScheduleBuilder(
            LEAGUE_5_SLOTS,
            SchedulerError,
            Phase2Config(require_home_away_streak_caps=False),
        )


def test_streak_caps_on_without_divisions_is_allowed() -> None:
    builder = _pcfl_model(
        Phase2Config(**{**_off_dict(), "require_home_away_streak_caps": True})
    )
    names = [v.name for v in builder.model.proto.variables]
    assert any(n.startswith("has3h_") for n in names)
    assert not any(n.startswith("has3d_") for n in names)


def test_max_consecutive_window_follows_the_cap() -> None:
    # cap 2 -> 3-week windows: 10 per team for 12 weeks, two constraints each.
    two = _counts(
        _pcfl_model(Phase2Config(**_off_dict(), max_consecutive_home_or_away=2))
    )
    three = _counts(
        _pcfl_model(Phase2Config(**_off_dict(), max_consecutive_home_or_away=3))
    )
    assert two[1] - three[1] == 18 * 2 * (10 - 9)


def test_opening_nonconference_weeks_add_one_constraint_per_team_week() -> None:
    off = _counts(_pcfl_model())
    on = _counts(
        _pcfl_model(Phase2Config(**_off_dict(), opening_nonconference_weeks=3))
    )
    assert on[1] - off[1] == 18 * 3


def test_conference_streak_cap_adds_two_constraints_per_window() -> None:
    # cap 2: every window of 3..12 weeks -> 55 windows per team, two each.
    off = _counts(_pcfl_model())
    on = _counts(
        _pcfl_model(
            Phase2Config(**_off_dict(), max_consecutive_conference_home_or_away=2)
        )
    )
    assert on[1] - off[1] == 18 * 2 * 55


def test_rivalry_week_adds_one_constraint_per_pair() -> None:
    off = _counts(_pcfl_model())
    rotating = _counts(_pcfl_model(rivalries=RIVALRIES, season=2028))
    free = _counts(
        _pcfl_model(rivalries=RIVALRIES, rotate_rivalry_home_by_season=False)
    )
    assert rotating[1] - off[1] == 9
    assert free[1] - off[1] == 9


def test_rivalry_rotation_needs_a_season() -> None:
    with pytest.raises(SchedulerError, match="season"):
        ScheduleBuilder(
            PCFL_LEAGUE, SchedulerError, PCFL_AMOUNTS, weeks=12, rivalries=RIVALRIES
        )


def test_rivalry_rotation_pins_the_host_by_season_parity() -> None:
    # Even season: the first-listed team hosts. The pinned literal is x[first, second, last].
    even = _pcfl_model(rivalries=RIVALRIES, season=2028)
    odd = _pcfl_model(rivalries=RIVALRIES, season=2029)
    first, second = RIVALRIES[0]
    even_var = even.x[first, second, 11].index
    odd_var = odd.x[second, first, 11].index
    even_pinned = {
        c.linear.vars[0]
        for c in even.model.proto.constraints
        if len(c.linear.vars) == 1 and list(c.linear.domain) == [1, 1]
    }
    odd_pinned = {
        c.linear.vars[0]
        for c in odd.model.proto.constraints
        if len(c.linear.vars) == 1 and list(c.linear.domain) == [1, 1]
    }
    assert even_var in even_pinned
    assert odd_var in odd_pinned
