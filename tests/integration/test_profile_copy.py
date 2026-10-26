"""Integration tests for `athc profile copy`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest

from athc.cli import cli
from athc.cli.profile.copy import copy
from athc.errors import FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    SubstitutionPair,
    SubstitutionSettings,
    read_profile,
    write_profile,
)
from tests.integration.conftest import (
    DEF1,
    DENVER,
    HINT,
    OFF1,
    build_teams,
    location,
    profile_file,
)

_GOAL_LINE = frozenset({FieldPosition.INSIDE_DEF_5, FieldPosition.INSIDE_OFF_5})
Lg2League = Callable[..., Path]

HELP = """\
Usage: athc profile copy [OPTIONS] SOURCE TARGET...

  Copy settings from one profile to others.

  Targets of the other side are skipped; run 'athc profile check' afterward.

Positional arguments:
  SOURCE  Profile to copy from: a .prf file or a profile key.
  TARGET  Profiles to copy into: .prf files, folders, wildcards or profile
          keys.

Options:
  -r, --recursive     Include subfolders.
  --stop-clock        Copy the stop-clock setting of every situation.
  --substitutions     Copy the substitution percentages.
  --field-goal-range  Copy the field-goal range.
  --fourth-down       Copy every 4th-down situation.
  --goal-line         Copy every goal-line situation (inside the 5).
  --pat-logic         Copy the PAT table (60 situations).
  --team NAME         Team the profile keys refer to (default: 'team' in
                      league.toml).
  --league NAME       League to use (default: the one set with 'athc config
                      set league').
  -h, --help          Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile copy off1 off2 --stop-clock --substitutions
    athc profile copy new.prf off1 off2 --substitutions
"""


@pytest.fixture
def denver(lg2_league: Lg2League, work: Path) -> Path:
    """Your team's league location, Denver's four profiles in it."""
    return location(build_teams(lg2_league, team="Denver"), DENVER)


def _key_file(folder: Path, key: str) -> Path:
    return profile_file(folder, DENVER, key)


def _copy_prf(src: Path, dest_dir: Path, *, name: str) -> Path:
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return dest


def _mutated_source(src: Path, tmp_path: Path, *, flip: tuple[int, ...]) -> Path:
    profile = read_profile(str(src))
    for n in flip:
        profile.situations[n - 1].stop_clock = not profile.situations[n - 1].stop_clock
    dest = tmp_path / "source.prf"
    write_profile(profile, str(dest))
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


def _bumped(cw: CategoryWeights) -> CategoryWeights:
    out = deepcopy(cw)
    out.weight1 = (cw.weight1 + 1) % 11
    return out


def _stop_clock(path: Path) -> tuple[bool, ...]:
    return tuple(s.stop_clock for s in read_profile(str(path)).situations)


# ── usage / argument validation ───────────────────────────────────────────────


def test_cli_no_copy_flag_is_a_sentence(runner) -> None:
    result = runner.invoke(copy, [str(OFF1), "t.prf"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: At least one copy option is required (--stop-clock, "
        "--substitutions, --field-goal-range, --fourth-down, --goal-line, "
        "--pat-logic).\n"
    )


@pytest.mark.parametrize(
    ("targets", "error"),
    [(0, "Missing argument 'TARGET...'."), (1, None)],
    ids=["none", "one"],
)
def test_cli_takes_one_or_more_targets(
    runner, tmp_path: Path, targets: int, error: str | None
) -> None:
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(OFF1), *[str(target)][:targets], "--stop-clock"])
    if error is None:
        assert result.exit_code == 0
        assert "1 file(s) processed, 1 updated" in result.stdout
    else:
        assert result.exit_code == 2
        assert result.stderr.endswith(f"Error: {error}\n")


def test_cli_missing_source_argument(runner) -> None:
    result = runner.invoke(copy, ["--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'SOURCE'.\n")


def test_cli_sub_percent_option_removed(runner, tmp_path: Path) -> None:
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(OFF1), str(target), "--sub-percent"])
    assert result.exit_code == 2
    assert "Error: No such option '--sub-percent'" in result.stderr


def test_help_screen(runner) -> None:
    result = runner.invoke(
        cli, ["profile", "copy", "--help"], prog_name="athc", terminal_width=78
    )
    assert result.exit_code == 0
    assert result.stdout == HELP


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
    profile = read_profile(str(OFF1))
    profile.substitutions = _custom_subs()
    write_profile(profile, str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--substitutions"])
    assert result.exit_code == 0
    assert f"OK   {target}: updated (substitutions)" in result.stdout
    assert read_profile(str(target)).substitutions == _custom_subs()


def test_cli_copies_field_goal_range(runner, tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    new_range = (
        base.field_goal_range + 1
        if base.field_goal_range < 50
        else base.field_goal_range - 1
    )
    source = tmp_path / "source.prf"
    edited = deepcopy(base)
    edited.field_goal_range = new_range
    write_profile(edited, str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    assert (
        runner.invoke(copy, [str(source), str(target), "--field-goal-range"]).exit_code
        == 0
    )
    assert read_profile(str(target)).field_goal_range == new_range


def test_cli_copies_goal_line_and_stop_clock_combined(runner, tmp_path: Path) -> None:
    """Both applied; the OK line names them in the help's order, whatever
    order they were given in."""
    base = read_profile(str(OFF1))
    marker = _bumped(base.situations[0].category_weights)
    flips = {1, 100, 2520}
    edited = deepcopy(base)
    for n, state, s in edited.iter_situations():
        if n in flips:
            s.stop_clock = not s.stop_clock
        if state.field_position in _GOAL_LINE:
            s.category_weights = marker
    sits = edited.situations
    source = tmp_path / "source.prf"
    write_profile(edited, str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    run = runner.invoke(copy, [str(source), str(target), "--goal-line", "--stop-clock"])
    assert run.exit_code == 0
    assert run.stdout.startswith(f"OK   {target}: updated (stop-clock, goal-line)\n")
    result = read_profile(str(target))
    assert [s.stop_clock for s in result.situations] == [s.stop_clock for s in sits]
    goal_line = [
        s
        for _, state, s in result.iter_situations()
        if state.field_position in _GOAL_LINE
    ]
    assert goal_line and all(s.category_weights == marker for s in goal_line)


def test_cli_copies_fourth_down(runner, tmp_path: Path) -> None:
    """Every source situation differs, so only the 4th-down ones may arrive."""
    base = read_profile(str(OFF1))
    edited = deepcopy(base)
    for s in edited.situations:
        s.stop_clock = not s.stop_clock
        s.category_weights = _bumped(s.category_weights)
    sits = edited.situations
    source = tmp_path / "source.prf"
    write_profile(edited, str(source))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--fourth-down"])
    assert result.exit_code == 0
    assert f"OK   {target}: updated (fourth-down)" in result.stdout
    expected = deepcopy(base)
    expected.situations = [
        s if state.down == Down.FOURTH else t
        for (_, state, t), s in zip(base.iter_situations(), sits, strict=True)
    ]
    assert read_profile(str(target)) == expected


# ── console output ────────────────────────────────────────────────────────────


def _bumped_pat_source(src: Path, tmp_path: Path) -> Path:
    profile = read_profile(str(src))
    for p in profile.pat_situations:
        p.category_weights = _bumped(p.category_weights)
    dest = tmp_path / "source.prf"
    write_profile(profile, str(dest))
    return dest


def test_cli_copies_pat_logic(runner, tmp_path: Path) -> None:
    source = _bumped_pat_source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--pat-logic"])
    assert result.exit_code == 0
    assert f"{target}: updated (pat-logic)" in result.stdout
    assert (
        read_profile(str(target)).pat_situations
        == read_profile(str(source)).pat_situations
    )


def test_cli_prints_updated_line_and_summary(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert f"OK   {target}: updated (stop-clock)" in result.stdout
    assert "1 file(s) processed, 1 updated, 0 skipped, 0 failed" in result.stdout


def test_cli_wildcard_target(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """athc expands the wildcard itself: the two matching profiles only."""
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    for name in ("Off1.prf", "Off2.prf", "other.prf"):
        shutil.copy2(OFF1, targets / name)
    monkeypatch.chdir(targets)
    result = runner.invoke(copy, [str(source), "Off*.prf", "--stop-clock"])
    assert result.exit_code == 0
    assert "2 file(s) processed, 2 updated, 0 skipped, 0 failed" in result.stdout
    assert _stop_clock(targets / "Off1.prf") == _stop_clock(source)
    assert _stop_clock(targets / "Off2.prf") == _stop_clock(source)
    assert _stop_clock(targets / "other.prf") == _stop_clock(OFF1)


# ── no backups ────────────────────────────────────────────────────────────────


def test_cli_writes_no_backup(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []
    assert "; backup " not in result.stdout


def test_cli_no_backup_option_removed(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    result = runner.invoke(
        copy, [str(source), str(target), "--stop-clock", "--no-backup"]
    )
    assert result.exit_code == 2
    assert "No such option" in result.stderr


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
    assert "2 file(s) processed" in result.stdout and "2 updated" in result.stdout


def test_cli_directory_recursive(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    shutil.copy2(OFF1, targets / "top.prf")
    (targets / "sub").mkdir()
    shutil.copy2(OFF1, targets / "sub" / "deep.prf")
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock", "-r"])
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.stdout


def test_cli_offense_source_skips_defense_targets(runner, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    targets = tmp_path / "targets"
    targets.mkdir()
    shutil.copy2(OFF1, targets / "off.prf")
    shutil.copy2(DEF1, targets / "def.prf")
    pre_def = (targets / "def.prf").read_bytes()
    result = runner.invoke(copy, [str(source), str(targets), "--stop-clock"])
    assert result.exit_code == 0
    assert f"SKIP {targets / 'def.prf'}: defense profile" in result.stdout
    assert "2 file(s) processed, 1 updated, 1 skipped, 0 failed" in result.stdout
    assert (targets / "def.prf").read_bytes() == pre_def


def test_cli_single_wrong_side_target_skipped(runner, tmp_path: Path) -> None:
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    pre = target.read_bytes()
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 0
    assert f"SKIP {target}: defense profile" in result.stdout
    assert "1 file(s) processed, 0 updated, 1 skipped, 0 failed" in result.stdout
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
    assert result.exit_code == 2
    assert f"OK   {good}: updated" in result.stdout
    assert result.stderr == f"FAIL {bad}: Invalid header '\x00\x00\x00\x00' at 0x0.\n"
    assert "2 file(s) processed, 1 updated, 0 skipped, 1 failed" in result.stdout


def test_cli_bug_in_one_file_keeps_the_batch_going(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    """A bug on one target is reported as unexpected and leaves it as it was;
    the other is still updated, and the run still exits 2."""
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    doomed = _copy_prf(OFF1, tmp_path, name="doomed.prf")
    good = _copy_prf(OFF1, tmp_path, name="good.prf")
    from athc.cli.profile import copy as copy_module

    real_write = copy_module.write_profile

    def write(profile, path: str) -> None:
        if Path(path) == doomed:
            raise RuntimeError("kaboom")
        real_write(profile, path)

    monkeypatch.setattr(copy_module, "write_profile", write)
    result = runner.invoke(copy, [str(source), str(doomed), str(good), "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {doomed}: Unexpected error. See {log_dir / 'athc.log'} for details.\n"
    )
    assert result.stdout == (
        f"OK   {good}: updated (stop-clock)\n"
        "\n2 file(s) processed, 1 updated, 0 skipped, 1 failed\n"
    )
    assert doomed.read_bytes() == OFF1.read_bytes()
    assert _stop_clock(good) == _stop_clock(source)


def test_cli_missing_source_exit_2(runner, tmp_path: Path) -> None:
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    pre = target.read_bytes()
    result = runner.invoke(
        copy, [str(tmp_path / "nope.prf"), str(target), "--stop-clock"]
    )
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.prf'}: {FILE_NOT_FOUND}\n"
    assert target.read_bytes() == pre  # untouched when source can't be read


def test_cli_file_onto_itself_exit_2(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same file however it is spelled; the line names the target as given."""
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    before = source.read_bytes()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(copy, [str(source), "source.prf", "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == "FAIL source.prf: The file cannot be copied onto itself.\n"
    assert result.stdout == ""
    assert source.read_bytes() == before


def test_cli_folder_holding_source_skips_it(runner, tmp_path: Path) -> None:
    """One TARGET, but a folder: the source in it is only skipped."""
    folder = tmp_path / "drafts"
    folder.mkdir()
    source = _mutated_source(OFF1, folder, flip=(1,))
    other = _copy_prf(OFF1, folder, name="other.prf")
    result = runner.invoke(copy, [str(source), str(folder), "--stop-clock"])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {other}: updated (stop-clock)\n"
        f"SKIP {source}: the source profile\n"
        "\n2 file(s) processed, 1 updated, 1 skipped, 0 failed\n"
    )


def test_cli_missing_target_exit_2(runner, tmp_path: Path) -> None:
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    target = tmp_path / "nope.prf"
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {target}: {FILE_NOT_FOUND}\n"
    assert result.stdout == "\n0 file(s) processed, 0 updated, 0 skipped, 1 failed\n"


def test_cli_missing_target_folder_not_created_exit_2(runner, tmp_path: Path) -> None:
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    target = tmp_path / "missing" / "target.prf"
    result = runner.invoke(copy, [str(source), str(target), "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {target}: {PATH_NOT_FOUND}\n"
    assert not target.parent.exists()


# ── profile keys ──────────────────────────────────────────────────────────────


def test_cli_key_to_key(runner, denver: Path) -> None:
    """1st half to 2nd half."""
    off1, off2 = _key_file(denver, "off1"), _key_file(denver, "off2")
    assert _stop_clock(off2) != _stop_clock(off1)
    result = runner.invoke(copy, ["off1", "off2", "--stop-clock"])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {off2}: updated (stop-clock)\n"
        "\n1 file(s) processed, 1 updated, 0 skipped, 0 failed\n"
    )
    assert _stop_clock(off2) == _stop_clock(off1)


def test_cli_file_to_two_keys(runner, denver: Path, tmp_path: Path) -> None:
    source = tmp_path / "new.prf"
    profile = read_profile(str(OFF1))
    profile.substitutions = _custom_subs()
    write_profile(profile, str(source))
    off1, off2 = _key_file(denver, "off1"), _key_file(denver, "off2")
    result = runner.invoke(copy, [str(source), "off1", "off2", "--substitutions"])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {off1}: updated (substitutions)\n"
        f"OK   {off2}: updated (substitutions)\n"
        "\n2 file(s) processed, 2 updated, 0 skipped, 0 failed\n"
    )
    assert read_profile(str(off1)).substitutions == _custom_subs()
    assert read_profile(str(off2)).substitutions == _custom_subs()


@pytest.mark.parametrize("keys", [["def1"], ["def1", "def2"]], ids=["one", "two"])
def test_cli_offense_key_to_defense_keys(runner, denver: Path, keys: list[str]) -> None:
    """One SKIP per target of the other side, and still 0."""
    before = {key: _key_file(denver, key).read_bytes() for key in keys}
    result = runner.invoke(copy, ["off1", *keys, "--stop-clock"])
    assert result.exit_code == 0
    skips = "".join(f"SKIP {_key_file(denver, key)}: defense profile\n" for key in keys)
    assert result.stdout == (
        f"{skips}\n{len(keys)} file(s) processed, 0 updated, {len(keys)} skipped, "
        "0 failed\n"
    )
    assert {key: _key_file(denver, key).read_bytes() for key in keys} == before


def test_cli_key_onto_itself(runner, denver: Path) -> None:
    """The source as the only target is refused, as Windows' copy does."""
    off1 = _key_file(denver, "off1")
    before = off1.read_bytes()
    result = runner.invoke(copy, ["off1", "off1", "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {off1}: The file cannot be copied onto itself.\n"
    assert result.stdout == ""
    assert off1.read_bytes() == before


def test_cli_key_onto_itself_and_another(runner, denver: Path) -> None:
    """With a second target the source is only skipped."""
    off1, off2 = _key_file(denver, "off1"), _key_file(denver, "off2")
    result = runner.invoke(copy, ["off1", "off1", "off2", "--stop-clock"])
    assert result.exit_code == 0
    assert result.stdout == (
        f"SKIP {off1}: the source profile\n"
        f"OK   {off2}: updated (stop-clock)\n"
        "\n2 file(s) processed, 1 updated, 1 skipped, 0 failed\n"
    )


def test_cli_folder_and_key(runner, denver: Path, tmp_path: Path) -> None:
    """Targets in TARGET order, a folder's files sorted."""
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    folder = tmp_path / "drafts"
    folder.mkdir()
    for name in ("b.prf", "a.prf"):
        shutil.copy2(OFF1, folder / name)
    result = runner.invoke(copy, [str(source), str(folder), "off2", "--stop-clock"])
    assert result.exit_code == 0
    updated = [folder / "a.prf", folder / "b.prf", _key_file(denver, "off2")]
    assert result.stdout == (
        "".join(f"OK   {path}: updated (stop-clock)\n" for path in updated)
        + "\n3 file(s) processed, 3 updated, 0 skipped, 0 failed\n"
    )


def test_cli_key_repeated_once(runner, denver: Path, tmp_path: Path) -> None:
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    result = runner.invoke(copy, [str(source), "off2", "OFF2", "--stop-clock"])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {_key_file(denver, 'off2')}: updated (stop-clock)\n"
        "\n1 file(s) processed, 1 updated, 0 skipped, 0 failed\n"
    )


def test_cli_missing_key_target_counts_failed(
    runner, denver: Path, tmp_path: Path
) -> None:
    """The other targets are still updated; the run ends with 2."""
    source = _mutated_source(OFF1, tmp_path, flip=(1,))
    missing = _key_file(denver, "off2")
    missing.unlink()
    result = runner.invoke(copy, [str(source), "off2", "off1", "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND} {HINT}\n"
    assert f"OK   {_key_file(denver, 'off1')}: updated (stop-clock)" in result.stdout
    assert "1 file(s) processed, 1 updated, 0 skipped, 1 failed" in result.stdout


def test_cli_missing_key_source_touches_nothing(runner, denver: Path) -> None:
    missing = _key_file(denver, "off1")
    missing.unlink()
    target = _key_file(denver, "off2")
    before = target.read_bytes()
    result = runner.invoke(copy, ["off1", "off2", "--stop-clock"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND} {HINT}\n"
    assert result.stdout == ""
    assert target.read_bytes() == before
