"""Shared scheduler helpers: the CP-SAT solver setup both phases use, the solve
a Ctrl+C press stops and the hold that lets the output files finish."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from athc.scheduler import cpu
from athc.scheduler.schedulers import utils
from athc.scheduler.schedulers.utils import (
    CTRL_C_EVENT,
    make_solver,
    resolve_workers,
    run_solver,
    write_hold,
)

CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2


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
    # CP-SAT's own Ctrl+C handling is off; run_solver stops the search.
    assert params.catch_sigint_signal is False


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


# --- Ctrl+C: the solve helper and the write hold ------------------------------

Routine = Callable[[int], bool]
STATUS = "OPTIMAL"  # what the stub solver's solve returns


@dataclass
class FakeKernel32:
    """kernel32 in miniature: SetConsoleCtrlHandler records each call and keeps
    the installed routines, latest last."""

    calls: list[tuple[Routine, bool]] = field(default_factory=list)
    installed: list[Routine] = field(default_factory=list)

    def SetConsoleCtrlHandler(self, routine: Routine, add: bool) -> bool:
        self.calls.append((routine, add))
        if add:
            self.installed.append(routine)
        else:
            self.installed.remove(routine)
        return True


@pytest.fixture
def kernel32(monkeypatch: pytest.MonkeyPatch) -> FakeKernel32:
    fake = FakeKernel32()
    monkeypatch.setattr(utils, "_kernel32", fake)
    return fake


@dataclass
class _Solver:
    """A stub solver: `solve` records the handler installed while it runs and
    calls `during` with it; `stop_search` counts its calls."""

    kernel32: FakeKernel32
    during: Callable[[Routine], object] = lambda _: None
    seen: list[Routine] = field(default_factory=list)
    stopped: int = 0
    finished: bool = False

    def solve(self, model: object) -> str:
        routine = self.kernel32.installed[-1]
        self.seen.append(routine)
        self.during(routine)
        self.finished = True
        return STATUS

    def stop_search(self) -> None:
        self.stopped += 1


def test_run_solver_returns_the_status_and_removes_its_handler(
    kernel32: FakeKernel32,
) -> None:
    solver = _Solver(kernel32)
    assert run_solver(solver, object()) == STATUS  # type: ignore[arg-type]
    (routine,) = solver.seen  # installed while the solve ran
    assert kernel32.calls == [(routine, True), (routine, False)]
    assert kernel32.installed == []
    assert solver.stopped == 0


def test_ctrl_c_during_the_solve_stops_the_search_then_interrupts(
    kernel32: FakeKernel32,
) -> None:
    answers: list[bool] = []
    solver = _Solver(
        kernel32, during=lambda routine: answers.append(routine(CTRL_C_EVENT))
    )
    with pytest.raises(KeyboardInterrupt):
        run_solver(solver, object())  # type: ignore[arg-type]
    assert answers == [True]  # handled: Python's own handler never hears it
    assert solver.stopped == 1
    assert solver.finished  # the interrupt came once the solve returned
    assert kernel32.installed == []


@pytest.mark.parametrize("event", [CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT])
def test_other_console_events_pass_on(kernel32: FakeKernel32, event: int) -> None:
    answers: list[bool] = []
    solver = _Solver(kernel32, during=lambda routine: answers.append(routine(event)))
    assert run_solver(solver, object()) == STATUS  # type: ignore[arg-type]
    assert answers == [False]
    assert solver.stopped == 0


def test_write_hold_without_a_press_removes_its_handler(kernel32: FakeKernel32) -> None:
    with write_hold():
        assert len(kernel32.installed) == 1
    assert kernel32.installed == []


def test_ctrl_c_in_the_write_hold_interrupts_on_the_way_out(
    kernel32: FakeKernel32,
) -> None:
    answers: list[bool] = []
    after_the_press: list[str] = []
    with pytest.raises(KeyboardInterrupt), write_hold():
        (routine,) = kernel32.installed
        answers.append(routine(CTRL_C_EVENT))
        after_the_press.append("the rest of the block ran")
    assert answers == [True]
    assert after_the_press  # held until the block ended
    assert kernel32.installed == []
