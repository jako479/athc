"""Integration tests for `athc gameplan replace-play`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.replace_play import (
    Picked,
    Skipped,
    format_replacement_lines,
    pick_replacement,
    replace_in_gameplan,
    replace_play,
)
from athc.errors import FILE_NOT_FOUND, PATH_NOT_FOUND, AthcError
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    read_gameplan,
    write_gameplan,
)
from athc.gameplan import OffenseCategoryRule, Rules
from athc.gameplan.writer import build_custom_play
from athc.playpool import PlayPool, read_play_pool
from tests.conftest import LEAGUE, PNFL_LABELS, athc_toml, league_toml, toml_error
from tests.integration.conftest import (
    GP_DEFENSE,
    GP_OFFENSE,
    PLAYS,
    TEAM_NAMES,
    build_gameplan,
    defense_normal,
    defense_special,
    lge,
    offense_normal,
    offense_special,
    team,
)

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league; its play_path is the curated test pool."""
    write_config(athc_toml())
    return make_league(LEAGUE, league_toml(PLAYS))


# Real plays in the curated pool (and, for OR45RL01, in offense.pln slot 1-1).
NORMAL_TARGET = "OR45RL01"  # offense Run Left, present in offense.pln
NORMAL_REPL = "DN28RM01"  # a different offense Run Middle play in the pool
SPECIAL_REPL = "SFFGXPAT"  # offense Field Goal/PAT (special category 1) in the pool
KICKOFF_REPL = "LIONKICK"  # offense Kickoff (special category 2) in the pool
DEFENSE_REPL = "NY31RL01"  # a defense play in the pool
MISSING = "NOSUCHPLAYXX"


# ── constructed-gameplan helpers ──────────────────────────────────────────────


def _offense_gameplan(
    *,
    normals: dict[int, CustomPlayRef] | None = None,
    specials: dict[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """Empty offense gameplan with the given normal slots (0-based) and custom
    special slots (1-based category) filled."""
    return build_gameplan(ProfileType.OFFENSE, normals, specials)


def _defense_gameplan(
    *,
    normals: dict[int, CustomPlayRef] | None = None,
    specials: dict[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """Empty defense gameplan (no clock slots) with the given slots filled."""
    return build_gameplan(ProfileType.DEFENSE, normals, specials)


def _write(gp: GamePlan, tmp_path: Path, name: str = "gp.pln") -> Path:
    path = tmp_path / name
    write_gameplan(gp, path)
    return path


def _name(play: PlayRef | None) -> str:
    assert play is not None
    return play.name


# ── pick_replacement (constructed gameplans) ──────────────────────────────────

RM_MAX_0 = Rules(offense_categories={"Run Middle": OffenseCategoryRule(max_count=0)})
OTHER_RM = "DN28RMX3"  # a second offense Run Middle play in the pool
OTHER_DEFENSE = "MN31RLD5"  # a second defense Run Left play in the pool


@pytest.fixture(scope="module")
def pool() -> PlayPool:
    return read_play_pool(PLAYS, labels=PNFL_LABELS)


def _entries(pool: PlayPool, *names: str) -> list[CustomPlayRef]:
    """The `.pln` entries for pool plays, in order."""
    entries: list[CustomPlayRef] = []
    for name in names:
        record = pool.find_by_name(name)
        assert record is not None
        entries.append(build_custom_play(record, pool.root_dir))
    return entries


def test_pick_skips_play_already_in_gameplan(pool: PlayPool) -> None:
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    entries = _entries(pool, NORMAL_REPL, NORMAL_TARGET)
    picked = pick_replacement(gp, "OLDRUN", entries, Rules(), pool)
    assert picked.skipped == (Skipped(NORMAL_REPL, ("already in the game plan",)),)
    assert picked.entry is not None and picked.entry.name == NORMAL_TARGET
    assert picked.updated is not None
    assert _name(picked.updated.normal_plays[0]) == NORMAL_TARGET
    assert picked.updated == _offense_gameplan(
        normals={0: entries[1], 1: offense_normal(NORMAL_REPL, 0x09)}
    )


def test_pick_skips_play_breaking_a_rule(pool: PlayPool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    picked = pick_replacement(
        gp, "OLDRUN", _entries(pool, NORMAL_REPL, NORMAL_TARGET), RM_MAX_0, pool
    )
    assert picked.skipped == (
        Skipped(
            NORMAL_REPL,
            (
                "fails check: [Run Middle] Offensive category 'Run Middle' "
                "has 1 plays; allows at most 0.",
            ),
        ),
    )
    assert picked.entry is not None and picked.entry.name == NORMAL_TARGET


def test_pick_none_fits(pool: PlayPool) -> None:
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_TARGET)}
    )
    picked = pick_replacement(
        gp, "OLDRUN", _entries(pool, NORMAL_REPL, NORMAL_TARGET), RM_MAX_0, pool
    )
    assert picked.updated is None and picked.entry is None
    assert [i for i, _ in picked.normal_hits] == [0]
    assert [s.name for s in picked.skipped] == [NORMAL_REPL, NORMAL_TARGET]


def test_pick_no_hits(pool: PlayPool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    picked = pick_replacement(gp, MISSING, _entries(pool, NORMAL_REPL), Rules(), pool)
    assert picked == Picked(None, None, [], [], ())


def test_pick_plan_still_failing_check_is_not_replaced(pool: PlayPool) -> None:
    """Run Middle is over its cap before the swap and still is after it."""
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    picked = pick_replacement(gp, "OLDRUN", _entries(pool, OTHER_RM), RM_MAX_0, pool)
    assert picked.updated is None and picked.entry is None
    assert picked.skipped == (
        Skipped(
            OTHER_RM,
            (
                "fails check: [Run Middle] Offensive category 'Run Middle' "
                "has 2 plays; allows at most 0.",
            ),
        ),
    )


def test_pick_swap_that_fixes_the_plan_is_used(pool: PlayPool) -> None:
    """The play being replaced puts Run Middle over its cap; swapping it fixes
    the plan, so the replacement is used."""
    gp = _offense_gameplan(normals={0: offense_normal(NORMAL_REPL, 0x09)})
    picked = pick_replacement(
        gp, NORMAL_REPL, _entries(pool, NORMAL_TARGET), RM_MAX_0, pool
    )
    assert picked.entry is not None and picked.entry.name == NORMAL_TARGET
    assert picked.skipped == ()


def test_pick_play_replaced_by_itself(pool: PlayPool) -> None:
    """The play being replaced is not 'already in the game plan'."""
    gp = _offense_gameplan(normals={0: offense_normal(NORMAL_TARGET)})
    picked = pick_replacement(
        gp, NORMAL_TARGET, _entries(pool, NORMAL_TARGET), Rules(), pool
    )
    assert picked.entry is not None and picked.skipped == ()


def test_pick_model_refusal_keeps_the_text_for_one_replacement(
    pool: PlayPool,
) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    picked = pick_replacement(
        gp, "OLDRUN", _entries(pool, SPECIAL_REPL), Rules(), pool, Path("x.pln")
    )
    assert picked.updated is None and picked.entry is None
    assert str(picked.refused).startswith(
        "x.pln: Normal slot 0 contains a special-teams play"
    )


def test_pick_refused_later_replacement_named_and_skips_kept(
    pool: PlayPool,
) -> None:
    """With a list, the refusal names the replacement; earlier skips stay."""
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    entries = _entries(pool, NORMAL_REPL, DEFENSE_REPL, NORMAL_TARGET)
    picked = pick_replacement(gp, "OLDRUN", entries, Rules(), pool, Path("x.pln"))
    assert picked.updated is None and picked.entry is None
    assert picked.skipped == (Skipped(NORMAL_REPL, ("already in the game plan",)),)
    assert str(picked.refused) == (
        f"x.pln: '{DEFENSE_REPL}' does not fit: Normal slot 0: play has "
        "defensive play_category=0x92, but profile_type is OFFENSE."
    )


def test_pick_defense_skips_play_already_in_gameplan(pool: PlayPool) -> None:
    gp = _defense_gameplan(
        normals={0: defense_normal("OLDDEF"), 1: defense_normal(DEFENSE_REPL)}
    )
    picked = pick_replacement(
        gp, "OLDDEF", _entries(pool, DEFENSE_REPL, OTHER_DEFENSE), Rules(), pool
    )
    assert picked.skipped == (Skipped(DEFENSE_REPL, ("already in the game plan",)),)
    assert picked.entry is not None and picked.entry.name == OTHER_DEFENSE


# ── replace_in_gameplan (pure) ────────────────────────────────────────────────


def test_replace_no_match_unchanged() -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, MISSING, offense_normal("NEW")
    )
    assert not normal_hits and not special_hits and out is gp


def test_replace_offense_normal_multiple_slots() -> None:
    """Offense normal play in several slots: all swap; bystander preserved."""
    old = offense_normal("OLDRUN")
    gp = _offense_gameplan(
        normals={0: old, 5: old, 63: old, 1: offense_normal("KEEPME", 0x09)}
    )
    new = offense_normal("NEW", 0x09)
    out, normal_hits, special_hits = replace_in_gameplan(gp, "OLDRUN", new)
    assert [i for i, _ in normal_hits] == [0, 5, 63] and special_hits == []
    assert [_name(out.normal_plays[i]) for i in (0, 5, 63)] == ["NEW"] * 3
    assert _name(out.normal_plays[1]) == "KEEPME"  # bystander preserved
    assert out == _offense_gameplan(
        normals={0: new, 5: new, 63: new, 1: offense_normal("KEEPME", 0x09)}
    )


def test_replace_defense_normal() -> None:
    gp = _defense_gameplan(
        normals={0: defense_normal("OLDDEF"), 1: defense_normal("KEEPDEF")}
    )
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDDEF", defense_normal("NEWDEF")
    )
    assert [i for i, _ in normal_hits] == [0] and special_hits == []
    assert _name(out.normal_plays[0]) == "NEWDEF"
    assert _name(out.normal_plays[1]) == "KEEPDEF"  # bystander preserved
    assert out == _defense_gameplan(
        normals={0: defense_normal("NEWDEF"), 1: defense_normal("KEEPDEF")}
    )


def test_replace_offense_special() -> None:
    gp = _offense_gameplan(
        specials={1: offense_special("OLDFG", 1), 2: offense_special("KEEPKICK", 2)}
    )
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDFG", offense_special("NEWFG", 1)
    )
    assert normal_hits == [] and [n for n, _ in special_hits] == [1]
    assert _name(out.custom_special_plays[0]) == "NEWFG"
    assert _name(out.custom_special_plays[1]) == "KEEPKICK"  # other special preserved
    assert out == _offense_gameplan(
        specials={1: offense_special("NEWFG", 1), 2: offense_special("KEEPKICK", 2)}
    )


def test_replace_defense_special() -> None:
    gp = _defense_gameplan(
        specials={2: defense_special("OLDKR", 2), 3: defense_special("KEEPPR", 3)}
    )
    out, normal_hits, special_hits = replace_in_gameplan(
        gp, "OLDKR", defense_special("NEWKR", 2)
    )
    assert normal_hits == [] and [n for n, _ in special_hits] == [2]
    assert _name(out.custom_special_plays[1]) == "NEWKR"  # category 2 → index 1
    assert _name(out.custom_special_plays[2]) == "KEEPPR"  # other special preserved
    assert out == _defense_gameplan(
        specials={2: defense_special("NEWKR", 2), 3: defense_special("KEEPPR", 3)}
    )


def test_replace_case_insensitive_target() -> None:
    gp = _offense_gameplan(normals={7: offense_normal("MixedCase")})
    out, normal_hits, _ = replace_in_gameplan(gp, "mixedcase", offense_normal("NEW"))
    assert [i for i, _ in normal_hits] == [7] and _name(out.normal_plays[7]) == "NEW"
    assert out == _offense_gameplan(normals={7: offense_normal("NEW")})


def test_replace_special_into_normal_raises() -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    with pytest.raises(AthcError):
        replace_in_gameplan(gp, "OLDRUN", offense_special("FG", 1))


def test_replace_wrong_special_category_raises() -> None:
    gp = _offense_gameplan(specials={1: offense_special("OLDFG", 1)})
    with pytest.raises(AthcError):
        replace_in_gameplan(gp, "OLDFG", offense_special("KICK", 2))


def test_replace_wrong_side_raises() -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    with pytest.raises(AthcError):
        replace_in_gameplan(gp, "OLDRUN", defense_normal("DEFPLAY"))


def test_replace_error_names_the_path_first() -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    with pytest.raises(AthcError) as exc:
        replace_in_gameplan(gp, "OLDRUN", offense_special("FG", 1), Path("x.pln"))
    assert str(exc.value).startswith("x.pln: Normal slot 0 contains a special-teams")
    assert exc.value.path == Path("x.pln")


# ── format_replacement_lines (short category; normal vs special phrasing) ──────


def test_format_lines_normal_slot() -> None:
    line = format_replacement_lines(
        Path("OFF.pln"),
        [(0, offense_normal("OLDRUN"))],
        [],
        offense_normal("NEWRUN", 0x09),
        PNFL_LABELS,
    )
    assert line == ["OFF.pln: 'OLDRUN' (RL) replaced with 'NEWRUN' (RM) [1-1]"]


def test_format_lines_multiple_normal_slots() -> None:
    """Many normal hits collapse to one line, slots bracketed in order."""
    dup = offense_normal("DUP", 0x09)
    line = format_replacement_lines(
        Path("OFF.pln"),
        [(2, dup), (13, dup)],
        [],
        offense_normal("NEW", 0x09),
        PNFL_LABELS,
    )
    assert line == ["OFF.pln: 'DUP' (RM) replaced with 'NEW' (RM) [1-3][4-2]"]


def test_format_lines_special_slot() -> None:
    line = format_replacement_lines(
        Path("OFF.pln"),
        [],
        [(1, offense_special("OLDFG", 1))],
        offense_special("NEWFG", 1),
        PNFL_LABELS,
    )
    assert line == [
        "OFF.pln: Replaced 'OLDFG' (Field Goal/PAT) in special slot 1 "
        "with 'NEWFG' (Field Goal/PAT)"
    ]


# ── command: usage / replacement resolution ───────────────────────────────────


def test_cli_requires_args(runner) -> None:
    assert runner.invoke(replace_play, []).exit_code == 2


def test_cli_bare_is_missing_play(runner) -> None:
    result = runner.invoke(replace_play, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'PLAY'.\n")


def test_cli_one_name_is_usage_error(runner) -> None:
    result = runner.invoke(replace_play, [NORMAL_TARGET])
    assert result.exit_code == 2
    assert "Missing argument 'REPLACEMENT...'." in result.stderr


def test_cli_every_name_is_a_play(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The location is `--path`: a name that is also a folder is still a
    replacement."""
    (tmp_path / NORMAL_REPL).mkdir()
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_REPL


def test_cli_repeated_replacement_tried_once(runner, tmp_path: Path) -> None:
    """A replacement listed again, in any case, is tried once, where it first
    stands."""
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    p = _write(gp, tmp_path)
    result = runner.invoke(
        replace_play,
        ["OLDRUN", NORMAL_REPL, NORMAL_REPL.lower(), NORMAL_TARGET, "--path", str(p)],
    )
    assert result.exit_code == 0
    assert result.stdout == (  # one SKIP: the repeat is not tried again
        f"SKIP {p}: '{NORMAL_REPL}' already in the game plan\n"
        f"OK   {p}: 'OLDRUN' (RL) replaced with '{NORMAL_TARGET}' (RL) [1-1]\n"
    )


def test_cli_repeated_replacement_named_once_in_the_tally(
    runner, tmp_path: Path
) -> None:
    _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    result = runner.invoke(
        replace_play,
        ["OLDRUN", NORMAL_REPL, NORMAL_REPL.lower(), "--path", str(tmp_path)],
    )
    assert result.stdout.endswith(
        f"\n'OLDRUN' -> '{NORMAL_REPL}': replaced 1 instance(s) in "
        "1 game plan(s), 0 failed, 0 not replaced\n"
    )


def test_cli_every_replacement_must_be_in_pool(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, MISSING, "--path", str(p)]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL Replacement play '{MISSING}' is not in the play pool.\n"
    )
    assert p.read_bytes() == original


def test_cli_no_quiet_option(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(p), "-q"]
    )
    assert result.exit_code == 2


def test_cli_replacement_not_in_pool_exit_2(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", MISSING, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL Replacement play '{MISSING}' is not in the play pool.\n"
    )


def test_cli_replacement_case_insensitive(runner, tmp_path: Path) -> None:
    p = _target_plan(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL.lower(), "--path", str(p)]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_REPL


# ── command: single file ──────────────────────────────────────────────────────


def _copy_offense(tmp_path: Path, name: str = "offense.pln") -> Path:
    dst = tmp_path / name
    shutil.copy2(GP_OFFENSE, dst)
    return dst


def _target_plan(folder: Path, name: str = "offense.pln") -> Path:
    """A made-up offense gameplan holding only the target, at 1-1 as in
    offense.pln. offense.pln holds every offense play in the test pool, so a
    swap into a copy of it is always refused as already in the game plan."""
    gp = _offense_gameplan(normals={0: offense_normal(NORMAL_TARGET)})
    return _write(gp, folder, name)


def test_cli_single_file_replaces_normal(runner, tmp_path: Path) -> None:
    """Target in one slot: swapped; bystander kept."""
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(OTHER_RM, 0x09)}
    )
    p = _write(gp, tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert _name(rt.normal_plays[0]) == NORMAL_REPL
    assert _name(rt.normal_plays[1]) == OTHER_RM  # untouched
    assert result.stdout == (
        f"OK   {p}: 'OLDRUN' (RL) replaced with '{NORMAL_REPL}' (RM) [1-1]\n"
    )


def test_cli_play_in_several_slots_not_replaced(runner, tmp_path: Path) -> None:
    """One replacement in several slots is a duplicate, which fails check."""
    old = offense_normal("OLDRUN")
    p = _write(_offense_gameplan(normals={0: old, 5: old, 63: old}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 1
    assert result.stdout == (
        f"SKIP {p}: '{NORMAL_REPL}' fails check: Duplicate play '{NORMAL_REPL}' "
        "at slot 6 (2-2) (already at slot 1 (1-1))\n"
        f"SKIP {p}: '{NORMAL_REPL}' fails check: Duplicate play '{NORMAL_REPL}' "
        "at slot 64 (16-4) (already at slot 1 (1-1))\n"
        f"{p}: 'OLDRUN' not replaced, no valid replacement\n"
    )
    assert p.read_bytes() == original


def test_cli_output_uses_game_names_without_league_labels(
    runner, league: Path, tmp_path: Path
) -> None:
    (league / "league.toml").write_text(
        league_toml(PLAYS, labels=False), encoding="utf-8"
    )
    old = offense_normal("OLDRUN")
    p = _write(_offense_gameplan(normals={0: old}), tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {p}: 'OLDRUN' (Run Left) replaced with '{NORMAL_REPL}' "
        "(Run Middle) [1-1]\n"
    )


def test_cli_single_file_replaces_special(runner, tmp_path: Path) -> None:
    gp = _offense_gameplan(
        specials={1: offense_special("OLDFG", 1), 2: offense_special("KEEPKICK", 2)}
    )
    p = _write(gp, tmp_path)
    result = runner.invoke(replace_play, ["OLDFG", SPECIAL_REPL, "--path", str(p)])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert _name(rt.custom_special_plays[0]) == SPECIAL_REPL
    assert _name(rt.custom_special_plays[1]) == "KEEPKICK"  # untouched
    assert result.stdout == (
        f"OK   {p}: Replaced 'OLDFG' (Field Goal/PAT) in special slot 1 "
        f"with '{SPECIAL_REPL}' (Field Goal/PAT)\n"
    )


def test_cli_single_file_target_case_insensitive(runner, tmp_path: Path) -> None:
    p = _target_plan(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET.lower(), NORMAL_REPL, "--path", str(p)]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_REPL


def test_cli_single_file_miss_exit_1(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, [MISSING, NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 1
    assert result.stdout == f"{p}: '{MISSING}' not found\n"
    assert p.read_bytes() == original  # untouched


# ── command: backup replacements and league rules ─────────────────────────────


def test_cli_backup_used_when_first_already_in_plan(runner, tmp_path: Path) -> None:
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    p = _write(gp, tmp_path)
    result = runner.invoke(
        replace_play, ["OLDRUN", NORMAL_REPL, NORMAL_TARGET, "--path", str(p)]
    )
    assert result.exit_code == 0
    assert result.stdout == (
        f"SKIP {p}: '{NORMAL_REPL}' already in the game plan\n"
        f"OK   {p}: 'OLDRUN' (RL) replaced with '{NORMAL_TARGET}' (RL) [1-1]\n"
    )
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL_TARGET


def test_cli_backup_used_when_first_breaks_rule(
    runner, league: Path, tmp_path: Path
) -> None:
    (league / "gameplan.toml").write_text("[offense.RM]\nmax_count = 0\n", "utf-8")
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    result = runner.invoke(
        replace_play, ["OLDRUN", NORMAL_REPL, NORMAL_TARGET, "--path", str(p)]
    )
    assert result.exit_code == 0
    assert result.stdout == (
        f"SKIP {p}: '{NORMAL_REPL}' fails check: [Run Middle] Offensive "
        "category 'Run Middle' has 1 plays; allows at most 0.\n"
        f"OK   {p}: 'OLDRUN' (RL) replaced with '{NORMAL_TARGET}' (RL) [1-1]\n"
    )


def test_cli_rollout_cap_uses_the_play_file(
    runner, league: Path, tmp_path: Path
) -> None:
    """The rollout flag comes from the play file: AF1AwagR's QB rolls out."""
    (league / "gameplan.toml").write_text(
        "[offense.PSL]\nmax_rollouts_count = 0\n", "utf-8"
    )
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    result = runner.invoke(
        replace_play, ["OLDRUN", "AF1AwagR", "JJ1AarrX", "--path", str(p)]
    )
    assert result.exit_code == 0
    assert result.stdout == (
        f"SKIP {p}: 'AF1AwagR' fails check: [Pass Short Left] Offensive "
        "category 'Pass Short Left' has 1 of 1 rollouts; allows at most 0.\n"
        f"OK   {p}: 'OLDRUN' (RL) replaced with 'JJ1AarrX' (PSL) [1-1]\n"
    )


# A swap across categories moves one play from the losing category to the
# gaining one; both counts are checked against the rules afterwards.
PSL_TARGET = "AF1AwagR"  # offense Pass Short Left, in the pool
PSL_OTHER = "JJ1AarrX"  # a second Pass Short Left play in the pool
PML_REPL = "AT4Aqp01"  # offense Pass Medium Left, in the pool
PML_OTHER = "AT4AcrsB"  # a second Pass Medium Left play in the pool


def _psl_pml_plan(tmp_path: Path) -> Path:
    """Two Pass Short Left plays and one Pass Medium Left, all in the pool, the
    target at 1-1. Two PSL plays because min_count is not checked on a category
    the swap empties."""
    gp = _offense_gameplan(
        normals={
            0: offense_normal(PSL_TARGET, 0x07),
            1: offense_normal(PSL_OTHER, 0x07),
            2: offense_normal(PML_OTHER, 0x17),
        }
    )
    return _write(gp, tmp_path)


def test_cli_cross_category_swap_within_limits(
    runner, league: Path, tmp_path: Path
) -> None:
    """PSL -> PML lands the losing category on its min_count and the gaining one
    on its max_count, so the plan still passes check and the swap is made."""
    (league / "gameplan.toml").write_text(
        "[offense.PSL]\nmin_count = 1\n[offense.PML]\nmax_count = 2\n", "utf-8"
    )
    p = _psl_pml_plan(tmp_path)
    result = runner.invoke(replace_play, [PSL_TARGET, PML_REPL, "--path", str(p)])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {p}: '{PSL_TARGET}' (PSL) replaced with '{PML_REPL}' (PML) [1-1]\n"
    )
    rt = read_gameplan(str(p))
    assert [_name(rt.normal_plays[i]) for i in range(3)] == [
        PML_REPL,
        PSL_OTHER,
        PML_OTHER,
    ]


def test_cli_cross_category_swap_leaves_losing_category_short(
    runner, league: Path, tmp_path: Path
) -> None:
    """PSL -> PML with PSL already at its min_count: the swap would leave PSL one
    short, so the plan fails check and nothing is replaced."""
    (league / "gameplan.toml").write_text(
        "[offense.PSL]\nmin_count = 2\n[offense.PML]\nmax_count = 2\n", "utf-8"
    )
    p = _psl_pml_plan(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, [PSL_TARGET, PML_REPL, "--path", str(p)])
    assert result.exit_code == 1
    assert result.stdout == (
        f"SKIP {p}: '{PML_REPL}' fails check: [Pass Short Left] Offensive "
        "category 'Pass Short Left' has 1 plays; requires at least 2.\n"
        f"{p}: '{PSL_TARGET}' not replaced, no valid replacement\n"
    )
    assert p.read_bytes() == original


def test_cli_no_valid_replacement_single_file(
    runner, league: Path, tmp_path: Path
) -> None:
    (league / "gameplan.toml").write_text("[offense.RM]\nmax_count = 0\n", "utf-8")
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_TARGET)}
    )
    p = _write(gp, tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        replace_play, ["OLDRUN", NORMAL_REPL, NORMAL_TARGET, "--path", str(p)]
    )
    assert result.exit_code == 1
    assert result.stdout == (
        f"SKIP {p}: '{NORMAL_REPL}' fails check: [Run Middle] Offensive "
        "category 'Run Middle' has 1 plays; allows at most 0.\n"
        f"SKIP {p}: '{NORMAL_TARGET}' already in the game plan\n"
        f"{p}: 'OLDRUN' not replaced, no valid replacement\n"
    )
    assert p.read_bytes() == original


def test_cli_directory_counts_not_replaced(
    runner, league: Path, tmp_path: Path
) -> None:
    (league / "gameplan.toml").write_text("[offense.RM]\nmax_count = 0\n", "utf-8")
    _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path, "a.pln")
    full = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_TARGET)}
    )
    _write(full, tmp_path, "b.pln")
    result = runner.invoke(
        replace_play, ["OLDRUN", NORMAL_REPL, NORMAL_TARGET, "--path", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert result.stdout.endswith(
        f"\n'OLDRUN' -> '{NORMAL_REPL}', '{NORMAL_TARGET}': replaced 1 instance(s) "
        "in 1 game plan(s), 0 failed, 1 not replaced\n"
    )
    assert _name(read_gameplan(str(tmp_path / "a.pln")).normal_plays[0]) == (
        NORMAL_TARGET
    )


def test_cli_refused_later_replacement_names_it(runner, tmp_path: Path) -> None:
    gp = _offense_gameplan(
        normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)}
    )
    p = _write(gp, tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        replace_play,
        ["OLDRUN", NORMAL_REPL, DEFENSE_REPL, NORMAL_TARGET, "--path", str(p)],
    )
    assert result.exit_code == 2
    assert result.stdout == f"SKIP {p}: '{NORMAL_REPL}' already in the game plan\n"
    assert result.stderr == (
        f"FAIL {p}: '{DEFENSE_REPL}' does not fit: Normal slot 0: play has "
        "defensive play_category=0x92, but profile_type is OFFENSE.\n"
    )
    assert p.read_bytes() == original


def test_cli_wildcard_path_works_like_a_folder(runner, tmp_path: Path) -> None:
    """A tally, and a matched plan without the play stays silent."""
    _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path, "a.pln")
    _write(_offense_gameplan(), tmp_path, "b.pln")
    pattern = str(tmp_path / "*.pln")
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", pattern])
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {tmp_path / 'a.pln'}: 'OLDRUN' (RL) replaced with '{NORMAL_REPL}' "
        "(RM) [1-1]\n"
        "\n"
        f"'OLDRUN' -> '{NORMAL_REPL}': replaced 1 instance(s) in 1 game plan(s), "
        "0 failed, 0 not replaced\n"
    )


def test_cli_bad_rules_file_exit_2(runner, league: Path, tmp_path: Path) -> None:
    (league / "gameplan.toml").write_text("not = valid = toml", encoding="utf-8")
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'gameplan.toml'}: {toml_error('not = valid = toml')}\n"
    )
    assert p.read_bytes() == original


# ── command: no backups ───────────────────────────────────────────────────────


def test_writes_no_backup(runner, tmp_path: Path) -> None:
    p = _target_plan(tmp_path)
    result = runner.invoke(replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []
    assert result.stdout == (  # no "<file>: backup <name>" line any more
        f"OK   {p}: '{NORMAL_TARGET}' (RL) replaced with '{NORMAL_REPL}' (RM) [1-1]\n"
    )


def test_no_backup_option_removed(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(p), "--no-backup"]
    )
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── command: directory / tree ─────────────────────────────────────────────────


def test_cli_directory_updates_matching_files(runner, tmp_path: Path) -> None:
    _target_plan(tmp_path, "off1.pln")
    _target_plan(tmp_path, "off2.pln")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "replaced 2 instance(s) in 2 game plan(s), 0 failed" in result.stdout
    for name in ("off1.pln", "off2.pln"):
        assert _name(read_gameplan(str(tmp_path / name)).normal_plays[0]) == NORMAL_REPL


def test_cli_directory_leaves_other_side_untouched(runner, tmp_path: Path) -> None:
    _target_plan(tmp_path)
    def_pln = tmp_path / "defense.pln"
    shutil.copy2(GP_DEFENSE, def_pln)
    original_def = def_pln.read_bytes()
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "in 1 game plan(s), 0 failed" in result.stdout
    assert def_pln.read_bytes() == original_def  # no OR45RL01 there → untouched


def test_cli_directory_no_hits_exit_1(runner, tmp_path: Path) -> None:
    _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play, [MISSING, NORMAL_REPL, "--path", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "replaced 0 instance(s) in 0 game plan(s), 0 failed" in result.stdout


def test_cli_recursive_replaces_in_subdir(runner, tmp_path: Path) -> None:
    sub = tmp_path / "team_a"
    sub.mkdir()
    _target_plan(sub)
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(tmp_path), "-r"]
    )
    assert result.exit_code == 0
    assert _name(read_gameplan(str(sub / "offense.pln")).normal_plays[0]) == NORMAL_REPL


# ── command: validation / errors (target left untouched) ──────────────────────


def test_cli_replacement_special_for_normal_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", SPECIAL_REPL, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {p}: Normal slot 0 contains a special-teams play "
        "(special_category=1); only non-special-teams plays allowed in normal "
        "slots.\n"
    )
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_replacement_wrong_side_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDRUN", DEFENSE_REPL, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {p}: Normal slot 0: play has defensive play_category=0x92, "
        "but profile_type is OFFENSE.\n"
    )
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_replacement_wrong_special_category_fails(runner, tmp_path: Path) -> None:
    p = _write(_offense_gameplan(specials={1: offense_special("OLDFG", 1)}), tmp_path)
    original = p.read_bytes()
    result = runner.invoke(replace_play, ["OLDFG", KICKOFF_REPL, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {p}: Special category 1: custom play has special_category=2.\n"
    )
    assert list(tmp_path.glob("*.bak")) == [] and p.read_bytes() == original


def test_cli_missing_path_exit_2(runner, tmp_path: Path) -> None:
    missing = tmp_path / "nope.pln"
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(missing)]
    )
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""  # a single path that failed: no tally


def test_cli_malformed_pln_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(bad)]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
    )


def test_cli_invalid_play_path_exit_2(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "missing"), encoding="utf-8"
    )
    p = _copy_offense(tmp_path)
    result = runner.invoke(replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(p)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'missing'}: {PATH_NOT_FOUND} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


def test_cli_play_path_option_removed(runner, tmp_path: Path) -> None:
    p = _copy_offense(tmp_path)
    result = runner.invoke(
        replace_play,
        [NORMAL_TARGET, NORMAL_REPL, "--path", str(p), "--play-path", str(PLAYS)],
    )
    assert result.exit_code == 2
    assert "No such option" in result.stderr


def test_cli_continues_past_failed_file(runner, tmp_path: Path) -> None:
    _target_plan(tmp_path)
    (tmp_path / "broken.pln").write_bytes(b"\x00\x01\x02")
    result = runner.invoke(
        replace_play, [NORMAL_TARGET, NORMAL_REPL, "--path", str(tmp_path)]
    )
    assert result.exit_code == 2
    assert "replaced 1 instance(s) in 1 game plan(s), 1 failed" in result.stdout


# ── your team's game plans ────────────────────────────────────────────────────

# Denver's four game plans, named after their keys, in .lg2 order.
TEAM_PLANS = ("OFF1.pln", "DEF1.pln", "OFF2.pln", "DEF2.pln")
TALLY = (
    "'OLDRUN' -> '{repl}': replaced {n} instance(s) in {n} game plan(s), "
    "{failed} failed, 0 not replaced"
)


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def team_league(
    league: Path, tmp_path: Path, names: tuple[str, ...] = TEAM_PLANS, **settings
) -> Path:
    """The league's .lg2 and .lge in `tmp_path/lg2`, Denver's four game plans
    named `names`, `path` and `settings` set; returns Denver's league folder,
    made but empty."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    off1, def1, off2, def2 = names
    record = team(
        ("o1.prf", off1), ("d1.prf", def1), ("o2.prf", off2), ("d2.prf", def2)
    )
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(record)
    (lg2_dir / f"{LEAGUE}.lge").write_bytes(lge(TEAM_NAMES[0]))
    set_league(league, path=lg2_dir, **settings)
    folder = lg2_dir / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    return folder


def write_team_plans(folder: Path, names: tuple[str, ...] = TEAM_PLANS) -> None:
    """OLDRUN in each offense game plan; the defense ones lack it."""
    for name in dict.fromkeys(names):
        if name.startswith("OFF"):
            _write(
                _offense_gameplan(normals={0: offense_normal("OLDRUN")}), folder, name
            )
        else:
            shutil.copy2(GP_DEFENSE, folder / name)


def replaced_line(path: Path) -> str:
    return f"OK   {path}: 'OLDRUN' (RL) replaced with '{NORMAL_REPL}' (RM) [1-1]\n"


def test_cli_default_scope_is_your_teams_game_plans(
    runner, league: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --path: your team's four in .lg2 order, misses silent, then the
    tally; a game plan in the current folder is not touched."""
    folder = team_league(league, tmp_path, team="Denver")
    write_team_plans(folder)
    here = tmp_path / "here"
    here.mkdir()
    draft = _write(_offense_gameplan(normals={0: offense_normal("OLDRUN")}), here)
    monkeypatch.chdir(here)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL])
    assert result.exit_code == 0
    assert result.stdout == (
        replaced_line(folder / "OFF1.pln")
        + replaced_line(folder / "OFF2.pln")
        + "\n"
        + TALLY.format(repl=NORMAL_REPL, n=2, failed=0)
        + "\n"
    )
    assert _name(read_gameplan(draft).normal_plays[0]) == "OLDRUN"


def test_cli_shared_game_plan_once(runner, league: Path, tmp_path: Path) -> None:
    names = ("OFF.pln", "DEF.pln", "OFF.pln", "DEF.pln")
    folder = team_league(league, tmp_path, names, team="Denver")
    write_team_plans(folder, names)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL])
    assert result.exit_code == 0
    assert result.stdout == (
        replaced_line(folder / "OFF.pln")
        + "\n"
        + TALLY.format(repl=NORMAL_REPL, n=1, failed=0)
        + "\n"
    )


@pytest.mark.parametrize(("key", "replaced"), [("off2", True), ("DEF1", False)])
def test_cli_key_is_one_file(
    runner, league: Path, tmp_path: Path, key: str, replaced: bool
) -> None:
    """A key is one game plan: its line, no tally."""
    folder = team_league(league, tmp_path, team="Denver")
    write_team_plans(folder)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--path", key])
    if replaced:
        assert result.exit_code == 0
        assert result.stdout == replaced_line(folder / "OFF2.pln")
    else:
        assert result.exit_code == 1
        assert result.stdout == f"{folder / 'DEF1.pln'}: 'OLDRUN' not found\n"
    assert _name(read_gameplan(folder / "OFF1.pln").normal_plays[0]) == "OLDRUN"


def test_cli_league_location_missing_game_plan_counts_as_failed(
    runner, league: Path, tmp_path: Path
) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    write_team_plans(folder)
    (folder / "OFF2.pln").unlink()
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL])
    assert result.exit_code == 2
    assert result.stderr.endswith(f"FAIL {folder / 'OFF2.pln'}: {FILE_NOT_FOUND}\n")
    assert result.stdout == (
        replaced_line(folder / "OFF1.pln")
        + "\n"
        + TALLY.format(repl=NORMAL_REPL, n=1, failed=1)
        + "\n"
    )


def test_cli_ppp_path_with_no_game_plans(runner, league: Path, tmp_path: Path) -> None:
    """The one scope line, a WARN: nothing replaced, so exit 1."""
    mine = tmp_path / "mine"
    mine.mkdir()
    team_league(league, tmp_path, team="Denver", ppp_path=mine)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL])
    assert result.exit_code == 1
    assert result.stderr.endswith(
        f"WARN {mine}: No Denver game plans. The league file names "
        f"{', '.join(TEAM_PLANS)}.\n"
    )
    assert result.stdout == "\n" + TALLY.format(repl=NORMAL_REPL, n=0, failed=0) + "\n"


def test_cli_team_typo_shows_before_the_pool(
    runner, league: Path, tmp_path: Path
) -> None:
    """The team is resolved before the pool is read: no pool WARN lines."""
    team_league(league, tmp_path, team="Denver")
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, "--team", "Denvr"])
    assert result.exit_code == 2
    assert "WARN " not in result.stderr
    assert result.stderr.endswith(
        "Error: Invalid value for '--team': no team named 'Denvr'. Teams: "
        "Denver Broncos.\n"
    )


def test_cli_team_with_a_path_is_a_usage_error(runner, tmp_path: Path) -> None:
    p = _target_plan(tmp_path)
    result = runner.invoke(
        replace_play,
        [NORMAL_TARGET, NORMAL_REPL, "--path", str(p), "--team", "Denver"],
    )
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires --path to be a game plan key (off1, def1, off2 or "
        "def2) or left out.\n"
    )
