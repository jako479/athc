"""Orchestrate schedule generation: load config, run a scheduler, write outputs."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from os import PathLike
from pathlib import Path

from athc.scheduler.config import load_scheduler_config
from athc.scheduler.cpu import cpu_name
from athc.scheduler.league_files import load_league
from athc.scheduler.schedulers.types import (
    SchedulerResult,
    get_scheduler,
)
from athc.scheduler.schedulers.utils import write_hold
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
    previous_file: StrPath,
    upcoming_file: StrPath,
    output_dir: StrPath,
    seed: int,
    phase2_time_limit: int | None,
    command_line: str,
    progress: Callable[[str], None] | None = None,
    warn: Callable[[str], None] | None = None,
) -> GeneratedSchedule:
    """Solve `league`'s season schedule and write outputs to `output_dir`.

    The previous season's `.lge`, `previous_file`, gives the standings, the
    upcoming season's, `upcoming_file`, the conferences, divisions and teams;
    one file can be both, and then no team is renamed. `config_path` is the
    rules file (optional; its `[renames.<season>]` maps the teams that changed
    name). Writes a `.txt` and `.html` schedule plus an `.html` report into
    `output_dir` (created in full if missing), all named
    `schedule_<season>_<YYYYMMDD_HHMM>` (the report adds a `_report` suffix);
    the league name titles the HTML files. A Ctrl+C press while they
    are written waits until all three are. `progress` hears each progress
    line, the solver's phases included, and `warn` each noted oddity (an
    unfinished season); nothing is printed or logged here.
    """
    say = progress or (lambda _: None)
    complain = warn or (lambda _: None)
    scheduler_config = load_scheduler_config(config_path, required=False)
    if phase2_time_limit is not None:  # --phase2-time-limit replaces the file's
        scheduler_config = replace(
            scheduler_config,
            solver=replace(
                scheduler_config.solver, phase2_time_limit=phase2_time_limit
            ),
        )
    one_file = Path(previous_file) == Path(upcoming_file)
    structure = load_league(
        previous_file,
        upcoming_file,
        {} if one_file else scheduler_config.renames.get(season, {}),
        season=season,
        seed=seed,
        rules_path=Path(config_path),
        warn=complain,
    )

    # Before the solve, so a folder that cannot be made never costs one.
    Path(output_dir).mkdir(parents=True, exist_ok=True)
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

    with write_hold():
        TxtScheduleWriter(txt_path).write(result.schedule)
        HtmlScheduleWriter(
            html_path, league_name=league, season_label=str(season)
        ).write(result.schedule)
        report = build_schedule_report(
            schedule=result.schedule,
            matchup_plan=result.matchup_plan,
            league=structure,
            seed=seed,
            config_path=config_path,
            elapsed_time_seconds=elapsed,
            command_line=command_line,
            difficulty_slope=scheduler_config.phase1.difficulty_slope,
            random_nonconference=scheduler_config.phase1.random_nonconference,
            cpu=cpu_name(),
            threads=result.workers,
        )
        HtmlReportWriter(report_path, league_name=league).write(report)
    return GeneratedSchedule(result, seed, (txt_path, html_path, report_path))
