"""Shared fixtures for fbpro98_lg2 tests.

`make_entry` and `make_team` build valid .lg2 bytes; override a field to get
the malformed and edge buffers no real file holds. A value as long as its
field leaves no NUL.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from athc.fbpro98_lg2.schema import FILENAME_SIZE, FOLDER_SIZE, TEAM_TRAILER_SIZE

DEFAULT_FOLDER = b"Plans\\Team"
DEFAULT_FILENAMES = (
    b"O1.prf",
    b"O1.pln",
    b"D1.prf",
    b"D1.pln",
    b"O2.prf",
    b"O2.pln",
    b"D2.prf",
    b"D2.pln",
)


def build_entry(folder: bytes = DEFAULT_FOLDER, filename: bytes = b"O1.prf") -> bytes:
    """One file entry, each field NUL-padded to its size."""
    assert len(folder) <= FOLDER_SIZE
    assert len(filename) <= FILENAME_SIZE
    return folder.ljust(FOLDER_SIZE, b"\x00") + filename.ljust(FILENAME_SIZE, b"\x00")


def build_team(entries: Sequence[bytes] | None = None) -> bytes:
    """One team record: eight entries plus the 9 unknown bytes."""
    if entries is None:
        entries = [build_entry(filename=name) for name in DEFAULT_FILENAMES]
    return b"".join(entries) + bytes(TEAM_TRAILER_SIZE)


def entries_with(index: int, entry: bytes) -> list[bytes]:
    """The default eight entries with one replaced."""
    entries = [build_entry(filename=name) for name in DEFAULT_FILENAMES]
    entries[index] = entry
    return entries


@pytest.fixture
def make_entry():
    """Factory that builds one file entry (see build_entry)."""
    return build_entry


@pytest.fixture
def make_team():
    """Factory that builds one team record (see build_team)."""
    return build_team


@pytest.fixture
def make_entries():
    """Factory for the default entries with one replaced (see entries_with)."""
    return entries_with
