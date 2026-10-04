"""Integration test for `athc generate-schedule` (CLI -> files), per league.

Golden regression: for each test league a fixed seed must reproduce byte-for-byte
the three frozen output files (schedule .txt, schedule .html, report .html), and
the generated schedule must obey every rule that applies to that league. Slow (a
full solve per league); skipped by default. Run with `pytest -m slow`.

To regenerate every golden set after an intentional change, run this module as a
script: `python -m tests.integration.test_generate_schedule --bless`.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from athc.cli import cli
from athc.scheduler.config import load_league, load_scheduler_config
from tests.integration.conftest import DATA, EXPECTED
from tests.integration.schedule_validation import (
    game_keys,
    parse_schedule_html,
    parse_schedule_txt,
    validate_report,
    validate_schedule,
)


@dataclass(frozen=True)
class GoldenCase:
    """A test league: committed, test-owned inputs (standings, a frozen rules
    file with every output-affecting key set, the seed) and its golden set."""

    league: str
    season: int
    seed: int = 0

    @property
    def standings(self) -> Path:
        return DATA / f"{self.league}.{self.season}.ini"

    @property
    def rules(self) -> Path:
        return DATA / f"{self.league}.scheduler.toml"

    @property
    def golden_txt(self) -> Path:
        return EXPECTED / f"schedule_{self.season}.txt"

    @property
    def golden_html(self) -> Path:
        return EXPECTED / f"schedule_{self.season}.html"

    @property
    def golden_report(self) -> Path:
        return EXPECTED / f"schedule_{self.season}_report.html"


CASES = (GoldenCase("divisions", 2026), GoldenCase("conferences", 2029))

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


def _write_config(config_dir: Path, case: GoldenCase) -> None:
    """Install the league's committed standings + rules as its league folder in an
    athc config dir."""
    folder = config_dir / "leagues" / case.league
    (folder / "rules").mkdir(parents=True)
    (folder / "standings").mkdir()
    shutil.copy(case.standings, folder / "standings" / f"{case.season}.league.ini")
    shutil.copy(case.rules, folder / "rules" / "scheduler.toml")


def _generate(directory: Path, case: GoldenCase) -> tuple[str, str, str]:
    """Run the CLI into `directory` and return (txt, html, normalized report).

    No `--time-limit`: the run is driven entirely by the installed rules file.
    """
    from click.testing import CliRunner

    result = CliRunner().invoke(
        cli,
        [
            "--league",
            case.league,
            "generate-schedule",
            "--season",
            str(case.season),
            "--seed",
            str(case.seed),
        ],
    )
    assert result.exit_code == 0, result.output

    report_path = _single(directory, f"schedule_{case.season}_*_report.html")
    html_path = _single(
        directory,
        f"schedule_{case.season}_*[0-9].html",  # excludes the *_report.html
    )
    txt_path = _single(directory, f"schedule_{case.season}_*.txt")
    return (
        txt_path.read_text(encoding="utf-8"),
        html_path.read_text(encoding="utf-8"),
        _normalize_report(report_path.read_text(encoding="utf-8")),
    )


def _validate(case: GoldenCase, config_dir: Path, txt: str, html: str) -> None:
    """Correctness of each output file, independent of the golden bytes: the
    .txt schedule obeys every rule, the .html schedule encodes the same games,
    and the report's ranks/SOS values are correct for this schedule."""
    folder = config_dir / "leagues" / case.league
    league = load_league(folder / "standings" / f"{case.season}.league.ini")
    config = load_scheduler_config(folder / "rules" / "scheduler.toml")
    schedule = parse_schedule_txt(txt, league)
    validate_schedule(schedule, league, config, season=case.season)
    assert game_keys(parse_schedule_html(html, league)) == game_keys(schedule), (
        "HTML schedule does not encode the same games as the .txt"
    )
    validate_report(schedule, league)


@pytest.mark.slow
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.league)
def test_generate_schedule_matches_golden(
    case: GoldenCase, tmp_path: Path, config_dir: Path, monkeypatch
) -> None:
    _write_config(config_dir, case)
    monkeypatch.chdir(tmp_path)

    txt, html, report = _generate(tmp_path, case)
    _validate(case, config_dir, txt, html)

    # Regression + seed determinism: byte-identical to the frozen goldens.
    assert txt == case.golden_txt.read_text(encoding="utf-8"), "schedule .txt drifted"
    assert html == case.golden_html.read_text(encoding="utf-8"), (
        "schedule .html drifted"
    )
    assert report == case.golden_report.read_text(encoding="utf-8"), (
        "report .html drifted"
    )


def _bless() -> None:
    """Regenerate every golden set from a fresh solve (after validating rules)."""
    import os
    import tempfile

    origin = Path.cwd()
    for case in CASES:
        with tempfile.TemporaryDirectory() as raw:
            try:
                workdir = Path(raw)
                config = workdir / "config"
                config.mkdir(parents=True)
                os.environ["ATHC_CONFIG_DIR"] = str(config)
                _write_config(config, case)
                os.chdir(workdir)

                txt, html, report = _generate(workdir, case)
                _validate(case, config, txt, html)  # valid before freezing

                EXPECTED.mkdir(exist_ok=True)
                case.golden_txt.write_text(txt, encoding="utf-8", newline="\r\n")
                case.golden_html.write_text(html, encoding="utf-8", newline="\r\n")
                case.golden_report.write_text(report, encoding="utf-8", newline="\r\n")
                print(f"Blessed {case.league} goldens in {EXPECTED} (validated).")
            finally:
                os.chdir(origin)  # leave the temp dir so it can be removed (Windows)


if __name__ == "__main__":
    if "--bless" in sys.argv:
        _bless()
    else:
        print("Pass --bless to regenerate the golden files.")
