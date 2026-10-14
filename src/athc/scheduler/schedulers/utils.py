"""Shared scheduler helpers used by both phases: the CP-SAT solver setup, the
solve a Ctrl+C press stops, and the hold that lets the output files finish."""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from ctypes import wintypes
from typing import TYPE_CHECKING

from athc.scheduler import cpu
from athc.scheduler.config import SolverWorkers

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

# The console event a Ctrl+C press raises. Ctrl+Break, closing the console,
# logoff and shutdown are other events, left to the handlers after these.
CTRL_C_EVENT = 0

# BOOL WINAPI HandlerRoutine(DWORD dwCtrlType), for SetConsoleCtrlHandler.
HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.SetConsoleCtrlHandler.argtypes = [HandlerRoutine, wintypes.BOOL]
_kernel32.SetConsoleCtrlHandler.restype = wintypes.BOOL


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

    CP-SAT's own Ctrl+C handling is off: it keeps its handler on the solving
    thread, and Windows runs the Ctrl+C handler on a thread of its own, so a
    press would end the process at once with no line. `run_solver` stops the
    search instead.
    """
    # Imported here so the CLI loads without the solver; a missing ortools is
    # then its own line once the league files are read.
    from ortools.sat.python import cp_model

    count = resolve_workers(workers)
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    solver.parameters.num_search_workers = count
    solver.parameters.interleave_search = True
    solver.parameters.interleave_batch_size = count
    solver.parameters.max_deterministic_time = time_limit
    solver.parameters.catch_sigint_signal = False
    return solver


def run_solver(
    solver: cp_model.CpSolver, model: cp_model.CpModel
) -> cp_model.CpSolverStatus:
    """`solver.solve(model)`, stopped by Ctrl+C: a press ends the search at
    once, and KeyboardInterrupt follows when the solve returns."""
    with _on_ctrl_c(solver.stop_search) as pressed:
        status = solver.solve(model)
    if pressed.is_set():
        raise KeyboardInterrupt
    return status


@contextmanager
def write_hold() -> Iterator[None]:
    """Hold a Ctrl+C press until the block ends, so files being written are
    all written; KeyboardInterrupt follows on the way out."""
    with _on_ctrl_c(lambda: None) as pressed:
        yield
    if pressed.is_set():
        raise KeyboardInterrupt


@contextmanager
def _on_ctrl_c(act: Callable[[], None]) -> Iterator[threading.Event]:
    """Inside the block, a Ctrl+C press sets the event and calls `act` in
    place of Python's own handler; the console's other events pass on."""
    pressed = threading.Event()

    def handle(event: int) -> bool:
        if event != CTRL_C_EVENT:
            return False
        pressed.set()
        act()
        return True

    # Kept referenced for as long as Windows may call it.
    routine = HandlerRoutine(handle)
    _set_handler(routine, add=True)
    try:
        yield pressed
    finally:
        _set_handler(routine, add=False)


def _set_handler(routine: object, *, add: bool) -> None:
    if not _kernel32.SetConsoleCtrlHandler(routine, add):
        raise ctypes.WinError(ctypes.get_last_error())
