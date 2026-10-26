"""Tests for athc.fileio.atomic_write."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from athc import fileio
from athc.fileio import atomic_write


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """An empty folder of its own, so the listing shows every file written."""
    out = tmp_path / "out"
    out.mkdir()
    return out


def _entries(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


def test_bytes_replace_the_target(folder: Path) -> None:
    target = folder / "plan.pln"
    target.write_bytes(b"old")
    atomic_write(target, b"new bytes")
    assert target.read_bytes() == b"new bytes"
    assert _entries(folder) == ["plan.pln"]


def test_text_uses_the_platform_newline(folder: Path) -> None:
    target = folder / "athc.toml"
    atomic_write(target, "a\nb\n")
    assert target.read_bytes() == f"a{os.linesep}b{os.linesep}".encode()


def test_new_file_is_created(folder: Path) -> None:
    target = folder / "new.prf"
    atomic_write(target, b"data")
    assert target.read_bytes() == b"data"
    assert _entries(folder) == ["new.prf"]


def test_missing_folder_names_the_target(folder: Path) -> None:
    target = folder / "missing" / "plan.pln"
    with pytest.raises(FileNotFoundError) as exc:
        atomic_write(target, b"data")
    assert exc.value.filename == str(target)
    assert _entries(folder) == []


def test_failed_swap_leaves_the_old_file_and_no_temp(folder: Path) -> None:
    target = folder / "plan.pln"
    target.write_bytes(b"old")
    # Windows refuses to replace a file another handle holds open.
    with target.open("rb"), pytest.raises(PermissionError) as exc:
        atomic_write(target, b"new")
    assert exc.value.filename == str(target)
    assert target.read_bytes() == b"old"
    assert _entries(folder) == ["plan.pln"]


def _refusing_swaps(monkeypatch: pytest.MonkeyPatch, failures: int) -> list[int]:
    """Make the first `failures` swaps fail as a scanner's hold would, with no
    wait between tries; returns the list the swap count is kept in."""
    calls = [0]
    real = Path.replace

    def replace(self: Path, target: Path) -> Path:
        calls[0] += 1
        if calls[0] <= failures:
            raise PermissionError(13, "held", str(self))
        return real(self, target)

    monkeypatch.setattr(Path, "replace", replace)
    monkeypatch.setattr(fileio.time, "sleep", lambda seconds: None)
    return calls


def test_swap_held_four_times_succeeds_on_the_fifth_try(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = folder / "plan.pln"
    calls = _refusing_swaps(monkeypatch, failures=4)
    atomic_write(target, b"new")
    assert calls[0] == 5
    assert target.read_bytes() == b"new"
    assert _entries(folder) == ["plan.pln"]


def test_swap_held_five_times_fails_naming_the_target(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = folder / "plan.pln"
    calls = _refusing_swaps(monkeypatch, failures=5)
    with pytest.raises(PermissionError) as exc:
        atomic_write(target, b"new")
    assert calls[0] == 5
    assert exc.value.filename == str(target)
    assert _entries(folder) == []
