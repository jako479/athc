"""Shared helpers for `athc gameplan` subcommands: files, rules, pool, listing."""

from __future__ import annotations

import glob
import logging
import shutil
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import click

from athc.fbpro98_gameplan import GamePlan
from athc.gameplan import Rules, RulesFileError, load_rules
from athc.playpool import PlayPool, read_play_pool
from athc.playpool import RulesFileError as PoolRulesFileError
from athc.playpool import load_rules as load_pool_rules

COMMENT_TOKEN = "::"
_GLOB_CHARS = frozenset("*?[")


def make_backup(path: Path) -> Path:
    """Copy `path` to `<path>.<YYYY-MM-DD-HHMM>.bak`; returns the backup path."""
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, backup)
    return backup


def parse_play_list(text: str) -> list[str]:
    """Play names in order; drops blanks, `::` lines, and ` ::` trailers."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(COMMENT_TOKEN):
            continue
        idx = line.find(f" {COMMENT_TOKEN}")
        if idx >= 0:
            line = line[:idx].rstrip()
        if line:
            out.append(line)
    return out


def is_glob(s: str) -> bool:
    return any(c in s for c in _GLOB_CHARS)


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
) -> Rules | None:
    """Load gameplan rules from `rule_files`; return None (a hard error for the
    caller) when none are configured or loading fails."""
    files = list(rule_files)
    if not files:
        logger.error(
            "%s: no rules configured - nothing to check. "
            "Set rule_files in athc.ini [gameplan] or pass --rules.",
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


def build_pool(
    play_path: Path,
    playpool_rules: Path | None,
    *,
    prog: str,
    logger: logging.Logger,
) -> PlayPool | None:
    """Build a PlayPool from `play_path`, classified by folder/filename. Optional
    `playpool_rules` is the playpool filename-filter TOML; returns None on a
    missing directory or unreadable rules file."""
    if not play_path.is_dir():
        logger.error("%s: play path '%s' is not a directory", prog, play_path)
        return None
    try:
        rules = load_pool_rules(playpool_rules) if playpool_rules else None
        return read_play_pool(play_path, rules=rules)
    except PoolRulesFileError as error:
        for line in error.errors:
            logger.error("%s: %s", prog, line)
        return None
    except OSError as error:
        logger.error("%s: %s", prog, error)
        return None


def normal_play_lines(gp: GamePlan, *, sort: str) -> list[str]:
    """The 64 normal play names. `slot` keeps positions (empty slot = ""); `name`
    drops blanks and sorts case-insensitively."""
    names = ["" if p is None else p.name for p in gp.normal_plays]
    if sort == "name":
        return sorted((n for n in names if n), key=str.casefold)
    return names


def special_play_lines(gp: GamePlan) -> list[str]:
    """The custom special-teams play names in source order (empty slot = "")."""
    return ["" if p is None else p.name for p in gp.custom_special_plays]


def emit_play_list(
    lines: list[str],
    out_path: Path | None,
    source: Path,
    *,
    force: bool,
    prog: str,
    logger: logging.Logger,
    noun: str,
) -> int:
    """Print `lines` to stdout, or write them to `out_path` with a `:: <source>`
    header. Returns the exit code (0 ok, 1 refused/write error)."""
    if out_path is None:
        click.echo("\n".join(lines))
        return 0
    if out_path.exists() and not force:
        logger.error("%s: %s already exists (use -f to overwrite)", prog, out_path)
        return 1
    text = f":: {source.resolve()}\n" + "\n".join(lines) + "\n"
    try:
        out_path.write_text(text, encoding="utf-8")
    except OSError as error:
        logger.error("%s: %s", prog, error)
        return 1
    click.echo(f"Wrote {sum(1 for n in lines if n)} {noun} play(s) to {out_path}")
    return 0
