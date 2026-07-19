"""Integration tests for `athc gameplan set-normals`."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from athc.cli.gameplan.set_normals import set_normals
from athc.fbpro98_gameplan import PlayRef, read_gameplan
from tests.integration.conftest import GP_OFFENSE, PLAYS, POOL_RULES

POOL_FLAGS = ["--play-path", str(PLAYS), "--playpool-rules", str(POOL_RULES)]
NORMAL = "OR45RL01"  # a real normal offense play in the pool
SPECIAL = "SFFGXPAT"  # a real special-teams offense play in the pool


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


def test_requires_input_or_stdin(runner, tmp_path: Path) -> None:
    assert (
        runner.invoke(set_normals, [str(_copy(tmp_path)), *POOL_FLAGS]).exit_code == 2
    )


def test_rejects_input_and_stdin_together(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(
        set_normals, [str(p), str(inp), "--stdin", *POOL_FLAGS], input=NORMAL + "\n"
    )
    assert result.exit_code == 2


# ── file input ────────────────────────────────────────────────────────────────


def test_writes_from_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert rt.normal_plays[0] is not None and rt.normal_plays[0].name == NORMAL
    assert all(x is None for x in rt.normal_plays[1:])


def test_creates_backup_by_default(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    backups = list(tmp_path.glob("offense.pln.*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original


def test_no_backup_skips_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals,
        [str(p), str(_input(tmp_path, NORMAL + "\n")), "--no-backup", *POOL_FLAGS],
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []


def test_logs_backup_path(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert "Updated" in result.output and "Backup:" in result.output


# ── comment parsing ───────────────────────────────────────────────────────────


def test_skips_comment_lines(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n{NORMAL}\n:: another\n")
    assert runner.invoke(set_normals, [str(p), str(inp), *POOL_FLAGS]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_strips_inline_comments(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL} :: my favorite play\n")
    assert runner.invoke(set_normals, [str(p), str(inp), *POOL_FLAGS]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_inline_comment_requires_space(runner, tmp_path: Path) -> None:
    """`name::comment` (no space) is not split, so the whole token fails to resolve."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL}::comment\n")
    assert runner.invoke(set_normals, [str(p), str(inp), *POOL_FLAGS]).exit_code == 1


# ── quiet / stdin ─────────────────────────────────────────────────────────────


def test_quiet_still_updates(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), "-q", *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert result.output == ""  # -q suppresses the success line
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_reads_from_stdin(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), "--stdin", *POOL_FLAGS], input=NORMAL + "\n"
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


# ── validation / errors (target left untouched) ───────────────────────────────


def test_rejects_special_teams_play(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_normals"):
        result = runner.invoke(
            set_normals, [str(p), str(_input(tmp_path, SPECIAL + "\n")), *POOL_FLAGS]
        )
    assert result.exit_code == 1
    assert "special teams play" in caplog.text and "set-specials" in caplog.text
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_missing_play_aborts(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    with caplog.at_level(logging.ERROR, logger="athc.gameplan.writer"):
        result = runner.invoke(
            set_normals, [str(p), str(_input(tmp_path, "NOTAREALPLAY\n")), *POOL_FLAGS]
        )
    assert result.exit_code == 1
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_too_many_plays_rejected(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_normals"):
        result = runner.invoke(
            set_normals,
            [str(p), str(_input(tmp_path, (NORMAL + "\n") * 65)), *POOL_FLAGS],
        )
    assert result.exit_code == 1
    assert "max is 64" in caplog.text


def test_missing_pln(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(
        set_normals, [str(tmp_path / "nope.pln"), str(inp), *POOL_FLAGS]
    )
    assert result.exit_code == 1


def test_invalid_play_path(runner, tmp_path: Path, caplog) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.set_normals"):
        result = runner.invoke(
            set_normals,
            [
                str(p),
                str(inp),
                "--play-path",
                str(tmp_path / "missing"),
                "--playpool-rules",
                str(POOL_RULES),
            ],
        )
    assert result.exit_code == 1
    assert "not a directory" in caplog.text
