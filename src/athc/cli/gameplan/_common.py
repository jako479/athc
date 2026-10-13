"""Shared helpers for `athc gameplan` subcommands: files, search, rules, pool,
listing."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from athc.cli._files import Collected, collect_files, is_glob, named_file
from athc.config import play_dir
from athc.console import console
from athc.errors import ConfigFileError
from athc.fbpro98_gameplan import GamePlan, PlayRef
from athc.fbpro98_play import (
    CategoryLabels,
    DefensiveCategory,
    OffensiveCategory,
    PlayCategory,
    resolve_category,
)
from athc.gameplan import Rules, RuleViolation, load_rules
from athc.gameplan.writer import PlayLine
from athc.playpool import PlayPool, read_play_pool

__all__ = [
    "COMMENT_TOKEN",
    "Collected",
    "build_pool",
    "category_of",
    "collect_files",
    "emit_play_list",
    "find_in_gameplan",
    "format_violation",
    "is_glob",
    "load_rules_or_raise",
    "named_file",
    "normal_play_lines",
    "parse_play_list",
    "special_play_lines",
]

COMMENT_TOKEN = "::"

# Listing order for `list-normals --sort category`: the league's reading order,
# with User Specific closing each side.
_OFFENSE_CATEGORY_ORDER: tuple[PlayCategory, ...] = (
    OffensiveCategory.RUN_LEFT,
    OffensiveCategory.RUN_MIDDLE,
    OffensiveCategory.RUN_RIGHT,
    OffensiveCategory.PASS_SHORT_LEFT,
    OffensiveCategory.PASS_SHORT_MIDDLE,
    OffensiveCategory.PASS_SHORT_RIGHT,
    OffensiveCategory.PASS_MEDIUM_LEFT,
    OffensiveCategory.PASS_MEDIUM_MIDDLE,
    OffensiveCategory.PASS_MEDIUM_RIGHT,
    OffensiveCategory.PASS_LONG_LEFT,
    OffensiveCategory.PASS_LONG_MIDDLE,
    OffensiveCategory.PASS_LONG_RIGHT,
    OffensiveCategory.RAZZLE_DAZZLE_RUN,
    OffensiveCategory.RAZZLE_DAZZLE_PASS,
    OffensiveCategory.GOAL_LINE_RUN,
    OffensiveCategory.GOAL_LINE_PASS,
    OffensiveCategory.USER_SPECIFIC,
)
_DEFENSE_CATEGORY_ORDER: tuple[PlayCategory, ...] = (
    DefensiveCategory.RUN_LEFT,
    DefensiveCategory.RUN_MIDDLE,
    DefensiveCategory.RUN_RIGHT,
    DefensiveCategory.PASS_SHORT,
    DefensiveCategory.PASS_MEDIUM,
    DefensiveCategory.PASS_LONG,
    DefensiveCategory.PASS_DAZZLE,
    DefensiveCategory.RUN_DAZZLE,
    DefensiveCategory.GOAL_LINE_RUN,
    DefensiveCategory.GOAL_LINE_PASS,
    DefensiveCategory.USER_SPECIFIC,
)


def parse_play_list(text: str) -> list[PlayLine]:
    """Play names in order with their line numbers; drops blanks, `::` lines,
    and ` ::` trailers."""
    out: list[PlayLine] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_TOKEN):
            continue
        idx = line.find(f" {COMMENT_TOKEN}")
        if idx >= 0:
            line = line[:idx].rstrip()
        if line:
            out.append(PlayLine(number, line))
    return out


def find_in_gameplan(
    gp: GamePlan, play_name: str
) -> tuple[list[tuple[int, PlayRef]], list[tuple[int, PlayRef]]]:
    """Case-insensitive name match across a gameplan's normal + custom-special slots
    -> `(normal_hits, special_hits)`. Stock specials and clock plays are skipped.
    Normal hits carry the 0-based slot index; special hits a 1-based category."""
    target = play_name.casefold()
    normal_hits: list[tuple[int, PlayRef]] = [
        (i, p)
        for i, p in enumerate(gp.normal_plays)
        if p is not None and p.name.casefold() == target
    ]
    special_hits: list[tuple[int, PlayRef]] = [
        (i + 1, p)
        for i, p in enumerate(gp.custom_special_plays)
        if p is not None and p.name.casefold() == target
    ]
    return normal_hits, special_hits


def format_violation(v: RuleViolation) -> str:
    """One violation as `check` prints it: `[category] message`, or just the
    message when it has no category."""
    prefix = f"[{v.category}] " if v.category else ""
    return f"{prefix}{v.message}"


def load_rules_or_raise(rule_files: Iterable[Path], labels: CategoryLabels) -> Rules:
    """The league's gameplan rules, read with its category `labels`.
    ConfigFileError when none are configured; a rules file that cannot be read
    or parsed raises its own error."""
    files = list(rule_files)
    if not files:
        raise ConfigFileError(
            "No rules configured. Add gameplan.toml to the league folder."
        )
    return load_rules(files, labels=labels)


def build_pool(play_path: Path, labels: CategoryLabels, league_file: Path) -> PlayPool:
    """Build a PlayPool from `play_path` (each play classified from its file) with
    the league's category `labels` naming its folders. Every pool issue is a
    `WARN` line. ConfigFileError, naming `league_file`, when `play_path` is not a
    folder."""
    play_dir(play_path, league_file)
    pool = read_play_pool(play_path, labels=labels)
    for issue in pool.issues:
        console.warn(issue)
    return pool


def category_of(play: PlayRef) -> PlayCategory:
    """A gameplan play's category, from the category bytes copied into the `.pln`."""
    return resolve_category(
        play.play_category, play.special_category, play.user_category
    )


def normal_play_lines(gp: GamePlan, *, sort: str, labels: CategoryLabels) -> list[str]:
    """The 64 normal play names. `slot` keeps positions (empty slot = ""); `name`
    drops blanks and sorts case-insensitively; `category` drops blanks and groups
    them in category order, each group under a `:: <label>` header (the league's
    label, else the game name), slot order within a group, no header for an
    empty category."""
    if sort == "category":
        return _category_lines(gp, labels)
    names = ["" if p is None else p.name for p in gp.normal_plays]
    if sort == "name":
        return sorted((n for n in names if n), key=str.casefold)
    return names


def _category_lines(gp: GamePlan, labels: CategoryLabels) -> list[str]:
    order = _OFFENSE_CATEGORY_ORDER if gp.is_offense else _DEFENSE_CATEGORY_ORDER
    plays = [(category_of(p), p.name) for p in gp.normal_plays if p is not None]
    lines: list[str] = []
    # The reader rejects an unrecognized category, and the GamePlan invariants
    # (side parity, no special-teams play in a normal slot) keep every play's
    # category inside `order`, so none is dropped here.
    for category in order:
        names = [name for found, name in plays if found is category]
        if names:
            lines.append(f"{COMMENT_TOKEN} {labels.label(category)}")
            lines.extend(names)
    return lines


def special_play_lines(gp: GamePlan) -> list[str]:
    """The custom special-teams play names in source order (empty slot = "")."""
    return ["" if p is None else p.name for p in gp.custom_special_plays]


def emit_play_list(
    lines: list[str], out_path: Path | None, source: Path, *, noun: str
) -> None:
    """Print `lines` (the result, stdout), or write them to `out_path` (replacing
    it, its missing folders created) with a `:: <source>` header and say so with
    an `OK` line. A write that fails raises its OSError. The count reported
    leaves out blanks and `::` header lines."""
    if out_path is None:
        console.print("\n".join(lines))
        return
    text = f":: {source.resolve()}\n" + "\n".join(lines) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    count = sum(1 for n in lines if n and not n.startswith(COMMENT_TOKEN))
    console.ok(f"{out_path}: {count} {noun} play(s)")
