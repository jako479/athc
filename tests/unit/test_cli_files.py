"""`named_file`: the one file a single-file command was given, checked before
anything reads it, so a problem reads in Windows' words and never as Python's
`[Errno 2]` text. `collect_files`: the files, errors and warnings the batch
commands' paths give; a name that exists is a name, never a wildcard.
`resolve_output` / `resolve_output_folder`: where a command writes, from its
`OUTPUT` or `OUTPUT_FOLDER`."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli._files import (
    collect_files,
    named_file,
    resolve_output,
    resolve_output_folder,
)
from athc.errors import (
    ACCESS_DENIED,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    AthcError,
)

# ── collect_files ─────────────────────────────────────────────────────────────


def test_collect_single_file(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    collected = collect_files([str(f)], suffix=".pln", recursive=False)
    assert collected.files == [f]
    assert collected.errors == [] and collected.warnings == []


def test_collect_directory_top_level(tmp_path: Path) -> None:
    (tmp_path / "a.pln").touch()
    (tmp_path / "b.pln").touch()
    (tmp_path / "skip.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    collected = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert collected.files == [tmp_path / "a.pln", tmp_path / "b.pln"]
    assert collected.errors == [] and collected.warnings == []


def test_collect_directory_recursive(tmp_path: Path) -> None:
    (tmp_path / "top.pln").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pln").touch()
    collected = collect_files([str(tmp_path)], suffix=".pln", recursive=True)
    assert sorted(f.name for f in collected.files) == ["deep.pln", "top.pln"]
    assert collected.errors == [] and collected.warnings == []


def test_collect_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    collected = collect_files([str(missing)], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.warnings == []
    assert collected.errors == [f"{missing}: {FILE_NOT_FOUND}"]


def test_collect_file_of_another_kind(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.touch()
    collected = collect_files([str(bad)], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.warnings == []
    assert collected.errors == [f"{bad}: Not a .pln file."]


def test_collect_empty_dir_is_a_warning(tmp_path: Path) -> None:
    collected = collect_files([str(tmp_path)], suffix=".pln", recursive=False)
    assert collected.files == [] and collected.errors == []
    assert collected.warnings == [f"{tmp_path}: No .pln files."]


def test_collect_dedupes(tmp_path: Path) -> None:
    f = tmp_path / "a.pln"
    f.touch()
    collected = collect_files([str(f), str(tmp_path)], suffix=".pln", recursive=False)
    assert collected.files == [f]


@pytest.mark.parametrize(
    ("pattern", "expected", "warnings"),
    [
        ("Off*.pln", ["Off1.pln", "Off2.pln"], []),
        ("*", ["Def.pln", "Off1.pln", "Off2.pln"], []),
        ("*.prf", [], ["*.prf: No .pln files match."]),
    ],
    ids=["filters", "keeps the suffix", "no match"],
)
def test_collect_wildcard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pattern: str,
    expected: list[str],
    warnings: list[str],
) -> None:
    for name in ("Off1.pln", "Off2.pln", "Def.pln", "skip.txt"):
        (tmp_path / name).touch()
    monkeypatch.chdir(tmp_path)
    collected = collect_files([pattern], suffix=".pln", recursive=False)
    assert collected.files == [Path(name) for name in expected]
    assert collected.errors == [] and collected.warnings == warnings


def test_collect_wildcard_reaches_into_subfolders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`**` matches any depth of folders, `-r` or not."""
    (tmp_path / "plans" / "2049" / "week6").mkdir(parents=True)
    (tmp_path / "plans" / "top.pln").touch()
    (tmp_path / "plans" / "2049" / "week6" / "deep.pln").touch()
    monkeypatch.chdir(tmp_path)
    collected = collect_files([r"plans\**\*.pln"], suffix=".pln", recursive=False)
    assert collected.files == [
        Path("plans") / "2049" / "week6" / "deep.pln",
        Path("plans") / "top.pln",
    ]


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


# ── resolve_output ────────────────────────────────────────────────────────────

DEFAULT = Path("plans") / "OFF.normals.txt"


def test_output_left_out_is_the_default() -> None:
    assert resolve_output(None, DEFAULT, ".txt") == DEFAULT


def test_output_existing_folder_gets_the_default_name(tmp_path: Path) -> None:
    assert resolve_output(str(tmp_path), DEFAULT, ".txt") == (
        tmp_path / "OFF.normals.txt"
    )


def test_output_current_folder_gets_the_default_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_output(".", DEFAULT, ".txt") == Path("OFF.normals.txt")


def test_output_existing_folder_named_like_a_file_is_a_folder(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "w.xlsx"
    folder.mkdir()
    assert resolve_output(str(folder), DEFAULT, ".txt") == (folder / "OFF.normals.txt")


@pytest.mark.parametrize("slash", ["\\", "/"], ids=["backslash", "slash"])
def test_output_ending_in_a_slash_is_a_folder(tmp_path: Path, slash: str) -> None:
    """A folder that is not there yet; whoever writes the file creates it."""
    lists = tmp_path / "lists"
    assert resolve_output(f"{lists}{slash}", DEFAULT, ".txt") == (
        lists / "OFF.normals.txt"
    )
    assert not lists.exists()


def test_output_bare_drive_is_a_folder() -> None:
    """A drive has no name to add an extension to: it is a folder, there or
    not (a missing one then fails in Windows' words where the file is
    written)."""
    assert resolve_output("Q:", DEFAULT, ".txt") == Path("Q:") / "OFF.normals.txt"


def test_output_quoted_folder_ending_in_a_backslash_is_a_folder(
    tmp_path: Path,
) -> None:
    """Windows reads the `\\"` that ends `"E:\\My Lists\\"` as a quote mark,
    so the program gets `E:\\My Lists"`; a `"` is never part of a Windows
    name."""
    lists = tmp_path / "My Lists"
    assert resolve_output(f'{lists}"', DEFAULT, ".txt") == (lists / "OFF.normals.txt")


def test_output_ending_in_a_slash_on_a_file_is_invalid(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("x", encoding="utf-8")
    with pytest.raises(AthcError) as exc:
        resolve_output(f"{notes}\\", DEFAULT, ".txt")
    assert str(exc.value) == f"{notes}: {DIRECTORY_INVALID}"


@pytest.mark.parametrize("name", ["plays.txt", "WEEK6.XLSM", "plays.v2"])
def test_output_with_an_extension_is_kept(tmp_path: Path, name: str) -> None:
    """Any extension stays as given, in any case; checking it is the
    command's."""
    assert resolve_output(str(tmp_path / name), DEFAULT, ".txt") == tmp_path / name


def test_output_without_an_extension_gets_one(tmp_path: Path) -> None:
    assert resolve_output(str(tmp_path / "plays"), DEFAULT, ".txt") == (
        tmp_path / "plays.txt"
    )


def test_output_without_an_extension_gets_one_even_when_that_file_exists(
    tmp_path: Path,
) -> None:
    (tmp_path / "out").write_text("x", encoding="utf-8")
    assert resolve_output(str(tmp_path / "out"), DEFAULT, ".txt") == (
        tmp_path / "out.txt"
    )


# ── resolve_output_folder ─────────────────────────────────────────────────────


def test_output_folder_left_out_is_the_current_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_output_folder(None) == Path.cwd()


def test_output_folder_existing_folder(tmp_path: Path) -> None:
    assert resolve_output_folder(str(tmp_path)) == tmp_path


def test_output_folder_any_name_is_a_folder(tmp_path: Path) -> None:
    """A name like a file's is still a folder; whoever writes creates it."""
    output = tmp_path / "output.txt"
    assert resolve_output_folder(str(output)) == output
    assert not output.exists()


def test_output_folder_quoted_ending_in_a_backslash(tmp_path: Path) -> None:
    """`"E:\\2049 Schedules\\"` reaches the program as `E:\\2049 Schedules"`."""
    output = tmp_path / "2049 Schedules"
    assert resolve_output_folder(f'{output}"') == output


def test_output_folder_that_is_a_file_is_invalid(tmp_path: Path) -> None:
    output = tmp_path / "output.txt"
    output.write_text("x", encoding="utf-8")
    with pytest.raises(AthcError) as exc:
        resolve_output_folder(str(output))
    assert str(exc.value) == f"{output}: {DIRECTORY_INVALID}"
