"""Turn the paths a command was given into the files it works on."""

from __future__ import annotations

import glob
from collections.abc import Iterable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

from athc.errors import AthcError

_GLOB_CHARS = frozenset("*?[")


def is_glob(s: str) -> bool:
    return any(c in s for c in _GLOB_CHARS)


@dataclass(frozen=True, slots=True)
class Collected:
    """The files a command works on, plus what was wrong with the paths it was
    given. `errors` are failed items (`<path>: not found`, `<path>: not a .pln
    file`); `warnings` are paths with nothing to do (`<dir>: no .pln files`)."""

    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def collect_files(paths: Iterable[str], *, suffix: str, recursive: bool) -> Collected:
    """Resolve paths (file / directory / glob) to a deduped list of `suffix`
    files, in order, with the errors and warnings the paths produced."""
    suffix = suffix.lower()
    collected = Collected()
    seen: set[Path] = set()
    for raw in paths:
        if is_glob(raw):
            matches = [
                Path(m)
                # glob.glob is the right tool here: raw is a complete pattern
                # the user typed, like plays\**\*.ply. pathlib has no
                # equivalent — Path.glob only matches within a folder you
                # already have. PTH207 flags glob on sight; it is wrong here.
                for m in sorted(glob.glob(raw, recursive=True))  # noqa: PTH207
                if Path(m).is_file() and Path(m).suffix.lower() == suffix
            ]
            if not matches:
                collected.warnings.append(f"{raw}: no {suffix} files match")
                continue
            for match in matches:
                _add(match, collected.files, seen)
            continue
        path = Path(raw)
        if not path.exists():
            collected.errors.append(f"{raw}: not found")
            continue
        if path.is_file():
            if path.suffix.lower() != suffix:
                collected.errors.append(f"{raw}: not a {suffix} file")
            else:
                _add(path, collected.files, seen)
            continue
        pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
        dir_matches = sorted(path.glob(pattern))
        if not dir_matches:
            collected.warnings.append(f"{raw}: no {suffix} files")
            continue
        for match in dir_matches:
            _add(match, collected.files, seen)
    return collected


def named_file(raw: str | PathLike[str]) -> Path:
    """The one file a command was given, as a Path. AthcError `<path>: not
    found` when it does not exist and `<path>: not a file` when it is a
    folder, checked before anything reads it, so Python's `[Errno 2]` text
    never shows for a mistyped name."""
    path = Path(raw)
    if not path.exists():
        raise AthcError("not found", path)
    if not path.is_file():
        raise AthcError("not a file", path)
    return path


def _add(path: Path, files: list[Path], seen: set[Path]) -> None:
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    files.append(path)
