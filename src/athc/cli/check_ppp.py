"""`athc check-ppp` — validate a profile with its gameplan, and how they fit.

Replaced `profile check --gameplan`. It shares no code with `profile check` or
`gameplan check`: its reading, rules loading and reports live here, printed in
their format.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path, PureWindowsPath

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli.gameplan._common import build_pool
from athc.config import (
    LEAGUE_FILE,
    ConfigFileError,
    LeagueError,
    load_league_config,
)
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
from athc.fbpro98_lg2 import InvalidLg2Error, Lg2File, UnsupportedLg2Error, read_lg2
from athc.fbpro98_profile import (
    InvalidProfileError,
    Profile,
    UnsupportedProfileError,
    read_profile,
)
from athc.gameplan import Rules, validate_gameplan
from athc.gameplan import RulesFileError as GameplanRulesFileError
from athc.gameplan import Violation as GameplanViolation
from athc.gameplan import load_rules as load_gameplan_rule_files
from athc.gameplan.config import load_config as load_gameplan_config
from athc.playpool import PlayPool
from athc.profile import (
    CompatIssue,
    ProfileRules,
    check_gameplan_compatibility,
    gameplan_extra_categories,
    validate_profile,
)
from athc.profile import RulesFileError as ProfileRulesFileError
from athc.profile import Violation as ProfileViolation
from athc.profile import load_rules as load_profile_rule_files
from athc.profile.config import load_config as load_profile_config

PROG = "athc check-ppp"
LEAGUE_PATH_KEY = "path"
logger = logging.getLogger(__name__)


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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if second is None:
        ctx.exit(check_directory(first, league, recursive=recursive))
    ctx.exit(check_pair(first, second, league))


def check_pair(first: str, second: str, league: str | None) -> int:
    """Check one profile with one gameplan; return the exit code."""
    profile_path, gameplan_path, input_errors = sort_inputs([first, second])
    for error in input_errors:
        logger.error("%s: %s", PROG, error)
    if input_errors or profile_path is None or gameplan_path is None:
        return 2  # both files are required, so neither is checked

    # A setup error never hides another error: every setup problem is logged,
    # and each file is still read and side-checked, which needs no rules. Like
    # `gameplan check` and `profile check`, though, a setup error or a side
    # mismatch stops every rule check and the summary, so no file is validated.
    logged: set[str] = set()
    setup = load_setup(league, logged)
    reports, mismatch = check_files(profile_path, gameplan_path, setup)
    if setup is None or mismatch is not None:
        # Nothing was validated: the reports hold only unreadable-file lines.
        for _, line in reports:
            click.echo(line)
        if mismatch is not None:
            click.echo(mismatch)
        return 2
    return summarize(reports)


def check_directory(raw: str, league: str | None, *, recursive: bool) -> int:
    """Check the league-file pairs in a directory (each folder of its tree
    with `recursive`); return the exit code."""
    directory = Path(raw)
    if not directory.exists():
        logger.error("%s: %s: path does not exist", PROG, raw)
        return 2
    if not directory.is_dir():
        logger.error(
            "%s: %s: not a directory; pass one profile and one gameplan, "
            "or a directory",
            PROG,
            raw,
        )
        return 2

    # Every setup problem is logged, as in two-file mode; the league file is
    # what names the pairs, so without it there is nothing to check.
    logged: set[str] = set()
    setup = load_setup(league, logged)
    lg2 = load_lg2(league, logged)
    if lg2 is None:
        return 2
    pairs = find_pairs(directory, league_pairs(lg2), recursive=recursive)
    if not pairs:
        # Not an error: no file has to be there. A status line, so stdout.
        scope = "tree" if recursive else "directory"
        click.echo(
            f"{raw}: no profile and gameplan pairs from the league file in {scope}"
        )
        return 2 if setup is None else 0

    reports: list[tuple[int, str]] = []
    reported: set[Path] = set()  # gameplans with a line of their own already
    for profile_path, gameplan_path in pairs:
        pair_reports, mismatch = check_files(
            profile_path,
            gameplan_path,
            setup,
            report_gameplan=gameplan_path not in reported,
        )
        if mismatch is not None:
            # This pair only: the league file paired them, not the user.
            reports.append((-1, mismatch))
            continue
        reported.add(gameplan_path)
        reports.extend(pair_reports)
    if setup is None:
        # Nothing was validated: only unreadable-file and mismatch lines.
        for _, line in reports:
            click.echo(line)
        return 2
    return summarize(reports)


def load_lg2(league: str | None, logged: set[str]) -> Lg2File | None:
    """The league's `.lg2`, read from the folder `path` names (the file
    is named after the league); None (already logged) when it can't load."""
    try:
        config = load_league_config(league)
    except (ConfigFileError, LeagueError) as error:
        _log_once(error, logged)
        return None
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        logger.error(
            "%s: no %s for the league; set %s in %s",
            PROG,
            LEAGUE_PATH_KEY,
            LEAGUE_PATH_KEY,
            config.dir / LEAGUE_FILE,
        )
        return None
    try:
        return read_lg2(config.name, folder)
    except (OSError, InvalidLg2Error, UnsupportedLg2Error) as error:
        logger.error("%s: %s", PROG, error)
        return None


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


def summarize(reports: Sequence[tuple[int, str]]) -> int:
    """Print every report and the summary line; return the exit code."""
    total = files_with_violations = total_violations = io_errors = 0
    for count, line in reports:
        click.echo(line)
        total += 1
        if count < 0:
            io_errors += 1
        elif count > 0:
            files_with_violations += 1
            total_violations += count

    click.echo()
    click.echo(
        f"{total} file(s) checked, {total_violations} violation(s) "
        f"across {files_with_violations} file(s)."
    )
    if io_errors:
        return 2
    return 1 if total_violations else 0


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
            errors.append(f"{raw}: path does not exist")
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


def load_setup(league: str | None, logged: set[str]) -> Setup | None:
    """The league's profile rules, gameplan rules and play pool; None (every
    problem already logged) when any of them can't load."""
    profile_rules = load_profile_rules(league, logged)
    gameplan_setup = load_gameplan_setup(league, logged)
    if profile_rules is None or gameplan_setup is None:
        return None
    return Setup(profile_rules, *gameplan_setup)


def load_profile_rules(league: str | None, logged: set[str]) -> ProfileRules | None:
    """The league's profile rules; None (already logged) when they can't load."""
    try:
        config = load_profile_config(league)
    except (ConfigFileError, LeagueError) as error:
        _log_once(error, logged)
        return None
    return _load_rules(config.rule_files, load_profile_rule_files, "profile.toml")


def load_gameplan_setup(
    league: str | None, logged: set[str]
) -> tuple[Rules, PlayPool] | None:
    """The league's gameplan rules and play pool; None (already logged) when
    either can't load."""
    try:
        config = load_gameplan_config(league)
    except ValueError as error:  # league, athc.ini and play_path errors alike
        _log_once(error, logged)
        return None
    rules = _load_rules(
        config.rule_files,
        partial(load_gameplan_rule_files, labels=config.categories),
        "gameplan.toml",
    )
    # Built even when the rules failed, so a bad pool is reported in the same run.
    pool = build_pool(
        config.play_path,
        config.playpool_rules,
        config.categories,
        prog=PROG,
        logger=logger,
    )
    if rules is None or pool is None:
        return None
    return rules, pool


def check_files(
    profile_path: Path,
    gameplan_path: Path,
    setup: Setup | None,
    *,
    report_gameplan: bool = True,
) -> tuple[list[tuple[int, str]], str | None]:
    """Each file's `(count, line)`, profile first, plus the side-mismatch error
    line. Both files are read, so a read error or mismatch reports even without
    rules. A file is validated only when the setup loaded and the sides match;
    the cross-check runs only on two readable files. Without `report_gameplan`
    (a gameplan another pair already reported), the gameplan is still read for
    the cross-check but gets no line of its own."""
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
    elif setup is not None:
        other = gp if isinstance(gp, GamePlan) else None
        reports.append(profile_report(profile_path, prof, setup, other))
    if report_gameplan:
        if isinstance(gp, str):
            reports.append((-1, gp))
        elif setup is not None:
            reports.append(gameplan_report(gameplan_path, gp, setup))
    return reports, None


def read_profile_file(path: Path) -> Profile | str:
    """The profile, or its `<path>: ERROR: ...` line when it can't be read."""
    try:
        return read_profile(str(path))
    except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
        return f"{path}: ERROR: {error}"


def read_gameplan_file(path: Path) -> GamePlan | str:
    """The gameplan, or its `<path>: ERROR: ...` line when it can't be read."""
    try:
        return read_gameplan(str(path))
    except (OSError, InvalidGamePlanError, ValueError) as error:
        return f"{path}: ERROR: {error}"


def side_mismatch(path: Path, prof: Profile, gameplan: GamePlan) -> str | None:
    """The `<path>: ERROR: ...` line when the profile and gameplan sides differ."""
    if prof.is_offense == gameplan.is_offense:
        return None
    return (
        f"{path}: ERROR: profile is {_side(prof.is_offense)} but gameplan is "
        f"{_side(gameplan.is_offense)}; sides must match"
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
            return 0, f"{path}: OK ({summary})"
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
        head = f"{path}: OK ({summary}; gameplan compatible)"
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
    """`(count, line)` in `gameplan check`'s format: OK, or its violations."""
    violations = validate_gameplan(gp, setup.gameplan_rules, setup.pool)
    normal = sum(1 for p in gp.normal_plays if p is not None)
    summary = f"{_side(gp.is_offense)}, {normal} normal"
    if not violations:
        return 0, f"{path}: OK ({summary})"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_gameplan_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _load_rules[R](
    files: Sequence[Path], load: Callable[[list[Path]], R], name: str
) -> R | None:
    """Load a rule set; log every problem and return None when it can't load."""
    if not files:
        logger.error(
            "%s: no rules configured - nothing to check. Add %s to the league folder.",
            PROG,
            name,
        )
        return None
    try:
        return load(list(files))
    except (ProfileRulesFileError, GameplanRulesFileError) as error:
        for line in error.errors:
            logger.error("%s: %s", PROG, line)
        return None
    except OSError as error:
        logger.error("%s: %s", PROG, error)
        return None


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


def _log_once(error: Exception, logged: set[str]) -> None:
    """Log a config error once: both sides resolve the same league."""
    message = str(error)
    if message not in logged:
        logged.add(message)
        logger.error("%s: %s", PROG, message)
