"""Integration tests for `athc generate-schedule` (CLI -> files).

Slow (full solves), skipped by default. Run with `pytest -m slow` or
`pytest -m slow_c`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from athc.cli.generate_schedule import generate_schedule
from tests.integration.conftest import DATA

LEAGUE = DATA / "league.ini"
SEASON = 2026


@pytest.mark.slow
@pytest.mark.slow_c
def test_generate_schedule_writes_schedules_and_report(
    runner, tmp_path: Path, config_dir: Path, monkeypatch
) -> None:
    # Only league.ini is needed (with [DivisionStandings]); --season resolves
    # it. Output lands in the current directory.
    shutil.copy(LEAGUE, config_dir / f"{SEASON}.league.ini")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        generate_schedule,
        [
            "--season",
            str(SEASON),
            "--seed",
            "0",
            "--time-limit",
            "1200",
        ],
    )
    assert result.exit_code == 0, result.output

    reports = list(tmp_path.glob(f"schedule_{SEASON}_C_*_report.html"))
    txts = list(tmp_path.glob(f"schedule_{SEASON}_C_*.txt"))
    htmls = [
        p
        for p in tmp_path.glob(f"schedule_{SEASON}_C_*.html")
        if not p.name.endswith("_report.html")
    ]
    assert len(txts) == 1 and txts[0].read_text(encoding="utf-8").strip()
    assert len(htmls) == 1 and htmls[0].read_text(encoding="utf-8").strip()
    assert len(reports) == 1 and reports[0].read_text(encoding="utf-8").strip()
