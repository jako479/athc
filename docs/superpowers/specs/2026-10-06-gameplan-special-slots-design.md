# Gameplan special slots: one typed slot per category, all categories supported — design

Date: 2026-10-06. Status: approved by the user; implemented.

## Goal

A game plan supports every play category the game has; only a league's rules
file decides what a plan may or may not contain. The `.pln` model represents
the special-teams table the way the file does, one entry per category 1-12, so
no consumer needs index arithmetic or a separate clock-play structure. A play
whose category bytes are unrecognized is an error, because the plan is either
unsupported or corrupt.

## Current state (branch `worktree-gameplan-special-slots`, on main fe6a786)

- `SpecialOffensiveCategory` has the ten kicking categories (`0x01`-`0x0A`)
  but not the two clock categories `0x0B` Run Clock and `0x0C` Stop Clock,
  which [pln.md](../../fbpro98_gameplan/specs/pln.md) and
  [ply.md](../../fbpro98_play/specs/ply.md) document and the real
  `offense.pln` fixture confirms (`RUNCLOCK` at `0x0B`, `STOPCLOK` at `0x0C`).
- `GamePlan` splits the on-disk 22-entry special table into `special_plays`
  (20 entries, custom/stock interleaved for categories 1-10) and
  `clock_plays` (2 entries). Validators and `replace-play` reach a category's
  slots with `(category - 1) * 2`; categories 11-12 are unreachable by number.
- The gameplan rules loader resolves `[offense.X]` / `[defense.X]` labels
  through `category_by_short`, which drops every category whose short label
  equals its game name: offense Razzle Dazzle Run, Pass Long Left, Pass Long
  Middle, User Specific; defense User Specific. Those five can't be given
  rules.
- The `.pln` reader never resolves a play ref's category bytes; an unknown
  code reads as "Unknown" downstream.
- The `.ply` reader already raises `InvalidPlayFileError` on an unknown
  category; the `.prf` reader already raises `InvalidProfileError` on an
  out-of-range category code.
- `docs/fbpro98_gameplan/ARCHITECTURE.md` names clock slot 11 "spike" and 12
  "kneel"; the spec and fixture say 11 is Run Clock and 12 is Stop Clock.

## Decisions (the user's)

- Add Run Clock (`0x0B`) and Stop Clock (`0x0C`) to `SpecialOffensiveCategory`.
  Defense has no clock plays, so `SpecialDefensiveCategory` is unchanged.
- Model shape: `special_plays` is twelve typed `SpecialSlot(custom, stock)`
  records, one per category 1-12; `clock_plays` is removed.
- `list-specials` keeps printing ten lines, one per category that has a custom
  slot. The "categories 11-12 are stock-only" fact lives in one place in the
  model and consumers ask it.
- Every `SpecialOffensiveCategory` name is valid in
  `required_special_categories`, Run Clock and Stop Clock included.
- An unrecognized play category in a `.pln` is an `InvalidGamePlanError` from
  the reader.
- The four unused category dicts at the top of `fbpro98_profile/model.py`
  are left alone.

## Model (`fbpro98_gameplan`)

```python
@dataclass(frozen=True, slots=True)
class SpecialSlot:
    custom: CustomPlayRef | None = None
    stock: StockPlayRef | None = None


class GamePlan:
    NUMBER_NORMAL_PLAYS = 64
    NUMBER_SPECIAL_CATEGORIES = 12          # special_plays length
    CUSTOM_SPECIAL_CATEGORIES = range(1, 11)  # categories with a custom slot
    NUMBER_PLAY_SLOTS = 86                  # G95 offsets table

    normal_plays: tuple[PlayRef | None, ...]
    special_plays: tuple[SpecialSlot, ...]  # index = category - 1
```

- `NUMBER_SPECIAL_SLOTS`, `NUMBER_CLOCK_SLOTS` and `clock_plays` go away.
- `custom_special_plays` stays: the ten `custom` entries of
  `CUSTOM_SPECIAL_CATEGORIES`, in order. `stock_special_plays` is removed;
  consumers read `special_plays[c - 1].stock`.
- `with_custom_special_plays(plays)` keeps its contract: each play self-slots
  by `special_category`, which must be in `CUSTOM_SPECIAL_CATEGORIES`; stock
  entries are preserved; uncovered custom entries are cleared.

Invariants (`ValueError` from `__post_init__`):

- Exactly 64 normal and 12 special entries.
- Category `c` entry: `custom` is a `CustomPlayRef` with `special_category == c`
  or None; `stock` is a `StockPlayRef` with `special_category == c` or None.
- Categories outside `CUSTOM_SPECIAL_CATEGORIES` (11-12): `custom` is None.
  Offense: `stock` is set. Defense: `stock` is None.
- Every play's `play_category` parity matches the profile type.
- Normal-slot plays have `special_category == 0`.

## Reader and writer

- Offsets 64-83 pair into categories 1-10 (custom, stock); offsets 84 and 85
  are the `stock` of categories 11 and 12.
- The reader resolves every play ref's category bytes with
  `resolve_category`; `UNKNOWN_CATEGORY` raises `InvalidGamePlanError` naming
  the slot and the three bytes, `in {path}` like the other messages.
- The writer flattens the twelve slots back to the same 22 offsets; J95
  `num_special` counts `custom` entries, as today.

## Rules and validators (`gameplan`)

- Section labels resolve per side over the whole enum
  (`{c.short: c for c in OffensiveCategory}`, same for defense), so
  `[offense."Pass Long Left"]`, `[offense."Pass Long Middle"]`,
  `[offense."Razzle Dazzle Run"]`, `[offense."User Specific"]` and
  `[defense."User Specific"]` load. Unknown and wrong-side labels are still
  rejected; the valid-label lists in the messages include the five.
  `category_by_short` in `fbpro98_play` is unchanged (the play pool uses it
  for folder names).
- `required_special_categories` accepts every `SpecialOffensiveCategory`
  name; a required category is satisfied when its slot has a `custom` or a
  `stock`.
- `custom_special_play_required` checks `CUSTOM_SPECIAL_CATEGORIES` only.
- `replace-play` swaps a special hit with `replace(slot, custom=entry)`.

## Profile

No code change. The `.prf` reader already rejects an out-of-range category
code, and the profile tool's gameplan-compatibility check reads the `.pln`
through the reader above and uses `custom_special_plays`.

## Tests

- `fbpro98_play`: the parametrized special-category tests pick up the two new
  members; `resolve_category(0x01, 0x0B, 0)` is Run Clock and the defense side
  of `0x0B` is unknown.
- `fbpro98_gameplan` model: special length 11 and 13 rejected, 12 accepted;
  a `custom` in category 11 or 12 rejected; offense missing stock 11 or 12
  rejected; defense with stock 11 or 12 rejected; category mismatch in either
  entry rejected; `with_custom_special_plays` accepts categories 1 and 10,
  rejects 0 and 11.
- Reader: the real offense fixture yields `RUNCLOCK` in category 11 and
  `STOPCLOK` in 12; a fixture copy with an unknown `user_category` raises
  `InvalidGamePlanError`; the defense fixture has no stock in 11-12.
- Writer: round-trip byte equality unchanged.
- Rules: the five labels load on their side; `[defense."Pass Long Left"]`
  rejected; `required_special_categories = ["Run Clock"]` loads; an unknown
  name is rejected.
- Validators: a required Run Clock is satisfied by an offense plan;
  `custom_special_play_required` ignores categories 11-12.
- CLI: `list-specials` still ten lines; `replace-play` and `find-play` special
  hits unchanged.

## Docs

- `docs/fbpro98_gameplan/README.md` and `ARCHITECTURE.md`: model shape,
  invariants, Run Clock / Stop Clock names (fixing spike/kneel).
- `docs/fbpro98_gameplan/specs/pln.md` section 7 (Reader Validation): add
  the unknown category check.
- `docs/gameplan/ARCHITECTURE.md`: section labels and special names.
- Rules TOML header comments (dev and release, PNFL and PCFL): the five labels
  and the two special names.
- Test folder READMEs that list cases; `CHANGELOG.md`.

## Out of scope

- The unused category dicts in `fbpro98_profile/model.py`.
- Any `.prf` or profile-tool change.
- `pdbtoexcel`, which doesn't read special slots.
