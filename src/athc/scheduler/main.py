"""Orchestrate schedule generation: load config, run a scheduler, write outputs."""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime
from os import PathLike
from pathlib import Path

from athc.scheduler.config import (
    ConfigError,
    load_history,
    load_league,
    load_scheduler_config,
)
from athc.scheduler.domain.history import NonConfHistory
from athc.scheduler.schedulers.types import (
    DEFAULT_SCHEDULER,
    SchedulerResult,
    get_scheduler,
    scheduler_uses_division_standings,
)
from athc.scheduler.writers.html_writer import HtmlScheduleWriter
from athc.scheduler.writers.report import HtmlReportWriter, build_schedule_report
from athc.scheduler.writers.txt_writer import TxtScheduleWriter

logger = logging.getLogger(__name__)

StrPath = str | PathLike[str]


def generate_schedule(
    *,
    season: int,
    scheduler: str = DEFAULT_SCHEDULER,
    config_path: StrPath,
    league_path: StrPath,
    history_path: StrPath | None,
    output_dir: StrPath,
    seed: int,
    time_limit: int | None,
    command_line: str,
) -> SchedulerResult:
    """Solve the season schedule and write outputs to `output_dir`.

    Writes a `.txt` and `.html` schedule plus an `.html` report, all named
    `schedule_<season>_<A|B|C|D>_<YYYYMMDD_HHMM>` (the report adds a `_report`
    suffix). Returns the solver result.
    """
    scheduler_config = load_scheduler_config()  # config_path = report provenance
    if time_limit is not None:  # CLI --time-limit overrides the configured value
        scheduler_config = replace(
            scheduler_config,
            solver=replace(scheduler_config.solver, time_limit=time_limit),
        )
    league = load_league(league_path)
    if (
        scheduler_uses_division_standings(scheduler)
        and league.division_standings is None
    ):
        raise ConfigError(
            f"Scheduler {scheduler} needs a [DivisionStandings] section in "
            f"'{league_path}'."
        )
    # history_path is None when the scheduler doesn't use history (Scheduler B).
    history = load_history(history_path, league) if history_path else NonConfHistory()

    started = time.perf_counter()
    result = get_scheduler(scheduler)(
        league=league,
        history=history,
        seed=seed,
        scheduler_config=scheduler_config,
    )
    elapsed = time.perf_counter() - started

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    # `scheduler` is the A/B/C/D key, which is also the filename token.
    base = Path(output_dir) / f"schedule_{season}_{scheduler}_{stamp}"
    report_path = base.with_name(f"{base.name}_report.html")

    TxtScheduleWriter(base.with_suffix(".txt")).write(result.schedule)
    HtmlScheduleWriter(base.with_suffix(".html"), season_label=str(season)).write(
        result.schedule
    )
    report = build_schedule_report(
        schedule=result.schedule,
        matchup_plan=result.matchup_plan,
        league=league,
        history=history,
        seed=seed,
        scheduler_kind=scheduler,
        config_path=config_path,
        history_path=history_path or "-",
        elapsed_time_seconds=elapsed,
        command_line=command_line,
        difficulty_amplitude=scheduler_config.difficulty.amplitude,
        difficulty_period=scheduler_config.difficulty.period,
        difficulty_c_spread=scheduler_config.difficulty.c_spread,
        difficulty_d_spread=scheduler_config.difficulty.d_spread,
    )
    HtmlReportWriter(report_path).write(report)
    logger.info(
        "Generated %d games -> %s.{txt,html}; report -> %s (seed %d)",
        len(result.schedule.games),
        base.name,
        report_path.name,
        seed,
    )
    return result
