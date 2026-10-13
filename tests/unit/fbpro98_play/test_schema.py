"""Tests for athc.fbpro98_play.schema — binary layout constants (guards drift)."""

from athc.fbpro98_play import schema


def test_struct_sizes():
    assert schema.PLY_HEADER.size == 8
    assert schema.PLY_PLAYER_OFFSETS.size == 22
    assert schema.PLY_METADATA.size == 3
    assert schema.PLY_PLAYER_HEADER.size == 4
    assert schema.PLY_BOX_COUNT.size == 2
    assert schema.PLY_BOX.size == 6
    assert schema.PLY_COMMAND.size == 2
    assert schema.PLY_ARGUMENT.size == 2


def test_derived_offsets():
    assert schema.PLY_PLAYER_OFFSETS_OFFSET == 8
    assert schema.PLY_METADATA_OFFSET == 0x1E
    assert schema.PLY_PLAYER_DATA_BASE == 8


def test_block_id():
    assert schema.ID_P95 == b"P95:"


def test_codes():
    """The command and position codes the play attributes read (ply.md 2.5, 4.1)."""
    assert (
        schema.COMMAND_MOVE_TO,
        schema.COMMAND_TIMED_PASS,
        schema.COMMAND_CHECK_RECEIVERS,
        schema.COMMAND_RUN,
    ) == (0x02, 0x06, 0x08, 0x0C)
    assert (
        schema.POSITION_G,
        schema.POSITION_T,
        schema.POSITION_C,
        schema.POSITION_QB,
        schema.POSITION_DT,
        schema.POSITION_DE,
    ) == (0x0010, 0x0011, 0x0012, 0x0020, 0x0101, 0x0102)
