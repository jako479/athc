"""Tests for `athc generate-schedule` argument handling and config errors.

Config is resolved from `config_dir()` (autouse fixture). The CLI requires
`leagues/<NAME>/standings/<season>.league.ini` for the league. The real solve runs
only in the slow fixtures; here `run_generate` is stubbed where needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import athc.cli.generate_schedule as cli_module
import athc.scheduler.main as main_module
from athc.cli.generate_schedule import generate_schedule
from athc.errors import ConfigFileError
from athc.scheduler.domain.league import Conference, Team
from athc.scheduler.domain.schedule import Game, Schedule
from athc.scheduler.main import GeneratedSchedule
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.types import MatchupPlan, SchedulerResult
from tests.conftest import league_not_found, no_league_selected

from .test_config import LEAGUE, LEAGUE_MISSING_DIVISION_STANDINGS, VALID_LEAGUE


@pytest.fixture(autouse=True)
def league_config(config_dir: Path, write_config) -> None:
    """A configured league with its folder, so tests without --league resolve one."""
    folder = config_dir / "leagues" / LEAGUE
    folder.mkdir(parents=True)
    (folder / "standings").mkdir()
    write_config(f"[athc]\nleague = {LEAGUE}\n")


def _standings_path(config_dir: Path, season: int) -> Path:
    return config_dir / "leagues" / LEAGUE / "standings" / f"{season}.league.ini"


def _write_season_files(config_dir: Path, season: int) -> Path:
    """Dummy standings file so resolution succeeds (content unused when stubbed).
    Returns its path."""
    path = _standings_path(config_dir, season)
    path.write_text("x", encoding="utf-8")
    return path


def test_requires_season(runner) -> None:
    assert runner.invoke(generate_schedule, []).exit_code == 2


def test_rejects_non_integer_time_limit(runner) -> None:
    # --time-limit is now an integer; a fractional value is a usage error.
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--time-limit", "1.5"]
    )
    assert result.exit_code == 2


def test_no_worker_count_override(runner) -> None:
    # solver_workers is config-only (a reproducibility contract), never a CLI
    # flag; an unknown option is a usage error.
    result = runner.invoke(generate_schedule, ["--season", "2048", "--workers", "4"])
    assert result.exit_code == 2


def test_errors_when_league_file_missing(runner) -> None:
    # No standings/2026.league.ini in the league folder -> clear error naming it,
    # exit 2.
    result = runner.invoke(generate_schedule, ["--season", "2026"])
    assert result.exit_code == 2
    assert result.stderr.startswith("FAIL ") and "2026.league.ini" in result.stderr


def test_errors_on_oserror(runner, monkeypatch, config_dir: Path) -> None:
    # An OSError while writing/reading aborts cleanly, exit 2 (no traceback).
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 2
    assert result.stderr == "FAIL disk full\n"


def test_errors_when_dependency_missing(runner, monkeypatch, config_dir: Path) -> None:
    # Missing solver dep -> exit 2, message names the module.
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise ModuleNotFoundError("No module named 'ortools'", name="ortools")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 2
    assert result.stderr == "FAIL missing ortools -- reinstall athc\n"


def test_errors_when_no_feasible_schedule(
    runner, monkeypatch, config_dir: Path
) -> None:
    # A solver SchedulerError is a clean one-line exit 2, like a config error.
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise SchedulerError("CP-SAT returned status INFEASIBLE - no feasible schedule")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 2
    assert "FAIL CP-SAT returned status INFEASIBLE - no feasible schedule" in (
        result.stderr
    )


class _ReachedSolver(Exception):
    """Raised by the stubbed scheduler to prove the pre-checks passed."""


def _stub_solver(monkeypatch) -> None:
    def fake_get_scheduler():
        def run(**kwargs: object) -> None:
            # main() must forward the season: rivalry hosting rotates on it.
            assert kwargs["season"] == 2048
            raise _ReachedSolver

        return run

    monkeypatch.setattr(main_module, "get_scheduler", fake_get_scheduler)


def _run_main(league_path: Path, tmp_path: Path) -> None:
    main_module.generate_schedule(
        league=LEAGUE,
        season=2048,
        config_path=tmp_path / "rules.toml",
        league_path=league_path,
        output_dir=tmp_path,
        seed=0,
        time_limit=None,
        command_line="test",
    )


def test_main_errors_without_division_standings(tmp_path: Path) -> None:
    # [DivisionStandings] is required; the check runs before any solve.
    league_path = tmp_path / "league.ini"
    league_path.write_text(LEAGUE_MISSING_DIVISION_STANDINGS, encoding="utf-8")
    with pytest.raises(ConfigFileError, match="DivisionStandings"):
        _run_main(league_path, tmp_path)


def test_main_accepts_division_standings(tmp_path: Path, monkeypatch) -> None:
    league_path = tmp_path / "league.ini"
    league_path.write_text(VALID_LEAGUE, encoding="utf-8")
    _stub_solver(monkeypatch)
    with pytest.raises(_ReachedSolver):
        _run_main(league_path, tmp_path)


def test_cli_errors_without_division_standings(runner, config_dir: Path) -> None:
    # End to end through the CLI: clean exit 2, message names the section.
    _standings_path(config_dir, 2048).write_text(
        LEAGUE_MISSING_DIVISION_STANDINGS, encoding="utf-8"
    )
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {_standings_path(config_dir, 2048)}: must have exactly one of the "
        "[DivisionStandings] and [ConferenceStandings] sections.\n"
    )


def _capture(captured: dict[str, object], tmp_path: Path):
    """A `run_generate` stub that records its arguments and returns a solved run."""

    def run(**kwargs: object) -> GeneratedSchedule:
        captured.update(kwargs)
        return _generated(tmp_path)

    return run


def test_league_and_season_resolve_files_and_output_to_cwd(
    runner, monkeypatch, config_dir: Path, tmp_path: Path, write_config
) -> None:
    # --league names the league; --season picks its file; output_dir is cwd.
    write_config("[athc]\n")  # no configured league: --league alone names it
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(generate_schedule, ["--season", "2048", "--league", LEAGUE])
    assert result.exit_code == 0, result.stderr
    folder = config_dir / "leagues" / LEAGUE
    assert captured["league"] == LEAGUE
    assert captured["league_path"] == folder / "standings" / "2048.league.ini"
    assert captured["config_path"] == folder / "scheduler.toml"
    assert captured["output_dir"] == Path.cwd()  # output goes to the current dir


def test_season_resolves_files_for_the_configured_league(
    runner, monkeypatch, config_dir: Path, tmp_path: Path
) -> None:
    # No --league: the league named in athc.ini.
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", _capture(captured, tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 0, result.stderr
    folder = config_dir / "leagues" / LEAGUE
    assert captured["league"] == LEAGUE
    assert captured["league_path"] == folder / "standings" / "2048.league.ini"


def test_errors_when_league_has_no_folder(runner, config_dir: Path) -> None:
    # --league names a league with no folder under leagues -> exit 2 naming it.
    _write_season_files(config_dir, 2048)
    result = runner.invoke(generate_schedule, ["--season", "2048", "--league", "nope"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "nope", LEAGUE)


def test_errors_when_no_league_is_configured(
    runner, config_dir: Path, write_config
) -> None:
    # No --league, no [athc] league -> exit 2.
    write_config("[athc]\n")
    _write_season_files(config_dir, 2048)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)


# ── progress and the result lines ─────────────────────────────────────────────


def _generated(tmp_path: Path) -> GeneratedSchedule:
    """What a solved run returns: 128 games, seed 7, the three files."""
    conference = Conference("AFC")
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
    runner, monkeypatch, config_dir: Path, tmp_path: Path
) -> None:
    _write_season_files(config_dir, 2048)
    generated = _generated(tmp_path)
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: generated)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 0
    assert result.stdout == "".join(f"OK   {path}\n" for path in generated.files) + (
        "Generated 128 games (seed 7)\n"
    )
    assert result.stderr == ""


def test_main_says_generating_and_forwards_progress_to_the_solver(
    tmp_path: Path, monkeypatch
) -> None:
    league_path = tmp_path / "league.ini"
    league_path.write_text(VALID_LEAGUE, encoding="utf-8")
    said: list[str] = []
    seen: dict[str, object] = {}

    def fake_get_scheduler():
        def run(**kwargs: object) -> None:
            seen.update(kwargs)
            raise _ReachedSolver

        return run

    monkeypatch.setattr(main_module, "get_scheduler", fake_get_scheduler)
    with pytest.raises(_ReachedSolver):
        main_module.generate_schedule(
            league=LEAGUE,
            season=2048,
            config_path=tmp_path / "rules.toml",
            league_path=league_path,
            output_dir=tmp_path,
            seed=0,
            time_limit=None,
            command_line="test",
            progress=said.append,
        )
    assert said == ["Generating the 2048 schedule"]
    assert seen["progress"] == said.append
