"""Integration test for `athc generate-schedule` (default scheduler, CLI -> file).

Slow (full solve), so it is skipped by default; run with `pytest -m slow`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.cli.generate_schedule import generate_schedule

RELEASE = Path(__file__).resolve().parents[2] / "release"
LEAGUE = RELEASE / "league.ini"
HISTORY = RELEASE / "nonconf_history.json"


@pytest.mark.slow
def test_generate_schedule_writes_schedule_and_report(runner, tmp_path: Path) -> None:
    output = tmp_path / "season.txt"
    result = runner.invoke(
        generate_schedule,
        [
            "--output",
            str(output),
            "--season",
            "2026",
            "--league",
            str(LEAGUE),
            "--history",
            str(HISTORY),
            "--seed",
            "0",
            "--time-limit",
            "1200",  # 20-minute cap
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.read_text(encoding="utf-8").strip()  # schedule written, non-empty
    report = output.with_name("season-report.txt")
    assert report.read_text(encoding="utf-8").strip()  # companion report written
