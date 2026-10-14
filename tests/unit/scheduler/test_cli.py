"""Tests for `athc generate-schedule` argument handling and config errors.

Config is resolved from `config_dir()` (autouse fixture). The CLI reads the
upcoming season's `.lge` from `--upcoming`, else `<league>.lge` in the
league's `path`, and the previous season's from `--previous`, else the
upcoming file. The real solve runs only in the slow fixtures; here
`run_generate` is stubbed where needed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import Result

import athc.cli.generate_schedule as cli_module
import athc.scheduler.main as main_module
from athc.cli import cli
from athc.cli.generate_schedule import generate_schedule
from athc.errors import AthcError
from athc.scheduler.domain.league import Conference, Team
from athc.scheduler.domain.schedule import Game, Schedule
from athc.scheduler.main import GeneratedSchedule
from athc.scheduler.schedulers import utils
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.types import MatchupPlan, SchedulerResult
from athc.scheduler.schedulers.utils import CTRL_C_EVENT
from tests.conftest import league_not_found, no_league_selected

from .test_config import LEAGUE
from .test_league_files import DATA, PREVIOUS_2047, UPCOMING_2048
from .test_utils import FakeKernel32

RENAMES_TOML = '[renames.2048]\nBaltimore = "Los Angeles"\n'

HELP = r"""Usage: athc generate-schedule [OPTIONS]

  Generate a league's season schedule and report.

  Writes a .txt and .html schedule and a report to the current folder.

Options:
  --season YEAR       Season to schedule, e.g. 2048.  [required]
  --previous FILE     Previous season's .lge file, saved after its last
                      playoff game (default: the --upcoming file).
  --upcoming FILE     Upcoming season's .lge file (default: the league's .lge
                      in path in league.toml).
  --seed NUMBER       Seed for a repeatable run (default: random; the last
                      line shows it).
  --time-limit LIMIT  Solver budget for placing games into weeks, in the
                      solver's own time units, not seconds (default:
                      time_limit in scheduler.toml).
  --league NAME       League to use (default: the one set with athc config set
                      league).
  -h, --help          Show this message and exit.

  Examples:

    athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge
    athc generate-schedule --season 2030 --league PCFL --previous PCFL.lge
"""


@pytest.fixture
def folders(tmp_path: Path) -> tuple[Path, Path]:
    """`previous\\` and `upcoming\\` folders holding the 2047 final and the 2048
    league files as `<LEAGUE>.lge`."""
    previous, upcoming = tmp_path / "previous", tmp_path / "upcoming"
    for folder, fixture in ((previous, PREVIOUS_2047), (upcoming, UPCOMING_2048)):
        folder.mkdir()
        shutil.copy(DATA / f"{fixture}.lge", folder / f"{LEAGUE}.lge")
    return previous, upcoming


@pytest.fixture(autouse=True)
def league_folder(config_dir: Path, write_config, folders) -> Path:
    """A configured league whose `path` is the upcoming folder."""
    folder = config_dir / "leagues" / LEAGUE
    folder.mkdir(parents=True)
    _, upcoming = folders
    (folder / "league.toml").write_text(
        f"[league]\npath = '{upcoming}'\n", encoding="utf-8"
    )
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


def _lge(folder: Path) -> Path:
    return folder / f"{LEAGUE}.lge"


# ── help ──────────────────────────────────────────────────────────────────────


def test_help_screen(runner) -> None:
    result = runner.invoke(
        cli, ["generate-schedule", "-h"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == HELP


# ── arguments ─────────────────────────────────────────────────────────────────


def test_requires_season(runner, folders) -> None:
    previous, _ = folders
    result = runner.invoke(generate_schedule, ["--previous", str(_lge(previous))])
    assert result.exit_code == 2
    assert "season" in result.stderr


def test_rejects_non_integer_time_limit(runner, folders) -> None:
    # --time-limit is an integer; a fractional value is a usage error.
    previous, _ = folders
    result = runner.invoke(
        generate_schedule,
        ["--season", "2048", "--previous", str(_lge(previous)), "--time-limit", "1.5"],
    )
    assert result.exit_code == 2


def test_no_worker_count_override(runner, folders) -> None:
    # solver_workers is config-only (a reproducibility contract), never a CLI
    # flag; an unknown option is a usage error.
    previous, _ = folders
    result = runner.invoke(
        generate_schedule,
        ["--season", "2048", "--previous", str(_lge(previous)), "--workers", "4"],
    )
    assert result.exit_code == 2


def _capture(captured: dict[str, object], tmp_path: Path):
    """A `run_generate` stub that records its arguments and returns a solved run."""

    def run(**kwargs: object) -> GeneratedSchedule:
        captured.update(kwargs)
        return _generated(tmp_path)

    return run


def _invoke_captured(
    runner, monkeypatch, tmp_path: Path, *arguments: str
) -> tuple[dict[str, object], Result]:
    """Run the command on `arguments` with `run_generate` stubbed; returns what
    it was called with and the result."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    result = runner.invoke(generate_schedule, ["--season", "2048", *arguments])
    return captured, result


@pytest.mark.parametrize("seed", ["0", "2147483647"])
def test_seed_at_its_bounds_is_forwarded(
    runner, monkeypatch, tmp_path: Path, seed: str
) -> None:
    captured, result = _invoke_captured(runner, monkeypatch, tmp_path, "--seed", seed)
    assert result.exit_code == 0, result.stderr
    assert captured["seed"] == int(seed)


@pytest.mark.parametrize("seed", ["-1", "2147483648"])
def test_seed_past_its_bounds_is_a_usage_error(
    runner, monkeypatch, tmp_path: Path, seed: str
) -> None:
    captured, result = _invoke_captured(runner, monkeypatch, tmp_path, "--seed", seed)
    assert result.exit_code == 2
    assert (
        f"Error: Invalid value for '--seed': must be 0 to 2147483647, got {seed}.\n"
    ) in result.stderr
    assert captured == {}  # never reached run_generate


def test_no_seed_draws_one_from_0_to_1000000(
    runner, monkeypatch, tmp_path: Path
) -> None:
    captured, result = _invoke_captured(runner, monkeypatch, tmp_path)
    assert result.exit_code == 0, result.stderr
    seed = captured["seed"]
    assert isinstance(seed, int)
    assert 0 <= seed <= 1_000_000


def test_time_limit_of_1_is_forwarded(runner, monkeypatch, tmp_path: Path) -> None:
    captured, result = _invoke_captured(
        runner, monkeypatch, tmp_path, "--time-limit", "1"
    )
    assert result.exit_code == 0, result.stderr
    assert captured["time_limit"] == 1


def test_time_limit_of_0_is_a_usage_error(runner, monkeypatch, tmp_path: Path) -> None:
    captured, result = _invoke_captured(
        runner, monkeypatch, tmp_path, "--time-limit", "0"
    )
    assert result.exit_code == 2
    assert (
        "Error: Invalid value for '--time-limit': must be 1 or more, got 0.\n"
    ) in result.stderr
    assert captured == {}


# ── the two league files ──────────────────────────────────────────────────────


def test_without_previous_the_upcoming_file_gives_both(
    runner, monkeypatch, tmp_path: Path, folders
) -> None:
    _, upcoming = folders
    captured, result = _invoke_captured(runner, monkeypatch, tmp_path)
    assert result.exit_code == 0, result.stderr
    assert captured["previous_file"] == _lge(upcoming)
    assert captured["upcoming_file"] == _lge(upcoming)


def test_errors_when_previous_file_missing(runner, tmp_path: Path) -> None:
    # The file's folder is absent: one FAIL line in Windows' words, exit 2.
    nowhere = tmp_path / "nowhere"
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(nowhere))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {_lge(nowhere)}: The system cannot find the path specified.\n"
    )


def test_errors_when_previous_file_missing_from_its_folder(
    runner, tmp_path: Path
) -> None:
    # The folder exists but holds no such file: Windows' file phrase.
    folder = tmp_path / "empty"
    folder.mkdir()
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(folder))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {_lge(folder)}: The system cannot find the file specified.\n"
    )


def test_errors_on_oserror(runner, monkeypatch, folders) -> None:
    # An OSError while writing/reading aborts cleanly, exit 2 (no traceback).
    previous, _ = folders

    def boom(**_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert result.stderr == "FAIL Disk full.\n"


def test_errors_when_dependency_missing(runner, monkeypatch, folders) -> None:
    # Missing solver dep -> exit 2, message names the module.
    previous, _ = folders

    def boom(**_: object) -> None:
        raise ModuleNotFoundError("No module named 'ortools'", name="ortools")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert result.stderr == "FAIL Missing ortools. Reinstall athc.\n"


def test_errors_when_no_feasible_schedule(runner, monkeypatch, folders) -> None:
    # A solver SchedulerError is a clean one-line exit 2, like a config error.
    previous, _ = folders

    def boom(**_: object) -> None:
        raise SchedulerError("CP-SAT returned status INFEASIBLE - no feasible schedule")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert "FAIL CP-SAT returned status INFEASIBLE - no feasible schedule" in (
        result.stderr
    )


class _ReachedSolver(AthcError):
    """Raised by the stubbed scheduler to prove the pre-checks passed; through
    the CLI it is one FAIL line."""

    def __init__(self) -> None:
        super().__init__("Reached the solver.")


REACHED = "FAIL Reached the solver.\n"


def _stub_solver(monkeypatch) -> None:
    def fake_get_scheduler():
        def run(**kwargs: object) -> None:
            # main() must forward the season: rivalry hosting rotates on it.
            assert kwargs["season"] == 2048
            # And the league built from the two files.
            assert kwargs["league"].has_divisions  # type: ignore[attr-defined]
            raise _ReachedSolver

        return run

    monkeypatch.setattr(main_module, "get_scheduler", fake_get_scheduler)


def _run_main(previous: Path, upcoming: Path, tmp_path: Path, **overrides) -> None:
    rules = tmp_path / "rules.toml"
    rules.write_text(RENAMES_TOML, encoding="utf-8")
    arguments = {
        "league": LEAGUE,
        "season": 2048,
        "config_path": rules,
        "previous_file": _lge(previous),
        "upcoming_file": _lge(upcoming),
        "output_dir": tmp_path,
        "seed": 0,
        "time_limit": None,
        "command_line": "test",
    }
    main_module.generate_schedule(**(arguments | overrides))


def test_main_errors_when_the_previous_season_is_not_finished(
    tmp_path: Path, monkeypatch, folders
) -> None:
    # A warning, not an error: warn hears it and the run reaches the solver.
    _, upcoming = folders
    _stub_solver(monkeypatch)
    said: list[str] = []
    with pytest.raises(_ReachedSolver):
        _run_main(upcoming, upcoming, tmp_path, warn=said.append)
    assert said == [f"{_lge(upcoming)}: Season not finished. 142 game(s) not played."]


def test_main_builds_the_league_and_reaches_the_solver(
    tmp_path: Path, monkeypatch, folders
) -> None:
    previous, upcoming = folders
    _stub_solver(monkeypatch)
    with pytest.raises(_ReachedSolver):
        _run_main(previous, upcoming, tmp_path)


def test_cli_errors_when_the_previous_season_is_not_finished(
    runner, monkeypatch, folders
) -> None:
    # End to end through the CLI: the WARN line names the file, and the run
    # goes on to the solver.
    _, upcoming = folders
    _stub_solver(monkeypatch)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(upcoming))]
    )
    assert result.stderr == (
        f"WARN {_lge(upcoming)}: Season not finished. 142 game(s) not played.\n"
        "Generating the 2048 schedule\n" + REACHED
    )


def test_without_previous_the_renames_are_ignored(
    runner, monkeypatch, league_folder: Path
) -> None:
    # One file for both seasons: [renames.2048] would name a Baltimore the
    # 2048 file does not have, yet the run reaches the solver.
    (league_folder / "scheduler.toml").write_text(RENAMES_TOML, encoding="utf-8")
    _stub_solver(monkeypatch)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.stderr.endswith(REACHED)
    assert "renames" not in result.stderr


def test_cli_errors_when_a_renamed_team_is_not_listed(
    runner, folders, league_folder: Path
) -> None:
    # No scheduler.toml, so no [renames.2048]: the message says where to add it.
    previous, upcoming = folders
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {_lge(previous)}: Team(s) not in {_lge(upcoming)}: Baltimore. "
        f"List renamed teams under [renames.2048] in "
        f"{league_folder / 'scheduler.toml'}.\n"
    )


def test_league_and_season_resolve_files_and_output_to_cwd(
    runner, monkeypatch, config_dir: Path, tmp_path: Path, write_config, folders
) -> None:
    # --league names the league; --previous the previous season's file; the
    # league's path holds the upcoming season's; output_dir is cwd.
    write_config("[athc]\n")  # no configured league: --league alone names it
    previous, upcoming = folders
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        generate_schedule,
        ["--season", "2048", "--league", LEAGUE, "--previous", str(_lge(previous))],
    )
    assert result.exit_code == 0, result.stderr
    folder = config_dir / "leagues" / LEAGUE
    assert captured["league"] == LEAGUE
    assert captured["season"] == 2048
    assert captured["previous_file"] == _lge(previous)
    assert captured["upcoming_file"] == _lge(upcoming)
    assert captured["config_path"] == folder / "scheduler.toml"
    assert captured["output_dir"] == Path.cwd()  # output goes to the current folder


def test_upcoming_option_overrides_the_league_path(
    runner, monkeypatch, tmp_path: Path, folders
) -> None:
    previous, _ = folders
    other = tmp_path / "other" / f"{LEAGUE}.lge"
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    result = runner.invoke(
        generate_schedule,
        [
            "--season",
            "2048",
            "--previous",
            str(_lge(previous)),
            "--upcoming",
            str(other),
        ],
    )
    assert result.exit_code == 0, result.stderr
    assert captured["upcoming_file"] == other


def test_errors_when_the_league_has_no_path(
    runner, folders, league_folder: Path
) -> None:
    # No --upcoming and no path in league.toml: nothing names the upcoming file.
    previous, _ = folders
    (league_folder / "league.toml").write_text("[league]\n", encoding="utf-8")
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league_folder / 'league.toml'}: League files folder is not set. "
        "Run 'athc config set path FOLDER' or pass --upcoming.\n"
    )


def test_season_resolves_files_for_the_configured_league(
    runner, monkeypatch, tmp_path: Path, folders
) -> None:
    # No --league: the league named in athc.ini.
    previous, upcoming = folders
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 0, result.stderr
    assert captured["league"] == LEAGUE
    assert captured["previous_file"] == _lge(previous)
    assert captured["upcoming_file"] == _lge(upcoming)


def test_errors_when_league_has_no_folder(runner, config_dir: Path, folders) -> None:
    # --league names a league with no folder under leagues -> exit 2 naming it.
    previous, _ = folders
    result = runner.invoke(
        generate_schedule,
        ["--season", "2048", "--previous", str(_lge(previous)), "--league", "nope"],
    )
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "nope", LEAGUE)


def test_errors_when_no_league_is_configured(
    runner, config_dir: Path, write_config, folders
) -> None:
    # No --league, no [athc] league -> exit 2.
    write_config("[athc]\n")
    previous, _ = folders
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)


# ── progress and the result lines ─────────────────────────────────────────────


def _generated(tmp_path: Path) -> GeneratedSchedule:
    """What a solved run returns: 128 games, seed 7, the three files."""
    conference = Conference(1, "AFC")
    home, away = Team("Denver", conference), Team("Las Vegas", conference)
    schedule = Schedule(games=tuple(Game(1, home, away) for _ in range(128)))
    result = SchedulerResult(schedule, MatchupPlan(matchups=()), workers=1)
    base = tmp_path / "schedule_2048_x"
    return GeneratedSchedule(
        result,
        7,
        (
            base.with_suffix(".txt"),
            base.with_suffix(".html"),
            base.with_name("schedule_2048_x_report.html"),
        ),
    )


def test_prints_files_and_result_line(
    runner, monkeypatch, tmp_path: Path, folders
) -> None:
    previous, _ = folders
    generated = _generated(tmp_path)
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: generated)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 0
    assert result.stdout == "".join(
        f"OK   {path}: written\n" for path in generated.files
    ) + ("Generated 128 games (seed 7)\n")
    assert result.stderr == ""


def test_main_says_generating_and_forwards_progress_to_the_solver(
    tmp_path: Path, monkeypatch, folders
) -> None:
    previous, upcoming = folders
    said: list[str] = []
    seen: dict[str, object] = {}

    def fake_get_scheduler():
        def run(**kwargs: object) -> None:
            seen.update(kwargs)
            raise _ReachedSolver

        return run

    monkeypatch.setattr(main_module, "get_scheduler", fake_get_scheduler)
    with pytest.raises(_ReachedSolver):
        _run_main(previous, upcoming, tmp_path, progress=said.append)
    assert said == ["Generating the 2048 schedule"]
    assert seen["progress"] == said.append


# ── Ctrl+C while the files are written ────────────────────────────────────────


def test_ctrl_c_during_the_writes_writes_all_three_then_interrupts(
    runner, monkeypatch, tmp_path: Path, folders, league_folder: Path
) -> None:
    # The press comes while the .txt is written; the .html and the report are
    # written all the same, then the run ends as Ctrl+C does anywhere.
    previous, _ = folders
    (league_folder / "scheduler.toml").write_text(RENAMES_TOML, encoding="utf-8")
    kernel32 = FakeKernel32()
    monkeypatch.setattr(utils, "_kernel32", kernel32)
    solved = _generated(tmp_path).result
    monkeypatch.setattr(main_module, "get_scheduler", lambda: lambda **_: solved)
    monkeypatch.setattr(main_module, "cpu_name", lambda: "CPU")
    monkeypatch.setattr(main_module, "build_schedule_report", lambda **_: None)

    def writer(press: bool):
        class Writer:
            def __init__(self, path: Path, **_: object) -> None:
                self.path = Path(path)

            def write(self, _: object) -> None:
                self.path.write_text("written", encoding="utf-8")
                if press:
                    (routine,) = kernel32.installed
                    assert routine(CTRL_C_EVENT) is True

        return Writer

    monkeypatch.setattr(main_module, "TxtScheduleWriter", writer(press=True))
    monkeypatch.setattr(main_module, "HtmlScheduleWriter", writer(press=False))
    monkeypatch.setattr(main_module, "HtmlReportWriter", writer(press=False))
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.chdir(output)
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--previous", str(_lge(previous))]
    )
    assert result.exit_code == 130
    assert result.stderr.endswith("FAIL Interrupted.\n")
    written = sorted(path.name for path in output.iterdir())
    assert len(written) == 3
    assert {Path(name).suffix for name in written} == {".txt", ".html"}
    assert sum(name.endswith("_report.html") for name in written) == 1
    assert kernel32.installed == []
