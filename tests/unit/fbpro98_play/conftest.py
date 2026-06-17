"""Shared fixtures for fbpro98_play tests.

`make_ply` builds a valid .ply byte buffer; override one field to produce the
malformed buffers the reader error tests need (no real file can be "truncated
at exactly byte N" or carry a bad magic).
"""

from __future__ import annotations

import pytest

from athc.fbpro98_play.schema import (
    ID_P95,
    PLY_HEADER,
    PLY_METADATA,
    PLY_METADATA_OFFSET,
    PLY_PLAYER_DATA_BASE,
    PLY_PLAYER_HEADER,
    PLY_PLAYER_OFFSETS,
)

_DEFAULT_PLAYER_HEADER = (1, 1, 0x20)  # rank, type, position
_RECORDS_FILE_START = PLY_METADATA_OFFSET + PLY_METADATA.size  # 0x21


def build_ply(
    *,
    block_id: bytes = ID_P95,
    play_category: int = 0x01,
    special_category: int = 0x00,
    user_category: int = 0x01,
    player_headers: tuple[tuple[int, int, int], ...] | None = None,
    player_offsets: tuple[int, ...] | None = None,
    stream_length: int | None = None,
) -> bytes:
    """Build a .ply buffer. Valid by default; 11 minimal player records sit
    immediately after the metadata, and the offsets point at them."""
    headers = (
        list(player_headers)
        if player_headers is not None
        else [_DEFAULT_PLAYER_HEADER] * 11
    )
    records = b"".join(PLY_PLAYER_HEADER.pack(*h) for h in headers)
    default_offsets = tuple(
        (_RECORDS_FILE_START - PLY_PLAYER_DATA_BASE) + i * PLY_PLAYER_HEADER.size
        for i in range(11)
    )
    offsets = tuple(player_offsets) if player_offsets is not None else default_offsets
    body = (
        PLY_PLAYER_OFFSETS.pack(*offsets)
        + PLY_METADATA.pack(play_category, special_category, user_category)
        + records
    )
    size = len(body) if stream_length is None else stream_length
    return PLY_HEADER.pack(block_id, size) + body


@pytest.fixture
def make_ply():
    """Factory that builds a .ply byte buffer (see build_ply)."""
    return build_ply
