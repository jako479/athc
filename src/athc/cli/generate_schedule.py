"""`athc generate-schedule` — generate a league's seasonal game schedule."""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.cli._files import resolve_output_folder
from athc.config import (
    LEAGUE_FILE,
    LEAGUE_PATH_KEY,
    LeagueConfig,
    load_league_config,
    not_set_line,
)
from athc.console import console
from athc.errors import AthcError, ConfigFileError
from athc.scheduler.config import scheduler_rules_path
from athc.scheduler.main import generate_schedule as run_generate

# CP-SAT's seed is a 32-bit integer; its setter refuses a larger one.
MAX_SEED = 2147483647
# The seed drawn when none is given; the result line shows it.
RANDOM_SEED_MAX = 1_000_000

PATH_NOT_SET = not_set_line("path", "--upcoming")

# The \b line keeps Click from joining the examples into one line.
EXAMPLES = """Examples:

\b
  athc generate-schedule --season 2050 --previous E:\\PNFL\\2049\\PNFL.lge
  athc generate-schedule --season 2030 --league PCFL --previous PCFL.lge
  athc generate-schedule --season 2050 E:\\PNFL\\Schedules
"""


def _seed_in_range(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    if value is not None and not 0 <= value <= MAX_SEED:
        raise click.BadParameter(f"must be 0 to {MAX_SEED}, got {value}.", ctx, param)
    return value


def _time_limit_in_range(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    if value is not None and value < 1:
        raise click.BadParameter(f"must be 1 or more, got {value}.", ctx, param)
    return value


def _not_the_console(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> str | None:
    """OUTPUT_FOLDER takes no `-`: the run writes three files, never the
    console. The hint is the bare name, never Click's `'[OUTPUT_FOLDER]'`."""
    if value == "-":
        raise click.BadParameter(
            "must be a folder, not -.",
            ctx,
            param,
            param_hint=f"'{param.human_readable_name}'",
        )
    return value


@click.command(
    name="generate-schedule",
    cls=AthcCommand,
    hidden=True,
    context_settings=CONTEXT_SETTINGS,
    epilog=EXAMPLES,
)
@click.argument(
    "output_folder",
    required=False,
    callback=_not_the_console,
    help="Folder for the schedule and report (default: the current folder).",
)
@click.option(
    "--season",
    required=True,
    type=int,
    metavar="YEAR",
    help="Season to schedule, e.g. 2048.",
)
@click.option(
    "--previous",
    "previous_file",
    default=None,
    metavar="FILE",
    help=(
        "Previous season's .lge file, saved after its last playoff game "
        "(default: the --upcoming file)."
    ),
)
@click.option(
    "--upcoming",
    "upcoming_file",
    default=None,
    metavar="FILE",
    help=(
        "Upcoming season's .lge file (default: the league's .lge in path in "
        "league.toml)."
    ),
)
@click.option(
    "--seed",
    type=int,
    default=None,
    metavar="NUMBER",
    callback=_seed_in_range,
    help="Seed for a repeatable run (default: random; the last line shows it).",
)
@click.option(
    "--phase2-time-limit",
    type=int,
    default=None,
    metavar="LIMIT",
    callback=_time_limit_in_range,
    help=(
        "Solver budget for placing games into weeks, in the solver's own time "
        "units, not seconds (default: phase2_time_limit in scheduler.toml)."
    ),
)
@league_option
def generate_schedule(
    output_folder: str | None,
    season: int,
    previous_file: str | None,
    upcoming_file: str | None,
    seed: int | None,
    phase2_time_limit: int | None,
    league: str | None,
) -> None:
    """Generate a league's season schedule and report.

    Writes a .txt and .html schedule and a report to OUTPUT_FOLDER.
    """
    folder = resolve_output_folder(output_folder)
    chosen_seed = seed if seed is not None else random.randint(0, RANDOM_SEED_MAX)
    config = load_league_config(league)
    config_path = scheduler_rules_path(config.name)
    upcoming = _upcoming_file(config, upcoming_file)
    previous = Path(previous_file) if previous_file is not None else upcoming
    try:
        generated = run_generate(
            league=config.name,
            season=season,
            config_path=config_path,
            previous_file=previous,
            upcoming_file=upcoming,
            output_dir=folder,
            seed=chosen_seed,
            phase2_time_limit=phase2_time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
            progress=console.progress,
            warn=console.warn,
        )
    except ImportError as error:
        raise AthcError(
            f"Missing {error.name or 'ortools'}. Reinstall athc."
        ) from error
    for path in generated.files:
        console.ok(f"{path}: written")
    games = len(generated.result.schedule.games)
    console.result(f"Generated {games} games (seed {generated.seed})")


def _upcoming_file(config: LeagueConfig, upcoming_file: str | None) -> Path:
    """`--upcoming`, else `<league>.lge` in the league's `path`; ConfigFileError
    when neither names the upcoming season's file."""
    if upcoming_file is not None:
        return Path(upcoming_file)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(PATH_NOT_SET, config.dir / LEAGUE_FILE)
    return folder / f"{config.name}.lge"
