"""`athc check-ppp` — check profiles against their game plans, as the league
file pairs them.

Replaced `profile check --gameplan`. It shares no code with `profile check` or
`gameplan check`: its reading, rules loading and reports live here, printed in
their format. Which team, and where its files are, comes from the shared team
layer in `_team.py`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option, team_option
from athc.cli._team import (
    LEAGUE_PATH_KEY,
    PPP_PATH_KEY,
    TEAM_KEY,
    LeagueFiles,
    Located,
    Source,
    folder_reason,
    folders,
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
from athc.cli.gameplan._common import build_pool
from athc.cli.gameplan._common import load_rules_or_raise as load_gameplan_rules
from athc.cli.profile._common import load_rules_or_raise as load_profile_rules
from athc.config import LEAGUE_FILE, load_league_config
from athc.console import console
from athc.errors import (
    ACCESS_DENIED,
    DIRECTORY_INVALID,
    PATH_NOT_FOUND,
    AthcError,
    ConfigFileError,
    error_line,
    missing_reason,
)
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
from athc.fbpro98_profile import (
    InvalidProfileError,
    Profile,
    UnsupportedProfileError,
    read_profile,
)
from athc.gameplan import Rules, validate_gameplan
from athc.gameplan import RuleViolation as GameplanRuleViolation
from athc.gameplan.config import load_config as load_gameplan_config
from athc.playpool import PlayPool
from athc.profile import (
    CompatIssue,
    ProfileRules,
    check_gameplan_compatibility,
    gameplan_extra_categories,
    validate_profile,
)
from athc.profile import RuleViolation as ProfileRuleViolation
from athc.profile.config import load_config as load_profile_config

# A report is `(count, line)`: a file's findings (0 or more), or one of these.
Report = tuple[int, str]
FAILED = -1  # a FAIL line about a file: counted as checked and as failed
MISSING = -2  # a file missing from a folder: a WARN line, counted as missing
NO_FILES = -3  # none of a team's files at a league location: FAIL, failed only

TEAM_NOT_SET = team_not_set("--team or --all-teams")
PATH_NOT_SET = path_not_set("the folder")
LEAGUE_LOCATION_HINT = location_hint("the folder")

# The \b line keeps Click from joining the examples into one line.
EXAMPLES = """Examples:

\b
  athc check-ppp
  athc check-ppp handed-in
"""


@dataclass(frozen=True, slots=True)
class Setup:
    """The league's loaded rules and play pool: all three, or no check runs."""

    profile_rules: ProfileRules
    gameplan_rules: Rules
    pool: PlayPool


@dataclass(slots=True)
class Seen:
    """What a run has checked so far, by resolved path: each pair once, and
    each game plan's own report (or missing line) once."""

    pairs: set[tuple[Path, Path]] = field(default_factory=set)
    gameplans: set[Path] = field(default_factory=set)


@click.command(
    name="check-ppp",
    cls=AthcCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=EXAMPLES,
)
@click.argument("path", nargs=-1, help="A .prf, a .pln, or a folder.")
@click.option("-r", "--recursive", is_flag=True, help="Include subfolders.")
@team_option("Team to check")
@click.option("-a", "--all-teams", is_flag=True, help="Every team in the league.")
@league_option
@click.pass_context
def check_ppp(
    ctx: click.Context,
    path: tuple[str, ...],
    recursive: bool,
    team: str | None,
    all_teams: bool,
    league: str | None,
) -> None:
    """Check profiles against their game plans.

    With no PATH, checks your team's files; a folder is searched for them, and
    one .prf and one .pln are checked as a pair.
    """
    if len(path) > 2:
        extra = " ".join(path[2:])
        noun = "argument" if len(path) == 3 else "arguments"
        # nargs=-1 takes any count, so Click never says it: its own words, and
        # the one place adds the period every usage error ends with.
        ctx.fail(f"Got unexpected extra {noun} ({extra})")
    if team is not None and all_teams:
        ctx.fail("--team and --all-teams cannot be used together.")
    if len(path) == 2:
        if team is not None or all_teams:
            ctx.fail("--team and --all-teams cannot be used with files.")
        ctx.exit(check_pair(path[0], path[1], league))
    folder = path[0] if path else None
    if folder is not None and (error := not_a_folder(folder)) is not None:
        console.fail(error)
        ctx.exit(2)
    ctx.exit(
        check_teams(folder, team, league, all_teams=all_teams, recursive=recursive)
    )


def not_a_folder(raw: str) -> str | None:
    """The `FAIL` line for one path that is not a folder: missing, or one file
    alone, which names the command that checks it alone."""
    path = Path(raw)
    if not path.exists():
        return f"{raw}: {PATH_NOT_FOUND}"
    if path.is_dir():
        return None
    match path.suffix.lower():
        case ".pln":
            return (
                f"{raw}: No profile given. Run 'athc gameplan check' to check a "
                "game plan alone."
            )
        case ".prf":
            return (
                f"{raw}: No game plan given. Run 'athc profile check' to check a "
                "profile alone."
            )
    return (
        f"{raw}: {DIRECTORY_INVALID} Pass one profile and one game plan, or a folder."
    )


def check_pair(first: str, second: str, league: str | None) -> int:
    """Check one profile with one gameplan; return the exit code."""
    profile_path, gameplan_path, argument_errors = identify_profile_and_gameplan(
        [first, second]
    )
    for error in argument_errors:
        console.fail(error)
    if argument_errors or profile_path is None or gameplan_path is None:
        return 2  # both files are required, so neither is checked
    setup = load_setup(league)
    reports, mismatch = check_files(profile_path, gameplan_path, setup)
    if mismatch is not None:
        # The user paired them: a mismatch is the run's failure.
        console.fail(mismatch)
        return 2
    return summarize(reports)


def check_teams(
    raw: str | None,
    team: str | None,
    league: str | None,
    *,
    all_teams: bool,
    recursive: bool,
) -> int:
    """Check one team's pairs, or every team's with `all_teams`: in the folder
    `raw` (each folder of its tree with `recursive`), else in `ppp_path` when
    the team is yours, else where the league file puts them. Return the exit
    code."""
    config = load_league_config(league)
    league_file = config.dir / LEAGUE_FILE
    # Read before the league files, so a team that is not set shows first.
    yours = None if all_teams else config.string(TEAM_KEY)
    if team is None and not all_teams and yours is None:
        raise ConfigFileError(TEAM_NOT_SET, league_file)
    league_path = config.path(LEAGUE_PATH_KEY)
    if league_path is None:
        raise ConfigFileError(PATH_NOT_SET, league_file)
    files = load_league_files(config.name, league_path)
    if all_teams:
        numbers = list(range(1, len(files.lge.teams) + 1))
    elif team is not None:
        numbers = [option_team(team, files)]
    else:
        assert yours is not None  # checked above: no flag needs `team`
        numbers = [setting_team(yours, files, league_file)]
    # `ppp_path` and the hint are for your team, named either way.
    your_team_alone = not all_teams and is_yours(yours, files, numbers[0])

    scope: Path | None = None
    if raw is not None:
        scope = Path(raw)
    elif your_team_alone and (ppp_path := config.path(PPP_PATH_KEY)) is not None:
        scope = ppp_folder(ppp_path)
    setup = load_setup(league)
    if scope is None:
        return check_league_locations(
            files, numbers, league_path, setup, hint=your_team_alone, tally=all_teams
        )
    return check_folders(
        scope,
        files,
        numbers,
        league_path,
        setup,
        recursive=recursive,
        all_teams=all_teams,
    )


def check_league_locations(
    files: LeagueFiles,
    numbers: Sequence[int],
    league_path: Path,
    setup: Setup,
    *,
    hint: bool,
    tally: bool,
) -> int:
    """Each team's pairs where the league file puts them; return the exit
    code. A team none of whose files are there gets one `FAIL` per folder
    (with the `ppp_path` hint when `hint`); otherwise a missing file is a
    `FAIL` and its partner is checked alone. `tally` adds the teams with no
    files to the tally."""
    reports: list[Report] = []
    failed = no_files = 0
    seen = Seen()
    for number in numbers:
        pairs = located_pairs(files, number, None, league_path)
        if not any(item.exists for pair in pairs for item in pair):
            no_files += 1
            label = team_label(files, number)
            ending = f" {LEAGUE_LOCATION_HINT}" if hint else ""
            reports.extend(
                (
                    NO_FILES,
                    f"{folder}: {folder_reason(folder, label, 'files')}{ending}",
                )
                for folder in dict.fromkeys(f.path.parent for p in pairs for f in p)
            )
            continue
        failed += check_pairs(pairs, setup, seen, reports)
    return summarize(reports, failed, no_files=no_files if tally else None)


def check_folders(
    scope: Path,
    files: LeagueFiles,
    numbers: Sequence[int],
    league_path: Path,
    setup: Setup,
    *,
    recursive: bool,
    all_teams: bool,
) -> int:
    """The teams' pairs in `scope`, each file found by its `.lg2` name (with
    `recursive`, each folder of the tree on its own); return the exit code.
    Nothing has to be there: a missing partner is a `WARN`, a whole pair
    missing prints nothing, and a team with no file in the scope is a `WARN`
    after the reports."""
    reports: list[Report] = []
    failed = 0
    seen = Seen()
    found: set[int] = set()
    for folder in folders(scope, recursive=recursive):
        for number in numbers:
            pairs = [
                pair
                for pair in located_pairs(files, number, folder, league_path)
                if pair[0].exists or pair[1].exists
            ]
            if pairs:
                found.add(number)
            failed += check_pairs(pairs, setup, seen, reports)
    absent = [number for number in numbers if number not in found]
    return summarize(
        reports,
        failed,
        missing=True,
        no_files=len(absent) if all_teams else None,
        last=no_files_lines(scope, files, absent, all_teams=all_teams),
    )


def no_files_lines(
    scope: Path, files: LeagueFiles, absent: Sequence[int], *, all_teams: bool
) -> list[str]:
    """The `WARN` line for the teams with no file in `scope`: every such team
    on one line with `all_teams`, else the one team with its file names."""
    if not absent:
        return []
    if all_teams:
        labels = ", ".join(team_label(files, number) for number in absent)
        return [f"{scope}: No files for {len(absent)} team(s): {labels}."]
    (number,) = absent
    team = files.lg2.teams[number - 1]
    locations = [
        location
        for (_, profile), (_, gameplan) in zip(
            team_files(team, "profile"), team_files(team, "gameplan"), strict=True
        )
        for location in (profile, gameplan)
    ]
    return [
        f"{scope}: No {team_label(files, number)} files. The league file names "
        f"{league_file_names(locations)}."
    ]


def located_pairs(
    files: LeagueFiles, number: int, folder: Path | None, league_path: Path
) -> list[tuple[Located, Located]]:
    """Team `number`'s four `(profile, game plan)` pairs in `.lg2` order, each
    file looked up in `folder`, else at its league location."""
    team = files.lg2.teams[number - 1]
    return [
        (locate(profile, folder, league_path), locate(gameplan, folder, league_path))
        for (_, profile), (_, gameplan) in zip(
            team_files(team, "profile"), team_files(team, "gameplan"), strict=True
        )
    ]


def check_pairs(
    pairs: Sequence[tuple[Located, Located]],
    setup: Setup,
    seen: Seen,
    reports: list[Report],
) -> int:
    """Check each pair not checked yet, adding its reports to `reports`; return
    how many pairs failed without a report. A game plan two pairs share gets
    its own report once; each profile gets its own cross-check."""
    failed = 0
    for profile, gameplan in pairs:
        key = (profile.path.resolve(), gameplan.path.resolve())
        if key in seen.pairs:
            continue
        seen.pairs.add(key)
        what = f"{profile.path} + {gameplan.path}"
        try:
            pair_reports, mismatch = check_files(
                profile,
                gameplan,
                setup,
                report_gameplan=key[1] not in seen.gameplans,
            )
        except (AthcError, OSError) as error:
            console.fail(error_line(error, what=what))
            failed += 1
            continue
        except Exception:
            console.unexpected(what)
            failed += 1
            continue
        if mismatch is not None:
            # This pair only: the league file paired them, not the user.
            reports.append((FAILED, mismatch))
            continue
        seen.gameplans.add(key[1])
        reports.extend(pair_reports)
    return failed


def missing_report(located: Located) -> Report:
    """A missing file's report: a `WARN` in a folder, where nothing has to be
    there, and a `FAIL` at its league location, where the game reads it."""
    kind = MISSING if located.source is Source.FOLDER else FAILED
    return kind, f"{located.path}: {missing_reason(located.path)}"


def summarize(
    reports: Sequence[Report],
    failed: int = 0,
    *,
    missing: bool = False,
    no_files: int | None = None,
    last: Sequence[str] = (),
) -> int:
    """Print every report, then the `last` warnings, then the tally; return the
    exit code. `failed` counts the pairs that never produced a report;
    `missing` adds the missing files to the tally, and `no_files` the teams
    with none."""
    total = files_with_violations = missing_files = 0
    for count, line in reports:
        if count == MISSING:
            missing_files += 1
            console.warn(line)
            continue
        if count == NO_FILES:
            failed += 1
            console.fail(line)
            continue
        total += 1
        if count == FAILED:
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
    for line in last:
        console.warn(line)

    console.print()
    fields = [
        f"{total} file(s) checked",
        f"{files_with_violations} with violations",
        f"{failed} failed",
    ]
    if missing:
        fields.append(f"{missing_files} missing")
    if no_files is not None:
        fields.append(f"{no_files} team(s) with no files")
    console.result(", ".join(fields))
    return 2 if failed else 1 if files_with_violations else 0


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
    pool = build_pool(gameplan_config.play_path, gameplan_config.categories)
    return Setup(profile_rules, gameplan_rules, pool)


def identify_profile_and_gameplan(
    paths: Sequence[str],
) -> tuple[Path | None, Path | None, list[str]]:
    """Which file argument is the profile and which the gameplan, by extension:
    `(profile, gameplan, errors)`.

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
            errors.append(f"{raw}: {missing_reason(raw)}")
        elif not path.is_file():
            errors.append(f"{raw}: {ACCESS_DENIED}")
        elif suffix == ".prf" and profile is None:
            profile = path
        elif suffix == ".pln" and gameplan is None:
            gameplan = path
        elif suffix in (".prf", ".pln"):
            errors.append(
                f"{raw}: Second {suffix} file. Pass one profile and one game plan."
            )
        else:
            errors.append(f"{raw}: Not a .prf or .pln file.")
    return profile, gameplan, errors


def check_files(
    profile: Path | Located,
    gameplan: Path | Located,
    setup: Setup,
    *,
    report_gameplan: bool = True,
) -> tuple[list[Report], str | None]:
    """Each file's report, profile first, plus the side-mismatch line. Both
    files are read, so a read error or mismatch reports even without rules. A
    file is validated only when the sides match; the cross-check runs only on
    two readable files. A missing file gets its missing line and is not read,
    so its partner is checked alone. Without `report_gameplan` (a gameplan
    another pair already reported), the gameplan is still read for the
    cross-check but gets no line of its own."""
    profile_path, gameplan_path = _path_of(profile), _path_of(gameplan)
    prof = _read(profile, read_profile_file)
    gp = _read(gameplan, read_gameplan_file)
    if (
        isinstance(prof, Profile)
        and isinstance(gp, GamePlan)
        and (mismatch := side_mismatch(profile_path, prof, gp)) is not None
    ):
        return [], mismatch  # both read fine, so there is nothing else to report

    reports: list[Report] = []
    if isinstance(prof, Profile):
        other = gp if isinstance(gp, GamePlan) else None
        reports.append(profile_report(profile_path, prof, setup, other))
    else:
        reports.append(prof)
    if report_gameplan:
        if isinstance(gp, GamePlan):
            reports.append(gameplan_report(gameplan_path, gp, setup))
        else:
            reports.append(gp)
    return reports, None


def _path_of(item: Path | Located) -> Path:
    return item.path if isinstance(item, Located) else item


def _read[T](item: Path | Located, reader: Callable[[Path], T | str]) -> T | Report:
    """The file read, or its report: missing, or the `FAIL` line of a file
    that can't be read."""
    if isinstance(item, Located) and not item.exists:
        return missing_report(item)
    read = reader(_path_of(item))
    return (FAILED, read) if isinstance(read, str) else read


def read_profile_file(path: Path) -> Profile | str:
    """The profile, or its `<path>: <reason>` line when it can't be read."""
    try:
        return read_profile(str(path))
    except (OSError, InvalidProfileError, UnsupportedProfileError) as error:
        return error_line(error)


def read_gameplan_file(path: Path) -> GamePlan | str:
    """The gameplan, or its `<path>: <reason>` line when it can't be read."""
    try:
        return read_gameplan(str(path))
    except (OSError, InvalidGamePlanError) as error:
        return error_line(error)


def side_mismatch(path: Path, prof: Profile, gameplan: GamePlan) -> str | None:
    """The `<path>: Profile is X but game plan is Y.` line when the sides differ."""
    if prof.is_offense == gameplan.is_offense:
        return None
    return (
        f"{path}: Profile is {_side(prof.is_offense)} but game plan is "
        f"{_side(gameplan.is_offense)}."
    )


def profile_report(
    path: Path, prof: Profile, setup: Setup, gameplan: GamePlan | None
) -> Report:
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
        head = f"{path}: {summary}; game plan compatible"
    else:
        head = (
            f"{path}: {len(violations)} violation(s), "
            f"{len(issues)} game plan issue(s) ({summary})"
        )
    lines = [head, *details]
    lines.extend(f"  game plan: {issue.message}" for issue in issues)
    lines.extend(f"  game plan info: {extra.message}" for extra in extras)
    return total, "\n".join(lines)


def gameplan_report(path: Path, gp: GamePlan, setup: Setup) -> Report:
    """`(count, line)` in `gameplan check`'s format: clean, or its violations."""
    violations = validate_gameplan(gp, setup.gameplan_rules, setup.pool)
    normal = sum(1 for p in gp.normal_plays if p is not None)
    summary = f"{_side(gp.is_offense)}, {normal} normal"
    if not violations:
        return 0, f"{path}: {summary}"
    lines = [f"{path}: {len(violations)} violation(s) ({summary})"]
    lines.extend(f"  {_gameplan_violation(v)}" for v in violations)
    return len(violations), "\n".join(lines)


def _profile_violation(v: ProfileRuleViolation) -> str:
    prefix = (
        f"[situation {v.situation_number}] " if v.situation_number is not None else ""
    )
    return f"{prefix}{v.message}"


def _gameplan_violation(v: GameplanRuleViolation) -> str:
    prefix = f"[{v.category}] " if v.category else ""
    return f"{prefix}{v.message}"


def _side(is_offense: bool) -> str:
    return "offense" if is_offense else "defense"
