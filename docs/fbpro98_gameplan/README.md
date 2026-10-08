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

- `read_gameplan(path)` reads a `.pln` and returns a `GamePlan`; `write_gameplan(gameplan, path)` writes one. `parse_gameplan(buffer, path)` and `build_gameplan_bytes(gameplan)` are the bytes-in / bytes-out pair, `path` only naming the source in errors.
- `GamePlan`: `profile_type` (`ProfileType.OFFENSE` / `DEFENSE`), `normal_plays` (64 `PlayRef | None`), `special_plays` (12 `SpecialSlot`, one per special category), `audible`, `map_filename`; `is_offense` / `is_defense`; `custom_special_plays`; `with_normal_plays(plays)` and `with_custom_special_plays(plays)` return edited copies. Constructing one that breaks a structural invariant (slot counts, side of ball, special-category alignment, stock-only clock categories) raises `ValueError`.
- `CustomPlayRef`: `filename`, `play_category`, `special_category`, `user_category`, `name`. `StockPlayRef`: `play_name`, `map_offset`, `map_size`, the same three category bytes, `name`. `SpecialSlot`: `custom`, `stock`.
- `InvalidGamePlanError`: any structural deviation from the format; the conditions are the validity rules in [`specs/pln.md`](specs/pln.md).
- Writing recomputes the J95 counts and the parity pad; `write_gameplan(read_gameplan(p), q)` reproduces `p` byte for byte.

## Testing

```bash
pytest
```
