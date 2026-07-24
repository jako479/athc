"""`athc generate-schedule` — generate the seasonal league game schedule."""

from __future__ import annotations

import logging
import random
import subprocess
import sys
from pathlib import Path

import click

from athc.scheduler.config import (
    ConfigError,
    find_config_path,
    find_league_path,
)
from athc.scheduler.main import generate_schedule as run_generate
from athc.scheduler.schedulers.types import DEFAULT_SCHEDULER

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
    help="Override the solver time limit (seconds).",
)
@click.pass_context
def generate_schedule(
    ctx: click.Context,
    season: int,
    seed: int | None,
    time_limit: int | None,
) -> None:
    """Generate the seasonal league schedule and an HTML report.

    Reads season files from the athc config dir (run `athc config path` to find
    it, or `athc config reveal` to open it):

    \b
      <season>.league.ini   divisions + previous season's standings, including
                            the [DivisionStandings] section

    Writes a .txt and .html schedule plus an .html report to the current
    directory, named `schedule_<season>_C_<timestamp>`.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    chosen_seed = seed if seed is not None else random.randint(0, 1_000_000)

    try:
        league_path = find_league_path(season)
        config = find_config_path()
        run_generate(
            season=season,
            scheduler=DEFAULT_SCHEDULER,
            config_path=config,
            league_path=league_path,
            output_dir=Path.cwd(),
            seed=chosen_seed,
            time_limit=time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
        )
    except (ConfigError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(1)
    except ImportError as error:
        logger.error(
            "%s: missing dependency %s -- reinstall athc", PROG, error.name or "ortools"
        )
        ctx.exit(1)
