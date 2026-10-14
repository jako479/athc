"""`athc convert-pdb` — build an Excel workbook from a WinLogStats PDB.

With no game plan option, your team's four game plans fill the Slot columns:
which team, and where its files are, comes from the shared team layer in
`_team.py`. With any game plan option, only the files given are used.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option, team_option
from athc.cli._files import named_file
from athc.cli._team import (
    LEAGUE_PATH_KEY,
    PPP_PATH_KEY,
    TEAM_KEY,
    Located,
    Source,
    folder_reason,
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
    DIRECTORY_INVALID,
    PATH_NOT_FOUND,
    AthcError,
    ConfigFileError,
    missing_reason,
    reason_of,
)
from athc.fbpro98_gameplan import GamePlan, InvalidGamePlanError, read_gameplan
from athc.pdbtoexcel.config import load_config
from athc.pdbtoexcel.main import convert_pdb as run_conversion

PLAN_OPTIONS = "-o, -o2, -d or -d2"
TEAM_NOT_SET = team_not_set("--team")
PATH_NOT_SET = path_not_set(f"a game plan with {PLAN_OPTIONS}")
LEAGUE_LOCATION_HINT = location_hint("--path")

# The \b line keeps Click from joining the examples into one line.
EXAMPLES = """Examples:

\b
  athc convert-pdb 49W6.pdb
  athc convert-pdb 49W6.pdb reports\\week6.xlsx -o try3.pln
"""


@dataclass(frozen=True, slots=True)
class Plans:
    """The game plan behind each Slot column; None hides that column."""

    offense: GamePlan | None = None
    offense_2: GamePlan | None = None
    defense: GamePlan | None = None
    defense_2: GamePlan | None = None


@dataclass(frozen=True, slots=True)
class Slot:
    """One of the team's four game plans, in `.lg2` order: which half, which
    side, and the Slot column it fills."""

    half: str
    offense: bool
    column: int

    @property
    def side(self) -> str:
        return "offense" if self.offense else "defense"

    @property
    def label(self) -> str:
        """The column, as a `WARN` line names it: `Offense Slot 1`."""
        return f"{self.side.capitalize()} Slot {self.column}"


# The four `.lg2` entries in order: 1st-half offense and defense, 2nd half.
SLOTS = (
    Slot("1st-half", offense=True, column=1),
    Slot("1st-half", offense=False, column=1),
    Slot("2nd-half", offense=True, column=2),
    Slot("2nd-half", offense=False, column=2),
)


def _ext(*extensions: str):
    """Click callback that rejects a path without one of `extensions`. An
    argument's hint is its bare name (`'OUTPUT_FILE'`), never Click's
    `'[OUTPUT_FILE]'` for an optional one."""

    def callback(ctx: click.Context, param: click.Parameter, value):
        if value is None:
            return None
        if Path(value).suffix.lower() not in extensions:
            hint = (
                f"'{param.human_readable_name}'"
                if isinstance(param, click.Argument)
                else None
            )
            raise click.BadParameter(
                f"must have a {' or '.join(extensions)} extension.",
                ctx,
                param,
                param_hint=hint,
            )
        return value

    return callback


def _plan_option(*names: str, help: str):
    """One of the four game plan options: a `.pln` file."""
    return click.option(
        *names,
        metavar="GAME_PLAN",
        type=click.Path(path_type=Path),
        default=None,
        callback=_ext(".pln"),
        help=help,
    )


@click.command(
    name="convert-pdb",
    cls=AthcCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=EXAMPLES,
)
@click.argument(
    "pdb_file",
    type=click.Path(path_type=Path),
    callback=_ext(".pdb"),
    help="WinLogStats .pdb file.",
)
@click.argument(
    "output_file",
    type=click.Path(path_type=Path),
    required=False,
    callback=_ext(".xlsx", ".xlsm"),
    help=(
        ".xlsx, or .xlsm to include sorting macros (default: PDB_FILE with "
        ".xlsm, beside it)."
    ),
)
@_plan_option("-o", "--pln-off", help="Offense Slot 1.")
@_plan_option("-o2", "--pln-off-2", help="Offense Slot 2.")
@_plan_option("-d", "--pln-def", help="Defense Slot 1.")
@_plan_option("-d2", "--pln-def-2", help="Defense Slot 2.")
@click.option(
    "--path",
    metavar="FOLDER",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Folder holding your team's game plans, by their league-file names "
        "(default: ppp_path, else where the game reads them)."
    ),
)
@team_option("Team whose game plans fill the Slot columns")
@click.option(
    "--percentages/--no-percentages",
    default=None,
    help="Overrides calculate_percentages in athc.ini (on by default).",
)
@league_option
@click.pass_context
def convert_pdb(
    ctx: click.Context,
    pdb_file: Path,
    output_file: Path | None,
    pln_off: Path | None,
    pln_off_2: Path | None,
    pln_def: Path | None,
    pln_def_2: Path | None,
    path: Path | None,
    team: str | None,
    percentages: bool | None,
    league: str | None,
) -> None:
    """Convert a WinLogStats PDB to an Excel workbook.

    Slot columns come from your team's game plans, or from -o, -o2, -d and -d2.
    """
    named = (pln_off, pln_off_2, pln_def, pln_def_2)
    given = any(plan is not None for plan in named)
    if given and team is not None:
        ctx.fail(f"--team cannot be used with {PLAN_OPTIONS}.")
    if given and path is not None:
        ctx.fail(f"--path cannot be used with {PLAN_OPTIONS}.")

    for file in (pdb_file, *named):
        if file is not None:
            named_file(file)
    config = load_config(league)
    play_dir(config.play_path)
    if given:
        plans = Plans(
            offense=named_plan(pln_off, offense=True),
            offense_2=named_plan(pln_off_2, offense=True),
            defense=named_plan(pln_def, offense=False),
            defense_2=named_plan(pln_def_2, offense=False),
        )
    else:
        plans = team_plans(path, team, league)

    output = output_file if output_file is not None else pdb_file.with_suffix(".xlsm")
    result = run_conversion(
        config=config,
        pdb_path=pdb_file,
        output_path=output,
        pln_offense=plans.offense,
        pln_offense_2=plans.offense_2,
        pln_defense=plans.defense,
        pln_defense_2=plans.defense_2,
        percentages=percentages,
        progress=console.progress,
    )
    for warning in result.warnings:
        console.warn(warning)
    console.ok(f"{output}: {result.plays} play(s)")


def named_plan(path: Path | None, *, offense: bool) -> GamePlan | None:
    """The game plan a plan option names, read; AthcError when it is the
    other side's, as the coach asked for this side."""
    if path is None:
        return None
    plan = read_gameplan(path)
    if plan.is_offense != offense:
        raise AthcError(f"Not {_a_side(offense)} game plan.", path)
    return plan


def team_plans(folder: Path | None, team: str | None, league: str | None) -> Plans:
    """Your team's four game plans (or the one `--team` names): from `folder`
    (`--path`), else `ppp_path` when the team is yours, else the league
    locations. A setting that is wrong raises; a plan that is not there or
    cannot be used is a `WARN` and leaves its column hidden."""
    config = load_league_config(league)
    league_file = config.dir / LEAGUE_FILE
    # Read before the league files, so a team that is not set shows first.
    yours = config.string(TEAM_KEY)
    if team is None and yours is None:
        if folder is not None:
            raise ConfigFileError(TEAM_NOT_SET, league_file)
        return Plans()  # nothing asked for: no Slot columns, no line
    league_path = config.path(LEAGUE_PATH_KEY)
    if league_path is None:
        raise ConfigFileError(PATH_NOT_SET, league_file)
    files = load_league_files(config.name, league_path)
    if team is not None:
        number = option_team(team, files)
    else:
        assert yours is not None  # checked above: one of the two is set
        number = setting_team(yours, files, league_file)
    # `ppp_path` and the hint are for your team, named either way.
    mine = is_yours(yours, files, number)

    scope: Path | None = None
    if folder is not None:
        scope = given_folder(folder)
    elif mine and (ppp_path := config.path(PPP_PATH_KEY)) is not None:
        scope = ppp_folder(ppp_path)
    entries = team_files(files.lg2.teams[number - 1], "gameplan")
    located = [locate(file, scope, league_path) for _, file in entries]
    label = team_label(files, number)
    if not any(item.exists for item in located):
        for line in no_plans_lines(scope, located, entries, label, hint=mine):
            console.warn(line)
        return Plans()
    return read_slots(located, label, hint=mine)


def given_folder(folder: Path) -> Path:
    """`--path` when it is a folder; else AthcError in Windows' words."""
    if not folder.is_dir():
        reason = DIRECTORY_INVALID if folder.exists() else PATH_NOT_FOUND
        raise AthcError(reason, folder)
    return folder


def no_plans_lines(
    scope: Path | None,
    located: Sequence[Located],
    entries: Sequence[tuple[str, str]],
    label: str,
    *,
    hint: bool,
) -> list[str]:
    """The `WARN` lines for a team none of whose game plans are there: one
    for the folder searched, with the names the league file gives them; else
    one per league location, with the `ppp_path` hint for your team."""
    if scope is not None:
        return [
            f"{scope}: No {label} game plans. The league file names "
            f"{league_file_names(file for _, file in entries)}."
        ]
    ending = f" {LEAGUE_LOCATION_HINT}" if hint else ""
    return [
        f"{folder}: {folder_reason(folder, label, 'game plans')}{ending}"
        for folder in dict.fromkeys(item.path.parent for item in located)
    ]


def read_slots(located: Sequence[Located], label: str, *, hint: bool) -> Plans:
    """Read each located plan for its Slot column, in `.lg2` order, naming
    each one used as progress. Both halves of a side on one file are read
    once and fill Slot 1 alone. A plan that is missing, unreadable or the
    other side's is a `WARN` and leaves its column hidden."""
    plans: list[GamePlan | None] = [None] * len(SLOTS)
    first_half = {slot.offense: index for index, slot in enumerate(SLOTS[:2])}
    for index, (slot, item) in enumerate(zip(SLOTS, located, strict=True)):
        shared = slot.column == 1 and _same_file(item, located[index + 2])
        if slot.column == 2 and _same_file(located[first_half[slot.offense]], item):
            continue  # its Slot 1 line covered it
        plans[index] = read_slot(item, slot, label, shared=shared, hint=hint)
    offense, defense, offense_2, defense_2 = plans
    return Plans(offense, offense_2, defense, defense_2)


def read_slot(
    item: Located, slot: Slot, label: str, *, shared: bool, hint: bool
) -> GamePlan | None:
    """One located plan: read and side-checked, with its progress line; None
    after its `WARN` line when it cannot fill the column."""
    reason: str | None = None
    plan: GamePlan | None = None
    ending = ""
    if not item.exists:
        reason = missing_reason(item.path)
        if hint and item.source is Source.LEAGUE:
            ending = f" {LEAGUE_LOCATION_HINT}"
    else:
        try:
            plan = read_gameplan(item.path)
        except InvalidGamePlanError as error:
            reason = error.reason
        except OSError as error:
            reason = reason_of(error)
        else:
            if plan.is_offense != slot.offense:
                reason = f"Not {_a_side(slot.offense)} game plan."
    if reason is not None:
        console.warn(f"{item.path}: {reason} {slot.label} is hidden.{ending}")
        return None
    if shared:
        console.progress(f"{item.path}: {label} {slot.side}, both halves, Slot 1")
    else:
        console.progress(
            f"{item.path}: {label} {slot.half} {slot.side}, Slot {slot.column}"
        )
    return plan


def _same_file(first: Located, second: Located) -> bool:
    """Whether two located plans are one file, as Windows compares paths."""
    return os.path.normcase(first.path.resolve()) == os.path.normcase(
        second.path.resolve()
    )


def _a_side(offense: bool) -> str:
    return "an offense" if offense else "a defense"
