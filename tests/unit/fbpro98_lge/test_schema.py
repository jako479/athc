"""Tests for athc.fbpro98_lge.schema — binary layout constants (guards drift)."""

from athc.fbpro98_lge import schema


def test_chunk_header_and_ids():
    assert schema.CHUNK_HEADER.format == "<4sI"
    assert schema.CHUNK_HEADER.size == 8
    assert schema.ID_L03 == b"L03:"
    assert schema.ID_C03 == b"C03:"
    assert schema.ID_D03 == b"D03:"
    assert schema.ID_T03 == b"T03:"
    assert schema.ID_R03 == b"R03:"
    assert schema.ID_S03 == b"S03:"


def test_chunk_sizes():
    assert schema.LEAGUE_BASE_SIZE == 89
    assert schema.CONFERENCE_BASE_SIZE == 29
    assert schema.DIVISION_BASE_SIZE == 29
    assert schema.TEAM_CHUNK_SIZE == 171
    assert schema.ROSTER_CHUNK_SIZE == 325


def test_field_offsets():
    assert schema.LEAGUE_CONFERENCES_OFFSET == 0x01
    assert schema.CONFERENCE_DIVISIONS_OFFSET == 0x02
    assert schema.CONFERENCE_NAME_OFFSET == 0x04
    assert schema.DIVISION_TEAMS_OFFSET == 0x03
    assert schema.DIVISION_NAME_OFFSET == 0x04
    assert schema.NAME_SIZE == 25
    assert schema.TEAM_NAME_OFFSET == 0x36
    assert schema.NICKNAME_OFFSET == 0x47
    assert schema.TEAM_TEXT_SIZE == 17


def test_mask_factor():
    assert schema.MASK_FACTOR == 0x69


def test_schedule_layout():
    assert schema.SCHEDULE_HEADER_SIZE == 3
    assert schema.SCHEDULE_REGULAR_WEEKS_OFFSET == 0x00
    assert schema.SCHEDULE_PLAYOFF_ROUNDS_OFFSET == 0x01
    assert schema.GAME.format == "6B"
    assert schema.GAME_PLAYED == 0
