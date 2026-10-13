"""Parse FbPro98 .ply play files into PlayFile objects.

Decodes the P95 block: header, 11 player offsets, play metadata
(play_category / special_category / user_category), and per-player records
(header, then the pre-snap and after-snap logic boxes).
"""

from __future__ import annotations

import struct
from os import PathLike
from pathlib import Path

from athc.errors import FileFormatError
from athc.fbpro98_play.model import (
    UNKNOWN_CATEGORY,
    Command,
    LogicBox,
    PlayerHeader,
    PlayerLogic,
    PlayFile,
)
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
    PLY_PLAYER_OFFSETS_OFFSET,
)

StrPath = str | PathLike[str]

# A damaged file gets one message, whatever broke: the size, a record, a count.
# Only a wrong block ID and an unknown category say more.
_INVALID_PLAY_FILE = "The play file is invalid or corrupted."


class InvalidPlayFileError(FileFormatError):
    """Raised when a `.ply` file is structurally invalid or has an unrecognized
    play category."""


def read_play(path: StrPath) -> PlayFile:
    """Read and parse a .ply play file from disk.

    Args:
        path: Filesystem path to the .ply file.

    Returns:
        Parsed PlayFile.

    Raises:
        InvalidPlayFileError: If the file is not a valid .ply (bad block ID,
            size mismatch, or truncated structure) or its play category is
            unrecognized.
        OSError: If the file cannot be opened or read (subclasses include
            FileNotFoundError, PermissionError, IsADirectoryError).
    """
    file_path = Path(path)
    play = parse_play(file_path.read_bytes(), file_path)
    if play.category is UNKNOWN_CATEGORY:
        raise InvalidPlayFileError(
            "Unrecognized play category "
            f"(play_category=0x{play.play_category:02X}, "
            f"special_category=0x{play.special_category:02X}, "
            f"user_category=0x{play.user_category:02X}).",
            file_path,
        )
    return play


def parse_play(buffer: bytes, path: StrPath = "<buffer>") -> PlayFile:
    """Parse a .ply play from raw bytes.

    Args:
        buffer: Full contents of a .ply file.
        path: Path used only in error messages and on the returned PlayFile's
            file_path attribute. Defaults to "<buffer>" when parsing data that
            did not come from disk.

    Returns:
        Parsed PlayFile.

    Raises:
        InvalidPlayFileError: If the buffer does not contain a valid P95 block.
            Triggered by a wrong block ID, mismatched size field, a buffer
            too short to contain the metadata or any player header, or a
            player record too short for its logic boxes.
    """
    file_path = Path(path)

    if len(buffer) < PLY_HEADER.size:
        raise InvalidPlayFileError(_INVALID_PLAY_FILE, file_path)

    block_id, stream_length = PLY_HEADER.unpack_from(buffer, 0)
    if block_id != ID_P95:
        block_id_str = block_id.decode("ASCII", errors="replace")
        raise InvalidPlayFileError(
            f"Invalid header '{block_id_str}' at 0x0.", file_path
        )

    if len(buffer) != PLY_HEADER.size + stream_length:
        raise InvalidPlayFileError(_INVALID_PLAY_FILE, file_path)

    if len(buffer) < PLY_METADATA_OFFSET + PLY_METADATA.size:
        raise InvalidPlayFileError(_INVALID_PLAY_FILE, file_path)

    player_offsets = PLY_PLAYER_OFFSETS.unpack_from(buffer, PLY_PLAYER_OFFSETS_OFFSET)

    play_category, special_category, user_category = PLY_METADATA.unpack_from(
        buffer,
        PLY_METADATA_OFFSET,
    )

    player_headers = tuple(
        _parse_player_header(buffer, offset, file_path) for offset in player_offsets
    )
    # Records sit back to back in slot order; the last ends at the end of the file.
    starts = [PLY_PLAYER_DATA_BASE + offset for offset in player_offsets]
    ends = [*starts[1:], len(buffer)]
    player_logic = tuple(
        _parse_player_logic(buffer, start, end, file_path)
        for start, end in zip(starts, ends, strict=True)
    )

    return PlayFile(
        file_path,
        stream_length,
        play_category,
        special_category,
        user_category,
        player_offsets,
        player_headers,
        player_logic,
    )


def _parse_player_header(buffer: bytes, offset: int, path: Path) -> PlayerHeader:
    absolute_offset = PLY_PLAYER_DATA_BASE + offset
    if len(buffer) < absolute_offset + PLY_PLAYER_HEADER.size:
        raise InvalidPlayFileError(_INVALID_PLAY_FILE, path)

    rank, player_type, position = PLY_PLAYER_HEADER.unpack_from(buffer, absolute_offset)
    return PlayerHeader(
        offset=offset,
        rank=rank,
        player_type=player_type,
        position=position,
    )


def _parse_player_logic(buffer: bytes, start: int, end: int, path: Path) -> PlayerLogic:
    """The two box lists after the header of the record at `start`, read within
    the record so a bad count can't run into the next one."""
    record = buffer[start + PLY_PLAYER_HEADER.size : end]
    try:
        pre_snap, offset = _parse_boxes(record, 0)
        after_snap, _ = _parse_boxes(record, offset)
    except struct.error:
        raise InvalidPlayFileError(_INVALID_PLAY_FILE, path) from None
    return PlayerLogic(pre_snap, after_snap)


def _parse_boxes(record: bytes, offset: int) -> tuple[tuple[LogicBox, ...], int]:
    """A box list starting at `offset` and the offset just past it."""
    (count,) = PLY_BOX_COUNT.unpack_from(record, offset)
    offset += PLY_BOX_COUNT.size
    boxes: list[LogicBox] = []
    for _ in range(count):
        x, y, command_count = PLY_BOX.unpack_from(record, offset)
        offset += PLY_BOX.size
        commands: list[Command] = []
        for _ in range(command_count):
            code, argument_count = PLY_COMMAND.unpack_from(record, offset)
            offset += PLY_COMMAND.size
            arguments: list[int] = []
            for _ in range(argument_count):
                (argument,) = PLY_ARGUMENT.unpack_from(record, offset)
                offset += PLY_ARGUMENT.size
                arguments.append(argument)
            commands.append(Command(code, tuple(arguments)))
        boxes.append(LogicBox(x, y, tuple(commands)))
    return tuple(boxes), offset
