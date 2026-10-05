"""This machine's CPU: its name and its fast threads, for solver_workers = "auto"."""

from __future__ import annotations

import os

from athc.scheduler import cpu


def _core(efficiency_class: int, threads: int) -> bytes:
    # One RelationProcessorCore record of GetLogicalProcessorInformationEx, in the
    # 64-bit layout: header, PROCESSOR_RELATIONSHIP, then one GROUP_AFFINITY.
    size = 48
    smt_flag = 1 if threads > 1 else 0
    mask = (1 << threads) - 1
    return (
        (0).to_bytes(4, "little")  # Relationship = RelationProcessorCore
        + size.to_bytes(4, "little")
        + bytes([smt_flag, efficiency_class])
        + bytes(20)  # RelativePerformance, RelativeEfficiency, Reserved
        + (1).to_bytes(2, "little")  # GroupCount, ending at the 8-byte-aligned mask
        + mask.to_bytes(8, "little")
        + bytes(8)  # Group, Reserved
    )


def test_hybrid_cpu_counts_only_the_performance_core_threads() -> None:
    # An i5-14600KF: 6 two-thread P-cores and 8 one-thread E-cores.
    raw = _core(1, 2) * 6 + _core(0, 1) * 8
    assert cpu.count_fast_threads(raw) == 12


def test_uniform_cpu_counts_every_thread() -> None:
    # A Ryzen 7 9700X: 8 identical two-thread cores, all efficiency class 0.
    assert cpu.count_fast_threads(_core(0, 2) * 8) == 16


def test_auto_workers_leave_two_fast_threads_free() -> None:
    assert cpu.workers_for(12) == 10
    assert cpu.workers_for(16) == 14


def test_auto_workers_never_drop_below_one() -> None:
    assert cpu.workers_for(3) == 1  # the last count that leaves two free
    assert cpu.workers_for(2) == 1  # one past it: still one worker


def test_this_machine_reports_its_fast_threads() -> None:
    fast = cpu.fast_thread_count()
    assert 1 <= fast <= (os.cpu_count() or fast)
    assert cpu.auto_workers() == cpu.workers_for(fast)


def test_this_machine_reports_a_cpu_name() -> None:
    assert cpu.cpu_name().strip()
