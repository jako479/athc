# Gameplan Special Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every play category is a first-class citizen of the `.pln` model and the gameplan rules: the two clock categories join the enum, `GamePlan` holds one typed slot per special category 1-12, the five categories without a league abbreviation can be given rules, and an unrecognized category in a `.pln` is a reader error.

**Architecture:** `fbpro98_play` gains `RUN_CLOCK` / `STOP_CLOCK`. `fbpro98_gameplan.GamePlan` replaces the 20-entry interleaved `special_plays` plus `clock_plays` with twelve `SpecialSlot(custom, stock)` records, and the reader resolves every play ref's category. The `gameplan` rules loader resolves section labels per side over the whole enum; validators and CLI read slots by category number. The profile tool needs no code change.

**Tech Stack:** Python 3.12+, dataclasses, pytest, ruff, pyright; `uv run` for every command.

**Spec:** `docs/superpowers/specs/2026-10-06-gameplan-special-slots-design.md`

## Global Constraints

- Python 3.12 syntax only (pyright is pinned to 3.12; the `.venv` runs 3.13).
- Ruff format at 88 columns, double quotes; `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` and `uv run pytest` (coverage floor 92%) all green before the branch is done.
- Every text file is UTF-8 with CRLF line endings and a final newline; after editing with a tool that writes LF, run `sed -i 's/\r$//; s/$/\r/' <file>`.
- Never edit `.pln` fixtures or `expected/*.txt`; error-path tests mutate a copy of the real bytes in `tmp_path`.
- Commit messages: one line, prefixed with the owning tool (`fbpro98_play:`, `fbpro98_gameplan:`, `gameplan:`), no body, no attribution trailers, no mention of Claude or AI tools.
- Comments explain why, not what. No new dependencies.
- Run commands from the worktree root `C:\Users\Brian\Projects\PNFL\athc\.claude\worktrees\gameplan-special-slots`, one command per call.
- New CHANGELOG entries go at the top of the `## athc` list.

## Review Focus

Inputs the spec implies but no task's tests would otherwise exercise; each line's test is pinned to the owning task.

1. A `.pln` whose clock slot holds a custom play (stock_flag 0 at offset 84): the reader must raise `ValueError` from the model ("stock-only"), not crash. Task 2, `test_reader.py::test_custom_play_in_clock_slot_raises`.
2. A rules file naming `"Stop Clock"` in `required_special_categories` and a defense plan: the validator must flag it (defense has no clock plays) instead of indexing past the tuple. Task 3, `test_validators.py::test_required_clock_category_fires_on_defense`.
3. `[defense."User Specific"]` must load as a defense rule while `[offense."User Specific"]` loads as an offense rule; the two sides share that label. Task 4, `test_rules.py::test_user_specific_label_loads_on_each_side`.
4. `set-specials` fed a `.ply` whose header says special category 11: must report a per-line error, not `IndexError`. Task 2, `tests/unit/gameplan/test_writer.py::test_special_play_without_custom_slot_is_rejected`.
5. `with_custom_special_plays` must leave the clock slots' stock plays untouched (offense plans would otherwise fail their own invariant). Task 2, `test_model.py::test_with_custom_special_plays_preserves_clock_slots`.

---

### Task 1: Clock categories in `SpecialOffensiveCategory`

**Files:**
- Modify: `src/athc/fbpro98_play/model.py:77-89`
- Test: `tests/unit/fbpro98_play/test_model.py`
- Modify: `tests/unit/fbpro98_play/README.md:70-71`

**Interfaces:**
- Consumes: nothing new.
- Produces: `SpecialOffensiveCategory.RUN_CLOCK` (code `0x0B`, short and long `"Run Clock"`) and `SpecialOffensiveCategory.STOP_CLOCK` (code `0x0C`, `"Stop Clock"`); `resolve_category(0x01, 0x0B, 0)` / `(0x01, 0x0C, 0)` return them. Task 2's reader check depends on this.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/fbpro98_play/test_model.py` (after `test_resolve_category_mask_and_unknown`):

```python
def test_clock_categories_are_offense_only():
    assert resolve_category(0x01, 0x0B, 0x00) is SpecialOffensiveCategory.RUN_CLOCK
    assert resolve_category(0x01, 0x0C, 0x00) is SpecialOffensiveCategory.STOP_CLOCK
    assert SpecialOffensiveCategory.RUN_CLOCK.long == "Run Clock"
    assert SpecialOffensiveCategory.STOP_CLOCK.long == "Stop Clock"
    # Defense has no clock plays, so the same bytes on the defense side are unknown.
    assert resolve_category(0x00, 0x0B, 0x00) is UNKNOWN_CATEGORY
    assert resolve_category(0x00, 0x0C, 0x00) is UNKNOWN_CATEGORY
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/fbpro98_play/test_model.py::test_clock_categories_are_offense_only -v`
Expected: FAIL with `AttributeError: RUN_CLOCK`.

- [ ] **Step 3: Add the two members**

In `src/athc/fbpro98_play/model.py`, after `SQUIB_KICK = (0x0A, "Squib Kick", "Squib Kick")` inside `SpecialOffensiveCategory`:

```python
    RUN_CLOCK = (0x0B, "Run Clock", "Run Clock")
    STOP_CLOCK = (0x0C, "Stop Clock", "Stop Clock")
```

Update the class docstring to:

```python
    """Kicking-side special-teams categories, keyed by `special_category`.
    11 and 12 are the clock plays, which exist only on offense."""
```

- [ ] **Step 4: Run the play model tests**

Run: `uv run pytest tests/unit/fbpro98_play -v`
Expected: PASS, including the two parametrized `test_offensive_special_teams_names` cases for the new members.

- [ ] **Step 5: Update the test matrix**

In `tests/unit/fbpro98_play/README.md`, change the row at line 70 to:

```
| `resolve_category` picks side + special table | bytes | offense/defense/special-off/special-def; clock `0x0B`/`0x0C` offense only | `test_resolve_category_picks_side_and_special`, `test_clock_categories_are_offense_only` | ☑ |
```

Then normalize endings: `sed -i 's/\r$//; s/$/\r/' tests/unit/fbpro98_play/README.md`

- [ ] **Step 6: Commit**

```bash
git add src/athc/fbpro98_play/model.py tests/unit/fbpro98_play/test_model.py tests/unit/fbpro98_play/README.md
git commit -m "fbpro98_play: Run Clock and Stop Clock special categories"
```

---

### Task 2: `SpecialSlot` model, reader, writer, and every consumer

The model's shape changes, so this task migrates every consumer in one commit; the suite is red until the last step.

**Files:**
- Modify: `src/athc/fbpro98_gameplan/model.py:86-313`
- Modify: `src/athc/fbpro98_gameplan/__init__.py`
- Modify: `src/athc/fbpro98_gameplan/reader.py:1-110, 159-203, 259-289`
- Modify: `src/athc/fbpro98_gameplan/writer.py:73-118`
- Modify: `src/athc/gameplan/validators.py:308-341`
- Modify: `src/athc/gameplan/writer.py:116-165`
- Modify: `src/athc/cli/gameplan/replace_play.py:65-83`
- Modify: `src/athc/cli/gameplan/set_specials.py:27`
- Test: `tests/unit/fbpro98_gameplan/test_model.py` (rewrite)
- Test: `tests/unit/fbpro98_gameplan/test_reader.py`
- Test: `tests/unit/fbpro98_gameplan/test_writer.py:95-115`
- Test: `tests/unit/gameplan/test_validators.py:62-69, 263-279, 505-517`
- Create: `tests/unit/gameplan/test_writer.py`
- Modify: `tests/unit/gameplan/README.md:86`
- Test: `tests/unit/profile/test_compat.py:51-58, 87-111`
- Test: `tests/integration/test_gameplan_find_play.py:34-66`
- Test: `tests/integration/test_gameplan_replace_play.py:51-57, 100-122`

**Interfaces:**
- Consumes: `resolve_category`, `UNKNOWN_CATEGORY` from `athc.fbpro98_play` (Task 1 makes clock bytes resolve).
- Produces:
  - `SpecialSlot(custom: CustomPlayRef | None = None, stock: StockPlayRef | None = None)`, frozen dataclass, exported from `athc.fbpro98_gameplan`.
  - `GamePlan.NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 12`, `GamePlan.CUSTOM_SPECIAL_CATEGORIES: ClassVar[range] = range(1, 11)`.
  - `GamePlan.special_plays: tuple[SpecialSlot, ...]` (12 entries, index = category - 1); `clock_plays`, `NUMBER_SPECIAL_SLOTS`, `NUMBER_CLOCK_SLOTS` and `stock_special_plays` are gone.
  - `GamePlan.custom_special_plays -> tuple[CustomPlayRef | None, ...]` (10 entries, categories 1-10).
  - `GamePlan.with_custom_special_plays(plays)` unchanged signature; rejects a category outside `CUSTOM_SPECIAL_CATEGORIES` with `ValueError("... must be 1..10")`.
  - Reader raises `InvalidGamePlanError("Unrecognized play category at slot N (...) in PATH")`.

- [ ] **Step 1: Rewrite the model tests**

Replace `tests/unit/fbpro98_gameplan/test_model.py` entirely:

```python
from __future__ import annotations

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)

CLOCK_CATEGORIES = (11, 12)


def _empty_normals() -> tuple[PlayRef | None, ...]:
    return (None,) * GamePlan.NUMBER_NORMAL_PLAYS


def _make_custom(*, special_category: int = 1, play_category: int = 0) -> CustomPlayRef:
    return CustomPlayRef(
        filename="X.PLY",
        play_category=play_category,
        special_category=special_category,
        user_category=0,
    )


def _make_stock(*, special_category: int = 1, play_category: int = 0) -> StockPlayRef:
    return StockPlayRef(
        play_name="X",
        map_offset=0,
        map_size=0,
        play_category=play_category,
        special_category=special_category,
        user_category=0,
    )


def _specials(**slots: SpecialSlot) -> tuple[SpecialSlot, ...]:
    """Twelve empty slots, with `c<N>=SpecialSlot(...)` overriding category N."""
    out = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for key, slot in slots.items():
        out[int(key[1:]) - 1] = slot
    return tuple(out)


def _offense_specials(**slots: SpecialSlot) -> tuple[SpecialSlot, ...]:
    """Like `_specials`, but with the two stock clock plays an offense plan needs."""
    clock = {
        f"c{c}": SpecialSlot(stock=_make_stock(special_category=c, play_category=1))
        for c in CLOCK_CATEGORIES
    }
    return _specials(**{**clock, **slots})  # a test's c11/c12 overrides the default


def _defense(
    normals: tuple[PlayRef | None, ...] | None = None,
    specials: tuple[SpecialSlot, ...] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_specials() if specials is None else specials,
    )


def _offense(
    normals: tuple[PlayRef | None, ...] | None = None,
    specials: tuple[SpecialSlot, ...] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_offense_specials() if specials is None else specials,
    )


# ── slot counts ───────────────────────────────────────────────────────────────


def test_special_plays_has_12_entries():
    assert GamePlan.NUMBER_SPECIAL_CATEGORIES == 12
    assert len(_defense().special_plays) == 12


@pytest.mark.parametrize("count", [11, 13])
def test_special_plays_wrong_length_raises(count: int):
    with pytest.raises(ValueError, match="special_plays must have exactly 12"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(SpecialSlot() for _ in range(count)),
        )


def test_normal_plays_wrong_length_raises():
    with pytest.raises(ValueError, match="normal_plays must have exactly"):
        _defense(normals=(None, None))


# ── clock categories (11-12): stock-only, offense-only ────────────────────────


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_custom_play_in_clock_category_raises(category: int):
    custom = _make_custom(special_category=category, play_category=1)
    with pytest.raises(ValueError, match=f"Special category {category} is stock-only"):
        _offense(specials=_offense_specials(**{f"c{category}": SpecialSlot(custom=custom)}))


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_offense_missing_clock_play_raises(category: int):
    with pytest.raises(ValueError, match=f"require a stock play in special category {category}"):
        _offense(specials=_offense_specials(**{f"c{category}": SpecialSlot()}))


def test_offense_without_any_clock_plays_raises():
    with pytest.raises(ValueError, match="require a stock play in special category 11"):
        _offense(specials=_specials())


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_defense_with_clock_play_raises(category: int):
    stock = _make_stock(special_category=category, play_category=0)
    with pytest.raises(ValueError, match=f"must not have a play in special category {category}"):
        _defense(specials=_specials(**{f"c{category}": SpecialSlot(stock=stock)}))


def test_custom_special_categories_are_1_to_10():
    assert list(GamePlan.CUSTOM_SPECIAL_CATEGORIES) == list(range(1, 11))


# ── slot typing and category alignment ────────────────────────────────────────


def test_stock_in_custom_field_raises():
    bad = SpecialSlot(custom=_make_stock())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="custom must be CustomPlayRef"):
        _defense(specials=_specials(c1=bad))


def test_custom_in_stock_field_raises():
    bad = SpecialSlot(stock=_make_custom())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="stock must be StockPlayRef"):
        _defense(specials=_specials(c1=bad))


def test_custom_category_mismatch_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=5))
    with pytest.raises(ValueError, match="Special category 2: custom play has special_category=5"):
        _defense(specials=_specials(c2=slot))


def test_stock_category_mismatch_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=5))
    with pytest.raises(ValueError, match="Special category 3: stock play has special_category=5"):
        _defense(specials=_specials(c3=slot))


# ── views ─────────────────────────────────────────────────────────────────────


def test_custom_special_plays_has_10_entries():
    assert len(_defense().custom_special_plays) == 10


def test_custom_special_plays_picks_custom_of_categories_1_to_10():
    custom = _make_custom(special_category=1)
    stock = _make_stock(special_category=3)
    gameplan = _defense(
        specials=_specials(c1=SpecialSlot(custom=custom), c3=SpecialSlot(stock=stock))
    )
    assert gameplan.custom_special_plays[0] is custom
    assert all(p is None for p in gameplan.custom_special_plays[1:])
    assert gameplan.special_plays[2].stock is stock


# ── with_custom_special_plays ─────────────────────────────────────────────────


def test_with_custom_special_plays_preserves_stock():
    stock_a = _make_stock(special_category=1)
    stock_b = _make_stock(special_category=2)
    gameplan = _defense(
        specials=_specials(c1=SpecialSlot(stock=stock_a), c2=SpecialSlot(stock=stock_b))
    )
    new_a = _make_custom(special_category=1)
    new_e = _make_custom(special_category=5)

    updated = gameplan.with_custom_special_plays([new_a, None, new_e])

    assert updated.special_plays[0] == SpecialSlot(custom=new_a, stock=stock_a)
    assert updated.special_plays[1] == SpecialSlot(stock=stock_b)
    assert updated.special_plays[4] == SpecialSlot(custom=new_e)


def test_with_custom_special_plays_preserves_clock_slots():
    gameplan = _offense()
    updated = gameplan.with_custom_special_plays([_make_custom(special_category=2, play_category=1)])
    assert updated.special_plays[10] == gameplan.special_plays[10]
    assert updated.special_plays[11] == gameplan.special_plays[11]


def test_with_custom_special_plays_clears_uncovered_customs():
    gameplan = _defense(specials=_specials(c4=SpecialSlot(custom=_make_custom(special_category=4))))
    updated = gameplan.with_custom_special_plays([_make_custom(special_category=2)])
    placed = updated.custom_special_plays
    assert placed[1] is not None and placed[1].special_category == 2
    assert all(p is None for i, p in enumerate(placed) if i != 1)


def test_with_custom_special_plays_order_independent():
    gameplan = _defense()
    a = _make_custom(special_category=3)
    b = _make_custom(special_category=7)
    c = _make_custom(special_category=1)
    assert (
        gameplan.with_custom_special_plays([a, b, c]).custom_special_plays
        == gameplan.with_custom_special_plays([c, b, a]).custom_special_plays
    )


def test_with_custom_special_plays_rejects_stock_via_post_init():
    with pytest.raises(ValueError, match="custom must be CustomPlayRef"):
        _defense().with_custom_special_plays([_make_stock()])  # type: ignore[list-item]


@pytest.mark.parametrize("category", [1, 10])
def test_with_custom_special_plays_accepts_range_ends(category: int):
    updated = _defense().with_custom_special_plays([_make_custom(special_category=category)])
    assert updated.special_plays[category - 1].custom is not None


@pytest.mark.parametrize("category", [0, 11])
def test_with_custom_special_plays_out_of_range_category_raises(category: int):
    with pytest.raises(ValueError, match=r"must be 1\.\.10"):
        _defense().with_custom_special_plays([_make_custom(special_category=category)])


def test_with_custom_special_plays_duplicate_category_raises():
    with pytest.raises(ValueError, match="Two custom special plays target special_category=3"):
        _defense().with_custom_special_plays(
            [_make_custom(special_category=3), _make_custom(special_category=3)]
        )


# ── side-of-ball parity ───────────────────────────────────────────────────────


def test_offensive_play_in_defensive_gameplan_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=1)  # odd = offensive
    with pytest.raises(ValueError, match="Normal slot 0:.*profile_type is DEFENSE"):
        _defense(normals=tuple(normals))


def test_defensive_play_in_offensive_gameplan_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=0)  # even = defensive
    with pytest.raises(ValueError, match="profile_type is OFFENSE"):
        _offense(normals=tuple(normals))


def test_defensive_special_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=1, play_category=0))
    with pytest.raises(ValueError, match="Special category 1 custom:.*profile_type is OFFENSE"):
        _offense(specials=_offense_specials(c1=slot))


def test_defensive_clock_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=11, play_category=0))
    with pytest.raises(ValueError, match="Special category 11 stock:.*profile_type is OFFENSE"):
        _offense(specials=_offense_specials(c11=slot))


def test_special_teams_play_in_normal_slot_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=2, play_category=0)
    with pytest.raises(ValueError, match="Normal slot 0 contains a special-teams play"):
        _defense(normals=tuple(normals))


# ── misc ──────────────────────────────────────────────────────────────────────


def test_is_offense_and_is_defense_match_profile_type():
    offense = _offense()
    assert offense.is_offense is True
    assert offense.is_defense is False
    defense = _defense()
    assert defense.is_offense is False
    assert defense.is_defense is True


def test_with_normal_plays_too_many_raises():
    with pytest.raises(ValueError, match="Expected at most 64 normal plays"):
        _defense().with_normal_plays([_make_custom(special_category=0)] * 65)


def test_with_normal_plays_returns_new_instance():
    gameplan = _defense()
    updated = gameplan.with_normal_plays([_make_custom(special_category=0)])
    assert updated is not gameplan
    assert gameplan.normal_plays[0] is None
    assert updated.normal_plays[0] is not None


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("plays\\Offense\\PSR\\OR45RL01.PLY", "OR45RL01"),
        ("X.ply", "X"),
        ("X", "X"),
        ("dir\\sub\\PLAY.PLY", "PLAY"),
    ],
)
def test_custom_play_name_extracts_stem(filename: str, expected: str) -> None:
    play = CustomPlayRef(
        filename=filename, play_category=0, special_category=0, user_category=0
    )
    assert play.name == expected
```

- [ ] **Step 2: Run the model tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_gameplan/test_model.py -q`
Expected: collection error, `ImportError: cannot import name 'SpecialSlot'`.

- [ ] **Step 3: Rewrite the model**

In `src/athc/fbpro98_gameplan/model.py`, change the imports to:

```python
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import PureWindowsPath
from typing import ClassVar
```

Update the `special_category` docstrings on both `CustomPlayRef` (line 39) and `StockPlayRef` (line 72) to:

```python
    """Special-teams category; 0 = not special teams, 1-12 = the special-teams
    categories (11 Run Clock and 12 Stop Clock are offense-only stock plays)."""
```

After `PlayRef = CustomPlayRef | StockPlayRef`, add:

```python
@dataclass(frozen=True, slots=True)
class SpecialSlot:
    """One special-teams category's two slots: the coach's `custom` play and the
    game's `stock` play. Categories 11-12 (Run Clock, Stop Clock) have no custom
    slot on disk, so their `custom` is always None."""

    custom: CustomPlayRef | None = None
    stock: StockPlayRef | None = None
```

Replace the `GamePlan` class from its docstring through the end of the file with:

```python
@dataclass(frozen=True, slots=True)
class GamePlan:
    """Full in-memory representation of a `.pln` gameplan file.

    See specs/pln.md for the on-disk binary format. Construction validates
    structural invariants (slot counts, side-of-ball consistency, special-
    category alignment, stock-only clock categories) via __post_init__;
    ValueError is raised for any violation.
    """

    NUMBER_NORMAL_PLAYS: ClassVar[int] = 64
    """Number of normal (non-special) play slots."""

    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 12
    """Special-teams categories 1-12; `special_plays` has one slot per category."""

    CUSTOM_SPECIAL_CATEGORIES: ClassVar[range] = range(1, 11)
    """Categories that have a custom slot. 11 (Run Clock) and 12 (Stop Clock)
    are stock-only and exist only in offense gameplans."""

    NUMBER_PLAY_SLOTS: ClassVar[int] = 86
    """Total slot count in the G95 offsets table (64 normal + 22 special)."""

    profile_type: ProfileType
    """Whether this gameplan is for offense or defense. Determines clock-category
    population and file-size parity."""

    normal_plays: tuple[PlayRef | None, ...]
    """The 64 normal play slots. None indicates an unused slot."""

    special_plays: tuple[SpecialSlot, ...]
    """One SpecialSlot per special-teams category; index = category - 1."""

    audible: bytes = b"\x00\x01\x02\x03"
    """Four-byte audible play reference stored in the G95 block."""

    map_filename: str = "STOCK98.MAP"
    """Filename of the stock-play map this gameplan references (stored in the
    S98 block)."""

    def __post_init__(self) -> None:
        if len(self.normal_plays) != self.NUMBER_NORMAL_PLAYS:
            raise ValueError(
                f"normal_plays must have exactly {self.NUMBER_NORMAL_PLAYS} "
                f"entries, got {len(self.normal_plays)}"
            )
        if len(self.special_plays) != self.NUMBER_SPECIAL_CATEGORIES:
            raise ValueError(
                f"special_plays must have exactly {self.NUMBER_SPECIAL_CATEGORIES} "
                f"entries, got {len(self.special_plays)}"
            )

        for category, slot in enumerate(self.special_plays, start=1):
            self._check_slot(category, slot)

        expected_parity = 1 if self.is_offense else 0
        for label, play in self._filled_plays():
            if play.play_category % 2 != expected_parity:
                play_side = "offensive" if play.play_category % 2 == 1 else "defensive"
                gp_side = "OFFENSE" if expected_parity == 1 else "DEFENSE"
                raise ValueError(
                    f"{label}: play has {play_side} "
                    f"play_category=0x{play.play_category:02X}, "
                    f"but profile_type is {gp_side}"
                )

        for i, play in enumerate(self.normal_plays):
            if play is None:
                continue
            if play.special_category != 0:
                raise ValueError(
                    f"Normal slot {i} contains a special-teams play "
                    f"(special_category={play.special_category}); "
                    f"only non-special-teams plays allowed in normal slots"
                )

    def _check_slot(self, category: int, slot: SpecialSlot) -> None:
        # Runtime type checks stay: callers can smuggle the wrong ref type past
        # the annotations (the tests do), and the writer trusts these fields.
        if slot.custom is not None:
            if not isinstance(slot.custom, CustomPlayRef):
                raise ValueError(
                    f"Special category {category}: custom must be CustomPlayRef "
                    f"or None, got {type(slot.custom).__name__}"
                )
            if slot.custom.special_category != category:
                raise ValueError(
                    f"Special category {category}: custom play has "
                    f"special_category={slot.custom.special_category}"
                )
        if slot.stock is not None:
            if not isinstance(slot.stock, StockPlayRef):
                raise ValueError(
                    f"Special category {category}: stock must be StockPlayRef "
                    f"or None, got {type(slot.stock).__name__}"
                )
            if slot.stock.special_category != category:
                raise ValueError(
                    f"Special category {category}: stock play has "
                    f"special_category={slot.stock.special_category}"
                )
        if category in self.CUSTOM_SPECIAL_CATEGORIES:
            return
        if slot.custom is not None:
            raise ValueError(
                f"Special category {category} is stock-only; custom must be None"
            )
        if self.is_offense and slot.stock is None:
            raise ValueError(
                f"Offense gameplans require a stock play in special category "
                f"{category}"
            )
        if self.is_defense and slot.stock is not None:
            raise ValueError(
                f"Defense gameplans must not have a play in special category "
                f"{category}"
            )

    def _filled_plays(self) -> Iterator[tuple[str, PlayRef]]:
        """Every filled play with the label error messages use for it."""
        for i, play in enumerate(self.normal_plays):
            if play is not None:
                yield f"Normal slot {i}", play
        for category, slot in enumerate(self.special_plays, start=1):
            if slot.custom is not None:
                yield f"Special category {category} custom", slot.custom
            if slot.stock is not None:
                yield f"Special category {category} stock", slot.stock

    @property
    def is_offense(self) -> bool:
        """True if this gameplan is for offense."""
        return self.profile_type == ProfileType.OFFENSE

    @property
    def is_defense(self) -> bool:
        """True if this gameplan is for defense."""
        return self.profile_type == ProfileType.DEFENSE

    @property
    def custom_special_plays(self) -> tuple[CustomPlayRef | None, ...]:
        """The custom play of each category in `CUSTOM_SPECIAL_CATEGORIES`, in
        category order (ten entries)."""
        return tuple(
            self.special_plays[c - 1].custom for c in self.CUSTOM_SPECIAL_CATEGORIES
        )

    def with_normal_plays(self, plays: Sequence[PlayRef | None]) -> GamePlan:
        """Return a new GamePlan with `plays` placed in the 64 normal slots.

        The original GamePlan is not mutated. Shorter sequences are right-padded
        with None to fill all 64 slots.

        Args:
            plays: Up to 64 plays (or None entries) in slot order.

        Returns:
            A new GamePlan with the updated normal slots; all other fields copied
            from self.

        Raises:
            ValueError: If `plays` contains more than 64 entries, or if the new
                GamePlan would violate any __post_init__ invariant.
        """
        if len(plays) > self.NUMBER_NORMAL_PLAYS:
            raise ValueError(
                f"Expected at most {self.NUMBER_NORMAL_PLAYS} normal plays, "
                f"got {len(plays)}"
            )
        padded = tuple(list(plays) + [None] * (self.NUMBER_NORMAL_PLAYS - len(plays)))
        return replace(self, normal_plays=padded)

    def with_custom_special_plays(
        self, plays: Iterable[CustomPlayRef | None]
    ) -> GamePlan:
        """Return a new GamePlan with `plays` written into the custom slots of
        categories 1-10.

        Each play is placed into the category dictated by its own
        `special_category`. Order doesn't matter. None entries are ignored.
        Categories not covered by any play have their custom slot cleared. Every
        stock slot, the clock categories included, is preserved.

        Args:
            plays: Iterable of CustomPlayRef (or None) values; each play's
                `special_category` selects its destination category.

        Returns:
            A new GamePlan with the updated custom special-teams slots.

        Raises:
            ValueError: If any play's `special_category` is outside
                `CUSTOM_SPECIAL_CATEGORIES`, or if two plays target the same
                category.
        """
        first, last = self.CUSTOM_SPECIAL_CATEGORIES[0], self.CUSTOM_SPECIAL_CATEGORIES[-1]
        customs: dict[int, CustomPlayRef] = {}
        for play in plays:
            if play is None:
                continue
            if play.special_category not in self.CUSTOM_SPECIAL_CATEGORIES:
                raise ValueError(
                    f"Play has special_category={play.special_category}, "
                    f"must be {first}..{last}"
                )
            if play.special_category in customs:
                raise ValueError(
                    f"Two custom special plays target "
                    f"special_category={play.special_category}"
                )
            customs[play.special_category] = play
        new_special = tuple(
            replace(slot, custom=customs.get(category))
            if category in self.CUSTOM_SPECIAL_CATEGORIES
            else slot
            for category, slot in enumerate(self.special_plays, start=1)
        )
        return replace(self, special_plays=new_special)
```

Also update the module docstring's second paragraph to list `SpecialSlot`:

```python
"""In-memory data model for FbPro98 .pln gameplan files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, CustomPlayRef, StockPlayRef, SpecialSlot, and the top-level GamePlan
dataclass.
"""
```

- [ ] **Step 4: Export `SpecialSlot`**

In `src/athc/fbpro98_gameplan/__init__.py`, add `SpecialSlot,` to the model import (alphabetical, after `ProfileType,`) and `"SpecialSlot",` to `__all__` (after `"ProfileType",`).

- [ ] **Step 5: Run the model tests**

Run: `uv run pytest tests/unit/fbpro98_gameplan/test_model.py -q`
Expected: PASS.

- [ ] **Step 6: Update the reader tests**

In `tests/unit/fbpro98_gameplan/test_reader.py`:

Add `SpecialSlot,` to the import from `athc.fbpro98_gameplan` (after `ProfileType,`).

Replace `test_offense_clock_plays_both_present`, `test_offense_special_plays_alternate_custom_and_stock` and `test_offense_special_plays_carry_correct_category` with:

```python
def test_offense_clock_categories_hold_stock_plays() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    run_clock = plan.special_plays[10]
    stop_clock = plan.special_plays[11]
    assert run_clock.custom is None and stop_clock.custom is None
    assert run_clock.stock is not None and run_clock.stock.name == "RUNCLOCK"
    assert stop_clock.stock is not None and stop_clock.stock.name == "STOPCLOK"
    assert run_clock.stock.special_category == 11
    assert stop_clock.stock.special_category == 12


def test_offense_special_slots_are_typed() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for slot in plan.special_plays:
        assert slot.custom is None or isinstance(slot.custom, CustomPlayRef)
        assert slot.stock is None or isinstance(slot.stock, StockPlayRef)


def test_offense_special_slots_carry_their_category() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    for category, slot in enumerate(plan.special_plays, start=1):
        for play in (slot.custom, slot.stock):
            if play is not None:
                assert play.special_category == category
```

Replace `test_defense_has_no_clock_plays` with:

```python
def test_defense_clock_categories_are_empty() -> None:
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    assert plan.special_plays[10] == SpecialSlot()
    assert plan.special_plays[11] == SpecialSlot()
```

In `test_parse_gameplan_from_buffer_matches_read_gameplan`, replace the two `special_plays` / `clock_plays` assertions with:

```python
    assert from_buffer.special_plays == from_file.special_plays
```

Replace `test_gameplan_special_plays_has_20_entries`, `test_gameplan_clock_plays_has_2_entries`, `test_gameplan_custom_special_plays_view_has_10_entries`, `test_gameplan_stock_special_plays_view_has_10_entries`, `test_gameplan_custom_special_plays_view_only_returns_custom_or_none` and `test_gameplan_stock_special_plays_view_only_returns_stock_or_none` with:

```python
def test_gameplan_special_plays_has_12_entries() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert len(plan.special_plays) == 12


def test_gameplan_custom_special_plays_view_has_10_entries() -> None:
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    assert len(plan.custom_special_plays) == 10
    for play in plan.custom_special_plays:
        assert play is None or isinstance(play, CustomPlayRef)
```

Add a helper after `_first_custom_record_offset`:

```python
def _record_offset(data: bytes | bytearray, slot: int) -> int:
    """Absolute offset of the play record in `slot`; skips when the slot is empty."""
    offsets = struct.unpack_from("<86H", data, 12)
    if offsets[slot] == 0:
        pytest.skip(f"Fixture slot {slot} is empty")
    return 12 + offsets[slot]
```

Append to the error-path section:

```python
def test_unrecognized_play_category_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    slot, record_offset = _first_used_slot_offset(data)
    data[record_offset + 3] = 0x3F  # user_category no table knows
    gameplan_path = tmp_path / "bad_category.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(
        InvalidGamePlanError, match=f"Unrecognized play category at slot {slot}"
    ):
        read_gameplan(gameplan_path)


def test_custom_play_in_clock_slot_raises(tmp_path):
    """A clock slot holding a custom record is a model violation, not a crash."""
    data = _load_fixture_bytes(OFFENSE_PATH)
    # Turn the Run Clock stock record (slot 84) into a custom record: stock_flag 0.
    # Its body then reads as a filename up to the first NUL inside map_offset, and
    # its special_category stays 11. Bump the J95 special count so the count check
    # passes and the model gets to judge the slot.
    data[_record_offset(data, 84)] = 0
    j95_special = _g95_end(data) + J95_HEADER.size + 5  # after type u8 + 2 x u16
    struct.pack_into(
        "<H", data, j95_special, struct.unpack_from("<H", data, j95_special)[0] + 1
    )
    gameplan_path = tmp_path / "custom_clock.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(ValueError, match="Special category 11: stock must be StockPlayRef"):
        read_gameplan(gameplan_path)
```

(The reader puts offset 84's record into the slot's `stock` field, so the model's type check is what fires; the message is still a `ValueError`, which is the point.)

- [ ] **Step 7: Update the reader**

In `src/athc/fbpro98_gameplan/reader.py`:

Change the imports:

```python
from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import cast

from athc.fbpro98_gameplan.model import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)
from athc.fbpro98_gameplan.schema import (
    ...unchanged...
)
from athc.fbpro98_play import UNKNOWN_CATEGORY, resolve_category
```

In `read_gameplan` and `parse_gameplan` docstrings, add to the `InvalidGamePlanError` bullet: "or a play whose category bytes are unrecognized".

Replace the tail of `parse_gameplan` (from `n_normal = ...`) with:

```python
    n_normal = GamePlan.NUMBER_NORMAL_PLAYS
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(plays_by_slot[:n_normal]),
        special_plays=_special_slots(plays_by_slot[n_normal:]),
        audible=audible,
        map_filename=map_filename,
    )


def _special_slots(plays: Sequence[PlayRef | None]) -> tuple[SpecialSlot, ...]:
    """Offsets 64-85 as one SpecialSlot per category: a (custom, stock) pair for
    each category with a custom slot, then one stock entry per clock category.
    Types are asserted by the model, not here."""
    paired = len(GamePlan.CUSTOM_SPECIAL_CATEGORIES) * 2
    slots = [
        SpecialSlot(
            custom=cast("CustomPlayRef | None", plays[i]),
            stock=cast("StockPlayRef | None", plays[i + 1]),
        )
        for i in range(0, paired, 2)
    ]
    slots.extend(
        SpecialSlot(stock=cast("StockPlayRef | None", play)) for play in plays[paired:]
    )
    return tuple(slots)
```

In `_parse_play`, after unpacking the header and before `body_start = ...`:

```python
    category = resolve_category(play_category, special_category, user_category)
    if category is UNKNOWN_CATEGORY:
        raise InvalidGamePlanError(
            f"Unrecognized play category at slot {slot} "
            f"(play_category=0x{play_category:02X}, "
            f"special_category=0x{special_category:02X}, "
            f"user_category=0x{user_category:02X}) in {path}"
        )
```

In `_validate_j95_counts`, replace the `n_special` line and `actual_special` with:

```python
    actual_special = sum(
        1 for p in plays_by_slot[n_normal:] if isinstance(p, CustomPlayRef)
    )
```

and delete the now-unused `n_special` local.

- [ ] **Step 8: Update the writer**

In `src/athc/fbpro98_gameplan/writer.py`, replace the start of `_build_g95` and `_build_j95`:

```python
def _build_g95(gameplan: GamePlan) -> bytes:
    all_plays: list[PlayRef | None] = [
        *gameplan.normal_plays,
        *_special_records(gameplan),
    ]
    ...rest unchanged...


def _special_records(gameplan: GamePlan) -> list[PlayRef | None]:
    """The 22 special offsets in file order: (custom, stock) for each category
    with a custom slot, then the stock play of each clock category."""
    records: list[PlayRef | None] = []
    for category, slot in enumerate(gameplan.special_plays, start=1):
        if category in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
            records.append(slot.custom)
        records.append(slot.stock)
    return records
```

```python
def _build_j95(gameplan: GamePlan) -> bytes:
    num_custom = sum(1 for p in gameplan.normal_plays if isinstance(p, CustomPlayRef))
    num_stock = sum(1 for p in gameplan.normal_plays if isinstance(p, StockPlayRef))
    num_special = sum(1 for s in gameplan.special_plays if s.custom is not None)
    ...unchanged...
```

- [ ] **Step 9: Update the writer test**

In `tests/unit/fbpro98_gameplan/test_writer.py`, replace `test_special_plays_preserved` with:

```python
def test_special_plays_preserved(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    write_gameplan(original.with_normal_plays([_make_play("TEST01")]), pln_path)
    reloaded = read_gameplan(pln_path)

    assert reloaded.special_plays == original.special_plays
```

(`SpecialSlot`, `CustomPlayRef` and `StockPlayRef` are frozen dataclasses, so equality compares every field including `map_offset` / `map_size`.) Remove the now-unused `StockPlayRef` import if ruff flags it.

- [ ] **Step 10: Run the library tests**

Run: `uv run pytest tests/unit/fbpro98_gameplan -q`
Expected: PASS, round-trip byte identity included.

- [ ] **Step 11: Migrate the validators**

In `src/athc/gameplan/validators.py`, replace `_validate_special_categories` and `_validate_custom_special_plays`:

```python
def _validate_special_categories(
    gameplan: GamePlan, required: frozenset[int]
) -> list[Violation]:
    """Each required special category (1-12) must have a custom or stock play."""
    violations: list[Violation] = []
    for category in sorted(required):
        slot = gameplan.special_plays[category - 1]
        if slot.custom is None and slot.stock is None:
            violations.append(
                Violation(
                    RuleName.SPECIAL_CATEGORY_REQUIRED,
                    f"Required special category {category} has no play",
                )
            )
    return violations


def _validate_custom_special_plays(gameplan: GamePlan) -> list[Violation]:
    """A populated special category must use its custom slot. Only categories
    that have one are checked; the clock categories are stock-only."""
    violations: list[Violation] = []
    for category in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
        slot = gameplan.special_plays[category - 1]
        if slot.stock is not None and slot.custom is None:
            violations.append(
                Violation(
                    RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED,
                    f"Special category {category} uses a stock play; "
                    "a custom play is required",
                )
            )
    return violations
```

- [ ] **Step 12: Migrate the gameplan writer (`set-specials` logic)**

In `src/athc/gameplan/writer.py`:

Change the import to `from athc.fbpro98_gameplan import CustomPlayRef, GamePlan` (unchanged) and in `_resolve_special_line`, after `cat = pf.special_category`, add before the `seen_categories` check:

```python
    if cat not in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
        violations.append(
            f"Special play '{name}' at line {line_no} is in special category {cat}, "
            "which has no custom slot"
        )
        return None
```

- [ ] **Step 13: Migrate the CLI**

`src/athc/cli/gameplan/replace_play.py`, in `replace_in_gameplan`, replace the specials loop:

```python
    specials = list(gp.special_plays)
    for category, _ in special_hits:
        specials[category - 1] = replace(specials[category - 1], custom=entry)
    updated = replace(gp, normal_plays=tuple(normals), special_plays=tuple(specials))
```

`src/athc/cli/gameplan/set_specials.py` line 27:

```python
SPECIAL_COUNT = len(GamePlan.CUSTOM_SPECIAL_CATEGORIES)
```

`src/athc/cli/gameplan/_common.py` and `src/athc/profile/compat.py` use only `custom_special_plays` and need no change.

- [ ] **Step 14: Migrate the test fixtures**

`tests/unit/gameplan/test_validators.py`:

Add `SpecialSlot` to the `athc.fbpro98_gameplan.model` import. Replace `defense_gameplan` (line 62) with:

```python
def empty_specials() -> tuple[SpecialSlot, ...]:
    return tuple(SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES))


def defense_gameplan(names: list[str]) -> GamePlan:
    normal = tuple(make_play(n) for n in names) + (None,) * (64 - len(names))
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=normal,
        special_plays=empty_specials(),
    )
```

Replace `_CLOCK_PLAYS` and `offense_gameplan` (lines 263-279) with:

```python
def offense_specials() -> tuple[SpecialSlot, ...]:
    """Empty slots plus the stock clock plays every offense gameplan carries."""
    slots = list(empty_specials())
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 0x01, category, 0x00)
        )
    return tuple(slots)


def offense_gameplan(plays: list[CustomPlayRef]) -> GamePlan:
    normal = tuple(plays) + (None,) * (64 - len(plays))
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=normal,
        special_plays=offense_specials(),
    )
```

Replace `test_custom_special_play_required_fires` (line 505) with:

```python
def test_custom_special_play_required_fires() -> None:
    """With custom_special_play_required, a stock-only special slot is flagged."""
    slots = list(empty_specials())
    slots[0] = SpecialSlot(stock=StockPlayRef("STOCK1", 0, 0, 0x00, 1, 0x00))
    gp = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=(None,) * 64,
        special_plays=tuple(slots),
    )
    rules = def_rules(custom_special_play_required=True)
    assert RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED in fired(gp, rules, make_pool([]))
```

`tests/unit/profile/test_compat.py`: add `SpecialSlot` to the `athc.fbpro98_gameplan` import, delete `_CLOCK` (lines 51-58), and replace the body of `make_gameplan` from `slots: list[...]` to the end with:

```python
    slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for s in special:
        slots[s - 1] = SpecialSlot(custom=CustomPlayRef(f"SP{s}.PLY", parity, s, 0))
    for s in stock_special:
        slots[s - 1] = SpecialSlot(stock=StockPlayRef(f"ST{s}", 0, 0, parity, s, 0))
    if offense:
        for s in (11, 12):
            slots[s - 1] = SpecialSlot(stock=StockPlayRef(f"CLOCK{s}", 0, 0, parity, s, 0))
    return GamePlan(
        profile_type=GamePlanType.OFFENSE if offense else GamePlanType.DEFENSE,
        normal_plays=normal_plays,
        special_plays=tuple(slots),
    )
```

`tests/integration/test_gameplan_find_play.py`: add `SpecialSlot` to the `athc.fbpro98_gameplan` import and replace `_empty_offense_gameplan` and `_set_custom_special` (lines 34-66) with:

```python
def _empty_offense_gameplan() -> GamePlan:
    slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 1, category, 0)
        )
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=tuple([None] * 64),
        special_plays=tuple(slots),
    )


def _set_normal_slots(gp: GamePlan, *placements: tuple[int, CustomPlayRef]) -> GamePlan:
    normals = list(gp.normal_plays)
    for index, play in placements:
        normals[index] = play
    return replace(gp, normal_plays=tuple(normals))


def _set_custom_special(gp: GamePlan, category: int, play: CustomPlayRef) -> GamePlan:
    """Place `play` in the custom slot of `category` (1-10)."""
    specials = list(gp.special_plays)
    specials[category - 1] = replace(specials[category - 1], custom=play)
    return replace(gp, special_plays=tuple(specials))
```

Remove `CustomPlayRef`-only clock helpers if any remain unused; keep the `StockPlayRef` import (now used).

`tests/integration/test_gameplan_replace_play.py`: add `SpecialSlot` and `StockPlayRef` to the `athc.fbpro98_gameplan` import, replace `_clock` (lines 51-57) with:

```python
def _clock(category: int) -> SpecialSlot:
    return SpecialSlot(stock=StockPlayRef(f"CLOCK{category}", 0, 0, 1, category, 0))
```

and replace the special/clock part of `_build` (lines 108-122) with:

```python
    special_slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category, play in (specials or {}).items():
        special_slots[category - 1] = SpecialSlot(custom=play)
    # Offense requires both stock clock plays; defense has none.
    if profile_type is ProfileType.OFFENSE:
        for category in (11, 12):
            special_slots[category - 1] = _clock(category)
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(normal_slots),
        special_plays=tuple(special_slots),
    )
```

Drop the `PlayRef` import from that file if it is now unused.

- [ ] **Step 15: Add the `set-specials` guard test**

`gameplan.writer` has no unit tests today (it is covered through the `set-specials` integration tests, which use the real pool and so can't produce a category-11 `.ply`). Create `tests/unit/gameplan/test_writer.py`:

```python
"""Unit tests for `gameplan.writer`: cases the real play pool can't produce."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_gameplan import GamePlan, ProfileType, SpecialSlot, StockPlayRef
from athc.fbpro98_play import PlayFile
from athc.gameplan.writer import InvalidPlayInputError, apply_special_plays
from athc.playpool import OffensivePlay, PlayPool


def _pool_with(name: str, *, special_category: int) -> PlayPool:
    """A pool holding one offensive play whose header claims `special_category`."""
    play_file = PlayFile(Path(f"{name}.ply"), 0, 0x01, special_category, 0, (), ())
    pool = PlayPool("root")
    record = OffensivePlay(name, play_file)
    pool._register(record)
    pool.offensive_plays.append(record)
    return pool


def _offense_gameplan() -> GamePlan:
    slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category in (11, 12):
        slots[category - 1] = SpecialSlot(
            stock=StockPlayRef(f"CLOCK{category}", 0, 0, 0x01, category, 0)
        )
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=(None,) * GamePlan.NUMBER_NORMAL_PLAYS,
        special_plays=tuple(slots),
    )


def test_special_play_without_custom_slot_is_rejected() -> None:
    """A .ply claiming special category 11 has no custom slot to land in."""
    pool = _pool_with("CLOCKPLY", special_category=11)
    with pytest.raises(
        InvalidPlayInputError, match="special category 11, which has no custom slot"
    ):
        apply_special_plays(_offense_gameplan(), ["CLOCKPLY"], pool)


def test_special_play_in_last_custom_category_is_accepted() -> None:
    """Category 10 is the last one with a custom slot."""
    pool = _pool_with("SQUIBPLY", special_category=10)
    updated = apply_special_plays(_offense_gameplan(), ["SQUIBPLY"], pool)
    placed = updated.special_plays[9].custom
    assert placed is not None and placed.name == "SQUIBPLY"
```

(`build_custom_play` computes the play's path relative to `pool.root_dir`; `PlayPool("root")` with a bare `SQUIBPLY.ply` path raises `ValueError` from `relative_to`, which `build_custom_play` catches nowhere. If the second test fails that way, give the record's `PlayFile` the path `Path("root") / "SQUIBPLY.ply"` instead.)

Add to `tests/unit/gameplan/README.md`, before the `## validators.py` heading (line 86):

```
## writer.py — `apply_special_plays`

| Case | Input | Expect | Test | Status |
|---|---|---|---|---|
| Special category 11 play (no custom slot) | make | `InvalidPlayInputError` "which has no custom slot" | `test_special_play_without_custom_slot_is_rejected` | ☑ |
| Special category 10 play (last custom slot) | make | placed in slot 10 | `test_special_play_in_last_custom_category_is_accepted` | ☑ |
```

(Match the table header style of the file's other tables; adjust the column set if they differ.)

- [ ] **Step 16: Run the whole suite, lint, format and types**

Run, one per call:

```
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright
```

Expected: all green. If `ruff format` rewrote files, re-run `uv run ruff check .`. Then normalize endings on every file this task touched: `git diff --name-only | xargs -I{} sed -i 's/\r$//; s/$/\r/' {}` (run once; Python files are text and must be CRLF too).

- [ ] **Step 17: Commit**

```bash
git add -A src tests
git commit -m "fbpro98_gameplan: one typed SpecialSlot per category 1-12; reader rejects an unrecognized play category"
```

---

### Task 3: Validator coverage for clock categories

**Files:**
- Test: `tests/unit/gameplan/test_validators.py`
- Modify: `tests/unit/gameplan/README.md:119-123`

**Interfaces:**
- Consumes: `GamePlan.special_plays` (Task 2), `offense_gameplan` / `defense_gameplan` / `empty_specials` helpers (Task 2 step 14).
- Produces: nothing new; pins behavior for `required_special_categories` with 11 and 12.

- [ ] **Step 1: Write the tests**

Append to the special-categories section of `tests/unit/gameplan/test_validators.py`:

```python
def test_required_clock_category_satisfied_on_offense() -> None:
    """Every offense gameplan carries both stock clock plays, so requiring them passes."""
    gp = offense_gameplan([])
    rules = off_rules(required_special_categories=frozenset({11, 12}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED not in fired(gp, rules, make_off_pool([]))


def test_required_clock_category_fires_on_defense() -> None:
    """Defense has no clock plays; a league requiring Stop Clock is told so."""
    gp = defense_gameplan([])
    rules = def_rules(required_special_categories=frozenset({12}))
    assert RuleName.SPECIAL_CATEGORY_REQUIRED in fired(gp, rules, make_pool([]))


def test_custom_special_play_required_ignores_clock_categories() -> None:
    """Clock categories are stock-only, so their stock plays never trip the rule."""
    gp = offense_gameplan([])
    rules = off_rules(custom_special_play_required=True)
    assert RuleName.CUSTOM_SPECIAL_PLAY_REQUIRED not in fired(gp, rules, make_off_pool([]))
```

`make_off_pool` (line 246) and `off_rules` (line 282) already exist in that file.

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/unit/gameplan/test_validators.py -q -k "clock"`
Expected: PASS (Task 2 already implemented the behavior; these pin it). If `test_required_clock_category_fires_on_defense` raises `IndexError`, Task 2 step 11 was not applied.

- [ ] **Step 3: Update the test matrix**

In `tests/unit/gameplan/README.md`, after the "Stock-only special" row (line 123) add:

```
| Required clock category on offense | make | no `SPECIAL_CATEGORY_REQUIRED` (stock clock plays present) | `test_required_clock_category_satisfied_on_offense` | ☑ |
| Required clock category on defense | make | `SPECIAL_CATEGORY_REQUIRED` | `test_required_clock_category_fires_on_defense` | ☑ |
| Clock categories exempt from custom-required | make | no `CUSTOM_SPECIAL_PLAY_REQUIRED` | `test_custom_special_play_required_ignores_clock_categories` | ☑ |
```

Normalize: `sed -i 's/\r$//; s/$/\r/' tests/unit/gameplan/README.md`

- [ ] **Step 4: Commit**

```bash
git add tests/unit/gameplan/test_validators.py tests/unit/gameplan/README.md
git commit -m "gameplan: required_special_categories covers the clock categories"
```

---

### Task 4: Rules labels for every category

**Files:**
- Modify: `src/athc/gameplan/rules.py:1-7, 18-23, 83-106, 280-301`
- Test: `tests/unit/gameplan/test_rules.py`
- Modify: `tests/unit/gameplan/README.md:9-15`

**Interfaces:**
- Consumes: `OffensiveCategory`, `DefensiveCategory`, `SpecialOffensiveCategory` from `athc.fbpro98_play`.
- Produces: `load_rules` accepts `[offense."Pass Long Left"]`, `[offense."Pass Long Middle"]`, `[offense."Razzle Dazzle Run"]`, `[offense."User Specific"]`, `[defense."User Specific"]`, and `required_special_categories = ["Run Clock", "Stop Clock"]`. `category_by_short` is no longer imported here.

- [ ] **Step 1: Write the failing tests**

Add to the short-name labels section of `tests/unit/gameplan/test_rules.py`:

```python
@pytest.mark.parametrize(
    "label",
    ["Pass Long Left", "Pass Long Middle", "Razzle Dazzle Run", "User Specific"],
)
def test_offense_game_name_label_loads(tmp_path: Path, label: str) -> None:
    """Categories without a league abbreviation are labeled by their game name."""
    text = MINIMAL + f'[offense."{label}"]\nmax_count = 0\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories[label].max_count == 0


def test_user_specific_label_loads_on_each_side(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + '[offense."User Specific"]\nmax_count = 0\n'
        + '[defense."User Specific"]\nmax_count = 1\n'
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories["User Specific"].max_count == 0
    assert rules.defense_categories["User Specific"].max_count == 1


def test_game_name_label_on_wrong_side_is_rejected(tmp_path: Path) -> None:
    text = MINIMAL + '[defense."Pass Long Left"]\nmax_count = 0\n'
    with pytest.raises(RulesFileError, match="not a defense category label"):
        load_rules([write(tmp_path, text)])


def test_unknown_label_message_lists_game_name_labels(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.ZZZ]\nmax_count = 0\n"
    with pytest.raises(RulesFileError, match="Pass Long Left"):
        load_rules([write(tmp_path, text)])


def test_required_special_accepts_clock_categories(tmp_path: Path) -> None:
    text = MINIMAL + 'required_special_categories = ["Run Clock", "Stop Clock"]\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.required_special_categories == frozenset({11, 12})
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/gameplan/test_rules.py -q -k "game_name or user_specific or clock"`
Expected: the label tests FAIL with "not an offense category label"; `test_required_special_accepts_clock_categories` PASSES already (Task 1 put the names in the enum). That is fine; it stays as a pin.

- [ ] **Step 3: Resolve labels per side over the whole enum**

In `src/athc/gameplan/rules.py`:

Module docstring, last sentence:

```python
"""...Categories are keyed by short label — offense uses
codes (`[offense.PSL]`), defense uses words (`[defense.RunDazzle]`); a category
with no league abbreviation uses its game name, quoted (`[offense."Pass Long Left"]`).
"""
```

Import: remove `category_by_short` from the `athc.fbpro98_play` import.

Replace lines 90-96 (`_OFFENSE_LABELS` / `_DEFENSE_LABELS`) with:

```python
# [offense.X] / [defense.X] section labels: every category's short label. Where a
# category has no league abbreviation the label is its game name (quoted in TOML).
_OFFENSE_BY_LABEL: Final[Mapping[str, OffensiveCategory]] = {
    c.short: c for c in OffensiveCategory
}
_DEFENSE_BY_LABEL: Final[Mapping[str, DefensiveCategory]] = {
    c.short: c for c in DefensiveCategory
}
_OFFENSE_LABELS: Final[list[str]] = sorted(_OFFENSE_BY_LABEL)
_DEFENSE_LABELS: Final[list[str]] = sorted(_DEFENSE_BY_LABEL)
```

Replace `_build_offense_section` and `_build_defense_section`:

```python
def _build_offense_section(
    label: str, section: Mapping[str, Any], source: Path
) -> tuple[str, OffenseCategoryRule]:
    member = _OFFENSE_BY_LABEL.get(label)
    if member is None:
        raise RulesFileError(
            f"{source}: [offense.{label}]: not an offense category label. "
            f"Valid: {_OFFENSE_LABELS}"
        )
    return member.long, _build_offense_rule(label, member, section, source)


def _build_defense_section(
    label: str, section: Mapping[str, Any], source: Path
) -> tuple[str, DefenseCategoryRule]:
    member = _DEFENSE_BY_LABEL.get(label)
    if member is None:
        raise RulesFileError(
            f"{source}: [defense.{label}]: not a defense category label. "
            f"Valid: {_DEFENSE_LABELS}"
        )
    return member.long, _build_defense_rule(label, section, source)
```

- [ ] **Step 4: Run the rules tests**

Run: `uv run pytest tests/unit/gameplan/test_rules.py -q`
Expected: PASS. (`_build_offense_rule` decides run-vs-pass subkeys from `member.is_run` / `member.is_pass`; Razzle Dazzle Run is a run and User Specific is neither, so a cap subkey on `[offense."User Specific"]` is still rejected as a wrong-type subkey — add no special handling.)

- [ ] **Step 5: Update the test matrix**

In `tests/unit/gameplan/README.md`, after line 15 add:

```
| Game-name labels load | tmp | `[offense."Pass Long Left"]` etc. (4) | `test_offense_game_name_label_loads` `[P]` | ☑ |
| `User Specific` on both sides | tmp | offense and defense rules both load | `test_user_specific_label_loads_on_each_side` | ☑ |
| Game-name label on wrong side | tmp | "not a defense category label" | `test_game_name_label_on_wrong_side_is_rejected` | ☑ |
| Unknown-label message lists game names | tmp | message contains "Pass Long Left" | `test_unknown_label_message_lists_game_name_labels` | ☑ |
| Clock names in `required_special_categories` | tmp | → `{11, 12}` | `test_required_special_accepts_clock_categories` | ☑ |
```

Normalize: `sed -i 's/\r$//; s/$/\r/' tests/unit/gameplan/README.md`

- [ ] **Step 6: Lint, types, commit**

Run `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` (one per call); fix anything reported, normalize endings on changed files, then:

```bash
git add src/athc/gameplan/rules.py tests/unit/gameplan/test_rules.py tests/unit/gameplan/README.md
git commit -m "gameplan: rules sections accept every category, labeled by game name where no league abbreviation exists"
```

---

### Task 5: Docs, rules-file comments, changelog

**Files:**
- Modify: `docs/fbpro98_gameplan/ARCHITECTURE.md:22, 29, 44-55, 68`
- Modify: `docs/fbpro98_gameplan/README.md:9, 30-33, 63-65`
- Modify: `docs/fbpro98_gameplan/specs/pln.md:177-187`
- Modify: `docs/gameplan/ARCHITECTURE.md:42-44, 75`
- Modify: `config/dev/leagues/PNFL/rules/gameplan.toml:23-29`, `config/dev/leagues/PCFL/rules/gameplan.toml` (same lines), `config/release/leagues/PNFL/rules/gameplan.toml:34-51, 127`, `config/release/leagues/PCFL/rules/gameplan.toml` (same lines)
- Modify: `tests/unit/fbpro98_gameplan/README.md:15-18, 32-36`
- Modify: `CHANGELOG.md:10`

**Interfaces:** none; prose only.

- [ ] **Step 1: fbpro98_gameplan ARCHITECTURE**

Line 22: `- Validates semantic correctness of the model (slot counts, stock-only clock categories by side, special-slot type/category alignment)`

Line 29: `- All callers respect the immutability of `GamePlan` and use `with_normal_plays` / `with_custom_special_plays` for updates; special slots are read as `special_plays[category - 1].custom` / `.stock``

Add to the Structural list (after the `stock_flag` line): `- Every play's category bytes resolve to a known category (`fbpro98_play.resolve_category`)`

Replace the Model list (lines 45-51) with:

```
- Exact slot counts: 64 normal, 12 special (`SpecialSlot(custom, stock)`, one per category)
- `custom` is `CustomPlayRef | None` and `stock` is `StockPlayRef | None`, each with `special_category` equal to its category
- Categories 11 (Run Clock) and 12 (Stop Clock) are stock-only: `custom` is None; offense requires their `stock`, defense forbids it
- Normal-slot plays have `special_category == 0`
- Play `play_category` parity matches profile (offense odd, defense even)
```

Line 55: `- `with_custom_special_plays` rejects a category outside 1-10 or a duplicate category`

Line 68: `- `tests/unit/fbpro98_gameplan/test_writer.py` — round-trip byte equality + partial-update semantics of `with_normal_plays` / `with_custom_special_plays``

- [ ] **Step 2: fbpro98_gameplan README**

Line 9: `- Normal (64) and special-teams (12 categories, custom + stock) slots`

Lines 30-33:

```python
# Two fixed-length tuples mirror the file structure:
# - normal_plays: 64 slots (None for empty)
# - special_plays: 12 SpecialSlot(custom, stock), one per special category;
#   11 Run Clock and 12 Stop Clock are stock-only (offense only)
```

Line 63: `...special-teams slots are preserved.` (drop "and clock plays").

Line 65: `For special-teams updates, `with_custom_special_plays(plays)` places each `CustomPlayRef` into the category dictated by its own `special_category` (1-10); uncovered custom slots are cleared, order doesn't matter, out-of-range or duplicate category raises `ValueError`. Stock slots, the clock categories included, are immutable through the API.`

- [ ] **Step 3: pln.md reader validation**

In section 7, after `- \`stock_flag ∉ {0, 1}\`` add: `- Play category bytes that no category table recognizes (see ply.md section 3)`

- [ ] **Step 4: gameplan ARCHITECTURE**

Line 42: `- Aggregate counts over the 64 normal slots: min/max plays per game category + per-category attribute caps; required special categories (1-12, clock categories included); disallowed categories; optional `custom_special_play_required` (categories 1-10, the ones with a custom slot).`

Line 44, first sentence: `Section labels are short category labels — `[offense.RM]` (Run Middle), `[defense.RunDazzle]` (Run Dazzle); a category with no league abbreviation is labeled by its game name, quoted (`[offense."Pass Long Left"]`, `[defense."User Specific"]`).`

Line 75, add after "Side and special-teams classification come from each play's `.ply` header, not the rules.": `A play in a stock-only special category (11-12) is rejected per line.`

- [ ] **Step 5: Rules-file header comments (four files)**

Dev files (`config/dev/leagues/PNFL/rules/gameplan.toml`, `config/dev/leagues/PCFL/rules/gameplan.toml`), replace lines 23-25 with:

```
# Valid OFFENSE labels:  GLR RL RM RR  GLP PRD PLR  PML PMM PMR  PSL PSM PSR
#                        "Razzle Dazzle Run" "Pass Long Left" "Pass Long Middle"
#                        "User Specific"   (game names, quoted)
# Valid DEFENSE labels:  GLrun RunDazzle RunLeft RunMiddle RunRight
#                        GLpass PassDazzle PassLong PassMedium PassShort
#                        "User Specific"   (game name, quoted)
```

and lines 27-29 with:

```
# Special teams that must each have a play assigned. Valid names:
#   "Field Goal/PAT" "Kickoff" "Punt" "Onside Kick" "Fake FG Run" "Fake FG Pass"
#   "Fake Punt Run" "Fake Punt Pass" "Free Kick" "Squib Kick" "Run Clock" "Stop Clock"
```

Release files (`config/release/leagues/PNFL/rules/gameplan.toml`, `config/release/leagues/PCFL/rules/gameplan.toml`): the "Valid names" comment is lines 6-8; apply the same two-line change. The `# Labels:` lines at 51 and 127 become:

```
# Labels: GLR RL RM RR  GLP PRD PLR PML PMM PMR  PSL PSM PSR
#         "Razzle Dazzle Run" "Pass Long Left" "Pass Long Middle" "User Specific"
```

```
# Labels: GLrun RunDazzle RunLeft RunMiddle RunRight  GLpass PassDazzle PassLong PassMedium PassShort
#         "User Specific"
```

- [ ] **Step 6: fbpro98_gameplan test matrix**

`tests/unit/fbpro98_gameplan/README.md`: line 15 → `| Clock categories 11/12: offense stock `RUNCLOCK` / `STOPCLOK`, no custom; defense empty | ☑ |`; line 17 → `| Special slots: typed custom/stock, each carrying its category | ☑ |`; line 18 → `| API surface: counts (64/12), `custom_special_plays` (10, custom-or-None), `parse == read`, `CustomPlayRef.name` strips dir/ext | ☑ |`. Add to the Error table: `| Unrecognized play category; custom record in a clock slot | ☑ |`. Line 32 → `| `__post_init__`: slot counts (normal 64; special 12, 11 and 13 rejected); stock-only clock categories by side; custom/stock typing; `special_category` alignment; side-of-ball parity (normal/special); special-in-normal-slot | ☑ |`; line 34 → `| `custom_special_plays` view (10, correct slots) | ☑ |`; line 36 → `| `with_custom_special_plays` (place by category, preserve stock and clock slots, order-independent, clears uncovered, reject stock, range ends 1/10 accepted and 0/11 rejected, duplicate) | ☑ |`. Update the passing count in line 3 to the number `uv run pytest tests/unit/fbpro98_gameplan -q` reports.

- [ ] **Step 7: CHANGELOG**

Insert at the top of the `## athc` list (before the current line 10):

```
- gameplan: rules can name every play category, game-name labels like `[offense."Pass Long Left"]` and `"Run Clock"` / `"Stop Clock"` as required specials; a `.pln` with an unrecognized play category is rejected as corrupt
```

- [ ] **Step 8: Normalize endings and commit**

`git diff --name-only | xargs -I{} sed -i 's/\r$//; s/$/\r/' {}` then:

```bash
git add -A docs config tests/unit/fbpro98_gameplan/README.md CHANGELOG.md
git commit -m "gameplan: docs and rules-file comments for typed special slots and game-name labels"
```

---

### Task 6: Final verification and hand-off

**Files:** none.

- [ ] **Step 1: Full gates**

One per call: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`. All green; if `ruff format` changed anything, normalize endings, commit as `gameplan: format`.

- [ ] **Step 2: Endings check**

`git ls-files -m -o --exclude-standard | xargs -I{} file {} | grep -v CRLF` must print nothing for text files; fix any LF file with the sed command and amend into a new commit.

- [ ] **Step 3: Hand-off**

Leave the worktree and return the session to the main checkout first. Then give two code blocks, each on its own line, never chained: the squash-merge and its commit; then the worktree removal and branch deletion. Do not merge.
