"""Integration tests for `athc gameplan find-play`."""

from __future__ import annotations

import logging
import shutil
from dataclasses import replace
from pathlib import Path

from athc.cli.gameplan.find_play import (
    _join_slots,
    find_in_gameplan,
    find_play,
    format_hit_line,
)
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    ProfileType,
    StockPlayRef,
    write_gameplan,
)
from tests.integration.conftest import GP_DEFENSE, GP_OFFENSE

# Real plays in the fixtures (offense.pln = O_64_06a, defense.pln = D_50_09).
KNOWN_NORMAL = "OR45RL01"
KNOWN_NORMAL_SHORT = "RL"  # offense Run Left short category (normal hits show short)
KNOWN_SPECIAL = "SFFGXPAT"
KNOWN_SPECIAL_CATEGORY = "Field Goal/PAT"  # special hits keep the long category
MISSING = "NOSUCHPLAYXX"


# ── constructed-gameplan helpers ──────────────────────────────────────────────


def _empty_offense_gameplan() -> GamePlan:
    clock_a = CustomPlayRef(
        filename="PNFL\\CLOCK11.PLY",
        play_category=1,
        special_category=11,
        user_category=0,
    )
    clock_b = CustomPlayRef(
        filename="PNFL\\CLOCK12.PLY",
        play_category=1,
        special_category=12,
        user_category=0,
    )
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=tuple([None] * 64),
        special_plays=tuple([None] * 20),
        clock_plays=(clock_a, clock_b),
    )


def _set_normal_slots(gp: GamePlan, *placements: tuple[int, CustomPlayRef]) -> GamePlan:
    normals = list(gp.normal_plays)
    for index, play in placements:
        normals[index] = play
    return replace(gp, normal_plays=tuple(normals))


def _set_custom_special(gp: GamePlan, category: int, play: CustomPlayRef) -> GamePlan:
    """Place `play` in the custom slot for `category` (1-10); index = (category - 1) * 2."""
    specials = list(gp.special_plays)
    specials[(category - 1) * 2] = play
    return replace(gp, special_plays=tuple(specials))


def _make_offense_normal(name: str, *, user_category: int = 0x05) -> CustomPlayRef:
    """Default user_category 0x05 = 'Run Left' (after masking 0x3F); play_category 1 = offense side."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=1,
        special_category=0,
        user_category=user_category,
    )


def _make_offense_special(name: str, special_category: int = 1) -> CustomPlayRef:
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=1,
        special_category=special_category,
        user_category=0,
    )


def _make_defense_special(name: str, special_category: int = 2) -> CustomPlayRef:
    """Defense special play (play_category 0 = receiving side)."""
    return CustomPlayRef(
        filename=f"PNFL\\{name}.PLY",
        play_category=0,
        special_category=special_category,
        user_category=0,
    )


def _write(gp: GamePlan, tmp_path: Path, name: str = "gp.pln") -> Path:
    path = tmp_path / name
    write_gameplan(gp, path)
    return path


# ── _join_slots ───────────────────────────────────────────────────────────────


def test_join_slots_one() -> None:
    assert _join_slots(["1-1"]) == "1-1"


def test_join_slots_two_uses_and() -> None:
    assert _join_slots(["1-1", "2-2"]) == "1-1 and 2-2"


def test_join_slots_three_uses_oxford_comma() -> None:
    assert _join_slots(["1-1", "2-2", "16-4"]) == "1-1, 2-2, and 16-4"


# ── find_in_gameplan ──────────────────────────────────────────────────────────


def test_find_no_match_returns_empty() -> None:
    assert find_in_gameplan(_empty_offense_gameplan(), MISSING) == ([], [])


def test_find_matches_normal_slot() -> None:
    gp = _set_normal_slots(
        _empty_offense_gameplan(), (0, _make_offense_normal("OR45RL01"))
    )
    normals, specials = find_in_gameplan(gp, "OR45RL01")
    assert specials == []
    assert [(i, p.name) for i, p in normals] == [(0, "OR45RL01")]


def test_find_multiple_in_one_gameplan() -> None:
    """One play in several normal slots of a single gameplan."""
    play = _make_offense_normal("DUPPLAY", user_category=0x09)
    gp = _set_normal_slots(_empty_offense_gameplan(), (0, play), (5, play), (63, play))
    normals, _ = find_in_gameplan(gp, "DUPPLAY")
    assert [i for i, _ in normals] == [0, 5, 63]


def test_find_multiple_different_plays() -> None:
    """Two different plays both present in one gameplan (find is per-play)."""
    gp = _set_normal_slots(
        _empty_offense_gameplan(),
        (0, _make_offense_normal("PLAYA")),
        (5, _make_offense_normal("PLAYB", user_category=0x09)),
    )
    assert [i for i, _ in find_in_gameplan(gp, "PLAYA")[0]] == [0]
    assert [i for i, _ in find_in_gameplan(gp, "PLAYB")[0]] == [5]


def test_find_case_insensitive() -> None:
    gp = _set_normal_slots(
        _empty_offense_gameplan(), (7, _make_offense_normal("MixedCase"))
    )
    assert [i for i, _ in find_in_gameplan(gp, "mixedcase")[0]] == [7]
    assert [i for i, _ in find_in_gameplan(gp, "MIXEDCASE")[0]] == [7]


def test_find_matches_custom_special() -> None:
    gp = _set_custom_special(
        _empty_offense_gameplan(), 3, _make_offense_special("KICK1", 3)
    )
    normals, specials = find_in_gameplan(gp, "KICK1")
    assert normals == []
    assert [(n, p.name) for n, p in specials] == [(3, "KICK1")]


def test_find_skips_stock_special_slots() -> None:
    gp = _empty_offense_gameplan()
    stock = StockPlayRef(
        play_name="STOCKFG",
        map_offset=0,
        map_size=128,
        play_category=1,
        special_category=1,
        user_category=0,
    )
    specials = list(gp.special_plays)
    specials[1] = stock  # odd index = stock slot
    gp = replace(gp, special_plays=tuple(specials))
    assert find_in_gameplan(gp, "STOCKFG") == ([], [])


def test_find_skips_clock_slots() -> None:
    gp = _empty_offense_gameplan()
    assert find_in_gameplan(gp, "CLOCK11") == ([], [])
    assert find_in_gameplan(gp, "CLOCK12") == ([], [])


# ── format_hit_line ───────────────────────────────────────────────────────────


def test_format_offense_normal() -> None:
    """Offensive normal: short category, bracketed slot at the end."""
    play = _make_offense_normal("OR45RL01", user_category=0x05)
    assert format_hit_line(Path("OFF.pln"), "OR45RL01", [(0, play)], []) == (
        "OFF.pln: 'OR45RL01' (RL) [1-1]"
    )


def test_format_normal_two_slots() -> None:
    play = _make_offense_normal("DUP", user_category=0x09)  # Run Middle
    assert format_hit_line(Path("OFF.pln"), "DUP", [(0, play), (5, play)], []) == (
        "OFF.pln: 'DUP' (RM) [1-1][2-2]"
    )


def test_format_normal_three_slots() -> None:
    play = _make_offense_normal("DUP", user_category=0x09)
    assert format_hit_line(
        Path("OFF.pln"), "DUP", [(0, play), (5, play), (63, play)], []
    ) == ("OFF.pln: 'DUP' (RM) [1-1][2-2][16-4]")


def test_format_masks_high_user_category_bits() -> None:
    play = _make_offense_normal(
        "VARMM", user_category=0x49
    )  # bits 5-0 = 0x09 -> Run Middle
    assert format_hit_line(Path("OFF.pln"), "VARMM", [(0, play)], []) == (
        "OFF.pln: 'VARMM' (RM) [1-1]"
    )


def test_format_defense_normal() -> None:
    """Defensive normal: defense category table, short label."""
    play = CustomPlayRef(
        filename="PNFL\\DRL.PLY",
        play_category=0,
        special_category=0,
        user_category=0x04,
    )
    assert format_hit_line(Path("DEF.pln"), "DRL", [(0, play)], []) == (
        "DEF.pln: 'DRL' (RunLeft) [1-1]"
    )


def test_format_offense_special() -> None:
    """Offensive special: long category + 'in special slot N' (unchanged)."""
    play = _make_offense_special("BCFGPAT", 1)
    assert format_hit_line(Path("OFF.pln"), "BCFGPAT", [], [(1, play)]) == (
        "OFF.pln: 'BCFGPAT' (Field Goal/PAT) in special slot 1"
    )


def test_format_defense_special() -> None:
    """Defensive special: long category + 'in special slot N'."""
    play = _make_defense_special("CINKR", 2)  # Kick Return
    assert format_hit_line(Path("DEF.pln"), "CINKR", [], [(2, play)]) == (
        "DEF.pln: 'CINKR' (Kick Return) in special slot 2"
    )


def test_format_unrecognized_category_shows_unknown() -> None:
    play = CustomPlayRef(
        filename="PNFL\\MYSTERY.PLY",
        play_category=1,
        special_category=0,
        user_category=0x15,  # not a known category code
    )
    assert format_hit_line(Path("OFF.pln"), "MYSTERY", [(3, play)], []) == (
        "OFF.pln: 'MYSTERY' (Unknown) [1-4]"
    )


# ── command: single file ──────────────────────────────────────────────────────


def test_cli_requires_args(runner) -> None:
    assert runner.invoke(find_play, []).exit_code == 2


def test_cli_single_arg_is_rejected(runner) -> None:
    """One positional means PATH-with-no-plays — a usage error."""
    assert runner.invoke(find_play, [KNOWN_NORMAL]).exit_code == 2


def test_cli_single_file_hit(runner) -> None:
    result = runner.invoke(find_play, [KNOWN_NORMAL, str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}' ({KNOWN_NORMAL_SHORT}) [1-1]" in result.output
    assert "Found " not in result.output  # no summary in single-file mode


def test_cli_single_file_miss_exit_1(runner) -> None:
    result = runner.invoke(find_play, [MISSING, str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert f"'{MISSING}' not found" in result.output


def test_cli_single_file_case_insensitive(runner) -> None:
    result = runner.invoke(find_play, [KNOWN_NORMAL.lower(), str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert f"({KNOWN_NORMAL_SHORT}) [1-1]" in result.output  # hit despite lowercase


def test_cli_finds_custom_special(runner) -> None:
    result = runner.invoke(find_play, [KNOWN_SPECIAL, str(GP_OFFENSE)])
    assert result.exit_code == 0
    assert (
        f"'{KNOWN_SPECIAL}' ({KNOWN_SPECIAL_CATEGORY}) in special slot 1"
        in result.output
    )


def test_cli_multiple_plays_all_hit(runner, tmp_path: Path) -> None:
    """Several plays across a directory: one play is in two slots of one gameplan,
    which also holds a second searched play."""
    gp1 = _set_normal_slots(
        _empty_offense_gameplan(),
        (0, _make_offense_normal("OR45RL01")),  # slot 1-1
        (6, _make_offense_normal("OR45RL01")),  # slot 2-3 (same play, 2nd slot)
        (5, _make_offense_normal("DUPRM", user_category=0x09)),  # slot 2-2 (2nd play)
    )
    gp2 = _set_normal_slots(
        _empty_offense_gameplan(), (0, _make_offense_normal("OR45RL01"))
    )
    _write(gp1, tmp_path, "gp1.pln")
    _write(gp2, tmp_path, "gp2.pln")
    result = runner.invoke(find_play, ["OR45RL01", "DUPRM", str(tmp_path)])
    assert result.exit_code == 0
    assert "'OR45RL01' (RL) [1-1][2-3]" in result.output  # one play, two slots in gp1
    assert "'DUPRM' (RM) [2-2]" in result.output  # a 2nd different play in gp1
    assert "'OR45RL01': Found 3 instance(s) in 2 gameplan(s)." in result.output
    assert "'DUPRM': Found 1 instance(s) in 1 gameplan(s)." in result.output


def test_cli_one_play_misses_exit_1(runner) -> None:
    result = runner.invoke(find_play, [KNOWN_NORMAL, MISSING, str(GP_OFFENSE)])
    assert result.exit_code == 1
    assert (
        f"'{KNOWN_NORMAL}'" in result.output
        and f"'{MISSING}' not found" in result.output
    )


# ── command: directory / tree ─────────────────────────────────────────────────


def test_cli_directory_hit_only_matching_file(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    shutil.copy2(GP_DEFENSE, tmp_path / "def.pln")
    result = runner.invoke(find_play, [KNOWN_SPECIAL, str(tmp_path)])
    assert result.exit_code == 0
    assert "off.pln" in result.output and "def.pln" not in result.output
    assert f"'{KNOWN_SPECIAL}': Found 1 instance(s) in 1 gameplan(s)." in result.output


def test_cli_directory_no_hits_silent_except_summary(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    result = runner.invoke(find_play, [MISSING, str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" not in result.output
    assert f"'{MISSING}': Found 0 instance(s) in 0 gameplan(s)." in result.output


def test_cli_directory_verbose_reports_misses(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    shutil.copy2(GP_DEFENSE, tmp_path / "def.pln")
    result = runner.invoke(find_play, [KNOWN_SPECIAL, str(tmp_path), "--verbose"])
    assert result.exit_code == 0
    assert "off.pln" in result.output and "def.pln" in result.output
    assert "not found" in result.output


def test_cli_directory_summary_counts_multiple_hits(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off1.pln")
    shutil.copy2(GP_OFFENSE, tmp_path / "off2.pln")
    result = runner.invoke(find_play, [KNOWN_NORMAL, str(tmp_path)])
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}': Found 2 instance(s) in 2 gameplan(s)." in result.output


def test_cli_directory_per_play_summary(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    result = runner.invoke(
        find_play, [KNOWN_NORMAL, KNOWN_SPECIAL, MISSING, str(tmp_path)]
    )
    assert result.exit_code == 1
    assert f"'{KNOWN_NORMAL}': Found 1 instance(s) in 1 gameplan(s)." in result.output
    assert f"'{MISSING}': Found 0 instance(s) in 0 gameplan(s)." in result.output


def test_cli_recursive_finds_in_subdir(runner, tmp_path: Path) -> None:
    sub = tmp_path / "team_a"
    sub.mkdir()
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    result = runner.invoke(find_play, [KNOWN_NORMAL, str(tmp_path), "-r"])
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}': Found 1 instance(s) in 1 gameplan(s)." in result.output


# ── command: error paths ──────────────────────────────────────────────────────


def test_cli_missing_path_exit_2(runner, tmp_path: Path, caplog) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(find_play, [KNOWN_NORMAL, str(tmp_path / "nope.pln")])
    assert result.exit_code == 2
    assert "does not exist" in caplog.text


def test_cli_malformed_pln_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(find_play, [KNOWN_NORMAL, str(bad)])
    assert result.exit_code == 2
    assert "ERROR" in result.output
