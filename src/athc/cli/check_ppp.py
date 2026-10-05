"""`athc check-ppp` — validate one profile and/or one gameplan, and how they fit.

Meant to replace `gameplan check` and `profile check`, so it takes nothing from
those two commands: its reading, rules loading and reports live here, printed
in their format.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli.gameplan._common import build_pool
from athc.config import ConfigFileError, LeagueError
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
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
logger = logging.getLogger(__name__)


@click.command(name="check-ppp", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.argument("first", metavar="file")
@click.argument("second", metavar="[file]", required=False)
@league_option
@click.pass_context
def check_ppp(
    ctx: click.Context, first: str, second: str | None, league: str | None
) -> None:
    """Validate a .prf profile and/or a .pln gameplan against the league rules.

    Pass one profile, one gameplan, or both, in either order; the extension
    tells them apart. Each file is checked like `profile check` and `gameplan
    check`. With both, they must be the same side, and every play category the
    profile uses must have a custom play in the gameplan; gameplan categories
    the profile never uses are listed as info only.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    profile_path, gameplan_path, input_errors = sort_inputs(
        [first] if second is None else [first, second]
    )
    for error in input_errors:
        logger.error("%s: %s", PROG, error)
    if profile_path is None and gameplan_path is None:
        ctx.exit(2)

    # A setup error never hides another error: every setup problem is logged,
    # and each file is still read and side-checked, which needs no rules. Like
    # `gameplan check` and `profile check`, though, a setup error or a side
    # mismatch stops every rule check and the summary, so no file is validated.
    logged: set[str] = set()
    profile_rules = (
        load_profile_rules(league, logged) if profile_path is not None else None
    )
    gameplan_setup = (
        load_gameplan_setup(league, logged) if gameplan_path is not None else None
    )
    setup_failed = (profile_path is not None and profile_rules is None) or (
        gameplan_path is not None and gameplan_setup is None
    )
    if setup_failed:
        profile_rules = gameplan_setup = None

    reports, mismatch = check_files(
        profile_path, profile_rules, gameplan_path, gameplan_setup
    )
    if setup_failed or mismatch is not None:
        # Nothing was validated: the reports hold only unreadable-file lines.
        for _, line in reports:
            click.echo(line)
        if mismatch is not None:
            click.echo(mismatch)
        ctx.exit(2)

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
    if io_errors or input_errors:
        ctx.exit(2)
    ctx.exit(1 if total_violations else 0)


def sort_inputs(paths: Sequence[str]) -> tuple[Path | None, Path | None, list[str]]:
    """Split the file arguments by extension into `(profile, gameplan, errors)`.

    A missing path, a non-file, another extension, or a second file of a kind
    is an error; the files that pass are still checked.
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
                f"{raw}: second {suffix} file; pass one profile and/or one gameplan"
            )
        else:
            errors.append(f"{raw}: not a .prf or .pln file")
    return profile, gameplan, errors


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
    rules = _load_rules(config.rule_files, load_gameplan_rule_files, "gameplan.toml")
    # Built even when the rules failed, so a bad pool is reported in the same run.
    pool = build_pool(config.play_path, config.playpool_rules, prog=PROG, logger=logger)
    if rules is None or pool is None:
        return None
    return rules, pool


def check_files(
    profile_path: Path | None,
    profile_rules: ProfileRules | None,
    gameplan_path: Path | None,
    gameplan_setup: tuple[Rules, PlayPool] | None,
) -> tuple[list[tuple[int, str]], str | None]:
    """Each file's `(count, line)`, profile first, plus the side-mismatch error
    line. Every file is read, so a read error or mismatch reports even without
    rules. A file is validated only when its rules are given and the sides
    match; the cross-check runs only on two readable files."""
    prof = read_profile_file(profile_path) if profile_path is not None else None
    gp = read_gameplan_file(gameplan_path) if gameplan_path is not None else None
    if (
        profile_path is not None
        and isinstance(prof, Profile)
        and isinstance(gp, GamePlan)
        and (mismatch := side_mismatch(profile_path, prof, gp)) is not None
    ):
        return [], mismatch  # both read fine, so there is nothing else to report

    reports: list[tuple[int, str]] = []
    if profile_path is not None:
        if isinstance(prof, str):
            reports.append((-1, prof))
        elif isinstance(prof, Profile) and profile_rules is not None:
            other = gp if isinstance(gp, GamePlan) else None
            reports.append(profile_report(profile_path, prof, profile_rules, other))
    if gameplan_path is not None:
        if isinstance(gp, str):
            reports.append((-1, gp))
        elif isinstance(gp, GamePlan) and gameplan_setup is not None:
            reports.append(gameplan_report(gameplan_path, gp, *gameplan_setup))
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
    path: Path, prof: Profile, rules: ProfileRules, gameplan: GamePlan | None
) -> tuple[int, str]:
    """`(count, line)` in `profile check`'s format. With a same-side gameplan,
    the cross-check follows the league rule, not the `[gameplan_compatibility]`
    flags (those are for `profile check`): a profile category the gameplan
    lacks is an issue that counts, and a gameplan category the profile never
    uses is an info line that doesn't."""
    violations = validate_profile(prof, rules)
    summary = f"{_side(prof.is_offense)}, FG range {prof.field_goal_range}"
    details = [f"  {_profile_violation(v)}" for v in violations]
    if gameplan is None:
        if not violations:
            return 0, f"{path}: OK ({summary})"
        head = f"{path}: {len(violations)} violation(s) ({summary})"
        return len(violations), "\n".join([head, *details])

    issues = check_gameplan_compatibility(prof, gameplan)
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
    lines.extend(
        f"  gameplan info: {extra.message}"
        for extra in gameplan_extra_categories(prof, gameplan)
    )
    return total, "\n".join(lines)


def gameplan_report(
    path: Path, gp: GamePlan, rules: Rules, pool: PlayPool
) -> tuple[int, str]:
    """`(count, line)` in `gameplan check`'s format: OK, or its violations."""
    violations = validate_gameplan(gp, rules, pool)
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
            "%s: no rules configured - nothing to check. "
            "Add rules\\%s to the league folder.",
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
