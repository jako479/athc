"""Shared helpers for `athc gameplan` subcommands: files, your team's game
plans, search, rules, pool, listing."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from athc.cli._files import Collected, collect_files, is_glob, named_file
from athc.cli._team import (
    LEAGUE_PATH_KEY,
    PPP_PATH_KEY,
    TEAM_KEY,
    Located,
    Source,
    folder_reason,
    folders,
    is_key,
    is_yours,
    league_file_names,
    load_league_files,
    locate,
    location_hint,
    option_team,
    path_not_set,
    ppp_folder,
    setting_team,
    team_files,
    team_label,
    team_not_set,
)
from athc.config import LEAGUE_FILE, load_league_config, play_dir
from athc.console import console
from athc.errors import (
    AthcError,
    ConfigFileError,
    missing_reason,
)
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
    "TEAM_HELP",
    "Collected",
    "build_pool",
    "category_of",
    "collect_entries",
    "collect_files",
    "emit_play_list",
    "epilog",
    "find_in_gameplan",
    "format_violation",
    "is_glob",
    "is_key",
    "is_one_file",
    "load_rules_or_raise",
    "named_file",
    "normal_play_lines",
    "one_game_plan",
    "parse_play_list",
    "path_option",
    "read_play_list",
    "require_a_key",
    "require_key_path",
    "scope",
    "special_play_lines",
]

COMMENT_TOKEN = "::"

# ── help ─────────────────────────────────────────────────────────────────────

TEAM_HELP = "Team the game plan keys refer to"

# The \b lines keep Click from joining the lines of each block into one.
_KEYS_BLOCK = """\b
Game plan keys, for your team's game plans:
  off1  1st-half offense    def1  1st-half defense
  off2  2nd-half offense    def2  2nd-half defense
"""


def epilog(*examples: str) -> str:
    """The help's closing blocks: the game plan keys, then the examples."""
    lines = "".join(f"  {example}\n" for example in examples)
    return f"{_KEYS_BLOCK}\nExamples:\n\n\b\n{lines}"


def path_option(head: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """`--path PATH` on the three batch commands; `head` says what the game
    plans are for."""
    return click.option(
        "--path",
        default=None,
        metavar="PATH",
        help=(
            f"{head}: a .pln file, a folder, a wildcard or a game plan key "
            "(default: your team's game plans)."
        ),
    )


# ── your team's game plans: the four keys ─────────────────────────────────────

_WAY_PATH = "--path"  # the default scope's own way out
_WAY_FILE = "a .pln file"  # a key's own way out
_KEY_REQUIRED = "--team requires a game plan key (off1, def1, off2 or def2)."
_KEY_PATH_REQUIRED = (
    "--team requires --path to be a game plan key (off1, def1, off2 or def2) or "
    "left out."
)


def is_one_file(path: str | None) -> bool:
    """Whether `--path` names one file: a key, or a path that is neither a
    folder nor a wildcard (missing or not, as today)."""
    if path is None:
        return False
    return is_key(path) or not (Path(path).is_dir() or is_glob(path))


def require_a_key(team: str | None, operands: Sequence[str]) -> None:
    """`--team` with no key among the operands is a usage error: it would
    name nothing."""
    if team is not None and not any(is_key(raw) for raw in operands):
        raise click.UsageError(_KEY_REQUIRED, click.get_current_context())


def require_key_path(team: str | None, path: str | None) -> None:
    """On the batch commands `--team` needs `--path` left out or a key."""
    if team is not None and path is not None and not is_key(path):
        raise click.UsageError(_KEY_PATH_REQUIRED, click.get_current_context())


@dataclass(frozen=True, slots=True)
class TeamGamePlans:
    """One team's four game plans as the league file names them, and where
    to look for them."""

    label: str
    """The `.lge` team name, as the lines name the team."""

    locations: tuple[tuple[str, str], ...]
    """`(key, .lg2 location)` in `.lg2` order, a shared game plan repeated."""

    folder: Path | None
    """`ppp_path`, when it applies (your team only)."""

    league_path: Path
    yours: bool
    """The team `team` in league.toml names: the `ppp_path` hints apply."""

    def locate(self, key: str) -> Located:
        """The game plan `key` names: in `ppp_path`, else at its league
        location."""
        location = dict(self.locations)[key.casefold()]
        return locate(location, self.folder, self.league_path)

    def all_in(self, folder: Path | None) -> list[Located]:
        """The four in `.lg2` order, each once, looked up in `folder`, else at
        their league locations."""
        found: dict[Path, Located] = {}
        for _, location in self.locations:
            located = locate(location, folder, self.league_path)
            found.setdefault(located.path.resolve(), located)
        return list(found.values())

    def missing(self, located: Located) -> AthcError:
        """The error for a key's game plan that is not there: with the
        `ppp_path` hint at your team's league location."""
        reason = missing_reason(located.path)
        if located.source is Source.LEAGUE and self.yours:
            reason += f" {location_hint(_WAY_FILE)}"
        return AthcError(reason, located.path)


def team_game_plans(team: str | None, league: str | None, *, way: str) -> TeamGamePlans:
    """The game plans of the team `--team` names, else of `team` in
    league.toml. `team` is read before the league files, so a team that is not
    set shows first; `way` ends the "not set" lines with the command's own
    way out."""
    config = load_league_config(league)
    league_file = config.dir / LEAGUE_FILE
    yours = config.string(TEAM_KEY)
    if team is None and yours is None:
        raise ConfigFileError(team_not_set(f"--team or {way}"), league_file)
    league_path = config.path(LEAGUE_PATH_KEY)
    if league_path is None:
        raise ConfigFileError(path_not_set(way), league_file)
    files = load_league_files(config.name, league_path)
    if team is not None:
        number = option_team(team, files)
    else:
        assert yours is not None  # checked above: no --team needs `team`
        number = setting_team(yours, files, league_file)
    mine = is_yours(yours, files, number)
    folder = None
    if mine and (ppp_path := config.path(PPP_PATH_KEY)) is not None:
        folder = ppp_folder(ppp_path)
    return TeamGamePlans(
        label=team_label(files, number),
        locations=tuple(team_files(files.lg2.teams[number - 1], "gameplan")),
        folder=folder,
        league_path=league_path,
        yours=mine,
    )


def scope(
    path: str | None, team: str | None, league: str | None, *, recursive: bool
) -> Collected:
    """The game plans a batch command works on: a real `--path` through
    `collect_files`, as today; a key, that one game plan (missing: an error
    line); no `--path`, the team's four (`_team_scope`)."""
    if path is not None and not is_key(path):
        return collect_files([path], suffix=".pln", recursive=recursive)
    way = _WAY_PATH if path is None else _WAY_FILE
    plans = team_game_plans(team, league, way=way)
    if path is None:
        return _team_scope(plans, recursive=recursive)
    located = plans.locate(path)
    if not located.exists:
        return Collected(errors=[str(plans.missing(located))])
    return Collected(files=[located.path])


def _team_scope(plans: TeamGamePlans, *, recursive: bool) -> Collected:
    """The team's four game plans, each once, in `.lg2` order. At the league
    locations (`-r` ignored) a missing one is an error line, and none there is
    one line per folder, counted as one failed item. In `ppp_path` (each
    folder of its tree with `-r`) a missing one is a warning in a folder that
    holds any of the four, and none in the whole scope is one warning."""
    collected = Collected()
    if plans.folder is None:
        located = plans.all_in(None)
        if not any(item.exists for item in located):
            ending = f" {location_hint(_WAY_PATH)}" if plans.yours else ""
            parents = dict.fromkeys(item.path.parent for item in located)
            # One item, however many folders: the console prints each line.
            collected.errors.append(
                "\n".join(
                    f"{folder}: "
                    f"{folder_reason(folder, plans.label, 'game plans')}{ending}"
                    for folder in parents
                )
            )
            return collected
        for item in located:
            if item.exists:
                collected.files.append(item.path)
            else:
                collected.errors.append(f"{item.path}: {missing_reason(item.path)}")
        return collected
    found = False
    for folder in folders(plans.folder, recursive=recursive):
        located = plans.all_in(folder)
        if not any(item.exists for item in located):
            continue
        found = True
        for item in located:
            if item.exists:
                collected.files.append(item.path)
            else:
                collected.warnings.append(f"{item.path}: {missing_reason(item.path)}")
    if not found:
        names = league_file_names(location for _, location in plans.locations)
        collected.warnings.append(
            f"{plans.folder}: No {plans.label} game plans. The league file names "
            f"{names}."
        )
    return collected


def collect_entries(
    entries: Sequence[str], team: str | None, league: str | None, *, recursive: bool
) -> Collected:
    """`check`'s PATHs, left to right: a key is that one game plan (missing: a
    failed item); anything else goes through `collect_files`. Each file once."""
    collected = Collected()
    seen: set[Path] = set()
    plans: TeamGamePlans | None = None
    for raw in entries:
        if is_key(raw):
            if plans is None:
                plans = team_game_plans(team, league, way=_WAY_FILE)
            located = plans.locate(raw)
            if located.exists:
                part = Collected(files=[located.path])
            else:
                part = Collected(errors=[str(plans.missing(located))])
        else:
            part = collect_files([raw], suffix=".pln", recursive=recursive)
        collected.errors.extend(part.errors)
        collected.warnings.extend(part.warnings)
        for file in part.files:
            if (resolved := file.resolve()) not in seen:
                seen.add(resolved)
                collected.files.append(file)
    return collected


def one_game_plan(raw: str, team: str | None, league: str | None) -> Path:
    """The one game plan a one-file command was given: a path through
    `named_file`, a key through the team's files. AthcError when it is not
    there, checked before anything reads it."""
    if not is_key(raw):
        return named_file(raw)
    plans = team_game_plans(team, league, way=_WAY_FILE)
    located = plans.locate(raw)
    if not located.exists:
        raise plans.missing(located)
    return located.path


def read_play_list(path: Path) -> str:
    """A play list's text. AthcError, naming the list, when it is missing, a
    folder or not text (a `.pln` given by mistake)."""
    try:
        return named_file(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise AthcError("Not a valid play list.", path) from error


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
    """Play names in order with their line numbers; a blank line is an empty
    name, and blanks after the last name are dropped. Drops `::` lines and
    ` ::` trailers."""
    out: list[PlayLine] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            out.append(PlayLine(number, ""))
            continue
        if line.startswith(COMMENT_TOKEN):
            continue
        idx = line.find(f" {COMMENT_TOKEN}")
        if idx >= 0:
            line = line[:idx].rstrip()
        out.append(PlayLine(number, line))
    while out and not out[-1].name:
        out.pop()
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


def build_pool(play_path: Path, labels: CategoryLabels) -> PlayPool:
    """Build a PlayPool from `play_path` (each play classified from its file) with
    the league's category `labels` naming its folders. Every pool issue is a
    `WARN` line. ConfigFileError, naming `play_path`, when it is not a folder."""
    play_dir(play_path)
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
    # (side parity, no special play in a normal slot) keep every play's
    # category inside `order`, so none is dropped here.
    for category in order:
        names = [name for found, name in plays if found is category]
        if names:
            lines.append(f"{COMMENT_TOKEN} {labels.label(category)}")
            lines.extend(names)
    return lines


def special_play_lines(gp: GamePlan) -> list[str]:
    """The custom special play names in source order (empty slot = "")."""
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
