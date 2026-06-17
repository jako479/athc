"""Tests for athc.fbpro98_profile.schema — binary layout constants (guards drift)."""

from athc.fbpro98_profile import schema


def test_struct_sizes():
    assert schema.F95_HEADER.size == 8
    assert schema.F95_SUBSTITUTIONS.size == 32  # 16 u16 (8 out/in pairs)
    assert schema.F95_CATEGORY_WEIGHTS.size == 6
    assert schema.F95_FIELD_GOAL_RANGE.size == 1
    assert schema.F95_USE_AUDIBLES.size == 4
    assert schema.I95_HEADER.size == 8
    assert schema.I95_DATA.size == 10


def test_block_ids():
    assert schema.ID_F95 == b"F95:"
    assert schema.ID_I95 == b"I95:"


def test_data_sizes_and_masks():
    assert schema.F95_DATA_SIZE == 0x3C9D
    assert schema.I95_DATA_SIZE == 0x0A
    assert schema.F95_STOCK_DATA_SIZES == frozenset({0x3F69, 0x4509})
    assert schema.STOP_CLOCK_BIT == 0x80
    assert schema.WEIGHT_MASK == 0x7F
