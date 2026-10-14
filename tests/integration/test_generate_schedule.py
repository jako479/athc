"""Integration test for `athc generate-schedule` (CLI -> files), per league.

Golden regression: for each test league a fixed seed must reproduce byte-for-byte
the three frozen output files (schedule .txt, schedule .html, report .html), and
the generated schedule must obey every rule that applies to that league. Slow (a
full solve per league); skipped by default. Run with `pytest -m slow`.

To regenerate every golden set after an intentional change, run this module as a
script: `python -m tests.integration.test_generate_schedule --bless`. It also
rewrites the built conference league files in data/.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

from athc.cli import cli
from athc.fbpro98_lge import parse_lge
from athc.scheduler.config import load_scheduler_config
from athc.scheduler.league_files import league_from_files
from tests.conftest import make_league_dir, write_config_file
from tests.integration.conftest import DATA, EXPECTED
from tests.integration.league_files import (
    CASE_BY_LEAGUE,
    CASES,
    GoldenCase,
    case_league,
    conference_league_files,
    no_warning,
    write_conference_league_files,
    write_league_files,
)
from tests.integration.schedule_validation import (
    game_keys,
    parse_schedule_html,
    parse_schedule_txt,
    validate_report,
    validate_schedule,
)
from tests.unit.scheduler.conftest import CONFERENCES_LEAGUE

# Report fields that vary run-to-run / machine-to-machine; normalized before
# any golden comparison. Everything else in the report is schedule-derived and
# stable for a fixed seed.
_VOLATILE_REPORT_LABELS = ("CPU", "Command line", "Config path", "Elapsed (s)")


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


def _write_config(config_dir: Path, case: GoldenCase, root: Path) -> Path:
    """Install the league in an athc config dir: its rules file and a
    `league.toml` whose `path` is the folder holding the upcoming season's
    file under `root`. Returns the previous season's file."""
    folder = make_league_dir(config_dir, case.league)
    previous, upcoming = write_league_files(case, root)
    write_config_file(folder, f"[league]\npath = '{upcoming.parent}'\n", "league.toml")
    shutil.copy(case.rules, folder / "scheduler.toml")
    return previous


def _generate(
    directory: Path, case: GoldenCase, previous: Path
) -> tuple[str, str, str]:
    """Run the CLI into `directory` and return (txt, html, normalized report).

    No `--time-limit`: the run is driven entirely by the installed rules file.
    """
    from click.testing import CliRunner

    result = CliRunner().invoke(
        cli,
        [
            "generate-schedule",
            "--league",
            case.league,
            "--season",
            str(case.season),
            "--previous",
            str(previous),
            "--seed",
            str(case.seed),
        ],
    )
    assert result.exit_code == 0, result.stderr

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


def _validate(case: GoldenCase, root: Path, txt: str, html: str) -> None:
    """Correctness of each output file, independent of the golden bytes: the
    .txt schedule obeys every rule, the .html schedule encodes the same games,
    and the report's ranks/SOS values are correct for this schedule."""
    league = case_league(case, root / "validate")
    config = load_scheduler_config(case.rules)
    schedule = parse_schedule_txt(txt, league)
    validate_schedule(schedule, league, config, season=case.season)
    assert game_keys(parse_schedule_html(html, league)) == game_keys(schedule), (
        "HTML schedule does not encode the same games as the .txt"
    )
    validate_report(schedule, league)


# --- the built conference league files (fast) ----------------------------------


def test_conference_league_files_reproduce_the_test_league() -> None:
    previous, upcoming = conference_league_files()
    case = CASE_BY_LEAGUE["conferences"]
    league = league_from_files(
        parse_lge(previous),
        parse_lge(upcoming),
        {},
        season=case.season,
        seed=case.seed,
        previous_path=DATA / case.previous,
        upcoming_path=DATA / case.upcoming,
        rules_path=case.rules,
        warn=no_warning,
    )
    assert league == CONFERENCES_LEAGUE


def test_committed_conference_league_files_match_the_builder() -> None:
    case = CASE_BY_LEAGUE["conferences"]
    committed = (
        (DATA / case.previous).read_bytes(),
        (DATA / case.upcoming).read_bytes(),
    )
    assert committed == conference_league_files(), (
        "run `python -m tests.integration.test_generate_schedule --bless`"
    )


# --- the goldens (slow) ---------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.league)
def test_generate_schedule_matches_golden(
    case: GoldenCase, tmp_path: Path, config_dir: Path, monkeypatch
) -> None:
    previous = _write_config(config_dir, case, tmp_path / "files")
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.chdir(output)

    txt, html, report = _generate(output, case, previous)
    _validate(case, tmp_path / "files", txt, html)

    # Regression + seed determinism: byte-identical to the frozen goldens.
    assert txt == case.golden_txt.read_text(encoding="utf-8"), "schedule .txt drifted"
    assert html == case.golden_html.read_text(encoding="utf-8"), (
        "schedule .html drifted"
    )
    assert report == case.golden_report.read_text(encoding="utf-8"), (
        "report .html drifted"
    )


def _bless() -> None:
    """Regenerate the built conference files and every golden set from a fresh
    solve (after validating rules)."""
    import os
    import tempfile

    write_conference_league_files()
    origin = Path.cwd()
    for case in CASES:
        with tempfile.TemporaryDirectory() as raw:
            try:
                workdir = Path(raw)
                config = workdir / "config"
                config.mkdir(parents=True)
                os.environ["ATHC_CONFIG_DIR"] = str(config)
                previous = _write_config(config, case, workdir / "files")
                output = workdir / "output"
                output.mkdir()
                os.chdir(output)

                txt, html, report = _generate(output, case, previous)
                _validate(case, workdir / "files", txt, html)  # valid before freezing

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
