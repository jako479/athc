"""Parse FbPro98 .pyr player files into PyrFile objects. See docs/formats/pyr.md."""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any

from athc.errors import FileFormatError
from athc.fbpro98_pyr.model import Injury, Player, Position, PyrFile, Ratings
from athc.fbpro98_pyr.schema import (
    FIRST_ID,
    HEADER_NAME_OFFSET,
    HEADER_SIZE,
    HEADER_UNKNOWN_OFFSET,
    HEADER_ZERO_FIELDS,
    INJURY,
    KEY_OFFSET,
    MAX_PLAYERS,
    NAME_SIZE,
    RECORD,
    RECORD_SIZE,
    U16,
    UNKNOWN_SIZE,
)

StrPath = str | PathLike[str]


class InvalidPyrError(FileFormatError):
    """Raised when a `.pyr` file is structurally invalid."""


def read_pyr(league: str, league_dir: StrPath) -> PyrFile:
    """Read and parse a league's .pyr file from disk.

    Args:
        league: League name; the file read is `<league>.pyr`.
        league_dir: Folder holding the league's files.

    Returns:
        Parsed PyrFile.

    Raises:
        InvalidPyrError: If the file is empty, shorter than its header, not the
            header plus whole player records, or holds more records than ids;
            a header byte the spec says is zero is not; the record ids do not
            reveal one consistent coding table; a record byte is not in that
            table; a position is not one of the spec's codes; or a decoded
            value breaks a rule `PyrFile.validate` checks.
        OSError: If the file cannot be opened or read.
    """
    file_path = Path(league_dir) / f"{league}.pyr"
    return parse_pyr(file_path.read_bytes(), file_path)


def parse_pyr(buffer: bytes, path: StrPath = "<buffer>") -> PyrFile:
    """Parse a .pyr player file from raw bytes.

    Args:
        buffer: Full contents of a .pyr file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed PyrFile.

    Raises:
        InvalidPyrError: If the buffer is empty, shorter than its header, not
            the header plus whole player records, or holds more records than
            ids; a header byte the spec says is zero is not; the record ids do
            not reveal one consistent coding table; a record byte is not in
            that table; a position is not one of the spec's codes; or a
            decoded value breaks a rule `PyrFile.validate` checks.
    """
    file_path = Path(path)
    if not buffer:
        raise InvalidPyrError("Empty file.", file_path)
    if len(buffer) < HEADER_SIZE:
        raise InvalidPyrError(
            f"File is {len(buffer)} bytes, shorter than the {HEADER_SIZE}-byte header.",
            file_path,
        )
    count, remainder = divmod(len(buffer) - HEADER_SIZE, RECORD_SIZE)
    if remainder:
        raise InvalidPyrError(
            f"File size {len(buffer)} is not the {HEADER_SIZE}-byte header plus a "
            f"whole number of {RECORD_SIZE}-byte player records.",
            file_path,
        )
    if count > MAX_PLAYERS:
        raise InvalidPyrError(
            f"File holds {count} player records; ids are 16-bit, so at most "
            f"{MAX_PLAYERS} fit.",
            file_path,
        )
    key, name, unknown = _parse_header(buffer, file_path)
    table = _learn_table(buffer, count, file_path)
    body = _decode(buffer[HEADER_SIZE:], table, file_path)
    players: dict[int, Player] = {}
    for index, values in enumerate(RECORD.iter_unpack(body)):
        try:
            player = _parse_player(values)
        except ValueError as e:  # a position outside the spec's codes
            offset = HEADER_SIZE + index * RECORD_SIZE
            raise InvalidPyrError(
                f"Record {index} at {offset:#x}: {e}.", file_path
            ) from e
        players[player.id] = player
    pyr = PyrFile(
        key=key, name=name, unknown=unknown, coding_table=table, players=players
    )
    try:
        pyr.validate()
    except ValueError as e:  # a model rule: the file is corrupt
        raise InvalidPyrError(f"{e}.", file_path) from e
    return pyr


def _parse_header(buffer: bytes, path: Path) -> tuple[int, str, bytes]:
    """The key, name and unknown bytes; every other header byte must be zero."""
    for offset, size in HEADER_ZERO_FIELDS:
        zeros = buffer[offset : offset + size]
        if any(zeros):
            index = next(i for i, byte in enumerate(zeros) if byte)
            raise InvalidPyrError(
                f"Header byte at {offset + index:#04x} is {zeros[index]:#04x}, "
                "expected 0.",
                path,
            )
    (key,) = U16.unpack_from(buffer, KEY_OFFSET)
    name = _read_text(buffer[HEADER_NAME_OFFSET : HEADER_NAME_OFFSET + NAME_SIZE])
    unknown = buffer[HEADER_UNKNOWN_OFFSET : HEADER_UNKNOWN_OFFSET + UNKNOWN_SIZE]
    return key, name, unknown


def _learn_table(buffer: bytes, count: int, path: Path) -> dict[int, int]:
    """The coding table the record ids reveal, plain -> disk (spec section 3):
    record i starts with player id FIRST_ID + i, so its first two bytes on
    disk show what the id's two plain bytes are written as."""
    table: dict[int, int] = {}
    stands_for: dict[int, int] = {}  # disk -> plain
    revealed_in: dict[int, int] = {}  # plain -> the record that revealed it
    for index in range(count):
        offset = HEADER_SIZE + index * RECORD_SIZE
        player_id = FIRST_ID + index
        low, high = buffer[offset], buffer[offset + 1]
        for plain, disk in ((player_id & 0xFF, low), (player_id >> 8, high)):
            if table.setdefault(plain, disk) != disk:
                raise InvalidPyrError(
                    f"Record {index} at {offset:#x}: plain {plain:#04x} is written "
                    f"as {disk:#04x}, but as {table[plain]:#04x} in record "
                    f"{revealed_in[plain]}.",
                    path,
                )
            if stands_for.setdefault(disk, plain) != plain:
                raise InvalidPyrError(
                    f"Record {index} at {offset:#x}: {disk:#04x} stands for both "
                    f"{stands_for[disk]:#04x} and {plain:#04x}.",
                    path,
                )
            revealed_in.setdefault(plain, index)
    return table


def _decode(body: bytes, table: dict[int, int], path: Path) -> bytes:
    """The records decoded: each disk byte replaced by the plain value it
    stands for. Every disk byte must be in `table`."""
    known = bytes(table.values())
    if body.translate(None, known):
        position = next(i for i, byte in enumerate(body) if byte not in known)
        index = position // RECORD_SIZE
        raise InvalidPyrError(
            f"Record {index} at {HEADER_SIZE + index * RECORD_SIZE:#x}: byte "
            f"{body[position]:#04x} at {HEADER_SIZE + position:#x} is not in the "
            "coding table the ids reveal.",
            path,
        )
    inverse = bytearray(256)
    for plain, disk in table.items():
        inverse[disk] = plain
    return body.translate(bytes(inverse))


def _parse_player(values: tuple[Any, ...]) -> Player:
    # The RECORD struct's values, in field order.
    player_id, first, last = values[0:3]
    potential = values[3:11]
    injury, group, position = values[11:14]
    actual = values[14:22]
    years, height, weight, unknown = values[22:26]
    return Player(
        id=player_id,
        first_name=_read_text(first),
        last_name=_read_text(last),
        position=Position(position),
        group=group,
        years=years,
        injury=Injury(*INJURY.unpack(injury)),
        height=height,
        weight=weight,
        potential=Ratings(*potential),
        actual=Ratings(*actual),
        unknown=unknown,
    )


def _read_text(field: bytes) -> str:
    # Text after the NUL is left over from an earlier, longer value; a name
    # that fills its field has no NUL.
    end = field.find(b"\x00")
    return field[: len(field) if end == -1 else end].decode("ASCII", errors="replace")
