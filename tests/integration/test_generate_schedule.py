"""Integration test for `athc generate-schedule` (CLI -> files).

Golden regression: a fixed seed must reproduce byte-for-byte the three frozen
output files (schedule .txt, schedule .html, report .html), and the generated
schedule must obey every scheduler rule. Slow (a full solve); skipped by
default. Run with `pytest -m slow`.

To regenerate the goldens after an intentional change, run this module as a
script: `python -m tests.integration.test_generate_schedule --bless`.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

from athc.cli.generate_schedule import generate_schedule
from athc.scheduler.config import load_league
from tests.integration.conftest import DATA, EXPECTED
from tests.integration.schedule_validation import (
    game_keys,
    parse_schedule_html,
    parse_schedule_txt,
    validate_report,
    validate_schedule,
)

# Committed, test-owned inputs that fully define the golden: the league file, a
# frozen scheduler rules file (solver width, time limits, every [phase2] amount,
# spread), and the seed. Nothing rides on in-code defaults or the shipped rules.
LEAGUE = DATA / "league.ini"
SCHEDULER_RULES = DATA / "PNFL.scheduler.toml"
SEASON = 2026
GOLDEN_SEED = 0

GOLDEN_TXT = EXPECTED / "schedule_2026.txt"
GOLDEN_HTML = EXPECTED / "schedule_2026.html"
GOLDEN_REPORT = EXPECTED / "schedule_2026_report.html"

# Report fields that vary run-to-run / machine-to-machine; normalized before
# any golden comparison. Everything else in the report is schedule-derived and
# stable for a fixed seed.
_VOLATILE_REPORT_LABELS = ("Command line", "Config path", "Elapsed (s)")


def _normalize_report(html: str) -> str:
    """Blank out the volatile info fields so the report is a stable golden."""
    for label in _VOLATILE_REPORT_LABELS:
        html = re.sub(
            rf"(<b>{re.escape(label)}:</b> ).*?(</p>)",
            r"\1<normalized>\2",
            html,
        )
    return html


def _single(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    assert len(matches) == 1, f"expected exactly one {pattern}, got {matches}"
    return matches[0]


def _write_config(config_dir: Path) -> None:
    """Install the committed league + scheduler rules into an athc config dir."""
    shutil.copy(LEAGUE, config_dir / f"{SEASON}.league.ini")
    rules_dir = config_dir / "rules"
    rules_dir.mkdir(exist_ok=True)
    shutil.copy(SCHEDULER_RULES, rules_dir / "PNFL.scheduler.toml")


def _generate(directory: Path) -> tuple[str, str, str]:
    """Run the CLI into `directory` and return (txt, html, normalized report).

    No `--time-limit`: the run is driven entirely by the installed rules file.
    """
    from click.testing import CliRunner

    result = CliRunner().invoke(
        generate_schedule, ["--season", str(SEASON), "--seed", str(GOLDEN_SEED)]
    )
    assert result.exit_code == 0, result.output

    report_path = _single(directory, f"schedule_{SEASON}_*_report.html")
    html_path = _single(
        directory,
        f"schedule_{SEASON}_*[0-9].html",  # excludes the *_report.html
    )
    txt_path = _single(directory, f"schedule_{SEASON}_*.txt")
    return (
        txt_path.read_text(encoding="utf-8"),
        html_path.read_text(encoding="utf-8"),
        _normalize_report(report_path.read_text(encoding="utf-8")),
    )


@pytest.mark.slow
def test_generate_schedule_matches_golden(
    tmp_path: Path, config_dir: Path, monkeypatch
) -> None:
    _write_config(config_dir)
    monkeypatch.chdir(tmp_path)

    txt, html, report = _generate(tmp_path)
    league = load_league(config_dir / f"{SEASON}.league.ini")
    schedule = parse_schedule_txt(txt, league)

    # 1. Correctness of each output file (independent of the golden bytes):
    #    - the .txt schedule obeys every rule
    #    - the .html schedule encodes the same games
    #    - the report's ranks/SOS values are correct for this schedule
    validate_schedule(schedule, league)
    assert game_keys(parse_schedule_html(html, league)) == game_keys(schedule), (
        "HTML schedule does not encode the same games as the .txt"
    )
    validate_report(schedule, league)

    # 2. Regression + seed determinism: byte-identical to the frozen goldens.
    assert txt == GOLDEN_TXT.read_text(encoding="utf-8"), "schedule .txt drifted"
    assert html == GOLDEN_HTML.read_text(encoding="utf-8"), "schedule .html drifted"
    assert report == GOLDEN_REPORT.read_text(encoding="utf-8"), "report .html drifted"


def _bless() -> None:
    """Regenerate the golden files from a fresh solve (after validating rules)."""
    import os
    import tempfile

    origin = Path.cwd()
    with tempfile.TemporaryDirectory() as raw:
        try:
            workdir = Path(raw)
            config = workdir / "config"
            config.mkdir(parents=True)
            os.environ["ATHC_CONFIG_DIR"] = str(config)
            _write_config(config)
            os.chdir(workdir)

            txt, html, report = _generate(workdir)
            league = load_league(config / f"{SEASON}.league.ini")
            schedule = parse_schedule_txt(txt, league)
            # Confirm all three files are valid before freezing them.
            validate_schedule(schedule, league)
            assert game_keys(parse_schedule_html(html, league)) == game_keys(schedule)
            validate_report(schedule, league)

            EXPECTED.mkdir(exist_ok=True)
            GOLDEN_TXT.write_text(txt, encoding="utf-8", newline="\n")
            GOLDEN_HTML.write_text(html, encoding="utf-8", newline="\n")
            GOLDEN_REPORT.write_text(report, encoding="utf-8", newline="\n")
            print(f"Blessed goldens in {EXPECTED} (schedule, HTML, report validated).")
        finally:
            os.chdir(origin)  # leave the temp dir so it can be removed (Windows)


if __name__ == "__main__":
    if "--bless" in sys.argv:
        _bless()
    else:
        print("Pass --bless to regenerate the golden files.")
