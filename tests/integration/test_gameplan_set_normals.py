"""Integration tests for `athc gameplan set-normals`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.set_normals import set_normals
from athc.fbpro98_gameplan import CustomPlayRef, PlayRef, read_gameplan
from tests.conftest import LEAGUE, league_toml
from tests.integration.conftest import GP_OFFENSE, PLAYS, POOL_RULES

NORMAL = "OR45RL01"  # a real normal offense play in the pool
SPECIAL = "SFFGXPAT"  # a real special-teams offense play in the pool
MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the curated test pool and its playpool rules."""
    folder = make_league(LEAGUE, league_toml(PLAYS))
    shutil.copy(POOL_RULES, folder / "playpool.toml")
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


def _name(play: PlayRef | None) -> str:
    assert play is not None
    return play.name


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "offense.pln"
    shutil.copy2(GP_OFFENSE, dst)
    return dst


def _input(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "plays.txt"
    p.write_text(text, encoding="utf-8")
    return p


# ── usage ─────────────────────────────────────────────────────────────────────


def test_requires_gameplan(runner) -> None:
    assert runner.invoke(set_normals, []).exit_code == 2


def test_requires_input_file(runner, tmp_path: Path) -> None:
    assert runner.invoke(set_normals, [str(_copy(tmp_path))]).exit_code == 2


@pytest.mark.parametrize(
    "extra",
    [
        ["--stdin"],
        ["--no-backup"],
        ["--play-path", "plays"],
        ["--playpool-rules", "rules.toml"],
    ],
)
def test_removed_options_rejected(runner, tmp_path: Path, extra: list[str]) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp), *extra])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── file input ────────────────────────────────────────────────────────────────


def test_writes_from_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert rt.normal_plays[0] is not None and rt.normal_plays[0].name == NORMAL
    assert all(x is None for x in rt.normal_plays[1:])


def test_slot_path_starts_with_play_pool_folder(runner, tmp_path: Path) -> None:
    """A slot's path starts with the play pool's folder name, not a fixed league."""
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    play = read_gameplan(str(p)).normal_plays[0]
    assert isinstance(play, CustomPlayRef)
    assert play.filename == f"{PLAYS.name}\\Offense\\RL\\{NORMAL}.ply"


def test_writes_no_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: 1 normal play(s)\n"
    assert list(tmp_path.glob("*.bak")) == []


# ── comment parsing ───────────────────────────────────────────────────────────


def test_skips_comment_lines(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n{NORMAL}\n:: another\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_strips_inline_comments(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL} :: my favorite play\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_inline_comment_requires_space(runner, tmp_path: Path) -> None:
    """`name::comment` (no space) is not split, so the whole token fails to resolve."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL}::comment\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 2


# ── quiet / console input ─────────────────────────────────────────────────────


def test_quiet_still_updates(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), "-q"]
    )
    assert result.exit_code == 0
    assert result.stdout == ""  # -q suppresses the success line
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_dash_reads_from_console(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input=NORMAL + "\n")
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_dash_input_errors_name_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input="NOTAREALPLAY\n")
    assert result.exit_code == 2
    assert (
        "FAIL line 1: 'NOTAREALPLAY' not found in the play pool (slot 1-1)\n"
        in result.stderr
    )
    assert "FAIL - " not in result.stderr


# ── validation / errors (target left untouched) ───────────────────────────────


def test_rejects_special_teams_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp} line 1: '{SPECIAL}' is a special teams play; use set-specials"
        in result.stderr
    )
    assert p.read_bytes() == original


def test_missing_play_aborts(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, "NOTAREALPLAY\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp} line 1: 'NOTAREALPLAY' not found in the play pool (slot 1-1)"
        in result.stderr
    )
    assert p.read_bytes() == original


def test_too_many_plays_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, (NORMAL + "\n") * 65))]
    )
    assert result.exit_code == 2
    assert result.stderr == "FAIL input has 65 play(s), max is 64\n"


def test_missing_pln(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(tmp_path / "nope.pln"), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.pln'}: not found\n"


def test_missing_input_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(tmp_path / "nope.txt")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.txt'}: not found\n"


def test_invalid_play_path(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "missing"), encoding="utf-8"
    )
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'missing'}: play path is not a directory\n"
    )
