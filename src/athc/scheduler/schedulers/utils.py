"""Shared scheduler helpers used by both phases."""

from __future__ import annotations

from ortools.sat.python import cp_model


def make_solver(seed: int, time_limit: float, workers: int) -> cp_model.CpSolver:
    """A CP-SAT solver that is parallel but reproducible.

    interleave_search is deterministic for a fixed seed AND a fixed `workers`
    count -- the result changes if the count changes -- so `workers` comes from
    config (solver_workers), never the machine's core count. It stops on
    deterministic time, not wall-clock, so the result is machine-speed
    independent; `time_limit` is that deterministic-time budget.
    """
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    solver.parameters.num_search_workers = workers
    solver.parameters.interleave_search = True
    solver.parameters.interleave_batch_size = workers
    solver.parameters.max_deterministic_time = time_limit
    return solver
