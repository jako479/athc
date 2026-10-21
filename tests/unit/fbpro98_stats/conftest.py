"""Shared fixtures for fbpro98_stats tests.

`make_dat` builds a valid .dat from slots made by `make_record` and
`make_deleted`; override a counted header field to get the malformed buffers
no real file holds. Offsets and sizes are the spec's literals
(docs/formats/stats.md), not the schema's, so the reader tests pin the schema.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

import pytest

HEADER = 140
SLOT = 20


def build_record(type_: int, id_: int, values: Sequence[int] = ()) -> bytes:
    """One 20-byte record; values padded with zeros to eight, each stored as
    its low 16 bits, so -1 and 0xFFFF are the same bytes."""
    assert len(values) <= 8
    padded = [*values, *[0] * (8 - len(values))]
    return struct.pack("<HH8H", type_, id_, *(value & 0xFFFF for value in padded))


def build_deleted(next_offset: int = 0) -> bytes:
    """One deleted slot: the 0xFF mark, the next deleted slot's offset, then
    15 leftover bytes."""
    return b"\xff" + struct.pack("<I", next_offset) + bytes(15)


def build_dat(
    slots: Sequence[bytes] = (),
    *,
    file_end: int | None = None,
    slots_end: int | None = None,
    records: int | None = None,
    record_size: int = SLOT,
    tail: bytes = b"",
) -> bytes:
    """A .dat: the 140-byte header (docs/formats/stats.md section 2), the
    slots, then `tail`. File end, slots end and the record count are computed
    from the slots unless given."""
    body = b"".join(slots)
    size = HEADER + len(body) + len(tail)
    live = sum(slot[0] != 0xFF for slot in slots)
    deleted = [HEADER + SLOT * n for n, slot in enumerate(slots) if slot[0] == 0xFF]
    header = bytearray(HEADER)
    struct.pack_into("<I", header, 0x00, size - 1 if file_end is None else file_end)
    struct.pack_into("<I", header, 0x04, deleted[0] if deleted else 0)
    struct.pack_into(
        "<I", header, 0x08, HEADER - 1 + len(body) if slots_end is None else slots_end
    )
    struct.pack_into("<I", header, 0x14, live)
    struct.pack_into("<I", header, 0x18, live if records is None else records)
    struct.pack_into("<H", header, 0x28, 0x0081)
    struct.pack_into("<H", header, 0x2C, record_size)
    struct.pack_into("<H", header, 0x2E, 4096)
    struct.pack_into("<H", header, 0x30, 1)
    struct.pack_into("<H", header, 0x3A, 1)
    struct.pack_into("<H", header, 0x3C, 512)
    struct.pack_into("<H", header, 0x3E, 1)
    header[0x60] = 0xFF
    header[0x64] = 1
    header[0x80:0x8C] = b"\xff" * 12
    return bytes(header) + body + tail


@pytest.fixture
def make_record():
    """Factory that builds one record (see build_record)."""
    return build_record


@pytest.fixture
def make_deleted():
    """Factory that builds one deleted slot (see build_deleted)."""
    return build_deleted


@pytest.fixture
def make_dat():
    """Factory that builds a whole .dat (see build_dat)."""
    return build_dat
