"""Parse FbPro98 .ply play files into PlayFile objects.

Decodes the P95 block: header, 11 player offsets, play metadata
(play_category / special_category / user_category), and per-player headers.
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from athc.fbpro98_play.model import PlayerHeader, PlayFile
from athc.fbpro98_play.schema import (
    ID_P95,
    PLY_HEADER,
    PLY_METADATA,
    PLY_METADATA_OFFSET,
    PLY_PLAYER_DATA_BASE,
    PLY_PLAYER_HEADER,
    PLY_PLAYER_OFFSETS,
    PLY_PLAYER_OFFSETS_OFFSET,
)

StrPath = str | PathLike[str]


class InvalidPlayFileError(ValueError):
    """Raised when a `.ply` file is structurally invalid."""


def read_play(path: StrPath) -> PlayFile:
    """Read and parse a .ply play file from disk.

    Args:
        path: Filesystem path to the .ply file.

    Returns:
        Parsed PlayFile.

    Raises:
        InvalidPlayFileError: If the file is not a valid .ply (bad block ID,
            size mismatch, or truncated structure).
        OSError: If the file cannot be opened or read (subclasses include
            FileNotFoundError, PermissionError, IsADirectoryError).
    """
    file_path = Path(path)
    return parse_play(file_path.read_bytes(), file_path)


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
            Triggered by a wrong block ID, mismatched size field, or a buffer
            too short to contain the metadata or any player header.
    """
    file_path = Path(path)

    if len(buffer) < PLY_HEADER.size:
        raise InvalidPlayFileError(
            f"File too small to contain P95 header in {file_path}"
        )

    block_id, stream_length = PLY_HEADER.unpack_from(buffer, 0)
    if block_id != ID_P95:
        block_id_str = block_id.decode("ASCII", errors="replace")
        raise InvalidPlayFileError(
            f"Invalid header '{block_id_str}' at 0x0 in {file_path}"
        )

    if len(buffer) != PLY_HEADER.size + stream_length:
        expected = PLY_HEADER.size + stream_length
        raise InvalidPlayFileError(
            f"File size {len(buffer)} does not match P95 block size "
            f"{expected} in {file_path}"
        )

    if len(buffer) < PLY_METADATA_OFFSET + PLY_METADATA.size:
        raise InvalidPlayFileError(
            f"File too small to contain play metadata in {file_path}"
        )

    player_offsets = PLY_PLAYER_OFFSETS.unpack_from(buffer, PLY_PLAYER_OFFSETS_OFFSET)

    play_category, special_category, user_category = PLY_METADATA.unpack_from(
        buffer,
        PLY_METADATA_OFFSET,
    )

    player_headers = tuple(
        _parse_player_header(buffer, offset, file_path) for offset in player_offsets
    )

    return PlayFile(
        file_path,
        stream_length,
        play_category,
        special_category,
        user_category,
        player_offsets,
        player_headers,
    )


def _parse_player_header(buffer: bytes, offset: int, path: Path) -> PlayerHeader:
    absolute_offset = PLY_PLAYER_DATA_BASE + offset
    if len(buffer) < absolute_offset + PLY_PLAYER_HEADER.size:
        raise InvalidPlayFileError(
            f"File too small to contain player header at "
            f"0x{absolute_offset:02X} in {path}"
        )

    rank, player_type, position = PLY_PLAYER_HEADER.unpack_from(buffer, absolute_offset)
    return PlayerHeader(
        offset=offset,
        rank=rank,
        player_type=player_type,
        position=position,
    )
