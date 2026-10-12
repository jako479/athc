"""`named_file`: the one file a single-file command was given, checked before
anything reads it, so a problem reads in Windows' words and never as Python's
`[Errno 2]` text."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli._files import named_file
from athc.errors import ACCESS_DENIED, FILE_NOT_FOUND, PATH_NOT_FOUND, AthcError


def test_named_file_returns_the_path(tmp_path: Path) -> None:
    path = tmp_path / "x.pln"
    path.write_bytes(b"")
    assert named_file(str(path)) == path


def test_missing_named_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pln"
    with pytest.raises(AthcError) as exc:
        named_file(missing)
    assert str(exc.value) == f"{missing}: {FILE_NOT_FOUND}"


def test_named_file_in_a_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "gone" / "nope.pln"
    with pytest.raises(AthcError) as exc:
        named_file(missing)
    assert str(exc.value) == f"{missing}: {PATH_NOT_FOUND}"


def test_directory_as_named_file_is_access_denied(tmp_path: Path) -> None:
    with pytest.raises(AthcError) as exc:
        named_file(tmp_path)
    assert str(exc.value) == f"{tmp_path}: {ACCESS_DENIED}"
