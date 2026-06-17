"""Tests for `athc generate-schedule` argument handling and config errors.

Config is resolved from `config_dir()` (isolated per-test via the autouse
`config_dir` fixture): scheduler tunables from `rules/PNFL.scheduler.toml`
(optional) and league data from `league.ini` (required). There is no `--config`
flag. The actual solve is exercised by the slow conftest-driven fixtures, not here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import athc.cli.generate_schedule as cli_module
from athc.cli.generate_schedule import generate_schedule


def test_requires_output(runner) -> None:
    assert runner.invoke(generate_schedule, ["--season", "2026"]).exit_code == 2


def test_requires_season(runner) -> None:
    assert runner.invoke(generate_schedule, ["--output", "s.txt"]).exit_code == 2


def test_unknown_output_format(runner, tmp_path: Path) -> None:
    result = runner.invoke(
        generate_schedule, ["--output", str(tmp_path / "s.xyz"), "--season", "2026"]
    )
    assert result.exit_code == 2


def test_errors_when_no_league(runner, caplog) -> None:
    # Empty config_dir -> no league.ini -> required-data error (scheduler config optional).
    with caplog.at_level("ERROR"):
        result = runner.invoke(
            generate_schedule, ["--output", "s.txt", "--season", "2026"]
        )
    assert result.exit_code == 2
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_rejects_unknown_scheduler(runner, tmp_path: Path) -> None:
    result = runner.invoke(
        generate_schedule,
        [
            "--output",
            str(tmp_path / "s.txt"),
            "--season",
            "2026",
            "--scheduler",
            "nope",
        ],
    )
    assert result.exit_code == 2


@pytest.mark.parametrize(
    ("args", "expected"),
    [([], "two-phase-rank"), (["--scheduler", "fixed-matchup"], "fixed-matchup")],
)
def test_scheduler_passes_through(
    runner, monkeypatch, tmp_path: Path, args: list[str], expected: str
) -> None:
    # Default is the new scheduler; --scheduler overrides. run_generate is stubbed
    # so no solve runs (the real solve is covered by the slow fixtures).
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "find_league_path", lambda: tmp_path / "league.ini")
    monkeypatch.setattr(cli_module, "run_generate", lambda **kw: captured.update(kw))
    result = runner.invoke(
        generate_schedule,
        ["--output", str(tmp_path / "s.txt"), "--season", "2026", *args],
    )
    assert result.exit_code == 0
    assert captured["scheduler"] == expected
