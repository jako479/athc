"""`athc generate-schedule` — generate a league's seasonal game schedule."""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.config import (
    LEAGUE_FILE,
    LEAGUE_PATH_KEY,
    LeagueConfig,
    load_league_config,
)
from athc.console import console
from athc.errors import AthcError, ConfigFileError
from athc.scheduler.config import scheduler_rules_path
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
    "--previous",
    "previous_dir",
    required=True,
    metavar="folder",
    help=(
        "Folder holding the previous season's league files; its <league>.lge "
        "gives the standings."
    ),
)
@click.option(
    "--upcoming",
    "upcoming_dir",
    default=None,
    metavar="folder",
    help=(
        "Folder holding the upcoming season's league files; its <league>.lge "
        "gives the conferences, divisions and teams. Default: path in league.toml."
    ),
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
    previous_dir: str,
    upcoming_dir: str | None,
    seed: int | None,
    time_limit: int | None,
    league: str | None,
) -> None:
    """Generate a league's seasonal schedule and an HTML report.

    Reads two of the league's game files, each named <league>.lge:

    \b
      --previous folder   the previous season's, after its last playoff game:
                          the standings (records, playoff finish)
      --upcoming folder   the upcoming season's: conferences, divisions and
                          team names (default: path in league.toml)

    Teams are matched by name; a team that changed its name between the two
    seasons is listed under [renames.<season>] in the league's scheduler.toml
    (optional rule amounts and solver settings) in the athc config dir (run
    `athc config path` to find it, or `athc config reveal` to open it).

    Writes a .txt and .html schedule plus an .html report to the current
    directory, named `schedule_<season>_<timestamp>`.
    """
    chosen_seed = seed if seed is not None else random.randint(0, 1_000_000)
    config = load_league_config(league)
    try:
        generated = run_generate(
            league=config.name,
            season=season,
            config_path=scheduler_rules_path(config.name),
            previous_dir=Path(previous_dir),
            upcoming_dir=_upcoming_dir(config, upcoming_dir),
            output_dir=Path.cwd(),
            seed=chosen_seed,
            time_limit=time_limit,
            # argv[1:] already starts with the subcommand name.
            command_line=subprocess.list2cmdline(["athc", *sys.argv[1:]]),
            progress=console.progress,
        )
    except ImportError as error:
        raise AthcError(
            f"Missing {error.name or 'ortools'}. Reinstall athc."
        ) from error
    for path in generated.files:
        console.ok(str(path))
    games = len(generated.result.schedule.games)
    console.result(f"Generated {games} games (seed {generated.seed})")


def _upcoming_dir(config: LeagueConfig, upcoming_dir: str | None) -> Path:
    """`--upcoming`, else the league's `path`; ConfigFileError when neither
    names the upcoming season's folder."""
    if upcoming_dir is not None:
        return Path(upcoming_dir)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(
            f"No {LEAGUE_PATH_KEY} for the league. Set {LEAGUE_PATH_KEY} in this file.",
            config.dir / LEAGUE_FILE,
        )
    return folder
