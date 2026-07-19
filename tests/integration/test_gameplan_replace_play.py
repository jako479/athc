"""Integration tests for `athc gameplan replace-play`."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from athc.cli.gameplan.replace_play import (
    format_replacement_lines,
    replace_in_gameplan,
    replace_play,
)
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    read_gameplan,
    write_gameplan,
)
from tests.integration.conftest import GP_DEFENSE, GP_OFFENSE, PLAYS

POOL_FLAGS = ["--play-path", str(PLAYS)]

# Real plays in the curated pool (and, for OR45RL01, in offense.pln slot 1-1).
NORMAL_TARGET = "OR45RL01"  # offense Run Left, present in offense.pln
NORMAL_REPL = "DN28RM01"  # a different offense Run Middle play in the pool
SPECIAL_REPL = "SFFGXPAT"  # offense Field Goal/PAT (special category 1) in the pool
KICKOFF_REPL = "LIONKICK"  # offense Kickoff (special category 2) in the pool
DEFENSE_REPL = "NY31RL01"  # a defense play in the pool
MISSING = "NOSUCHPLAYXX"


# ── constructed-gameplan helpers ──────────────────────────────────────────────


def _clock(category: int) -> CustomPlayRef:
    return CustomPlayRef(
        filename=f"PNFL\\CLOCK{category}.PLY",
        play_category=1,
        special_category=category,
        user_category=0,
    )


def _onorm(name: str, user_category: int = 0x05) -> CustomPlayRef:
    """Offense normal play (user_category 0x05 = Run Left)."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=1,
        special_category=0,
        user_category=user_category,
    )


def _ospec(name: str, category: int) -> CustomPlayRef:
    """Offense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=1,
        special_category=category,
        user_category=0,
    )


def _dnorm(name: str) -> CustomPlayRef:
    """Defense normal play."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=0,
        special_category=0,
        user_category=0x04,
    )


def _dspec(name: str, category: int) -> CustomPlayRef:
    """Defense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=0,
        special_category=category,
        user_category=0,
    )


def _build(
    profile_type: ProfileType,
    normals: dict[int, CustomPlayRef] | None,
    specials: dict[int, CustomPlayRef] | None,
) -> GamePlan:
    normal_slots: list[PlayRef | None] = [None] * 64
    for index, play in (normals or {}).items():
        normal_slots[index] = play
    special_slots: list[PlayRef | None] = [None] * 20
    for category, play in (specials or {}).items():
        special_slots[(category - 1) * 2] = play
    # Offense requires both clock slots filled; defense requires neither.
    clock = (
        (_clock(11), _clock(12))
        if profile_type is ProfileType.OFFENSE
        else (None, None)
    )
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(normal_slots),
        special_plays=tuple(special_slots),
        clock_plays=clock,
    )


def _offense_gameplan(
    *,
    normals: dict[int, CustomPlayRef] | None = None,
    specials: dict[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """Empty offense gameplan with the given normal slots (0-based) and custom
    special slots (1-based category) filled."""
    return _build(ProfileType.OFFENSE, normals, specials)


def _defense_gameplan(
    *,
    normals: dict[int, CustomPlayRef] | None = None,
    specials: dict[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """Empty defense gameplan (no clock slots) with the given slots filled."""
    return _build(ProfileType.DEFENSE, normals, specials)


def _write(gp: GamePlan, tmp_path: Path, name: str = "gp.pln") -> Path:
    path = tmp_path / name
    write_gameplan(gp, path)
    return path


def _name(play: PlayRef | None) -> str:
    assert play is not None
    return play.name


# ── replace_in_gameplan (pure) ────────────────────────────────────────────────


def test_replace_no_match_unchanged() -> None:
    gp = _offense_gameplan(normals={0: _onorm("OLDRUN")})
    out, normal_hits, special_hits = replace_in_gameplan(gp, MISSING, _onorm("NEW"))
    assert not normal_hits and not special_hits and out is gp


def test_replace_offense_normal_multiple_slots() -> None:
    """Offense normal play in several slots: all swap; bystander preserved."""
    old = _onorm("OLDRUN")
    gp = _offense_gameplan(normals={0: old, 5: old, 63: old, 1: _onorm("KEEPME", 0x09)})
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDRUN", _onorm("NEW", 0x09)
    )
    assert [i for i, _ in normal_hits] == [0, 5, 63] and special_hits == []
    assert [_name(out.normal_plays[i]) for i in (0, 5, 63)] == ["NEW"] * 3
    assert _name(out.normal_plays[1]) == "KEEPME"  # bystander preserved


def test_replace_defense_normal() -> None:
    gp = _defense_gameplan(normals={0: _dnorm("OLDDEF"), 1: _dnorm("KEEPDEF")})
    out, normal_hits, special_hits = replace_in_gameplan(gp, "OLDDEF", _dnorm("NEWDEF"))
    assert [i for i, _ in normal_hits] == [0] and special_hits == []
    assert _name(out.normal_plays[0]) == "NEWDEF"
    assert _name(out.normal_plays[1]) == "KEEPDEF"  # bystander preserved


def test_replace_offense_special() -> None:
    gp = _offense_gameplan(specials={1: _ospec("OLDFG", 1), 2: _ospec("KEEPKICK", 2)})
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDFG", _ospec("NEWFG", 1)
    )
    assert normal_hits == [] and [n for n, _ in special_hits] == [1]
    assert _name(out.custom_special_plays[0]) == "NEWFG"
    assert _name(out.custom_special_plays[1]) == "KEEPKICK"  # other special preserved


def test_replace_defense_special() -> None:
    gp = _defense_gameplan(specials={2: _dspec("OLDKR", 2), 3: _dspec("KEEPPR", 3)})
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDKR", _dspec("NEWKR", 2)
    )
    assert normal_hits == [] and [n for n, _ in special_hits] == [2]
    assert _name(out.custom_special_plays[1]) == "NEWKR"  # category 2 → index 1
    assert _name(out.custom_special_plays[2]) == "KEEPPR"  # other special preserved


def test_replace_case_insensitive_target() -> None:
    gp = _offense_gameplan(normals={7: _onorm("MixedCase")})
    out, normal_hits, _ = replace_in_gameplan(gp, "mixedcase", _onorm("NEW"))
    assert [i for i, _ in normal_hits] == [7] and _name(out.normal_plays[7]) == "NEW"


def test_replace_special_into_normal_raises() -> None:
    gp = _offense_gameplan(normals={0: _onorm("OLDRUN")})
    with pytest.raises(ValueError):
        replace_in_gameplan(gp, "OLDRUN", _ospec("FG", 1))


def test_replace_wrong_special_category_raises() -> None:
    gp = _offense_gameplan(specials={1: _ospec("OLDFG", 1)})
    with pytest.raises(ValueError):
        replace_in_gameplan(gp, "OLDFG", _ospec("KICK", 2))


def test_replace_wrong_side_raises() -> None:
    gp = _offense_gameplan(normals={0: _onorm("OLDRUN")})
    with pytest.raises(ValueError):
        replace_in_gameplan(gp, "OLDRUN", _dnorm("DEFPLAY"))


# ── format_replacement_lines (short category; normal vs special phrasing) ──────


def test_format_lines_normal_slot() -> None:
    line = format_replacement_lines(
        Path("OFF.pln"), [(0, _onorm("OLDRUN"))], [], _onorm("NEWRUN", 0x09)
    )
    assert line == ["OFF.pln: 'OLDRUN' (RL) replaced with 'NEWRUN' (RM) [1-1]"]


def test_format_lines_multiple_normal_slots() -> None:
    """Many normal hits collapse to one line, slots bracketed in order."""
    dup = _onorm("DUP", 0x09)
    line = format_replacement_lines(
        Path("OFF.pln"), [(2, dup), (13, dup)], [], _onorm("NEW", 0x09)
    )
    assert line == ["OFF.pln: 'DUP' (RM) replaced with 'NEW' (RM) [1-3][4-2]"]


def test_format_lines_special_slot() -> None:
    line = format_replacement_lines(
        Path("OFF.pln"), [], [(1, _ospec("OLDFG", 1))], _ospec("NEWFG", 1)
    )
    assert line == [
        "OFF.pln: Replaced 'OLDFG' (Field Goal/PAT) in special slot 1 "
        "with 'NEWFG' (Field Goal/PAT)"
    ]


# ── command: usage / replacement resolution ───────────────────────────────────


def test_cli_requires_args(runner) -> None:
    assert runner.invoke(replace_play, []).exit_code == 2


def test_cli_requires_path(runner) -> None:
    assert runner.invoke(replace_play, [NORMAL_TARGET, NORMAL_REPL]).exit_code == 2


def test_cli_rejects_multiple_plays(runner, tmp_path: Path) -> None:
    """Only one PLAY (unlike find-play): a fourth positional is a usage error."""
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, "SECONDPLAY", NORMAL_REPL, str(p), *POOL_FLAGS]
    )
    assert result.exit_code == 2


def test_cli_no_quiet_option(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: _onorm("OLDRUN")}), tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(p), "-q", *POOL_FLAGS]
    )
    assert result.exit_code == 2


def test_cli_replacement_not_in_pool_exit_2(runner, tmp_path: Path, caplog) -> None:
    p = _write(_offense_gameplan(normals={0: _onorm("OLDRUN")}), tmp_path)
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.replace_play"):
        result = runner.invoke(replace_play, ["OLDRUN", MISSING, str(p), *POOL_FLAGS])
    assert result.exit_code == 2
    assert "not found in the play pool" in caplog.text


def test_cli_replacement_case_insensitive(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL.lower(), str(p), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_REPL


# ── command: single file ──────────────────────────────────────────────────────


def _copy_offense(tmp_path: Path, name: str = "offense.pln") -> Path:
    dst = tmp_path / name
    shutil.copy2(GP_OFFENSE, dst)
    return dst


def test_cli_single_file_replaces_normal(runner, tmp_path: Path) -> None:
    """Target in several slots of one file: all swap, one collapsed line, bystander kept."""
    old = _onorm("OLDRUN")
    gp = _offense_gameplan(normals={0: old, 5: old, 63: old, 1: _onorm("KEEPME", 0x09)})
    p = _write(gp, tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert [_name(rt.normal_plays[i]) for i in (0, 5, 63)] == [NORMAL_REPL] * 3
    assert _name(rt.normal_plays[1]) == "KEEPME"  # untouched
    assert result.output.count("replaced with") == 1  # all slots in one line
    assert (
        f"'OLDRUN' (RL) replaced with '{NORMAL_REPL}' (RM) [1-1][2-2][16-4]"
        in result.output
    )


def test_cli_single_file_replaces_special(runner, tmp_path: Path) -> None:
    gp = _offense_gameplan(specials={1: _ospec("OLDFG", 1), 2: _ospec("KEEPKICK", 2)})
    p = _write(gp, tmp_path)
    result = runner.invoke(replace_play, ["OLDFG", SPECIAL_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert _name(rt.custom_special_plays[0]) == SPECIAL_REPL
    assert _name(rt.custom_special_plays[1]) == "KEEPKICK"  # untouched
    assert (
        f"Replaced 'OLDFG' (Field Goal/PAT) in special slot 1 "
        f"with '{SPECIAL_REPL}' (Field Goal/PAT)" in result.output
    )


def test_cli_single_file_target_case_insensitive(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET.lower(), NORMAL_REPL, str(p), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_REPL


def test_cli_single_file_miss_exit_1(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, [MISSING, NORMAL_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 1
    assert f"'{MISSING}' not found" in result.output
    assert p.read_bytes() == original  # untouched


# ── command: backup ───────────────────────────────────────────────────────────


def test_creates_backup_by_default(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(p), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    backups = list(tmp_path.glob("offense.pln.*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original


def test_no_backup_skips_backup(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(p), "--no-backup", *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []


def test_reports_backup_name(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(p), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert "backup offense.pln." in result.output and ".bak" in result.output


# ── command: directory / tree ─────────────────────────────────────────────────


def test_cli_directory_updates_matching_files(runner, tmp_path: Path) -> None:
    _copy_offense(tmp_path, "off1.pln")
    _copy_offense(tmp_path, "off2.pln")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(tmp_path), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert "replaced 2 instance(s) in 2 gameplan(s); 0 failed." in result.output
    for name in ("off1.pln", "off2.pln"):
        assert _name(read_gameplan(str(tmp_path / name)).normal_plays[0]) == NORMAL_REPL


def test_cli_directory_leaves_other_side_untouched(runner, tmp_path: Path) -> None:
    _copy_offense(tmp_path)
    def_pln = tmp_path / "defense.pln"
    shutil.copy2(GP_DEFENSE, def_pln)
    original_def = def_pln.read_bytes()
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(tmp_path), *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert "in 1 gameplan(s); 0 failed." in result.output
    assert def_pln.read_bytes() == original_def  # no OR45RL01 there → untouched


def test_cli_directory_no_hits_exit_1(runner, tmp_path: Path) -> None:
    _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [MISSING, NORMAL_REPL, str(tmp_path), *POOL_FLAGS]
    )
    assert result.exit_code == 1
    assert "replaced 0 instance(s) in 0 gameplan(s); 0 failed." in result.output


def test_cli_recursive_replaces_in_subdir(runner, tmp_path: Path) -> None:
    sub = tmp_path / "team_a"
    sub.mkdir()
    _copy_offense(sub)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(tmp_path), "-r", *POOL_FLAGS]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(sub / "offense.pln")).normal_plays[0]) == NORMAL_REPL


# ── command: validation / errors (target left untouched) ──────────────────────


def test_cli_replacement_special_for_normal_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: _onorm("OLDRUN")}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", SPECIAL_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 1
    assert "failed" in result.output
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_replacement_wrong_side_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: _onorm("OLDRUN")}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", DEFENSE_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 1
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_replacement_wrong_special_category_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(specials={1: _ospec("OLDFG", 1)}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDFG", KICKOFF_REPL, str(p), *POOL_FLAGS])
    assert result.exit_code == 1
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_missing_path_exit_2(runner, tmp_path: Path, caplog) -> None:
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.replace_play"):
        result = runner.invoke(
            replace_play,
            [NORMAL_TARGET, NORMAL_REPL, str(tmp_path / "nope.pln"), *POOL_FLAGS],
        )
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


def test_cli_malformed_pln_exit_1(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(bad), *POOL_FLAGS]
    )
    assert result.exit_code == 1
    assert "failed" in result.output


def test_cli_invalid_play_path_exit_2(runner, tmp_path: Path, caplog) -> None:
    p = _copy_offense(tmp_path)
    with caplog.at_level(logging.ERROR, logger="athc.cli.gameplan.replace_play"):
        result = runner.invoke(
            replace_play,
            [
                NORMAL_TARGET,
                NORMAL_REPL,
                str(p),
                "--play-path",
                str(tmp_path / "missing"),
            ],
        )
    assert result.exit_code == 2
    assert "not a directory" in caplog.text


def test_cli_continues_past_failed_file(runner, tmp_path: Path) -> None:
    _copy_offense(tmp_path)
    (tmp_path / "broken.pln").write_bytes(b"\x00\x01\x02")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, str(tmp_path), *POOL_FLAGS]
    )
    assert result.exit_code == 1
    assert "replaced 1 instance(s) in 1 gameplan(s); 1 failed." in result.output
