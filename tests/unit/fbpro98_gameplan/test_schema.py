"""Tests for athc.fbpro98_gameplan.schema — binary layout constants (guards drift)."""

from athc.fbpro98_gameplan import schema


def test_struct_sizes():
    assert schema.G95_HEADER.size == 8
    assert schema.G95_AUDIBLE.size == 4
    assert schema.G95_OFFSETS_TABLE.size == 172  # 86 u16 slots
    assert schema.G95_PLAY_HEADER.size == 4
    assert schema.G95_STOCK_PLAY_BODY.size == 14
    assert schema.J95_HEADER.size == 8
    assert schema.J95_PLAN_DATA.size == 7
    assert schema.S98_HEADER.size == 8


def test_block_ids():
    assert schema.ID_G95 == b"G95:"
    assert schema.ID_J95 == b"J95:"
    assert schema.ID_S98 == b"S98:"


def test_constants():
    assert schema.DEFAULT_AUDIBLE == b"\x00\x01\x02\x03"
    assert schema.S98_EXPECTED_DATA == b"STOCK98.MAP\x00"
