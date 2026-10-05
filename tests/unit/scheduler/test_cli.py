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
from athc.scheduler.config import ConfigError
from athc.scheduler.schedulers.errors import SchedulerError

from .test_config import LEAGUE, LEAGUE_MISSING_DIVISION_STANDINGS, VALID_LEAGUE


@pytest.fixture(autouse=True)
def league_config(config_dir: Path, write_config) -> None:
    """A configured league with its folder, so tests without --league resolve one."""
    folder = config_dir / "leagues" / LEAGUE
    (folder / "rules").mkdir(parents=True)
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


def test_errors_when_league_file_missing(runner, caplog) -> None:
    # No standings/2026.league.ini in the league folder -> clear error naming it,
    # exit 1.
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2026"])
    assert result.exit_code == 1
    assert any("2026.league.ini" in r.getMessage() for r in caplog.records)


def test_errors_on_oserror(runner, monkeypatch, caplog, config_dir: Path) -> None:
    # An OSError while writing/reading aborts cleanly, exit 1 (no traceback).
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_errors_when_dependency_missing(
    runner, monkeypatch, caplog, config_dir: Path
) -> None:
    # Missing solver dep -> exit 1, message names the module + the extra to install.
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise ModuleNotFoundError("No module named 'ortools'", name="ortools")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any("ortools" in r.getMessage() for r in caplog.records)


def test_errors_when_no_feasible_schedule(
    runner, monkeypatch, caplog, config_dir: Path
) -> None:
    # A solver SchedulerError is a clean one-line exit 1, like a config error.
    _write_season_files(config_dir, 2048)

    def boom(**_: object) -> None:
        raise SchedulerError("CP-SAT returned status INFEASIBLE - no feasible schedule")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any("no feasible schedule" in r.getMessage() for r in caplog.records)


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
    with pytest.raises(ConfigError, match="DivisionStandings"):
        _run_main(league_path, tmp_path)


def test_main_accepts_division_standings(tmp_path: Path, monkeypatch) -> None:
    league_path = tmp_path / "league.ini"
    league_path.write_text(VALID_LEAGUE, encoding="utf-8")
    _stub_solver(monkeypatch)
    with pytest.raises(_ReachedSolver):
        _run_main(league_path, tmp_path)


def test_cli_errors_without_division_standings(
    runner, caplog, config_dir: Path
) -> None:
    # End to end through the CLI: clean exit 1, message names the section.
    _standings_path(config_dir, 2048).write_text(
        LEAGUE_MISSING_DIVISION_STANDINGS, encoding="utf-8"
    )
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any("DivisionStandings" in r.getMessage() for r in caplog.records)


def test_league_and_season_resolve_files_and_output_to_cwd(
    runner, monkeypatch, config_dir: Path, tmp_path: Path, write_config
) -> None:
    # --league names the league; --season picks its file; output_dir is cwd.
    write_config("[athc]\n")  # no configured league: --league alone names it
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(generate_schedule, ["--season", "2048", "--league", LEAGUE])
    assert result.exit_code == 0, result.output
    folder = config_dir / "leagues" / LEAGUE
    assert captured["league"] == LEAGUE
    assert captured["league_path"] == folder / "standings" / "2048.league.ini"
    assert captured["config_path"] == folder / "rules" / "scheduler.toml"
    assert captured["output_dir"] == Path.cwd()  # output goes to the current dir


def test_season_resolves_files_for_the_configured_league(
    runner, monkeypatch, config_dir: Path, tmp_path: Path
) -> None:
    # No --league: the league named in athc.ini.
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 0, result.output
    folder = config_dir / "leagues" / LEAGUE
    assert captured["league"] == LEAGUE
    assert captured["league_path"] == folder / "standings" / "2048.league.ini"


def test_errors_when_league_has_no_folder(runner, caplog, config_dir: Path) -> None:
    # --league names a league with no folder under leagues -> exit 1 naming it.
    _write_season_files(config_dir, 2048)
    with caplog.at_level("ERROR"):
        result = runner.invoke(
            generate_schedule, ["--season", "2048", "--league", "nope"]
        )
    assert result.exit_code == 1
    assert any("league 'nope' not found" in r.getMessage() for r in caplog.records)


def test_errors_when_no_league_is_configured(
    runner, caplog, config_dir: Path, write_config
) -> None:
    # No --league, no [athc] league -> exit 1.
    write_config("[athc]\n")
    _write_season_files(config_dir, 2048)
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any("no league selected" in r.getMessage() for r in caplog.records)
