"""Turn the paths a command was given into the files it works on."""

from __future__ import annotations

import glob
from collections.abc import Iterable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

from athc.errors import ACCESS_DENIED, DIRECTORY_INVALID, AthcError, missing_reason

_GLOB_CHARS = frozenset("*?[")


def is_glob(s: str) -> bool:
    """Whether `s` is a wildcard. A name that exists is a name, never a
    wildcard, so a folder like `Season [2029]` is that folder."""
    return any(c in s for c in _GLOB_CHARS) and not Path(s).exists()


@dataclass(frozen=True, slots=True)
class Collected:
    """The files a command works on, plus what was wrong with the paths it was
    given. `errors` are failed items (`<path>: The system cannot find the file
    specified.`, `<path>: Not a .pln file.`); `warnings` are paths with nothing
    to do (`<dir>: No .pln files.`)."""

    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def collect_files(paths: Iterable[str], *, suffix: str, recursive: bool) -> Collected:
    """Resolve paths (file / directory / glob) to a deduped list of `suffix`
    files, in order, with the errors and warnings the paths produced. A path
    that exists is used as is, before any wildcard check (`is_glob`)."""
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
                collected.warnings.append(f"{raw}: No {suffix} files match.")
                continue
            for match in matches:
                _add(match, collected.files, seen)
            continue
        path = Path(raw)
        if not path.exists():
            collected.errors.append(f"{raw}: {missing_reason(raw)}")
            continue
        if path.is_file():
            if path.suffix.lower() != suffix:
                collected.errors.append(f"{raw}: Not a {suffix} file.")
            else:
                _add(path, collected.files, seen)
            continue
        pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
        dir_matches = sorted(path.glob(pattern))
        if not dir_matches:
            collected.warnings.append(f"{raw}: No {suffix} files.")
            continue
        for match in dir_matches:
            _add(match, collected.files, seen)
    return collected


def named_file(raw: str | PathLike[str]) -> Path:
    """The one file a command was given, as a Path. AthcError in Windows'
    words when it does not exist (the file or the path phrase) and
    `Access is denied.` when it is a folder, as `type` says, checked before
    anything reads it."""
    path = Path(raw)
    if not path.exists():
        raise AthcError(missing_reason(path), path)
    if not path.is_file():
        raise AthcError(ACCESS_DENIED, path)
    return path


def is_folder(raw: str) -> bool:
    """Whether an output path names a folder: one that exists; any path
    ending in a slash, or in the `"` Windows leaves in place of the final
    backslash of a quoted path; or a bare drive (`Q:`), which has no name. A
    `Path` drops a trailing slash, so this reads the string as given."""
    return raw.endswith(("/", "\\", '"')) or not Path(raw).name or Path(raw).is_dir()


def _unquoted(raw: str) -> Path:
    """The path as typed: a quoted path that ended in a backslash arrives
    ending in `"`, which no Windows name holds."""
    return Path(raw.removesuffix('"'))


def resolve_output(raw: str | None, default: Path, extension: str) -> Path:
    """The file a command writes for its `OUTPUT`: `default` when none is
    given; `default`'s name inside it when it is a folder (`is_folder`); else
    the path itself, with `extension` added when it has none. A folder path
    that names an existing file is an AthcError. `-` is the caller's."""
    if raw is None:
        return default
    path = _unquoted(raw)
    if is_folder(raw):
        if path.is_file():
            raise AthcError(DIRECTORY_INVALID, path)
        return path / default.name
    return path if path.suffix else path.with_suffix(extension)


def resolve_output_folder(raw: str | None) -> Path:
    """The folder a command writes into for its `OUTPUT_FOLDER`: the current
    folder when none is given, else the path, whatever its name (whoever
    writes creates it). An existing file there is an AthcError."""
    if raw is None:
        return Path.cwd()
    path = _unquoted(raw)
    if path.is_file():
        raise AthcError(DIRECTORY_INVALID, path)
    return path


def _add(path: Path, files: list[Path], seen: set[Path]) -> None:
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    files.append(path)
