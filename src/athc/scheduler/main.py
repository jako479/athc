"""Orchestrate schedule generation: load config, run a scheduler, write outputs."""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from os import PathLike
from pathlib import Path

from athc.scheduler.config import ConfigError, load_league, load_scheduler_config
from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.schedulers.types import (
    DEFAULT_SCHEDULER,
    SchedulerResult,
    get_scheduler,
)
from athc.scheduler.writers.report import TxtReportWriter, build_schedule_report
from athc.scheduler.writers.writer import get_writer

logger = logging.getLogger(__name__)

StrPath = str | PathLike[str]


def default_report_path(output: StrPath) -> Path:
    """Return `<output-stem>-report.txt` next to `output`."""
    output = Path(output)
    return output.with_name(f"{output.stem}-report.txt")


def generate_schedule(
    *,
    output: StrPath,
    output_format: str,
    season: int,
    scheduler: str = DEFAULT_SCHEDULER,
    config_path: StrPath,
    league_path: StrPath,
    history_path: StrPath,
    report_path: StrPath,
    seed: int,
    time_limit: float | None,
    command_line: str,
) -> SchedulerResult:
    """Run the chosen scheduler and persist its schedule + report.

    Loads league + non-conference history from the given paths, solves with
    the selected scheduler (subject to `time_limit`), writes the schedule via
    the format-appropriate writer, and writes a human-readable text report.
    """
    scheduler_config = load_scheduler_config()  # config_path = report provenance
    if time_limit is not None:  # CLI --time-limit overrides the configured value
        scheduler_config = replace(
            scheduler_config,
            solver=replace(scheduler_config.solver, time_limit=time_limit),
        )
    league = load_league(league_path)
    if scheduler == DEFAULT_SCHEDULER and league.rankings.overall is None:
        raise ConfigError(
            "The two-phase-rank scheduler needs overall standings: add a "
            "[Standings] list to league.ini, or use --scheduler fixed-matchup."
        )
    history = NonConfHistory.load(history_path)
    writer = get_writer(output_format, output)

    started = time.perf_counter()
    result = get_scheduler(scheduler)(
        league=league,
        history=history,
        season=season,
        seed=seed,
        scheduler_config=scheduler_config,
    )
    elapsed = time.perf_counter() - started

    writer.write(result.schedule)
    report = build_schedule_report(
        schedule=result.schedule,
        matchup_plan=result.matchup_plan,
        league=league,
        history=history,
        seed=seed,
        scheduler_kind=scheduler,
        config_path=config_path,
        history_path=history_path,
        elapsed_time_seconds=elapsed,
        command_line=command_line,
    )
    TxtReportWriter(report_path).write(report)
    logger.info(
        "Generated %d games -> %s; report -> %s (seed %d)",
        len(result.schedule.games),
        output,
        report_path,
        seed,
    )
    return result
