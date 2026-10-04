"""`athc generate-schedule` — generate a league's seasonal game schedule."""

from __future__ import annotations

import logging
import random
import subprocess
import sys
from pathlib import Path

import click

from athc.cli import league_option
from athc.config import LeagueError, resolve_league
from athc.scheduler.config import (
    ConfigError,
    find_league_path,
    scheduler_rules_path,
)
from athc.scheduler.main import generate_schedule as run_generate
from athc.scheduler.schedulers.errors import SchedulerError

PROG = "athc generate-schedule"
logger = logging.getLogger(__name__)


@click.command(name="generate-schedule", hidden=True)
@click.option(
    "--season",
    required=True,
    type=int,
    help="Season being scheduled (e.g. 2048).",
)
@click.option(
    "--seed", type=int, default=None, help="Random seed for deterministic generation."
)
@click.option(
    "--time-limit",
    type=int,
    default=None,
    help=(
        "Override the solver time limit "
        "(CP-SAT deterministic time, not wall-clock seconds)."
    ),
)
@league_option
@click.pass_context
def generate_schedule(
    ctx: click.Context,
    season: int,
    seed: int | None,
    time_limit: int | None,
    league: str | None,
) -> None:
    """Generate a league's seasonal schedule and an HTML report.

    Reads the league's files from the athc config dir (run `athc config path`
    to find it, or `athc config reveal` to open it):

    \b
      <league>.<season>.ini           [OverallStandings] plus [DivisionStandings]
                                      or [ConferenceStandings], teams in finish order
      rules\\<league>.scheduler.toml  optional rule amounts and solver settings

    Writes a .txt and .html schedule plus an .html report to the current
    directory, named `schedule_<season>_<timestamp>`.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    chosen_seed = seed if seed is not None else random.randint(0, 1_000_000)

    try:
        name = resolve_league(league)
        run_generate(
            league=name,
            season=season,
            config_path=scheduler_rules_path(name),
            league_path=find_league_path(name, season),
            output_dir=Path.cwd(),
            seed=chosen_seed,
            time_limit=time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
        )
    except (ConfigError, LeagueError, SchedulerError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    except ImportError as error:
        logger.error(
            "%s: missing dependency %s -- reinstall athc", PROG, error.name or "ortools"
        )
        ctx.exit(1)
