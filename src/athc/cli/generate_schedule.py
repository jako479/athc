"""`athc generate-schedule` — generate a league's seasonal game schedule."""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.config import resolve_league
from athc.console import console
from athc.errors import AthcError
from athc.scheduler.config import find_league_path, scheduler_rules_path
from athc.scheduler.main import generate_schedule as run_generate


@click.command(
    name="generate-schedule",
    cls=AthcCommand,
    hidden=True,
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--season",
    required=True,
    type=int,
    metavar="year",
    help="Season being scheduled (e.g. 2048).",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    metavar="number",
    help="Random seed for deterministic generation.",
)
@click.option(
    "--time-limit",
    type=int,
    default=None,
    metavar="number",
    help=(
        "Override the solver time limit "
        "(CP-SAT deterministic time, not wall-clock seconds)."
    ),
)
@league_option
def generate_schedule(
    season: int,
    seed: int | None,
    time_limit: int | None,
    league: str | None,
) -> None:
    """Generate a league's seasonal schedule and an HTML report.

    Reads the league's files from its folder under the athc config dir (run
    `athc config path` to find it, or `athc config reveal` to open it):

    \b
      standings\\<season>.league.ini  [OverallStandings] plus [DivisionStandings]
                                     or [ConferenceStandings], teams in finish order
      scheduler.toml                  optional rule amounts and solver settings

    Writes a .txt and .html schedule plus an .html report to the current
    directory, named `schedule_<season>_<timestamp>`.
    """
    chosen_seed = seed if seed is not None else random.randint(0, 1_000_000)
    name = resolve_league(league)
    try:
        generated = run_generate(
            league=name,
            season=season,
            config_path=scheduler_rules_path(name),
            league_path=find_league_path(name, season),
            output_dir=Path.cwd(),
            seed=chosen_seed,
            time_limit=time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
            progress=console.progress,
        )
    except ImportError as error:
        raise AthcError(
            f"missing {error.name or 'ortools'} -- reinstall athc"
        ) from error
    for path in generated.files:
        console.ok(str(path))
    games = len(generated.result.schedule.games)
    console.result(f"Generated {games} games (seed {generated.seed})")
