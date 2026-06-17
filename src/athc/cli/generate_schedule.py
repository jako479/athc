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
    find_history_path,
    find_league_path,
)
from athc.scheduler.main import default_report_path
from athc.scheduler.main import generate_schedule as run_generate
from athc.scheduler.schedulers.types import DEFAULT_SCHEDULER, available_schedulers
from athc.scheduler.writers.writer import available_writer_formats

PROG = "athc generate-schedule"
logger = logging.getLogger(__name__)


@click.command(name="generate-schedule", hidden=True)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output path for the generated schedule.",
)
@click.option(
    "--season",
    required=True,
    type=int,
    help="Season year being scheduled (e.g. 2026); sets non-conference drought costs.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(available_writer_formats()),
    default=None,
    help="Output format. Defaults to inferring from the --output extension.",
)
@click.option(
    "--league",
    "league_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Use this league.ini (divisions, conference ranking) instead of the default.",
)
@click.option(
    "--history",
    "history_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Non-conference history JSON file.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Text report path. Defaults to <output-stem>-report.txt.",
)
@click.option(
    "--time-limit",
    type=float,
    default=None,
    help="Override the solver time limit (seconds).",
)
@click.option(
    "--seed", type=int, default=None, help="Random seed for deterministic generation."
)
@click.option(
    "--scheduler",
    type=click.Choice(available_schedulers()),
    default=DEFAULT_SCHEDULER,
    show_default=True,
    help="Matchup generator to use.",
)
@click.pass_context
def generate_schedule(
    ctx: click.Context,
    output: Path,
    season: int,
    output_format: str | None,
    league_path: Path | None,
    history_path: Path | None,
    report_path: Path | None,
    time_limit: float | None,
    seed: int | None,
    scheduler: str,
) -> None:
    """Generate the seasonal league schedule and a human-readable text report.

    Reads the league (divisions, conference ranking) and non-conference history,
    solves the schedule with the chosen --scheduler subject to the configured time
    limit, and writes it in the format inferred from --output (or --format).
    Exit 0 = written, 2 = error.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fmt = _infer_format(ctx, output, output_format)
    history = history_path or find_history_path()
    report = report_path or default_report_path(output)
    chosen_seed = seed if seed is not None else random.randint(0, 1_000_000)

    try:
        config = find_config_path()
        league = league_path or find_league_path()
        run_generate(
            output=output,
            output_format=fmt,
            season=season,
            scheduler=scheduler,
            config_path=config,
            league_path=league,
            history_path=history,
            report_path=report,
            seed=chosen_seed,
            time_limit=time_limit,
            command_line=subprocess.list2cmdline([PROG, *sys.argv[1:]]),
        )
    except (ConfigError, OSError) as error:
        logger.error("%s: %s", PROG, error)
        ctx.exit(2)
    except ImportError:
        logger.error(
            "%s: requires ortools. Install it with: pip install athc[schedule]", PROG
        )
        ctx.exit(2)


def _infer_format(ctx: click.Context, output: Path, output_format: str | None) -> str:
    fmt = (output_format or output.suffix.lstrip(".")).lower()
    if not fmt:
        raise click.UsageError(
            "Could not infer output format from the file extension; use --format."
        )
    if fmt not in available_writer_formats():
        raise click.UsageError(f"Unsupported output format: {fmt}")
    return fmt
