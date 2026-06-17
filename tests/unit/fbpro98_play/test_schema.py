"""Tests for athc.fbpro98_play.schema — binary layout constants (guards drift)."""

from athc.fbpro98_play import schema


def test_struct_sizes():
    assert schema.PLY_HEADER.size == 8
    assert schema.PLY_PLAYER_OFFSETS.size == 22
    assert schema.PLY_METADATA.size == 3
    assert schema.PLY_PLAYER_HEADER.size == 4


def test_derived_offsets():
    assert schema.PLY_PLAYER_OFFSETS_OFFSET == 8
    assert schema.PLY_METADATA_OFFSET == 0x1E
    assert schema.PLY_PLAYER_DATA_BASE == 8


def test_block_id():
    assert schema.ID_P95 == b"P95:"
