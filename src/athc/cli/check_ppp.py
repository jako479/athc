"""`athc check-ppp` — validate a profile with its gameplan, and how they fit.

Replaced `profile check --gameplan`. It shares no code with `profile check` or
`gameplan check`: its reading, rules loading and reports live here, printed in
their format.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli.gameplan._common import build_pool
from athc.cli.gameplan._common import load_rules_or_raise as load_gameplan_rules
from athc.cli.profile._common import load_rules_or_raise as load_profile_rules
from athc.config import LEAGUE_FILE, load_league_config
from athc.console import console
from athc.errors import AthcError, ConfigFileError
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
from athc.fbpro98_lg2 import Lg2File, read_lg2
from athc.fbpro98_profile import (
    InvalidProfileError,
    Profile,
    UnsupportedProfileError,
    read_profile,
)
from athc.gameplan import Rules, validate_gameplan
from athc.gameplan import Violation as GameplanViolation
from athc.gameplan.config import load_config as load_gameplan_config
from athc.playpool import PlayPool
from athc.profile import (
    CompatIssue,
    ProfileRules,
    check_gameplan_compatibility,
    gameplan_extra_categories,
    validate_profile,
)
from athc.profile import Violation as ProfileViolation
from athc.profile.config import load_config as load_profile_config

LEAGUE_PATH_KEY = "path"


@dataclass(frozen=True, slots=True)
class Setup:
    """The league's loaded rules and play pool: all three, or no check runs."""

    profile_rules: ProfileRules
    gameplan_rules: Rules
    pool: PlayPool


@click.command(name="check-ppp", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.argument("first", metavar="path")
@click.argument("second", metavar="[path]", required=False)
@click.option(
    "-r",
    "--recursive",
    is_flag=True,
    help="Recurse into subdirectories of a directory path.",
)
@league_option
@click.pass_context
def check_ppp(
    ctx: click.Context,
    first: str,
    second: str | None,
    recursive: bool,
    league: str | None,
) -> None:
    """Validate .prf profiles with their .pln gameplans against the league rules.

    Pass one profile and one gameplan, in either order (the extension tells
    them apart), or a directory (the whole tree with -r). In a directory, the
    league's .lg2 file, in the folder that path in league.toml names, says
    which files go together (1st half offense profile with 1st half offense
    gameplan, and so on); every pair whose two files are both in the same
    folder is checked.

    Each file is checked like `profile check` and `gameplan check`. A pair
    must be the same side. The league's profile rules decide whether profile
    categories with no custom play in the gameplan fail the check, and its
    gameplan rules whether gameplan categories the profile never uses do;
    unused gameplan categories that don't fail are listed as info only.
    """
    if second is None:
        ctx.exit(check_directory(first, league, recursive=recursive))
    ctx.exit(check_pair(first, second, league))


def check_pair(first: str, second: str, league: str | None) -> int:
    """Check one profile with one gameplan; return the exit code."""
    profile_path, gameplan_path, input_errors = sort_inputs([first, second])
    for error in input_errors:
        console.fail(error)
    if input_errors or profile_path is None or gameplan_path is None:
        return 2  # both files are required, so neither is checked
    setup = load_setup(league)
    reports, mismatch = check_files(profile_path, gameplan_path, setup)
    if mismatch is not None:
        # The user paired them: a mismatch is the run's failure.
        console.fail(mismatch)
        return 2
    return summarize(reports)


def check_directory(raw: str, league: str | None, *, recursive: bool) -> int:
    """Check the league-file pairs in a directory (each folder of its tree
    with `recursive`); return the exit code."""
    directory = Path(raw)
    if not directory.exists():
        console.fail(f"{raw}: not found")
        return 2
    if not directory.is_dir():
        console.fail(
            f"{raw}: not a directory; pass one profile and one gameplan, or a directory"
        )
        return 2
    setup = load_setup(league)
    lg2 = load_lg2(league)  # names the pairs: without it there is nothing to check
    pairs = find_pairs(directory, league_pairs(lg2), recursive=recursive)
    if not pairs:
        # Not an error: no file has to be there.
        scope = "tree" if recursive else "directory"
        console.warn(
            f"{raw}: no profile and gameplan pairs from the league file in {scope}"
        )

    reports: list[tuple[int, str]] = []
    done: set[Path] = set()  # gameplans with a line of their own already
    failed = 0
    for profile_path, gameplan_path in pairs:
        try:
            pair_reports, mismatch = check_files(
                profile_path,
                gameplan_path,
                setup,
                report_gameplan=gameplan_path not in done,
            )
        except (AthcError, OSError) as error:
            console.fail(str(error))
            failed += 1
            continue
        except Exception:
            console.unexpected(f"{profile_path} + {gameplan_path}")
            failed += 1
            continue
        if mismatch is not None:
            # This pair only: the league file paired them, not the user.
            reports.append((-1, mismatch))
            continue
        done.add(gameplan_path)
        reports.extend(pair_reports)
    return summarize(reports, failed)


def load_setup(league: str | None) -> Setup:
    """The league's profile rules, gameplan rules and play pool. The first
    problem found (league, config, rules, pool) raises; nothing is checked
    without all three."""
    profile_config = load_profile_config(league)
    profile_rules = load_profile_rules(profile_config.rule_files)
    gameplan_config = load_gameplan_config(league)
    gameplan_rules = load_gameplan_rules(
        gameplan_config.rule_files, gameplan_config.categories
    )
    pool = build_pool(
        gameplan_config.play_path,
        gameplan_config.playpool_rules,
        gameplan_config.categories,
    )
    return Setup(profile_rules, gameplan_rules, pool)


def load_lg2(league: str | None) -> Lg2File:
    """The league's `.lg2`, read from the folder `path` names (the file is
    named after the league). ConfigFileError when the league has no `path`."""
    config = load_league_config(league)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(
            f"no {LEAGUE_PATH_KEY} for the league; set {LEAGUE_PATH_KEY} in "
            f"{config.dir / LEAGUE_FILE}"
        )
    return read_lg2(config.name, folder)


def league_pairs(lg2: Lg2File) -> list[tuple[str, str]]:
    """Every team's `(profile, gameplan)` file names, casefolded, in file
    order: per team, 1st-half offense, 1st-half defense, 2nd-half offense,
    2nd-half defense. Each pair once. The folders are dropped: they say where
    the game reads the files, not where they are being checked."""
    pairs: dict[tuple[str, str], None] = {}  # a dict keeps the first order
    for team in lg2.teams:
        for half in (team.first_half, team.second_half):
            for pair in (half.offense, half.defense):
                pairs.setdefault((_name(pair.profile), _name(pair.gameplan)), None)
    return list(pairs)


def find_pairs(
    directory: Path, pairs: Sequence[tuple[str, str]], *, recursive: bool
) -> list[tuple[Path, Path]]:
    """The `(profile, gameplan)` paths of each name pair whose two files are
    both in one folder, names matched ignoring case. Just `directory`, or with
    `recursive` every folder in its tree: top first, then subfolders by name;
    a folder that can't be read is skipped, as `os.walk` does. Inside a
    folder, `pairs` order. Each folder stands alone, since weeks and seasons
    reuse the same file names."""
    found: list[tuple[Path, Path]] = []
    for folder, subfolders, filenames in directory.walk():
        subfolders.sort(key=str.casefold)  # in place: walk descends in this order
        if not recursive:
            subfolders.clear()
        files = {name.casefold(): folder / name for name in filenames}
        found.extend(
            (files[profile], files[gameplan])
            for profile, gameplan in pairs
            if profile in files and gameplan in files
        )
    return found


def _name(location: str) -> str:
    return PureWindowsPath(location).name.casefold()


def summarize(reports: Sequence[tuple[int, str]], failed: int = 0) -> int:
    """Print every report and the tally; return the exit code. `failed` counts
    the pairs that never produced a report."""
    total = files_with_violations = 0
    for count, line in reports:
        total += 1
        if count < 0:
            failed += 1
            console.fail(line)
        elif count > 0:
            files_with_violations += 1
            head, *details = line.split("\n")
            console.result(head)
            for detail in details:
                console.print(detail)
        else:
            console.ok(line)

    console.print()
    console.result(
        f"{total} file(s) checked, {files_with_violations} with violations, "
        f"{failed} failed"
    )
    return 2 if failed else 1 if files_with_violations else 0


def sort_inputs(paths: Sequence[str]) -> tuple[Path | None, Path | None, list[str]]:
    """Split the file arguments by extension into `(profile, gameplan, errors)`.

    A missing path, a non-file, another extension, or a second file of a kind
    is an error.
    """
    profile: Path | None = None
    gameplan: Path | None = None
    errors: list[str] = []
    for raw in paths:
        path = Path(raw)
        suffix = path.suffix.lower()
        if not path.exists():
            errors.append(f"{raw}: not found")
        elif not path.is_file():
            errors.append(f"{raw}: not a file")
        elif suffix == ".prf" and profile is None:
            profile = path
        elif suffix == ".pln" and gameplan is None:
            gameplan = path
        elif suffix in (".prf", ".pln"):
            errors.append(
                f"{raw}: second {suffix} file; pass one profile and one gameplan"
            )
        else:
            errors.append(f"{raw}: not a .prf or .pln file")
    return profile, gameplan, errors


def check_files(
    profile_path: Path,
    gameplan_path: Path,
    setup: Setup,
    *,
    report_gameplan: bool = True,
) -> tuple[list[tuple[int, str]], str | None]:
    """Each file's `(count, line)`, profile first, plus the side-mismatch
    line. Both files are read, so a read error or mismatch reports even without
    rules. A file is validated only when the sides match; the cross-check runs
    only on two readable files. Without `report_gameplan` (a gameplan another
    pair already reported), the gameplan is still read for the cross-check but
    gets no line of its own."""
    prof = read_profile_file(profile_path)
    gp = read_gameplan_file(gameplan_path)
    if (
        isinstance(prof, Profile)
        and isinstance(gp, GamePlan)
        and (mismatch := side_mismatch(profile_path, prof, gp)) is not None
    ):
        return [], mismatch  # both read fine, so there is nothing else to report

    reports: list[tuple[int, str]] = []
    if isinstance(prof, str):
        reports.append((-1, prof))
    else:
        other = gp if isinstance(gp, GamePlan) else None
        reports.append(profile_report(profile_path, prof, setup, other))
    if report_gameplan:
        if isinstance(gp, str):
            reports.append((-1, gp))
        else:
            reports.append(gameplan_report(gameplan_path, gp, setup))
    return reports, None


def read_profile_file(path: Path) -> Profile | str:
    """The profile, or its `<path>: <reason>` line when it can't be read."""
    try:
        return read_profile(str(path))
    except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
        return str(error)


def read_gameplan_file(path: Path) -> GamePlan | str:
    """The gameplan, or its `<path>: <reason>` line when it can't be read."""
    try:
        return read_gameplan(str(path))
    except (OSError, InvalidGamePlanError) as error:
        return str(error)


def side_mismatch(path: Path, prof: Profile, gameplan: GamePlan) -> str | None:
    """The `<path>: profile is X but gameplan is Y` line when the sides differ."""
    if prof.is_offense == gameplan.is_offense:
        return None
    return (
        f"{path}: profile is {_side(prof.is_offense)} but gameplan is "
        f"{_side(gameplan.is_offense)}"
    )


def profile_report(
    path: Path, prof: Profile, setup: Setup, gameplan: GamePlan | None
) -> tuple[int, str]:
    """`(count, line)` in `profile check`'s format. With a same-side gameplan,
    the compatibility settings pick what counts: profile categories the
    gameplan lacks are issues when the profile rules require it, else
    unchecked; gameplan categories the profile never uses are issues when the
    gameplan rules require it, else info lines that don't count."""
    violations = validate_profile(prof, setup.profile_rules)
    summary = f"{_side(prof.is_offense)}, FG range {prof.field_goal_range}"
    details = [f"  {_profile_violation(v)}" for v in violations]
    if gameplan is None:
        if not violations:
            return 0, f"{path}: {summary}"
        head = f"{path}: {len(violations)} violation(s) ({summary})"
        return len(violations), "\n".join([head, *details])

    issues: tuple[CompatIssue, ...] = ()
    if setup.profile_rules.require_all_profile_categories_in_gameplan:
        issues += check_gameplan_compatibility(prof, gameplan)
    extras = gameplan_extra_categories(prof, gameplan)
    if setup.gameplan_rules.require_all_gameplan_categories_in_profile:
        issues += extras
        extras = ()
    total = len(violations) + len(issues)
    if total == 0:
        head = f"{path}: {summary}; gameplan compatible"
    else:
        head = (
            f"{path}: {len(violations)} violation(s), "
            f"{len(issues)} gameplan issue(s) ({summary})"
        )
    lines = [head, *details]
    lines.extend(f"  gameplan: {issue.message}" for issue in issues)
    lines.extend(f"  gameplan info: {extra.message}" for extra in extras)
    return total, "\n".join(lines)


def gameplan_report(path: Path, gp: GamePlan, setup: Setup) -> tuple[int, str]:
    """`(count, line)` in `gameplan check`'s format: clean, or its violations."""
    violations = validate_gameplan(gp, setup.gameplan_rules, setup.pool)
    normal = sum(1 for p in gp.normal_plays if p is not None)
    summary = f"{_side(gp.is_offense)}, {normal} normal"
    if not violations:
        return 0, f"{path}: {summary}"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_gameplan_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _profile_violation(v: ProfileViolation) -> str:
    prefix = (
        f"[situation {v.situation_number}] " if v.situation_number is not None else ""
    )
    return f"{prefix}{v.message}"


def _gameplan_violation(v: GameplanViolation) -> str:
    prefix = f"[{v.category}] " if v.category else ""
    return f"{prefix}{v.message}"


def _side(is_offense: bool) -> str:
    return "offense" if is_offense else "defense"
