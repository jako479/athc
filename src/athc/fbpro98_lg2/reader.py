"""Parse FbPro98 .lg2 league files into Lg2File objects. See specs/lg2.md."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from athc.fbpro98_lg2.model import FilePair, HalfFiles, Lg2File, TeamFiles
from athc.fbpro98_lg2.schema import (
    FILE_ENTRY_SIZE,
    FILENAME_SIZE,
    FILES_PER_TEAM,
    FOLDER_SIZE,
    MODERN_STOCK_FOLDER,
    OLD_STOCK_FOLDER,
    TEAM_RECORD_SIZE,
)

StrPath = str | PathLike[str]


class InvalidLg2Error(ValueError):
    """Raised when a `.lg2` file is structurally invalid."""


class UnsupportedLg2Error(ValueError):
    """Raised when the first folder field matches a stock league signature.

    Both stock layouts are rejected: modern (folder `STOCK`) and old (empty
    folder). The check runs before the field checks. See specs/lg2.md
    sections 3 and 4.
    """


def read_lg2(league: str, league_dir: StrPath) -> Lg2File:
    """Read and parse a league's .lg2 file from disk.

    Args:
        league: League name; the file read is `<league>.lg2`.
        league_dir: Folder holding the league's files.

    Returns:
        Parsed Lg2File.

    Raises:
        InvalidLg2Error: If the file is empty or not a whole number of team
            records, a folder or filename field has no NUL, or a filename is
            empty.
        UnsupportedLg2Error: If the file is for a stock league.
        OSError: If the file cannot be opened or read.
    """
    file_path = Path(league_dir) / f"{league}.lg2"
    return parse_lg2(file_path.read_bytes(), file_path)


def parse_lg2(buffer: bytes, path: StrPath = "<buffer>") -> Lg2File:
    """Parse a .lg2 league file from raw bytes.

    Args:
        buffer: Full contents of a .lg2 file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed Lg2File.

    Raises:
        InvalidLg2Error: If the buffer is empty or not a whole number of team
            records, a folder or filename field has no NUL, or a filename is
            empty.
        UnsupportedLg2Error: If the buffer is for a stock league.
    """
    file_path = Path(path)
    if not buffer:
        raise InvalidLg2Error(f"Empty file in {file_path}")
    team_count, remainder = divmod(len(buffer), TEAM_RECORD_SIZE)
    if remainder != 0:
        raise InvalidLg2Error(
            f"File size {len(buffer)} is not a whole number of "
            f"{TEAM_RECORD_SIZE}-byte team records in {file_path}"
        )
    _check_stock(buffer, file_path)
    return Lg2File(
        teams=tuple(
            _parse_team(buffer, index * TEAM_RECORD_SIZE, file_path)
            for index in range(team_count)
        )
    )


def _check_stock(buffer: bytes, path: Path) -> None:
    # Only the first entry decides; a later stock-looking entry is read as is.
    if buffer.startswith(MODERN_STOCK_FOLDER):
        raise UnsupportedLg2Error(f"Modern stock league not supported in {path}")
    if buffer.startswith(OLD_STOCK_FOLDER):
        raise UnsupportedLg2Error(f"Old stock league not supported in {path}")


def _parse_team(buffer: bytes, offset: int, path: Path) -> TeamFiles:
    locations = [
        _parse_entry(buffer, offset + index * FILE_ENTRY_SIZE, path)
        for index in range(FILES_PER_TEAM)
    ]
    # Fixed entry order: per half, offense profile, offense game plan,
    # defense profile, defense game plan.
    return TeamFiles(
        first_half=HalfFiles(
            offense=FilePair(profile=locations[0], gameplan=locations[1]),
            defense=FilePair(profile=locations[2], gameplan=locations[3]),
        ),
        second_half=HalfFiles(
            offense=FilePair(profile=locations[4], gameplan=locations[5]),
            defense=FilePair(profile=locations[6], gameplan=locations[7]),
        ),
    )


def _parse_entry(buffer: bytes, offset: int, path: Path) -> str:
    folder = _read_string(buffer, offset, FOLDER_SIZE, "folder", path)
    filename_offset = offset + FOLDER_SIZE
    filename = _read_string(buffer, filename_offset, FILENAME_SIZE, "filename", path)
    if not filename:
        raise InvalidLg2Error(f"Empty filename at {filename_offset:#x} in {path}")
    return f"{folder}\\{filename}" if folder else filename


def _read_string(buffer: bytes, offset: int, size: int, label: str, path: Path) -> str:
    # Text after the NUL is left over from an earlier, longer value.
    field = buffer[offset : offset + size]
    end = field.find(b"\x00")
    if end == -1:
        raise InvalidLg2Error(f"No NUL in {label} field at {offset:#x} in {path}")
    return field[:end].decode("ASCII", errors="replace")
