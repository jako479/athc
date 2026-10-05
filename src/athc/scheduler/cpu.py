"""This machine's CPU: its name, and how many fast threads the solver can use.

Windows-only, like the rest of athc. "Fast" threads are those on the cores of
the highest efficiency class: the P-cores of an Intel hybrid CPU, or every core
of a CPU whose cores are all alike (such as most AMD Ryzen chips).
"""

from __future__ import annotations

import ctypes
import struct
import winreg
from ctypes import wintypes

# Fast threads left free for Windows and other programs under "auto".
RESERVED_THREADS = 2

_RELATION_PROCESSOR_CORE = 0
_CPU_KEY = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"

# Offsets within one SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX record (64-bit):
# Relationship and Size head every record; a core's PROCESSOR_RELATIONSHIP
# follows, with its one GROUP_AFFINITY mask 8-byte aligned at offset 32.
_EFFICIENCY_CLASS = 9
_THREAD_MASK = 32


def cpu_name() -> str:
    """The CPU's name as Windows shows it, e.g. 'Intel(R) Core(TM) i5-14600KF'."""
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _CPU_KEY) as key:
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
    return str(name).strip()


def auto_workers() -> int:
    """The solver worker count "auto" stands for on this machine."""
    return workers_for(fast_thread_count())


def workers_for(fast_threads: int) -> int:
    """Leave RESERVED_THREADS fast threads free, but always use at least one."""
    return max(1, fast_threads - RESERVED_THREADS)


def fast_thread_count() -> int:
    """Threads on this machine's highest-efficiency-class cores."""
    query = ctypes.WinDLL(
        "kernel32", use_last_error=True
    ).GetLogicalProcessorInformationEx
    query.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
    query.restype = wintypes.BOOL
    length = wintypes.DWORD(0)
    query(_RELATION_PROCESSOR_CORE, None, ctypes.byref(length))  # sizes the buffer
    buffer = ctypes.create_string_buffer(length.value)
    if not query(_RELATION_PROCESSOR_CORE, buffer, ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    return count_fast_threads(buffer.raw[: length.value])


def count_fast_threads(raw: bytes) -> int:
    """Threads on the highest-efficiency-class cores in `raw`, the core records
    GetLogicalProcessorInformationEx returns."""
    threads_by_class: dict[int, int] = {}
    offset = 0
    while offset < len(raw):
        relationship, size = struct.unpack_from("<II", raw, offset)
        if relationship == _RELATION_PROCESSOR_CORE:
            efficiency_class = raw[offset + _EFFICIENCY_CLASS]
            (mask,) = struct.unpack_from("<Q", raw, offset + _THREAD_MASK)
            threads_by_class[efficiency_class] = (
                threads_by_class.get(efficiency_class, 0) + mask.bit_count()
            )
        offset += size
    return threads_by_class[max(threads_by_class)]
