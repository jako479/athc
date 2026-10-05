"""Shared scheduler helpers: the CP-SAT solver setup both phases use."""

from __future__ import annotations

import pytest

from athc.scheduler import cpu
from athc.scheduler.schedulers.utils import make_solver, resolve_workers


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


def test_auto_workers_resolve_to_this_machines_fast_threads_minus_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cpu, "fast_thread_count", lambda: 16)
    assert resolve_workers("auto") == 14
    params = make_solver(seed=3, time_limit=42.0, workers="auto").parameters
    assert params.num_search_workers == 14
    assert params.interleave_batch_size == 14


def test_a_fixed_worker_count_is_used_as_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cpu, "fast_thread_count", lambda: 16)
    assert resolve_workers(5) == 5
