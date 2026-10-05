"""Integration tests for `athc check-playpool`.

The command loads the play pool the way convert-pdb does and prints the pool's
own warnings, word for word, as its findings.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli.check_playpool import check_playpool
from tests.conftest import LEAGUE, OTHER_LEAGUE
from tests.integration.conftest import PLAYS

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

PLAY = "CC31rl5m"  # defensive Run Left


def run(runner, *args: Path | str) -> Result:
    return runner.invoke(check_playpool, [str(a) for a in args])


def copy_play(folder: Path, name: str = PLAY) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(next(PLAYS.glob(f"**/{name}.ply")), folder / f"{name}.ply")


def clean_tree(root: Path) -> Path:
    copy_play(root / "Defense" / "34RunLeft")
    return root


def league_with(make_league: MakeLeague, name: str, play_path: Path) -> Path:
    return make_league(name, f"[league]\nplay_path = {play_path}\n")


# ── findings ──────────────────────────────────────────────────────────────────


def test_clean_exit_0(runner, tmp_path: Path) -> None:
    root = clean_tree(tmp_path / "plays")
    result = run(runner, root)
    assert result.exit_code == 0
    assert result.stdout == f"1 play(s) checked in '{root}', 0 issue(s).\n"


def test_issues_print_word_for_word_exit_1(runner, tmp_path: Path) -> None:
    root = tmp_path / "plays"
    copy_play(root / "Defense" / "34RunMiddle")
    copy_play(root / "loose")
    result = run(runner, root)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert sorted(lines[:2]) == [
        f"Duplicate play name '{PLAY}'; last loaded wins",
        f"Run Left play in a Run Middle folder: Defense/34RunMiddle/{PLAY}.ply",
    ]
    assert lines[2:] == ["", f"2 play(s) checked in '{root}', 2 issue(s)."]


def test_invalid_file_is_an_issue(runner, tmp_path: Path) -> None:
    root = tmp_path / "plays"
    root.mkdir()
    (root / "bad.ply").write_bytes(b"\x00\x01\x02")
    result = run(runner, root)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith("Skipping invalid play file: ")
    assert lines[1:] == ["", f"0 play(s) checked in '{root}', 1 issue(s)."]


def test_issues_not_logged_twice(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "plays"
    copy_play(root / "Defense" / "34RunMiddle")
    pool_logger = logging.getLogger("athc.playpool")
    level = pool_logger.level
    with caplog.at_level(logging.INFO):
        result = run(runner, root)
    assert result.exit_code == 1
    assert caplog.records == []
    assert pool_logger.level == level  # restored for whatever runs next


# ── where the folder comes from ───────────────────────────────────────────────


def test_play_dir_needs_no_league(runner, tmp_path: Path) -> None:
    """No athc.ini and no leagues: a given play_dir still runs."""
    assert run(runner, clean_tree(tmp_path / "plays")).exit_code == 0


def test_default_is_current_league_play_path(
    runner, tmp_path: Path, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    root = clean_tree(tmp_path / "plays")
    league_with(make_league, LEAGUE, root)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner)
    assert result.exit_code == 0
    assert f"in '{root}'" in result.stdout


def test_league_option_picks_another_league(
    runner, tmp_path: Path, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    league_plays = clean_tree(tmp_path / "league_plays")
    other_plays = clean_tree(tmp_path / "other_plays")
    league_with(make_league, LEAGUE, league_plays)
    league_with(make_league, OTHER_LEAGUE, other_plays)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner, "--league", OTHER_LEAGUE)
    assert result.exit_code == 0
    assert f"in '{other_plays}'" in result.stdout


# ── errors: exit 2, on stderr ─────────────────────────────────────────────────


def test_no_league_exit_2(runner, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = run(runner)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "athc check-playpool: no league selected" in caplog.text


def test_league_without_play_path_exit_2(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    folder = make_league()
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    with caplog.at_level(logging.ERROR):
        result = run(runner)
    assert result.exit_code == 2
    assert (
        "athc check-playpool: no play_path for the league; "
        f"set play_path in {folder / 'league.ini'}"
    ) in caplog.text


def test_play_dir_not_a_directory_exit_2(
    runner, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "nowhere"
    with caplog.at_level(logging.ERROR):
        result = run(runner, missing)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert (
        f"athc check-playpool: play path '{missing}' is not a directory" in caplog.text
    )


def test_read_error_exit_2(
    runner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(root: Path, *, rules: object) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr("athc.cli.gameplan._common.read_play_pool", fail)
    with caplog.at_level(logging.ERROR):
        result = run(runner, clean_tree(tmp_path / "plays"))
    assert result.exit_code == 2
    assert "athc check-playpool: access denied" in caplog.text
