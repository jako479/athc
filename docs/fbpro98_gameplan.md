# fbpro98-gameplan

Library for reading and writing Front Page Sports Football Pro '98 gameplan (`.pln`) files.

## Features

- `.pln` reader and writer
- Typed `CustomPlayRef` / `StockPlayRef` models
- Normal (64) and special-teams (12 categories, custom + stock) slots
- In-memory codec (`parse_gameplan` / `build_gameplan_bytes`)
- Structural validation (`InvalidGamePlanError`)

## Setup

```bash
uv sync
```

## Usage

### Reading

```python
from athc.fbpro98_gameplan import read_gameplan

plan = read_gameplan("DEN-OGP1.pln")

print(plan.profile_type, plan.is_offense)

# Two fixed-length tuples mirror the file structure:
# - normal_plays: 64 slots (None for empty)
# - special_plays: 12 SpecialSlot(custom, stock), one per special category;
#   11 Run Clock and 12 Stop Clock are stock-only (offense only)
for slot, play in enumerate(plan.normal_plays):
    if play is not None:
        print(slot, play.name)
```

Each filled slot is either a `CustomPlayRef` (a user-authored play, referenced by filename) or a `StockPlayRef` (a built-in play referenced into `STOCK98.MAP`). Both expose a `.name` property.

### Writing

```python
from athc.fbpro98_gameplan import CustomPlayRef, read_gameplan, write_gameplan

plan = read_gameplan("DEN-OGP1.pln")

new_normals = [
    CustomPlayRef(
        filename=r"PNFL\Offense\PSR\AF3ArshZ.ply",
        play_category=0x9B,
        special_category=0x00,
        user_category=0xB3,
    ),
    None,  # empty slot
    # ... up to 64 entries; trailing slots auto-fill with None
]

updated = plan.with_normal_plays(new_normals)
write_gameplan(updated, "DEN-OGP1.pln")
```

`with_normal_plays` returns a new `GamePlan` with only the normal-play slots replaced; special-teams slots are preserved. J95 counts and parity padding are recomputed by `write_gameplan`.

For special-teams updates, `with_custom_special_plays(plays)` places each `CustomPlayRef` into the category dictated by its own `special_category` (1-10); uncovered custom slots are cleared, order doesn't matter, out-of-range or duplicate category raises `ValueError`. Stock slots, the clock categories included, are immutable through the API.

### In-memory codec

`parse_gameplan(buffer)` and `build_gameplan_bytes(plan)` are the bytes-in / bytes-out entry points; `read_gameplan` / `write_gameplan` are thin file-I/O wrappers.

## API

- `read_gameplan(path)` reads a `.pln` and returns a `GamePlan`; `write_gameplan(gameplan, path)` writes one. `parse_gameplan(buffer, path)` and `build_gameplan_bytes(gameplan)` are the bytes-in / bytes-out pair, `path` only naming the source in errors (`<path>: <reason>`).
- `GamePlan`: `profile_type` (`ProfileType.OFFENSE` / `DEFENSE`), `normal_plays` (64 `PlayRef | None`), `special_plays` (12 `SpecialSlot`, one per special category), `audible`, `map_filename`; `is_offense` / `is_defense`; `custom_special_plays`; `with_normal_plays(plays)` and `with_custom_special_plays(plays)` return edited copies. Constructing one that breaks a structural invariant (slot counts, side of ball, special-category alignment, stock-only clock categories) raises `ValueError`.
- `CustomPlayRef`: `filename`, `play_category`, `special_category`, `user_category`, `name`. `StockPlayRef`: `play_name`, `map_offset`, `map_size`, the same three category bytes, `name`. `SpecialSlot`: `custom`, `stock`.
- `InvalidGamePlanError`: any structural deviation from the format; the conditions are the validity rules in [`formats/pln.md`](formats/pln.md).
- Writing recomputes the J95 counts and the parity pad; `write_gameplan(read_gameplan(p), q)` reproduces `p` byte for byte.

## Testing

```bash
pytest
```

## How it works

### Module layout

```
src/athc/fbpro98_gameplan/
├── __init__.py    # public API re-exports
├── model.py       # GamePlan, PlayRef (CustomPlayRef | StockPlayRef), ProfileType, invariants
├── reader.py      # parse_gameplan, read_gameplan, InvalidGamePlanError
├── writer.py      # build_gameplan_bytes, write_gameplan
└── schema.py      # struct format strings for G95/J95/S98 blocks
```

`formats/pln.md` documents the on-disk byte layout independently of this code.

### What this package does

- Parses `.pln` files into a typed in-memory model
- Validates structural correctness of the bytes (block magics, sizes, offsets, parity)
- Validates semantic correctness of the model (slot counts, stock-only clock categories by side, special-slot type/category alignment)
- Serializes a `GamePlan` back to bytes that round-trip identically
- Exposes a frozen, type-safe model for downstream consumers

### What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.pln` format
- All callers respect the immutability of `GamePlan` and use `with_normal_plays` / `with_custom_special_plays` for updates; special slots are read as `special_plays[category - 1].custom` / `.stock`

### What this package enforces

Structural (raise `InvalidGamePlanError`):
- File ≥ minimum size; `G95:` / `J95:` / `S98:` block magics
- Block declared sizes fit within file
- Audible bytes match expected default
- Play offsets within G95 record region; play headers/bodies not truncated
- Custom play filenames null-terminated
- `stock_flag` ∈ {0, 1}; `profile_type` ∈ {0, 1}
- Every play's category bytes resolve to a known category (`fbpro98_play.resolve_category`)
- J95 declared counts match actual play counts
- S98 data = `STOCK98.MAP\0`
- File-size parity (offense even, defense odd)

Model (raise `ValueError` via `__post_init__`):
- Exact slot counts: 64 normal, 12 special (`SpecialSlot(custom, stock)`, one per category)
- `custom` is `CustomPlayRef | None` and `stock` is `StockPlayRef | None`, each with `special_category` equal to its category
- Categories 11 (Run Clock) and 12 (Stop Clock) are stock-only: `custom` is None; offense requires their `stock`, defense forbids it
- Normal-slot plays have `special_category == 0`
- Play `play_category` parity matches profile (offense odd, defense even)

Mutation methods (raise `ValueError`):
- `with_normal_plays` accepts ≤ 64 entries
- `with_custom_special_plays` rejects a category outside 1-10 or a duplicate category

### What this package does NOT do

- Resolve play names to play-pool records (lives in `playpool`)
- Parse individual `.ply` play files (lives in `fbpro98_play`)
- CLI argument parsing or text I/O (lives in the gameplan CLI layer)
- Enforce uniqueness of plays across slots — the binary format permits duplicates, and a permissive reader is required for inspecting quirky files.

### Testing

- `tests/unit/fbpro98_gameplan/test_model.py` — `__post_init__` invariants on synthesized instances
- `tests/unit/fbpro98_gameplan/test_reader.py` — real-fixture parsing + structural error paths via byte-corrupted fixture copies
- `tests/unit/fbpro98_gameplan/test_writer.py` — round-trip byte equality + partial-update semantics of `with_normal_plays` / `with_custom_special_plays`

The fixture `.pln` files in `tests/data/` are game-produced — they are the authoritative ground truth for any wire-format question.
