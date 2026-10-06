"""Tests for athc.fbpro98_lg2.schema — binary layout constants (guards drift)."""

from athc.fbpro98_lg2 import schema


def test_field_and_record_sizes():
    assert schema.FOLDER_SIZE == 0x105
    assert schema.FILENAME_SIZE == 0x106
    assert schema.FILE_ENTRY_SIZE == 0x20B
    assert schema.FILES_PER_TEAM == 8
    assert schema.TEAM_TRAILER_SIZE == 9
    assert schema.TEAM_RECORD_SIZE == 0x1061


def test_stock_signatures():
    assert schema.MODERN_STOCK_FOLDER == b"STOCK\x00A\\FBPRO97\\STOCK\x00"
    assert schema.OLD_STOCK_FOLDER == b"\x00"
