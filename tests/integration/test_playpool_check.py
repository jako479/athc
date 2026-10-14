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

from athc.cli import cli
from athc.cli.playpool.check import check
from athc.errors import DIRECTORY_INVALID, PATH_NOT_FOUND
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
    assert result.stdout == f"{root}: 1 play(s) checked, 0 issue(s)\n"


@pytest.mark.usefixtures("labeled_league")
def test_issues_print_word_for_word_exit_1(runner, tmp_path: Path) -> None:
    root = tmp_path / "plays"
    copy_play(root / "Defense" / "34RunMiddle")
    copy_play(root / "loose")
    result = run(runner, root)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert sorted(lines[:2]) == [
        f"Defense/34RunMiddle/{PLAY}.ply: Run Left play in a Run Middle folder.",
        f"Duplicate play name '{PLAY}'. The last one loaded wins.",
    ]
    assert lines[2:] == ["", f"{root}: 2 play(s) checked, 2 issue(s)"]


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
    assert result.stdout == f"{root}: 1 play(s) checked, 0 issue(s)\n"


def test_invalid_file_is_an_issue(runner, tmp_path: Path) -> None:
    root = tmp_path / "plays"
    root.mkdir()
    (root / "bad.ply").write_bytes(b"\x00\x01\x02")
    result = run(runner, root)
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith(f"{root / 'bad.ply'}: ")
    assert lines[0].endswith(" Skipped.")
    assert lines[1:] == ["", f"{root}: 0 play(s) checked, 1 issue(s)"]


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
    assert result.stdout == f"{root}: 1 play(s) checked, 0 issue(s)\n"


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
    assert result.stdout == f"{other_plays}: 1 play(s) checked, 0 issue(s)\n"


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
        f"FAIL {folder / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER' or pass the folder.\n"
    )


@pytest.mark.parametrize(
    ("is_file", "reason"),
    [(False, PATH_NOT_FOUND), (True, DIRECTORY_INVALID)],
    ids=["missing", "a file"],
)
def test_league_play_path_not_a_folder_gets_the_hint(
    runner,
    tmp_path: Path,
    make_league: MakeLeague,
    write_config: WriteConfig,
    is_file: bool,
    reason: str,
) -> None:
    """No FOLDER: the league's play_path that is not a folder is play_dir()'s
    line, with the hint every other pool consumer gives."""
    play_path = tmp_path / "plays"
    if is_file:
        play_path.write_text("x", encoding="utf-8")
    league_with(make_league, LEAGUE, play_path)
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    result = run(runner)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == (
        f"FAIL {play_path}: {reason} Run 'athc config set play_path FOLDER'.\n"
    )


@pytest.mark.parametrize(
    "play_path",
    ["'{missing}'", "['{missing}']"],
    ids=["missing on disk", "an array"],
)
def test_folder_run_never_reads_play_path(
    runner,
    tmp_path: Path,
    make_league: MakeLeague,
    write_config: WriteConfig,
    play_path: str,
) -> None:
    """A given FOLDER is checked alone: the league's play_path, however broken,
    is never read."""
    missing = tmp_path / "gone"
    make_league(LEAGUE, f"[league]\nplay_path = {play_path.format(missing=missing)}\n")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    root = clean_tree(tmp_path / "plays")
    result = run(runner, root)
    assert result.exit_code == 0
    assert "FAIL" not in result.stderr
    assert result.stdout == f"{root}: 1 play(s) checked, 0 issue(s)\n"


def test_two_folders_are_a_usage_error(runner, tmp_path: Path) -> None:
    """One FOLDER at most: a second is Click's usage error, with athc's period,
    and nothing is checked."""
    first = clean_tree(tmp_path / "one")
    second = clean_tree(tmp_path / "two")
    result = run(runner, first, second)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.endswith(f"Error: Got unexpected extra argument ({second}).\n")


def test_wildcard_folder_is_not_expanded(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FOLDER takes no wildcards: `plays*` is a folder that does not exist, even
    beside a `plays` folder."""
    clean_tree(tmp_path / "plays")
    monkeypatch.chdir(tmp_path)
    result = run(runner, "plays*")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == f"FAIL plays*: {PATH_NOT_FOUND}\n"


def test_missing_play_dir_is_not_found_exit_2(runner, tmp_path: Path) -> None:
    missing = tmp_path / "nowhere"
    result = run(runner, missing)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == f"FAIL {missing}: {PATH_NOT_FOUND}\n"


def test_play_dir_not_a_directory_exit_2(runner, tmp_path: Path) -> None:
    a_file = tmp_path / "plays.txt"
    a_file.write_text("x", encoding="utf-8")
    result = run(runner, a_file)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == f"FAIL {a_file}: {DIRECTORY_INVALID}\n"


def test_read_error_exit_2(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(root: Path, *, labels: object) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr("athc.cli.playpool.check.read_play_pool", fail)
    result = run(runner, clean_tree(tmp_path / "plays"))
    assert result.exit_code == 2
    assert result.stderr == "FAIL Access is denied.\n"


# ── help ──────────────────────────────────────────────────────────────────────

CONSOLE_WIDTH = 78  # Click's help width in an 80-column console

GROUP_HELP = """\
Usage: athc playpool [OPTIONS] COMMAND [ARGS]...

  Check the play pool (.ply).

Options:
  -h, --help  Show this message and exit.

Commands:
  check  Check the play pool for problems.
"""

CHECK_HELP = """\
Usage: athc playpool check [OPTIONS] [FOLDER]

  Check the play pool for problems.

  Finds plays in the wrong folder, duplicate names and invalid play files.

Positional arguments:
  FOLDER  Play pool folder (default: the league's play_path).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc playpool check
    athc playpool check newplays
"""


@pytest.mark.parametrize(
    ("args", "screen"),
    [(["playpool"], GROUP_HELP), (["playpool", "check"], CHECK_HELP)],
    ids=["playpool", "playpool check"],
)
def test_help_screen(runner, args: list[str], screen: str) -> None:
    """The help as an 80-column console shows it: Click wraps it 78 wide there,
    where CliRunner would force 80."""
    result = runner.invoke(
        cli, [*args, "--help"], prog_name="athc", terminal_width=CONSOLE_WIDTH
    )
    assert result.exit_code == 0
    assert result.stdout == screen
