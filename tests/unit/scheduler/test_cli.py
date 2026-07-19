"""Tests for `athc generate-schedule` argument handling and config errors.

Config is resolved from `config_dir()` (autouse fixture). The CLI requires
`<season>.league.ini` and `<season>.nonconf_history.json` there. The real solve
runs only in the slow fixtures; here `run_generate` is stubbed where needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import athc.cli.generate_schedule as cli_module
import athc.scheduler.main as main_module
from athc.cli.generate_schedule import generate_schedule
from athc.scheduler.config import ConfigError

from .test_config import LEAGUE_WITH_DIVISION_STANDINGS, VALID_LEAGUE


def _write_season_files(config_dir: Path, season: int) -> None:
    """Dummy season files so resolution succeeds (content unused when stubbed)."""
    (config_dir / f"{season}.league.ini").write_text("x", encoding="utf-8")
    (config_dir / f"{season}.nonconf_history.json").write_text("{}", encoding="utf-8")


def test_requires_season(runner) -> None:
    assert runner.invoke(generate_schedule, []).exit_code == 2


def test_rejects_non_integer_time_limit(runner) -> None:
    # --time-limit is now an integer; a fractional value is a usage error.
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--time-limit", "1.5"]
    )
    assert result.exit_code == 2


def test_rejects_unknown_scheduler(runner) -> None:
    result = runner.invoke(
        generate_schedule, ["--season", "2048", "--scheduler", "nope"]
    )
    assert result.exit_code == 2


def test_errors_when_league_file_missing(runner, caplog) -> None:
    # Empty config_dir -> no <season>.league.ini -> clear error, exit 1.
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2026"])
    assert result.exit_code == 1
    assert any("league" in r.getMessage() for r in caplog.records)


def test_errors_when_history_missing_for_scheduler_a(
    runner, caplog, config_dir: Path
) -> None:
    # Scheduler A needs history; missing -> clear error, exit 1.
    (config_dir / "2026.league.ini").write_text("x", encoding="utf-8")
    with caplog.at_level("ERROR"):
        result = runner.invoke(
            generate_schedule, ["--season", "2026", "--scheduler", "A"]
        )
    assert result.exit_code == 1
    assert any("history" in r.getMessage() for r in caplog.records)


def test_scheduler_b_does_not_require_history(
    runner, monkeypatch, config_dir: Path
) -> None:
    # Scheduler B (default) ignores history; only league.ini is needed.
    (config_dir / "2026.league.ini").write_text("x", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    result = runner.invoke(generate_schedule, ["--season", "2026"])
    assert result.exit_code == 0
    assert captured["history_path"] is None


@pytest.mark.parametrize("scheduler", ["C", "D"])
def test_schedulers_c_and_d_do_not_require_history(
    runner, monkeypatch, config_dir: Path, scheduler: str
) -> None:
    # C and D select by rank only; like B they ignore history.
    (config_dir / "2026.league.ini").write_text("x", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    result = runner.invoke(
        generate_schedule, ["--season", "2026", "--scheduler", scheduler]
    )
    assert result.exit_code == 0
    assert captured["history_path"] is None


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
    (config_dir / "2048.league.ini").write_text("x", encoding="utf-8")

    def boom(**_: object) -> None:
        raise ModuleNotFoundError("No module named 'ortools'", name="ortools")

    monkeypatch.setattr(cli_module, "run_generate", boom)
    with caplog.at_level("ERROR"):
        result = runner.invoke(generate_schedule, ["--season", "2048"])
    assert result.exit_code == 1
    assert any("ortools" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], "B"),
        (["--scheduler", "A"], "A"),
        (["--scheduler", "C"], "C"),
        (["--scheduler", "D"], "D"),
    ],
)
def test_scheduler_passes_through(
    runner, monkeypatch, config_dir: Path, args: list[str], expected: str
) -> None:
    # run_generate is stubbed so no solve runs; both season files must exist.
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    result = runner.invoke(generate_schedule, ["--season", "2048", *args])
    assert result.exit_code == 0
    assert captured["scheduler"] == expected


class _ReachedSolver(Exception):
    """Raised by the stubbed scheduler to prove the pre-checks passed."""


def _stub_solver(monkeypatch) -> None:
    def fake_get_scheduler(name: str):
        def run(**_: object) -> None:
            raise _ReachedSolver

        return run

    monkeypatch.setattr(main_module, "get_scheduler", fake_get_scheduler)


def _run_main(league_path: Path, scheduler: str, tmp_path: Path) -> None:
    main_module.generate_schedule(
        season=2048,
        scheduler=scheduler,
        config_path=tmp_path / "rules.toml",
        league_path=league_path,
        history_path=None,
        output_dir=tmp_path,
        seed=0,
        time_limit=None,
        command_line="test",
    )


@pytest.mark.parametrize("scheduler", ["C", "D"])
def test_main_errors_without_division_standings(tmp_path: Path, scheduler: str) -> None:
    # C and D need [DivisionStandings]; the check runs before any solve.
    league_path = tmp_path / "league.ini"
    league_path.write_text(VALID_LEAGUE, encoding="utf-8")
    with pytest.raises(ConfigError, match="DivisionStandings"):
        _run_main(league_path, scheduler, tmp_path)


@pytest.mark.parametrize("scheduler", ["C", "D"])
def test_main_accepts_division_standings(
    tmp_path: Path, monkeypatch, scheduler: str
) -> None:
    league_path = tmp_path / "league.ini"
    league_path.write_text(LEAGUE_WITH_DIVISION_STANDINGS, encoding="utf-8")
    _stub_solver(monkeypatch)
    with pytest.raises(_ReachedSolver):
        _run_main(league_path, scheduler, tmp_path)


def test_main_scheduler_b_ignores_missing_division_standings(
    tmp_path: Path, monkeypatch
) -> None:
    league_path = tmp_path / "league.ini"
    league_path.write_text(VALID_LEAGUE, encoding="utf-8")
    _stub_solver(monkeypatch)
    with pytest.raises(_ReachedSolver):
        _run_main(league_path, "B", tmp_path)


@pytest.mark.parametrize("scheduler", ["C", "D"])
def test_cli_errors_without_division_standings(
    runner, caplog, config_dir: Path, scheduler: str
) -> None:
    # End to end through the CLI: clean exit 1, message names the section.
    (config_dir / "2048.league.ini").write_text(VALID_LEAGUE, encoding="utf-8")
    with caplog.at_level("ERROR"):
        result = runner.invoke(
            generate_schedule, ["--season", "2048", "--scheduler", scheduler]
        )
    assert result.exit_code == 1
    assert any("DivisionStandings" in r.getMessage() for r in caplog.records)


def test_season_resolves_files_and_outputs_to_cwd(
    runner, monkeypatch, config_dir: Path, tmp_path: Path
) -> None:
    # Scheduler A resolves both season files; output_dir is the current directory.
    _write_season_files(config_dir, 2048)
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(generate_schedule, ["--season", "2048", "--scheduler", "A"])
    assert result.exit_code == 0
    assert captured["league_path"] == config_dir / "2048.league.ini"
    assert captured["history_path"] == config_dir / "2048.nonconf_history.json"
    assert captured["output_dir"] == Path.cwd()  # output goes to the current dir
