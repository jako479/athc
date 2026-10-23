"""Unit tests for ProfileWriter — selective field copy between profiles."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from athc.fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    GameState,
    Profile,
    SubstitutionPair,
    SubstitutionSettings,
    read_profile,
    write_profile,
)
from athc.profile.writer import ProfileTypeMismatchError, ProfileWriter
from tests.unit.profile.conftest import DATA

OFF1 = DATA / "TST-OFF1.prf"
DEF1 = DATA / "TST-DEF1.prf"


def _copy_prf(src: Path, tmp_path: Path, *, name: str) -> Path:
    dest = tmp_path / name
    shutil.copy2(src, dest)
    return dest


def _write_source(
    profile: Profile, tmp_path: Path, *, name: str = "source.prf"
) -> Path:
    dest = tmp_path / name
    write_profile(profile, str(dest))
    return dest


def _stop_clock_vector(path: Path) -> tuple[bool, ...]:
    return tuple(s.stop_clock for s in read_profile(str(path)).situations)


def _distinct_weights(base: CategoryWeights) -> CategoryWeights:
    """`base` with every category and every weight changed."""
    return CategoryWeights(
        (base.play_category1 + 1) % 0x1B,
        (base.weight1 + 1) % 11,
        (base.play_category2 + 1) % 0x1B,
        (base.weight2 + 1) % 11,
        (base.play_category3 + 1) % 0x1B,
        (base.weight3 + 1) % 11,
    )


def _other_range(value: int) -> int:
    return value + 1 if value < 50 else value - 1


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


def _differing(profile: Profile) -> Profile:
    """`profile` with every part a copy can take changed: the stop clock and
    weights of every situation, the PAT weights, the substitutions, the field
    goal range and the audibles flag. With this as the source, a copy that takes
    more than asked shows in the whole-result check."""
    situations = tuple(
        replace(
            s,
            stop_clock=not s.stop_clock,
            category_weights=_distinct_weights(s.category_weights),
        )
        for s in profile.situations
    )
    pats = tuple(
        replace(p, category_weights=_distinct_weights(p.category_weights))
        for p in profile.pat_situations
    )
    return replace(
        profile,
        situations=situations,
        pat_situations=pats,
        substitutions=_custom_subs(),
        field_goal_range=_other_range(profile.field_goal_range),
        use_audibles=not profile.use_audibles,
    )


def _source(src: Path, tmp_path: Path) -> Path:
    """A source profile differing from `src` in every copyable part."""
    return _write_source(_differing(read_profile(str(src))), tmp_path)


def _stamp_matching(
    profile: Profile, *, predicate: Callable[[GameState], bool], marker: CategoryWeights
) -> Profile:
    """`profile` with `marker` as the weights of every situation `predicate` matches."""
    sits = tuple(
        replace(s, category_weights=marker) if predicate(state) else s
        for _, state, s in profile.iter_situations()
    )
    return replace(profile, situations=sits)


def _is_fourth(state: GameState) -> bool:
    return state.down == Down.FOURTH


def _is_goal_line(state: GameState) -> bool:
    return state.field_position in (
        FieldPosition.INSIDE_DEF_5,
        FieldPosition.INSIDE_OFF_5,
    )


def _with_stop_clock(target: Profile, source: Profile) -> Profile:
    """`target` with `source`'s stop clock on every situation."""
    return replace(
        target,
        situations=tuple(
            replace(t, stop_clock=s.stop_clock)
            for t, s in zip(target.situations, source.situations, strict=True)
        ),
    )


def _with_situations(
    target: Profile, source: Profile, predicate: Callable[[GameState], bool]
) -> Profile:
    """`target` with `source`'s whole situation wherever `predicate` matches."""
    return replace(
        target,
        situations=tuple(
            s if predicate(state) else t
            for (_, state, t), s in zip(
                target.iter_situations(), source.situations, strict=True
            )
        ),
    )


# ── stop_clock ────────────────────────────────────────────────────────────────


def test_copy_stop_clock_replaces_every_situation(tmp_path: Path) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert _stop_clock_vector(source) == tuple(s.stop_clock for s in result.situations)
    assert result == _with_stop_clock(original, read_profile(str(source)))


def test_copy_stop_clock_idempotent_when_source_equals_target(tmp_path: Path) -> None:
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    original = _stop_clock_vector(target)
    original_profile = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert tuple(s.stop_clock for s in result.situations) == original
    assert result == original_profile


def test_copy_no_flags_returns_target_unchanged(tmp_path: Path) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply()
    assert result == original


def test_copy_stop_clock_works_on_defense(tmp_path: Path) -> None:
    source = _source(DEF1, tmp_path)
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert _stop_clock_vector(source) == tuple(s.stop_clock for s in result.situations)
    assert result == _with_stop_clock(original, read_profile(str(source)))


# ── sub_percent ───────────────────────────────────────────────────────────────


def test_copy_sub_percent_replaces_only_substitutions(tmp_path: Path) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_sub_percent=True)
    assert result == replace(original, substitutions=_custom_subs())


# ── field_goal_range ──────────────────────────────────────────────────────────


def test_copy_field_goal_range_replaces_only_the_range(tmp_path: Path) -> None:
    new_range = _other_range(read_profile(str(OFF1)).field_goal_range)
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_field_goal_range=True)
    assert result == replace(original, field_goal_range=new_range)


# ── fourth_down ───────────────────────────────────────────────────────────────


def test_copy_fourth_down_copies_only_fourth_down_situations(tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_matching(_differing(base), predicate=_is_fourth, marker=marker),
        tmp_path,
    )
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_fourth_down=True)
    for (_, state, before), after in zip(
        original.iter_situations(), result.situations, strict=True
    ):
        if state.down == Down.FOURTH:
            assert (
                after.category_weights == marker
                and after.stop_clock != before.stop_clock
            )
        else:
            assert (
                after.category_weights == before.category_weights
                and after.stop_clock == before.stop_clock
            )
    assert result == _with_situations(original, read_profile(str(source)), _is_fourth)


def test_copy_fourth_down_works_on_defense(tmp_path: Path) -> None:
    base = read_profile(str(DEF1))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_matching(_differing(base), predicate=_is_fourth, marker=marker),
        tmp_path,
    )
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_fourth_down=True)
    affected = [s for _, state, s in result.iter_situations() if _is_fourth(state)]
    assert affected and all(s.category_weights == marker for s in affected)
    assert result == _with_situations(original, read_profile(str(source)), _is_fourth)


# ── goal_line ─────────────────────────────────────────────────────────────────


def test_copy_goal_line_copies_only_goal_line_situations(tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_matching(_differing(base), predicate=_is_goal_line, marker=marker),
        tmp_path,
    )
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_goal_line=True)
    for (_, state, before), after in zip(
        original.iter_situations(), result.situations, strict=True
    ):
        expected = marker if _is_goal_line(state) else before.category_weights
        assert after.category_weights == expected
    assert result == _with_situations(
        original, read_profile(str(source)), _is_goal_line
    )


# Per docs/formats/prf.md 2.3.4, over the 20 (minutes, down) blocks of 126: 4th
# down is 5 blocks (630); the goal line is 14 cells inside the DEF 5 plus 28
# inside the OFF 5 per block (840); the two share 42 cells in each of the 5
# 4th-down blocks (210), so both flags copy 630 + 840 - 210.
@pytest.mark.parametrize(
    ("flags", "copied"),
    [
        (("copy_fourth_down",), 630),
        (("copy_goal_line",), 840),
        (("copy_fourth_down", "copy_goal_line"), 1260),
    ],
    ids=["fourth_down", "goal_line", "both"],
)
def test_copy_fourth_down_and_goal_line_slot_counts(
    tmp_path: Path, flags: tuple[str, ...], copied: int
) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(**dict.fromkeys(flags, True))
    changed = sum(
        after != before
        for before, after in zip(original.situations, result.situations, strict=True)
    )
    assert changed == copied


# ── combinations ──────────────────────────────────────────────────────────────


def test_combined_flags_apply_each_independently(tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    new_range = _other_range(base.field_goal_range)
    marker = _distinct_weights(base.situations[0].category_weights)
    stamped = _stamp_matching(_differing(base), predicate=_is_fourth, marker=marker)
    source = _write_source(stamped, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(
        copy_sub_percent=True, copy_field_goal_range=True, copy_fourth_down=True
    )
    assert result.substitutions == _custom_subs()
    assert result.field_goal_range == new_range
    assert all(
        s.category_weights == marker
        for _, state, s in result.iter_situations()
        if _is_fourth(state)
    )
    non_fourth_changed = [
        a
        for (_, state, a), o in zip(
            result.iter_situations(), original.situations, strict=True
        )
        if not _is_fourth(state) and a.category_weights != o.category_weights
    ]
    assert non_fourth_changed == []
    assert result == replace(
        _with_situations(original, stamped, _is_fourth),
        substitutions=_custom_subs(),
        field_goal_range=new_range,
    )


def test_fourth_down_and_stop_clock_combine_cleanly(tmp_path: Path) -> None:
    base = read_profile(str(OFF1))
    marker = _distinct_weights(base.situations[0].category_weights)
    stamped = _stamp_matching(_differing(base), predicate=_is_fourth, marker=marker)
    source = _write_source(stamped, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(
        copy_stop_clock=True, copy_fourth_down=True
    )
    for (_, state, before), after in zip(
        original.iter_situations(), result.situations, strict=True
    ):
        assert after.stop_clock != before.stop_clock
        if _is_fourth(state):
            assert after.category_weights == marker
        else:
            assert after.category_weights == before.category_weights
    assert result == _with_situations(
        _with_stop_clock(original, stamped), stamped, _is_fourth
    )


# ── pat_logic ─────────────────────────────────────────────────────────────────


def test_copy_pat_logic_replaces_only_the_pat_table(tmp_path: Path) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_pat_logic=True)
    assert result == replace(
        original, pat_situations=read_profile(str(source)).pat_situations
    )


def test_copy_pat_logic_works_on_defense(tmp_path: Path) -> None:
    source = _source(DEF1, tmp_path)
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_pat_logic=True)
    assert result.pat_situations == read_profile(str(source)).pat_situations
    assert result == replace(
        original, pat_situations=read_profile(str(source)).pat_situations
    )


def test_copy_without_pat_logic_leaves_pat_situations_alone(tmp_path: Path) -> None:
    source = _source(OFF1, tmp_path)
    target = _copy_prf(OFF1, tmp_path, name="target.prf")
    original = read_profile(str(target))
    result = ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert result.pat_situations == original.pat_situations
    assert result == _with_stop_clock(original, read_profile(str(source)))


# ── mismatched types ──────────────────────────────────────────────────────────


def test_mismatch_raises_before_any_copy(tmp_path: Path) -> None:
    """The side check comes first, so it raises even with no copy asked for."""
    source = _copy_prf(OFF1, tmp_path, name="source.prf")
    target = _copy_prf(DEF1, tmp_path, name="target.prf")
    with pytest.raises(ProfileTypeMismatchError) as exc_info:
        ProfileWriter(source, target).apply()
    assert exc_info.value.source_type.name == "OFFENSE"
    assert exc_info.value.target_type.name == "DEFENSE"
    assert str(exc_info.value) == (
        f"{target}: Cannot copy from {source} (offense) to a defense profile."
    )
