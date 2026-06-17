"""Shared helpers for `athc profile`: file collection, backup, rules loading."""

from __future__ import annotations

import glob
import logging
import shutil
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from athc.profile import ProfileRules, RulesFileError, load_rules

_GLOB_CHARS = frozenset("*?[")


def is_glob(s: str) -> bool:
    return any(c in s for c in _GLOB_CHARS)


def make_backup(path: Path) -> Path:
    """Copy `path` to `<path>.<YYYY-MM-DD-HHMM>.bak` and return the backup path."""
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, backup)
    return backup


def collect_files(
    paths: Iterable[str], *, suffix: str, recursive: bool
) -> tuple[list[Path], list[str]]:
    """Resolve paths (file / directory / glob) to a deduped list of `suffix` files.

    Returns `(files, errors)`.
    """
    suffix = suffix.lower()
    files: list[Path] = []
    seen: set[Path] = set()
    errors: list[str] = []
    for raw in paths:
        if is_glob(raw):
            matches = [
                Path(m)
                for m in sorted(glob.glob(raw, recursive=True))
                if Path(m).is_file() and Path(m).suffix.lower() == suffix
            ]
            if not matches:
                errors.append(f"{raw}: no {suffix} files match")
                continue
            for match in matches:
                _add(match, files, seen)
            continue
        path = Path(raw)
        if not path.exists():
            errors.append(f"{raw}: path does not exist")
            continue
        if path.is_file():
            if path.suffix.lower() != suffix:
                errors.append(f"{raw}: not a {suffix} file")
            else:
                _add(path, files, seen)
            continue
        pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
        dir_matches = sorted(path.glob(pattern))
        if not dir_matches:
            scope = "tree" if recursive else "directory"
            errors.append(f"{raw}: no {suffix} files in {scope}")
            continue
        for match in dir_matches:
            _add(match, files, seen)
    return files, errors


def _add(path: Path, files: list[Path], seen: set[Path]) -> None:
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    files.append(path)


def resolve_rules(
    rule_files: Iterable[Path], *, prog: str, logger: logging.Logger
) -> ProfileRules | None:
    """Load rules from `rule_files`; return None (caller treats as a hard error)
    when none are configured or loading fails."""
    files = list(rule_files)
    if not files:
        logger.error(
            "%s: no rules configured - nothing to check. "
            "Set rule_files in athc.ini [profile] or pass --rules.",
            prog,
        )
        return None
    try:
        return load_rules(files)
    except RulesFileError as error:
        for line in error.errors:
            logger.error("%s: %s", prog, line)
        return None
    except OSError as error:
        logger.error("%s: %s", prog, error)
        return None
