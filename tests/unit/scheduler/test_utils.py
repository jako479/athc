"""Shared scheduler helpers: the CP-SAT solver setup both phases use."""

from __future__ import annotations

from athc.scheduler.schedulers.utils import make_solver


def test_solver_is_configured_for_reproducible_parallel_search() -> None:
    # The worker count must reach the solver as a fixed interleave width (both
    # num_search_workers and interleave_batch_size), stopping on deterministic
    # time -- this is what keeps a seed reproducible across machines.
    params = make_solver(seed=3, time_limit=42.0, workers=5).parameters
    assert params.random_seed == 3
    assert params.num_search_workers == 5
    assert params.interleave_search is True
    assert params.interleave_batch_size == 5
    assert params.max_deterministic_time == 42.0
