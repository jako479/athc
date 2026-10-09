"""Integration tests for `athc gameplan set-specials`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.set_specials import set_specials
from athc.fbpro98_gameplan import PlayRef, read_gameplan
from tests.conftest import LEAGUE, league_toml
from tests.integration.conftest import GP_DEFENSE, GP_OFFENSE, PLAYS, POOL_RULES

SPECIAL = "LIONKICK"  # offense Kickoff, special_category 2 -> custom slot index 1
NORMAL = "OR45RL01"  # a normal offense play (not special teams)
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


def _copy(tmp_path: Path, name: str = "offense.pln", src: Path = GP_OFFENSE) -> Path:
    dst = tmp_path / name
    shutil.copy2(src, dst)
    return dst


def _input(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.txt"
    p.write_text(text, encoding="utf-8")
    return p


def _plans(tmp_path: Path) -> Path:
    """A folder for bulk runs, apart from the input file and the config dir."""
    folder = tmp_path / "plans"
    folder.mkdir()
    return folder


# ── usage ─────────────────────────────────────────────────────────────────────


def test_requires_path(runner) -> None:
    assert runner.invoke(set_specials, []).exit_code == 2


def test_requires_input_file(runner, tmp_path: Path) -> None:
    assert runner.invoke(set_specials, [str(_copy(tmp_path))]).exit_code == 2


def test_no_quiet_option(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n")), "-q"]
    )
    assert result.exit_code == 2


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
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_specials, [str(p), str(inp), *extra])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── single file ───────────────────────────────────────────────────────────────


def test_writes_special_from_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    placed = read_gameplan(str(p)).custom_special_plays[1]
    assert placed is not None and placed.name == SPECIAL


def test_merge_preserves_other_categories(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    before = read_gameplan(str(p)).custom_special_plays
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    after = read_gameplan(str(p)).custom_special_plays
    assert after[1] is not None and after[1].name == SPECIAL
    for i in range(len(after)):
        if i == 1:
            continue
        assert (after[i] is None) == (before[i] is None)
        if before[i] is not None:
            assert _name(after[i]) == _name(before[i])


def test_writes_no_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []
    assert "; backup " not in result.stdout  # the old "(N special play(s); backup X)"


def test_skips_and_strips_comments(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n{SPECIAL} :: kickoff\n")
    result = runner.invoke(set_specials, [str(p), str(inp)])
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


def test_dash_reads_from_console(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_specials, [str(p), "-"], input=SPECIAL + "\n")
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


def test_dash_input_errors_name_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_specials, [str(p), "-"], input=NORMAL + "\n")
    assert result.exit_code == 2
    assert (
        f"FAIL line 1: '{NORMAL}' is not a special teams play; use set-normals\n"
        in result.stderr
    )
    assert "FAIL - " not in result.stderr


# ── validation (no file written) ──────────────────────────────────────────────


def test_rejects_normal_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(set_specials, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1].startswith("FAIL ")  # after the WARN lines
    assert (
        "not a special teams play" in result.stderr and "set-normals" in result.stderr
    )
    assert p.read_bytes() == original


def test_rejects_duplicate_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, f"{SPECIAL}\n{SPECIAL}\n"))]
    )
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1].startswith("FAIL ")  # after the WARN lines
    assert "duplicate" in result.stderr.lower()


def test_too_many_plays_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, (SPECIAL + "\n") * 11))]
    )
    assert result.exit_code == 2
    assert result.stderr == "FAIL input has 11 play(s), max is 10\n"


def test_missing_target(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_specials, [str(tmp_path / "nope.pln"), str(inp)])
    assert result.exit_code == 2


def test_missing_input_file(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    result = runner.invoke(set_specials, [str(plans), str(tmp_path / "nope.txt")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.txt'}: not found\n"


def test_invalid_play_path(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "missing"), encoding="utf-8"
    )
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'missing'}: play path is not a directory\n"
    )


# ── bulk: directory / tree / side-skip / per-file failure ─────────────────────


def test_directory_top_level_only(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "a.pln")
    _copy(plans, "b.pln")
    sub = plans / "sub"
    sub.mkdir()
    deep = _copy(sub, "deep.pln")
    deep_pre = deep.read_bytes()
    result = runner.invoke(
        set_specials, [str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.stdout and "2 updated" in result.stdout
    assert deep.read_bytes() == deep_pre


def test_directory_recursive(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "top.pln")
    sub = plans / "sub"
    sub.mkdir()
    _copy(sub, "deep.pln")
    result = runner.invoke(
        set_specials, [str(plans), str(_input(tmp_path, SPECIAL + "\n")), "-r"]
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.stdout


def test_offense_input_skips_defense_files(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "off.pln")
    deff = _copy(plans, "def.pln", src=GP_DEFENSE)
    def_pre = deff.read_bytes()
    result = runner.invoke(
        set_specials, [str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert f"SKIP {deff}: defense gameplan" in result.stdout
    assert "2 file(s) processed, 1 updated, 1 skipped, 0 failed" in result.stdout
    assert deff.read_bytes() == def_pre


def test_continues_past_failed_file(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    good = _copy(plans, "good.pln")
    bad = plans / "bad.pln"
    bad.write_bytes(b"\x00" * 2636)  # even size so it isn't side-skipped, but malformed
    result = runner.invoke(
        set_specials, [str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 2
    assert f"OK   {good}: updated" in result.stdout
    assert f"FAIL {bad}: Invalid header" in result.stderr
    assert result.stderr.count(str(bad)) == 1
    assert "2 file(s) processed, 1 updated, 0 skipped, 1 failed" in result.stdout
