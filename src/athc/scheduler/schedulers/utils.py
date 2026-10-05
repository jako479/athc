"""Shared scheduler helpers used by both phases."""

from __future__ import annotations

from ortools.sat.python import cp_model

from athc.scheduler import cpu
from athc.scheduler.config import SolverWorkers


def resolve_workers(workers: SolverWorkers) -> int:
    """The worker count to run: a fixed count as given, "auto" from this CPU."""
    return workers if isinstance(workers, int) else cpu.auto_workers()


def make_solver(
    seed: int, time_limit: float, workers: SolverWorkers
) -> cp_model.CpSolver:
    """A CP-SAT solver that is parallel but reproducible.

    interleave_search is deterministic for a fixed seed AND a fixed `workers`
    count -- the result changes if the count changes -- so `workers` comes from
    config (solver_workers): a pinned count, or "auto" for this machine's fast
    threads minus two. It stops on deterministic time, not wall-clock, so the
    result is machine-speed independent; `time_limit` is that
    deterministic-time budget.
    """
    count = resolve_workers(workers)
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    solver.parameters.num_search_workers = count
    solver.parameters.interleave_search = True
    solver.parameters.interleave_batch_size = count
    solver.parameters.max_deterministic_time = time_limit
    return solver
