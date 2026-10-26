"""Shared fixtures for fbpro98_pyr tests.

`build_pyr` codes plain records from `build_record` with a chosen table into
a valid file behind a `build_header` header; override a field, patch a byte
or shrink the file to get the malformed and edge buffers no real file holds.
Offsets and sizes are the spec's literals (docs/formats/pyr.md), not the
schema's, so the reader tests pin the schema.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

import pytest

HEADER_SIZE = 60
RECORD_SIZE = 60
FIRST_ID = 100

# The tests' own coding table, plain -> disk: a bijection with no fixed point
# (167p + 29 = p mod 256 has no solution), so no plain byte is its own code.
TABLE = bytes((167 * plain + 29) & 0xFF for plain in range(256))

PLACEHOLDER_RATINGS = (1,) * 8  # "No One" players have every rating 1


def build_record(
    player_id: int,
    *,
    first: bytes = b"No",
    last: bytes = b"One",
    potential: Sequence[int] = PLACEHOLDER_RATINGS,
    injury: tuple[int, int, int] = (0, 0, 0),
    group: int = 0,
    position: int = 0,
    actual: Sequence[int] = PLACEHOLDER_RATINGS,
    years: int = 0,
    height: int = 0,
    weight: int = 0,
    unknown: bytes = bytes(6),
) -> bytes:
    """One plain 60-byte player record (pyr.md section 4); names NUL-padded."""
    assert len(first) <= 13 and len(last) <= 13
    return struct.pack(
        "<H13s13s8B4sBB8BBBH6s",
        player_id,
        first,
        last,
        *potential,
        struct.pack("<HBB", *injury),
        group,
        position,
        *actual,
        years,
        height,
        weight,
        unknown,
    )


def build_header(
    *, key: int = 0xCE5F, name: bytes = b"", unknown: bytes = bytes(6)
) -> bytes:
    """The 60-byte header (pyr.md section 2): key, name and the unknown bytes,
    zeros between."""
    assert len(name) <= 13 and len(unknown) == 6
    return struct.pack("<H13x13s26x6s", key, name, unknown)


def build_pyr(
    records: Sequence[bytes] = (),
    *,
    header: bytes | None = None,
    table: bytes = TABLE,
    pad_to: int = 256,
) -> bytes:
    """A whole file: the header, then the records coded with `table`.
    Placeholder players with the next ids fill the file up to `pad_to`
    records, so 256 or more make the ids reveal the whole table."""
    records = list(records)
    while len(records) < pad_to:
        # Past the last 16-bit id (a file with too many records) the id wraps;
        # the reader must stop at the count before it looks.
        records.append(build_record((FIRST_ID + len(records)) & 0xFFFF))
    body = b"".join(records)
    return (build_header() if header is None else header) + body.translate(table)


@pytest.fixture
def make_record():
    """Factory for one plain record (see build_record)."""
    return build_record


@pytest.fixture
def make_header():
    """Factory for the header (see build_header)."""
    return build_header


@pytest.fixture
def make_pyr():
    """Factory for a whole coded file (see build_pyr)."""
    return build_pyr
