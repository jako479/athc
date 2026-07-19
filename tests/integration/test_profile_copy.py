"""Integration tests for `athc profile copy`."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from athc.cli.profile.copy import copy
from athc.fbpro98_profile import (
    FieldPosition,
    SubstitutionPair,
    SubstitutionSettings,
    read_profile,
    write_profile,
)
from tests.integration.conftest import DEF1, OFF1

_GOAL_LINE = frozenset({FieldPosition.INSIDE_DEF_5, FieldPosition.INSIDE_OFF_5})


def _copy_prf(src: Path, dest_dir: Path, *, name: str) -> Path:
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return dest


def _mutated_source(src: Path, tmp_path: Path, *, flip: tuple[int, ...]) -> Path:
    profile = read_profile(str(src))
    sits = list(profile.situations)
    for n in flip:
        sits[n - 1] = replace(sits[n - 1], stop_clock=not sits[n - 1].stop_clock)
    dest = tmp_path / "source.prf"
    write_profile(replace(profile, situations=tuple(sits)), str(dest))
    return dest


def _custom_subs() -> SubstitutionSettings:
    return SubstitutionSettings(
        offensive_linemen=SubstitutionPair(10, 20),
        quarterbacks=SubstitutionPair(75, 80),
        running_backs=SubstitutionPair(30, 40),
        receivers=SubstitutionPair(35, 45),
        defensive_linemen=SubstitutionPair(50, 60),
        linebackers=SubstitutionPair(55, 65),
        defensive_backs=SubstitutionPair(60, 70),
        kickers=SubstitutionPair(65, 75),
    )


def _bumped(cw):
    return replace(cw, weight1=(cw.weight1 + 1) % 11)


def _stop_clock(path: Path) -> tuple[bool, ...]:
    return tuple(s.stop_clock for s in read_profile(str(path)).situations)


# ── usage / argument validation ───────────────────────────────────────────────


@pytest.mark.parametrize("args", [[], [str(OFF1)], [str(OFF1), "t.prf"]])
def test_cli_usage_errors_exit_2(runner, args: list[str]) -> None:
    # missing SRC / missing TARGET / no copy flag are all usage errors.
    assert runner.invoke(copy, args).exit_code == 2


# ── single-file flows ─────────────────────────────────────────────────────────


def test_cli_copies_stop_clock_offense(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1, 100, 2520))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert _stop_clock(target) == _stop_clock(source)


def test_cli_copies_stop_clock_defense(runner, tmp_path: Path) -> None:
    source = _mutated_source(DEF1, tmp_path, flip=(50, 1500))
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(copy, [str(source), str(target), "--stop-clock"]).exit_code == 0
    )
    assert _stop_clock(target) == _stop_clock(source)


def test_cli_copies_sub_percent(runner, tmp_path: Path) -> None:
    source = tmp_path / "source.prf"
    write_profile(
        replace(read_profile(str(OFF1)), substitutions=_custom_subs()), str(source)
    )
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(copy, [str(source), str(target), "--sub-percent"]).exit_code == 0
    )
    assert read_profile(str(target)).substitutions == _custom_subs()


def test_cli_copies_field_goal_range(runner, tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    new_range = (
        base.field_goal_range + 1
        if base.field_goal_range < 50
        else base.field_goal_range - 1
    )
    source = tmp_path / "source.prf"
    write_profile(replace(base, field_goal_range=new_range), str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(copy, [str(source), str(target), "--field-goal-range"]).exit_code
        == 0
    )
    assert read_profile(str(target)).field_goal_range == new_range


def test_cli_copies_goal_line_and_stop_clock_combined(runner, tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    marker = _bumped(base.situations[0].category_weights)
    flips = {1, 100, 2520}
    sits = tuple(
        replace(
            s,
            stop_clock=(not s.stop_clock)
            if s.situation_number in flips
            else s.stop_clock,
            category_weights=marker
            if s.field_position in _GOAL_LINE
            else s.category_weights,
        )
        for s in base.situations
    )
    source = tmp_path / "source.prf"
    write_profile(replace(base, situations=sits), str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(
            copy, [str(source), str(target), "--stop-clock", "--goal-line"]
        ).exit_code
        == 0
    )
    result = read_profile(str(target))
    assert tuple(s.stop_clock for s in result.situations) == tuple(
        s.stop_clock for s in sits
    )
    goal_line = [s for s in result.situations if s.field_position in _GOAL_LINE]
    assert goal_line and all(s.category_weights == marker for s in goal_line)


# ── console output ────────────────────────────────────────────────────────────


def test_cli_prints_updated_line_and_summary(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(
        copy, [str(source), str(target), "--stop-clock", "--no-backup"]
    )
    assert result.exit_code == 0
    assert f"{target}: updated (stop-clock)" in result.output
    assert "1 file(s) processed; 1 updated, 0 failed." in result.output


def test_cli_reports_backup_name(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert f"{target}: updated (stop-clock; backup target.prf." in result.output


# ── backup ────────────────────────────────────────────────────────────────────


def test_cli_creates_backup_by_default(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = target.read_bytes()
    assert (
        runner.invoke(copy, [str(source), str(target), "--stop-clock"]).exit_code == 0
    )
    backups = list(tmp_path.glob("target.prf.*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original


def test_cli_no_backup_skips_backup(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(
            copy, [str(source), str(target), "--stop-clock", "--no-backup"]
        ).exit_code
        == 0
    )
    assert list(tmp_path.glob("target.prf.*.bak")) == []


# ── bulk: directory + side filter ─────────────────────────────────────────────


def test_cli_directory_top_level_only(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    shutil.copy2(OFF1, targets / "a.prf")
    shutil.copy2(OFF1, targets / "b.prf")
    (targets / "sub").mkdir()
    shutil.copy2(OFF1, targets / "sub" / "deep.prf")
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock"])
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.output and "2 updated" in result.output


def test_cli_directory_recursive(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    shutil.copy2(OFF1, targets / "top.prf")
    (targets / "sub").mkdir()
    shutil.copy2(OFF1, targets / "sub" / "deep.prf")
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock", "-r"])
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.output


def test_cli_offense_source_skips_defense_targets(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    shutil.copy2(OFF1, targets / "off.prf")
    shutil.copy2(DEF1, targets / "def.prf")
    pre_def = (targets / "def.prf").read_bytes()
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock"])
    assert result.exit_code == 0
    assert "1 file(s) processed" in result.output and "1 updated" in result.output
    assert (targets / "def.prf").read_bytes() == pre_def


def test_cli_single_wrong_side_target_skipped(runner, tmp_path: Path) -> None:
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    pre = target.read_bytes()
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert "0 file(s) processed" in result.output
    assert target.read_bytes() == pre


# ── failures ──────────────────────────────────────────────────────────────────


def test_cli_continues_past_failed_file(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    good = targets / "good.prf"
    shutil.copy2(OFF1, good)
    bad = targets / "bad.prf"
    bad.write_bytes(b"\x00" * OFF1.stat().st_size)  # same (even) parity, but malformed
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock"])
    assert result.exit_code == 1
    assert f"{good}: updated" in result.output and f"{bad}: failed" in result.output
    assert "1 updated" in result.output and "1 failed" in result.output


def test_cli_missing_source_exit_2(runner, tmp_path: Path) -> None:
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    pre = target.read_bytes()
    result = runner.invoke(
        copy, [str(tmp_path / "nope.prf"), str(target), "--stop-clock"]
    )
    assert result.exit_code == 2
    assert target.read_bytes() == pre  # untouched when source can't be read


def test_cli_missing_target_exit_2(runner, tmp_path: Path) -> None:
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    result = runner.invoke(
        copy, [str(source), str(tmp_path / "nope.prf"), "--stop-clock"]
    )
    assert result.exit_code == 2
