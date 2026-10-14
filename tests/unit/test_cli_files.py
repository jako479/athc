"""`named_file`: the one file a single-file command was given, checked before
anything reads it, so a problem reads in Windows' words and never as Python's
`[Errno 2]` text. `collect_files`: a name that exists is a name, never a
wildcard."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli._files import collect_files, named_file
from athc.errors import ACCESS_DENIED, FILE_NOT_FOUND, PATH_NOT_FOUND, AthcError


def test_existing_name_with_wildcard_characters_is_a_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[2029]` would match one character as a wildcard; the folder exists,
    so it is that folder. A pattern that names nothing is still a wildcard."""
    season = tmp_path / "Season [2029]"
    season.mkdir()
    (season / "a.pln").touch()
    (tmp_path / "b.pln").touch()
    monkeypatch.chdir(tmp_path)
    collected = collect_files(
        ["Season [2029]", "[b].pln"], suffix=".pln", recursive=False
    )
    assert collected.files == [Path("Season [2029]") / "a.pln", Path("b.pln")]
    assert collected.errors == [] and collected.warnings == []


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
