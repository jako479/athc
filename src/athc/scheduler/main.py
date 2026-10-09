"""Orchestrate schedule generation: load config, run a scheduler, write outputs."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from os import PathLike
from pathlib import Path

from athc.scheduler.config import (
    load_league,
    load_scheduler_config,
)
from athc.scheduler.cpu import cpu_name
from athc.scheduler.schedulers.types import (
    SchedulerResult,
    get_scheduler,
)
from athc.scheduler.writers.html_writer import HtmlScheduleWriter
from athc.scheduler.writers.report import HtmlReportWriter, build_schedule_report
from athc.scheduler.writers.txt_writer import TxtScheduleWriter

StrPath = str | PathLike[str]


@dataclass(frozen=True, slots=True)
class GeneratedSchedule:
    """A solved season: the solver result, the seed it ran with and the files
    written (the `.txt` and `.html` schedules, then the `_report.html`)."""

    result: SchedulerResult
    seed: int
    files: tuple[Path, ...]


def generate_schedule(
    *,
    league: str,
    season: int,
    config_path: StrPath,
    league_path: StrPath,
    output_dir: StrPath,
    seed: int,
    time_limit: int | None,
    command_line: str,
    progress: Callable[[str], None] | None = None,
) -> GeneratedSchedule:
    """Solve `league`'s season schedule and write outputs to `output_dir`.

    Writes a `.txt` and `.html` schedule plus an `.html` report, all named
    `schedule_<season>_<YYYYMMDD_HHMM>` (the report adds a `_report` suffix);
    the league name titles the HTML files. `progress` hears each progress
    line, the solver's phases included; nothing is printed or logged here.
    """
    say = progress or (lambda _: None)
    scheduler_config = load_scheduler_config(config_path, required=False)
    if time_limit is not None:  # CLI --time-limit overrides the configured value
        scheduler_config = replace(
            scheduler_config,
            solver=replace(scheduler_config.solver, time_limit=time_limit),
        )
    structure = load_league(league_path)  # either standings section

    say(f"Generating the {season} schedule")
    started = time.perf_counter()
    result = get_scheduler()(
        league=structure,
        seed=seed,
        scheduler_config=scheduler_config,
        season=season,
        progress=progress,
    )
    elapsed = time.perf_counter() - started

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = Path(output_dir) / f"schedule_{season}_{stamp}"
    txt_path = base.with_suffix(".txt")
    html_path = base.with_suffix(".html")
    report_path = base.with_name(f"{base.name}_report.html")

    TxtScheduleWriter(txt_path).write(result.schedule)
    HtmlScheduleWriter(html_path, league_name=league, season_label=str(season)).write(
        result.schedule
    )
    report = build_schedule_report(
        schedule=result.schedule,
        matchup_plan=result.matchup_plan,
        league=structure,
        seed=seed,
        config_path=config_path,
        elapsed_time_seconds=elapsed,
        command_line=command_line,
        difficulty_spread=scheduler_config.difficulty.spread,
        cpu=cpu_name(),
        threads=result.workers,
    )
    HtmlReportWriter(report_path, league_name=league).write(report)
    return GeneratedSchedule(result, seed, (txt_path, html_path, report_path))
