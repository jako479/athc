"""`athc check-ppp` — validate one profile and/or one gameplan, and how they fit."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import click

from athc.cli import selected_league
from athc.cli.gameplan._common import build_pool
from athc.cli.gameplan._common import resolve_rules as resolve_gameplan_rules
from athc.cli.gameplan.check import read_file as read_gameplan_file
from athc.cli.gameplan.check import report as report_gameplan
from athc.cli.profile._common import resolve_rules as resolve_profile_rules
from athc.cli.profile.check import read_file as read_profile_file
from athc.cli.profile.check import report as report_profile
from athc.cli.profile.check import side_mismatch
from athc.config import ConfigFileError, LeagueError
from athc.fbpro98_gameplan import GamePlan
from athc.fbpro98_profile import Profile
from athc.gameplan import Rules
from athc.gameplan.config import load_config as load_gameplan_config
from athc.playpool import PlayPool
from athc.profile import ProfileRules, gameplan_extra_categories
from athc.profile.config import load_config as load_profile_config

PROG = "athc check-ppp"
logger = logging.getLogger(__name__)


@click.command(name="check-ppp")
@click.argument("first", metavar="FILE")
@click.argument("second", metavar="[FILE]", required=False)
@click.pass_context
def check_ppp(ctx: click.Context, first: str, second: str | None) -> None:
    """Validate a .prf profile and/or a .pln gameplan against the league rules.

    Pass one profile, one gameplan, or both, in either order; the extension
    tells them apart. Each file is checked like `profile check` and `gameplan
    check`. With both, they must be the same side, and every play category the
    profile uses must have a custom play in the gameplan; gameplan categories
    the profile never uses are listed as info only.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    league = selected_league(ctx)

    profile_path, gameplan_path, input_errors = sort_inputs(
        [first] if second is None else [first, second]
    )
    for error in input_errors:
        logger.error("%s: %s", PROG, error)
    if profile_path is None and gameplan_path is None:
        ctx.exit(2)

    # A setup error on one side never hides another error: every setup problem
    # is logged, and each file is still read and side-checked without rules.
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

    reports, mismatch = check_files(
        profile_path, profile_rules, gameplan_path, gameplan_setup
    )
    if not reports and mismatch is None:
        ctx.exit(2)  # only setup errors, all logged above
    total = files_with_violations = total_violations = io_errors = 0
    for count, line in reports:
        click.echo(line)
        total += 1
        if count < 0:
            io_errors += 1
        elif count > 0:
            files_with_violations += 1
            total_violations += count
    if mismatch is not None:
        click.echo(mismatch)

    click.echo()
    click.echo(
        f"{total} file(s) checked, {total_violations} violation(s) "
        f"across {files_with_violations} file(s)."
    )
    if setup_failed or io_errors or input_errors or mismatch is not None:
        ctx.exit(2)
    ctx.exit(1 if total_violations else 0)


def sort_inputs(paths: Sequence[str]) -> tuple[Path | None, Path | None, list[str]]:
    """Split the FILE arguments by extension into `(profile, gameplan, errors)`.

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
    return resolve_profile_rules(
        config.rule_files, prog=PROG, logger=logger, option=None
    )


def load_gameplan_setup(
    league: str | None, logged: set[str]
) -> tuple[Rules, PlayPool] | None:
    """The league's gameplan rules and play pool; None (already logged) when
    either can't load."""
    try:
        config = load_gameplan_config(league, play_path_option=None)
    except ValueError as error:  # league, athc.ini and play_path errors alike
        _log_once(error, logged)
        return None
    rules = resolve_gameplan_rules(
        config.rule_files, prog=PROG, logger=logger, option=None
    )
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
    line. Every file is read, so a read error or mismatch reports even when its
    rules failed to load; a file is validated only when they loaded. The
    cross-check runs only on two readable files of the same side."""
    gp: GamePlan | None = None
    gameplan_report: tuple[int, str] | None = None
    if gameplan_path is not None:
        read = read_gameplan_file(gameplan_path)
        if isinstance(read, str):
            gameplan_report = (-1, read)
        else:
            gp = read
            if gameplan_setup is not None:
                gameplan_report = report_gameplan(gameplan_path, gp, *gameplan_setup)

    reports: list[tuple[int, str]] = []
    mismatch: str | None = None
    if profile_path is not None:
        prof = read_profile_file(profile_path)
        if isinstance(prof, str):
            reports.append((-1, prof))
        else:
            if gp is not None:
                mismatch = side_mismatch(profile_path, prof, gp)
            if profile_rules is not None:
                same_side = None if mismatch else gp
                reports.append(
                    profile_report(profile_path, prof, profile_rules, same_side)
                )
    if gameplan_report is not None:
        reports.append(gameplan_report)
    return reports, mismatch


def profile_report(
    path: Path, prof: Profile, rules: ProfileRules, gameplan: GamePlan | None
) -> tuple[int, str]:
    """`profile check`'s report, with the cross-check fixed to the league rule
    rather than the `[gameplan_compatibility]` flags (those stay for `profile
    check`): a profile category the gameplan lacks always fails, and a gameplan
    category the profile never uses is always an info line that doesn't count."""
    league_rule = replace(
        rules,
        profile_categories_in_gameplan=True,
        gameplan_categories_in_profile=False,
    )
    count, text = report_profile(path, prof, league_rule, gameplan)
    if gameplan is None:
        return count, text
    info = "".join(
        f"\n  gameplan info: {issue.message}"
        for issue in gameplan_extra_categories(prof, gameplan)
    )
    return count, text + info


def _log_once(error: Exception, logged: set[str]) -> None:
    """Log a config error once: both sides resolve the same league."""
    message = str(error)
    if message not in logged:
        logged.add(message)
        logger.error("%s: %s", PROG, message)
