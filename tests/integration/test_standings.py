"""Integration tests for `athc standings`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.standings import standings
from athc.errors import FILE_NOT_FOUND
from athc.fbpro98_lge import LgeFile, parse_lge
from athc.fbpro98_standings import Method, Standings
from tests.conftest import LEAGUE, OTHER_LEAGUE, athc_toml, no_league_selected
from tests.integration.conftest import EXPECTED

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

LGE_DATA = Path(__file__).resolve().parents[1] / "unit" / "fbpro98_lge" / "data"
MID_SEASON = LGE_DATA / "PNFL-2048-after-week16.lge"
BEFORE_WEEK_ONE = LGE_DATA / "PNFL-before-week1.lge"


def _install(make_league: MakeLeague, tmp_path: Path, name: str, source: Path) -> Path:
    """A league folder whose `path` holds `source` as `<name>.lge`."""
    files = tmp_path / f"{name}-files"
    files.mkdir()
    shutil.copy(source, files / f"{name}.lge")
    make_league(name, f"[league]\npath = '{files}'\n")
    return files


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig, tmp_path: Path) -> Path:
    """The selected league, its `.lge` the mid-season PNFL file."""
    write_config(athc_toml())
    return _install(make_league, tmp_path, LEAGUE, MID_SEASON)


def _lge(path: Path = MID_SEASON) -> LgeFile:
    return parse_lge(path.read_bytes(), path)


def _expected(view: str) -> list[str]:
    return (EXPECTED / f"standings_{view}.txt").read_text(encoding="utf-8").splitlines()


def _espn_rows(lines: list[str]) -> list[list[str]]:
    """The cells of each team row of an ESPN view: the lines whose last cell
    is a streak (`W3`, `L2`, `-`)."""
    rows: list[list[str]] = []
    for line in lines:
        cells = line.split()
        if cells and (cells[-1] == "-" or cells[-1][0] in "WL"):
            rows.append(cells)
    return rows


@pytest.mark.parametrize("view", ["game", "league", "conference", "division"])
def test_view_matches_golden(runner, view: str) -> None:
    result = runner.invoke(standings, ["--view", view])
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == _expected(view)


def test_defaults_are_the_game_view_by_the_scheduler(runner) -> None:
    default = runner.invoke(standings, [])
    chosen = runner.invoke(standings, ["--view", "game", "--method", "scheduler"])
    assert default.exit_code == 0
    assert default.stdout == chosen.stdout


def test_records_match_the_file(runner) -> None:
    """W, L, T, PF and PA of every team equal the file's own records."""
    result = runner.invoke(standings, ["--view", "league"])
    records = {team.official_name: team.record for team in _lge().teams}
    rows = _espn_rows(result.stdout.splitlines())
    assert len(rows) == len(records)
    for cells in rows:
        name = " ".join(cells[1:-12])
        record = records[name]
        wins, losses, ties = cells[-12:-9]
        points_for, points_against = cells[-4:-2]
        assert (wins, losses, ties, points_for, points_against) == (
            str(record.wins),
            str(record.losses),
            str(record.ties),
            str(record.points_for),
            str(record.points_against),
        ), name


def test_league_view_numbers_every_team(runner) -> None:
    result = runner.invoke(standings, ["--view", "league"])
    numbers = [cells[0] for cells in _espn_rows(result.stdout.splitlines())]
    assert numbers == [str(number) for number in range(1, len(_lge().teams) + 1)]


def test_conference_view_numbers_each_conference(runner) -> None:
    result = runner.invoke(standings, ["--view", "conference"])
    numbers = [cells[0] for cells in _espn_rows(result.stdout.splitlines())]
    expected = [
        str(number)
        for conference in _lge().conferences
        for number in range(
            1, sum(len(division.teams) for division in conference.divisions) + 1
        )
    ]
    assert numbers == expected


@pytest.mark.parametrize("method", ["scheduler", "game", "nfl"])
def test_method_orders_the_league_view(runner, method: Method) -> None:
    result = runner.invoke(standings, ["--view", "league", "--method", method])
    assert result.exit_code == 0
    names = [" ".join(cells[1:-12]) for cells in _espn_rows(result.stdout.splitlines())]
    ranked = Standings(_lge(), method=method, seed=0)
    assert names == [team.official_name for team in ranked.league()]


def test_before_week_one_shows_every_team_at_zero(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    result = runner.invoke(standings, ["--view", "league", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    rows = _espn_rows(result.stdout.splitlines())
    assert len(rows) == len(_lge(BEFORE_WEEK_ONE).teams)
    for cells in rows:
        assert cells[-12:] == [
            "0", "0", "0", ".000", "0-0", "0-0", "0-0", "0-0", "0", "0", "0", "-",
        ]  # fmt: skip


def test_same_file_same_order(runner, make_league: MakeLeague, tmp_path: Path) -> None:
    """Before week 1 every team is level, so the coin decides every place."""
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    args = ["--view", "league", "--league", OTHER_LEAGUE]
    first = runner.invoke(standings, args).stdout
    assert all(runner.invoke(standings, args).stdout == first for _ in range(4))


def test_league_option_picks_the_league(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    result = runner.invoke(standings, ["--view", "league", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0] == OTHER_LEAGUE


def test_no_league_selected(
    runner, config_dir: Path, write_config: WriteConfig
) -> None:
    write_config("[athc]\n")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


def test_no_path(runner, config_dir: Path) -> None:
    folder = config_dir / "leagues" / LEAGUE
    (folder / "league.toml").write_text("[league]\n", encoding="utf-8")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: League files folder is not set. "
        "Run 'athc config set path FOLDER'.\n"
    )
    assert result.stdout == ""


def test_missing_lge(runner, league: Path) -> None:
    (league / f"{LEAGUE}.lge").unlink()
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league / f'{LEAGUE}.lge'}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_broken_lge(runner, league: Path) -> None:
    (league / f"{LEAGUE}.lge").write_bytes(b"")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league / f'{LEAGUE}.lge'}: Empty file.\n"
    assert result.stdout == ""


@pytest.mark.parametrize("option", ["--view", "--method"])
def test_bad_choice_is_a_usage_error(runner, option: str) -> None:
    result = runner.invoke(standings, [option, "bogus"])
    assert result.exit_code == 2
    assert f"Invalid value for '{option}'" in result.stderr
    assert result.stdout == ""
