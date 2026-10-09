"""Integration tests for `athc playpool check`.

The command loads the play pool the way convert-pdb does and prints the pool's
own warnings, word for word, as its findings.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli.playpool.check import check
from tests.conftest import (
    LEAGUE,
    OTHER_LEAGUE,
    league_not_found,
    league_toml,
    no_league_selected,
    toml_error,
)
from tests.integration.conftest import PLAYS

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

PLAY = "CC31rl5m"  # defensive Run Left


def run(runner, *args: Path | str) -> Result:
    return runner.invoke(check, [str(a) for a in args])


def copy_play(folder: Path, name: str = PLAY) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(next(PLAYS.glob(f"**/{name}.ply")), folder / f"{name}.ply")


def clean_tree(root: Path) -> Path:
    copy_play(root / "Defense" / "34RunLeft")
    return root


def league_with(make_league: MakeLeague, name: str, play_path: Path) -> Path:
    return make_league(name, f"[league]\nplay_path = '{play_path}'\n")


@pytest.fixture
def labeled_league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league with the PNFL category names and no play_path: a given
    play_dir still gets its folders named by the league."""
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return make_league(LEAGUE, league_toml())


# ── findings ──────────────────────────────────────────────────────────────────


def test_clean_exit_0(runner, tmp_path: Path) -> None:
    root = clean_tree(tmp_path / "plays")
    result = run(runner, root)
    assert result.exit_code == 0
    assert result.stdout == f"1 play(s) checked in '{root}', 0 issue(s)\n"


@pytest.mark.usefixtures("labeled_league")
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
    assert lines[2:] == ["", f"2 play(s) checked in '{root}', 2 issue(s)"]


def test_dir_with_unknown_league_option_exit_2(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    """A league the user names must exist, folder or not."""
    root = clean_tree(tmp_path / "plays")
    result = run(runner, root, "--league", "NOPE")
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE")


def test_dir_with_malformed_league_toml_exit_2(
    runner, tmp_path: Path, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    """A broken league file is reported even when a folder is given."""
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    folder = make_league(LEAGUE, "[league\nbroken")
    root = clean_tree(tmp_path / "plays")
    result = run(runner, root)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: {toml_error('[league' + chr(10) + 'broken')}\n"
    )


def test_dir_without_league_knows_no_category_folders(runner, tmp_path: Path) -> None:
    """No league configured: a given play_dir is still checked, but no folder
    name means a category, so a misfiled play is not a finding."""
    root = tmp_path / "plays"
    copy_play(root / "Defense" / "34RunMiddle")
    result = run(runner, root)
    assert result.exit_code == 0
    assert result.stdout == f"1 play(s) checked in '{root}', 0 issue(s)\n"


def test_invalid_file_is_an_issue(runner, tmp_path: Path) -> None:
    root = tmp_path / "plays"
    root.mkdir()
    (root / "bad.ply").write_bytes(b"\x00\x01\x02")
    result = run(runner, root)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith("Skipping invalid play file: ")
    assert lines[1:] == ["", f"0 play(s) checked in '{root}', 1 issue(s)"]


@pytest.mark.usefixtures("labeled_league")
def test_issues_are_results_not_warnings(runner, tmp_path: Path) -> None:
    """The issues are the findings: stdout only, never a WARN line too."""
    root = tmp_path / "plays"
    copy_play(root / "Defense" / "34RunMiddle")
    result = run(runner, root)
    assert result.exit_code == 1
    assert result.stderr == ""


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
    assert result.stdout == f"1 play(s) checked in '{root}', 0 issue(s)\n"


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
    assert result.stdout == f"1 play(s) checked in '{other_plays}', 0 issue(s)\n"


# ── errors: exit 2, on stderr ─────────────────────────────────────────────────


def test_no_league_exit_2(runner, config_dir: Path) -> None:
    result = run(runner)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == no_league_selected(config_dir)


def test_league_without_play_path_exit_2(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league()
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL no play_path for the league; set play_path in {folder / 'league.toml'}\n"
    )


def test_missing_play_dir_is_not_found_exit_2(runner, tmp_path: Path) -> None:
    missing = tmp_path / "nowhere"
    result = run(runner, missing)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == f"FAIL {missing}: not found\n"


def test_play_dir_not_a_directory_exit_2(runner, tmp_path: Path) -> None:
    a_file = tmp_path / "plays.txt"
    a_file.write_text("x", encoding="utf-8")
    result = run(runner, a_file)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == f"FAIL {a_file}: not a directory\n"


def test_read_error_exit_2(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(root: Path, *, labels: object) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr("athc.cli.playpool.check.read_play_pool", fail)
    result = run(runner, clean_tree(tmp_path / "plays"))
    assert result.exit_code == 2
    assert result.stderr == "FAIL access denied\n"
