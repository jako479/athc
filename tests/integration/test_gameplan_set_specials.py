"""Integration tests for `athc gameplan set-specials`."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from athc.cli.gameplan.set_specials import set_specials
from athc.fbpro98_gameplan import Play, read_gameplan
from tests.integration.conftest import GP_DEFENSE, GP_OFFENSE, PLAYS, POOL_RULES

POOL_FLAGS = ["--play-path", str(PLAYS), "--playpool-rules", str(POOL_RULES)]
SPECIAL = "LIONKICK"  # offense Kickoff, special_category 2 -> custom slot index 1
NORMAL = "OR45RL01"  # a normal offense play (not special teams)


def _name(play: Play | None) -> str:
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


# ── usage ─────────────────────────────────────────────────────────────────────


def test_requires_target(runner) -> None:
    assert runner.invoke(set_specials, []).exit_code == 2


def test_requires_input_or_stdin(runner, tmp_path: Path) -> None:
    assert (
        runner.invoke(set_specials, [str(_copy(tmp_path)), *POOL_FLAGS]).exit_code == 2
    )


def test_rejects_input_and_stdin_together(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials,
        [str(p), str(_input(tmp_path, SPECIAL + "\n")), "--stdin", *POOL_FLAGS],
    )
    assert result.exit_code == 2


def test_no_quiet_option(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n")), "-q", *POOL_FLAGS]
    )
    assert result.exit_code == 2


# ── single file ───────────────────────────────────────────────────────────────


def test_writes_special_from_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    placed = read_gameplan(str(p)).custom_special_plays[1]
    assert placed is not None and placed.name == SPECIAL


def test_merge_preserves_other_categories(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    before = read_gameplan(str(p)).custom_special_plays
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS]
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


def test_creates_backup_by_default(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        set_specials, [str(p), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    backups = list(tmp_path.glob("offense.pln.*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original


def test_no_backup_skips_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials,
        [str(p), str(_input(tmp_path, SPECIAL + "\n")), "--no-backup", *POOL_FLAGS],
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []


def test_skips_and_strips_comments(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n{SPECIAL} :: kickoff\n")
    result = runner.invoke(set_specials, [str(p), str(inp), *POOL_FLAGS])
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


def test_reads_from_stdin(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, [str(p), "--stdin", *POOL_FLAGS], input=SPECIAL + "\n"
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


# ── validation (no file written) ──────────────────────────────────────────────


def test_rejects_normal_play(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_specials"):
        result = runner.invoke(
            set_specials, [str(p), str(_input(tmp_path, NORMAL + "\n")), *POOL_FLAGS]
        )
    assert result.exit_code == 2
    assert "not a special teams play" in caplog.text and "set-normals" in caplog.text
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_rejects_duplicate_play(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_specials"):
        result = runner.invoke(
            set_specials,
            [str(p), str(_input(tmp_path, f"{SPECIAL}\n{SPECIAL}\n")), *POOL_FLAGS],
        )
    assert result.exit_code == 2
    assert "duplicate" in caplog.text.lower()


def test_too_many_plays_rejected(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_specials"):
        result = runner.invoke(
            set_specials,
            [str(p), str(_input(tmp_path, (SPECIAL + "\n") * 11)), *POOL_FLAGS],
        )
    assert result.exit_code == 2
    assert "max is 10" in caplog.text


def test_missing_target(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(
        set_specials, [str(tmp_path / "nope.pln"), str(inp), *POOL_FLAGS]
    )
    assert result.exit_code == 2


# ── bulk: directory / tree / side-skip / per-file failure ─────────────────────


def test_directory_top_level_only(runner, tmp_path: Path) -> None:
    _copy(tmp_path, "a.pln")
    _copy(tmp_path, "b.pln")
    sub = tmp_path / "sub"
    sub.mkdir()
    deep = _copy(sub, "deep.pln")
    deep_pre = deep.read_bytes()
    result = runner.invoke(
        set_specials,
        [str(tmp_path), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS],
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.output and "2 updated" in result.output
    assert deep.read_bytes() == deep_pre


def test_directory_recursive(runner, tmp_path: Path) -> None:
    _copy(tmp_path, "top.pln")
    sub = tmp_path / "sub"
    sub.mkdir()
    _copy(sub, "deep.pln")
    result = runner.invoke(
        set_specials,
        [str(tmp_path), str(_input(tmp_path, SPECIAL + "\n")), "-r", *POOL_FLAGS],
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.output


def test_offense_input_skips_defense_files(runner, tmp_path: Path) -> None:
    _copy(tmp_path, "off.pln")
    deff = _copy(tmp_path, "def.pln", src=GP_DEFENSE)
    def_pre = deff.read_bytes()
    result = runner.invoke(
        set_specials,
        [str(tmp_path), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS],
    )
    assert result.exit_code == 0
    assert "1 file(s) processed" in result.output and "1 updated" in result.output
    assert deff.read_bytes() == def_pre


def test_continues_past_failed_file(runner, tmp_path: Path) -> None:
    good = _copy(tmp_path, "good.pln")
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00" * 2636)  # even size so it isn't side-skipped, but malformed
    result = runner.invoke(
        set_specials,
        [str(tmp_path), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS],
    )
    assert result.exit_code == 1
    assert f"{good}: updated" in result.output and f"{bad}: failed" in result.output
    assert "1 updated" in result.output and "1 failed" in result.output
