"""`named_file`: the one file a single-file command was given, checked before
anything reads it, so a missing one is `<path>: not found` and never Python's
`[Errno 2]` text."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli._files import named_file
from athc.errors import AthcError


def test_named_file_returns_the_path(tmp_path: Path) -> None:
    path = tmp_path / "x.pln"
    path.write_bytes(b"")
    assert named_file(str(path)) == path


def test_missing_named_file_is_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pln"
    with pytest.raises(AthcError) as exc:
        named_file(missing)
    assert str(exc.value) == f"{missing}: not found"


def test_directory_as_named_file_is_not_a_file(tmp_path: Path) -> None:
    with pytest.raises(AthcError) as exc:
        named_file(tmp_path)
    assert str(exc.value) == f"{tmp_path}: not a file"
