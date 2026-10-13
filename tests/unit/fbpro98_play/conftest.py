"""Shared fixtures for fbpro98_play tests.

`make_ply` builds a valid .ply byte buffer; override one field to produce the
malformed buffers the reader error tests need (no real file can be "truncated
at exactly byte N" or carry a bad magic). `build_record` encodes one player
record, logic boxes included, for buffers whose players need logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import accumulate

import pytest

from athc.fbpro98_play import LogicBox
from athc.fbpro98_play.schema import (
    ID_P95,
    PLY_ARGUMENT,
    PLY_BOX,
    PLY_BOX_COUNT,
    PLY_COMMAND,
    PLY_HEADER,
    PLY_METADATA,
    PLY_METADATA_OFFSET,
    PLY_PLAYER_DATA_BASE,
    PLY_PLAYER_HEADER,
    PLY_PLAYER_OFFSETS,
)

_DEFAULT_PLAYER_HEADER = (1, 1, 0x20)  # rank, type, position
_RECORDS_FILE_START = PLY_METADATA_OFFSET + PLY_METADATA.size  # 0x21


def _encode_boxes(boxes: Sequence[LogicBox]) -> bytes:
    out = PLY_BOX_COUNT.pack(len(boxes))
    for box in boxes:
        out += PLY_BOX.pack(box.x, box.y, len(box.commands))
        for command in box.commands:
            out += PLY_COMMAND.pack(command.code, len(command.arguments))
            out += b"".join(PLY_ARGUMENT.pack(a) for a in command.arguments)
    return out


def build_record(
    position: int,
    *,
    rank: int = 1,
    player_type: int = 0,
    pre_snap: Sequence[LogicBox] = (),
    after_snap: Sequence[LogicBox] = (),
) -> bytes:
    """One player record: its header, then its pre-snap and after-snap box
    lists (empty lists by default)."""
    return (
        PLY_PLAYER_HEADER.pack(rank, player_type, position)
        + _encode_boxes(pre_snap)
        + _encode_boxes(after_snap)
    )


def build_ply(
    *,
    block_id: bytes = ID_P95,
    play_category: int = 0x01,
    special_category: int = 0x00,
    user_category: int = 0x01,
    player_headers: tuple[tuple[int, int, int], ...] | None = None,
    player_records: Sequence[bytes] | None = None,
    player_offsets: tuple[int, ...] | None = None,
    stream_length: int | None = None,
) -> bytes:
    """Build a .ply buffer. Valid by default; 11 minimal player records (a
    header and two empty box lists each) sit immediately after the metadata,
    and the offsets point at them. `player_records` replaces those records with
    whole encoded ones."""
    if player_records is None:
        headers = (
            list(player_headers)
            if player_headers is not None
            else [_DEFAULT_PLAYER_HEADER] * 11
        )
        player_records = [
            build_record(position, rank=rank, player_type=player_type)
            for rank, player_type, position in headers
        ]
    records = b"".join(player_records)
    default_offsets = tuple(
        accumulate(
            (len(r) for r in player_records[:-1]),
            initial=_RECORDS_FILE_START - PLY_PLAYER_DATA_BASE,
        )
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
