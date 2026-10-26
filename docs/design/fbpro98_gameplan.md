# fbpro98-gameplan

Library for reading and writing Front Page Sports Football Pro '98 gameplan (`.pln`) files.

## Features

- `.pln` reader and writer
- Typed `CustomPlayRef` / `StockPlayRef` models, edited by assignment
- Normal (64) and special (12 categories, custom + stock) slots
- In-memory codec (`parse_gameplan` / `build_gameplan`)
- One `validate()` for every rule the format imposes
- Structural validation (`InvalidGamePlanError`)
- Atomic writes

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

# Two fixed-length lists mirror the file structure:
# - normal_plays: 64 slots (None for empty)
# - special_plays: 12 SpecialSlot(custom, stock), one per special category;
#   11 Run Clock and 12 Stop Clock are stock-only (offense only)
for slot, play in enumerate(plan.normal_plays):
    if play is not None:
        print(slot, play.name)
```

Each filled slot is either a `CustomPlayRef` (a user-authored play, referenced by filename) or a `StockPlayRef` (a built-in play referenced into `STOCK98.MAP`). Both expose a `.name` property.

### Editing and writing

```python
from athc.fbpro98_gameplan import CustomPlayRef, read_gameplan, write_gameplan

plan = read_gameplan("DEN-OGP1.pln")

plan.normal_plays[0] = CustomPlayRef(
    filename=r"PNFL\Offense\PSR\AF3ArshZ.ply",
    play_category=0x9B,
    special_category=0x00,
    user_category=0xB3,
)
plan.normal_plays[1] = None          # empty slot
plan.special_plays[4].custom = None  # special category 5 loses its custom play

plan.validate()                      # optional: write_gameplan runs it first
write_gameplan(plan, "DEN-OGP1.pln")
```

Edit by assignment: a slot of `normal_plays`, the `custom` or `stock` of a `special_plays` entry, a play's fields. Nothing is checked until `validate()` runs, so a plan may be edited in several steps; `write_gameplan` (through `build_gameplan`) runs it first and writes nothing when it fails. J95 counts and the parity pad are recomputed on write, and the file is written whole: the bytes go to a temp file beside it, swapped in once complete.

### In-memory codec

`parse_gameplan(buffer)` and `build_gameplan(plan)` are the bytes-in / bytes-out entry points; `read_gameplan` / `write_gameplan` are thin file-I/O wrappers.

## API

- `read_gameplan(path)` reads a `.pln` and returns a `GamePlan`; `write_gameplan(gameplan, path)` writes one atomically. `parse_gameplan(buffer, path)` and `build_gameplan(gameplan)` are the bytes-in / bytes-out pair, `path` only naming the source in errors (`<path>: <reason>`).
- `GamePlan`: `profile_type` (`ProfileType.OFFENSE` / `DEFENSE`), `normal_plays` (64 `PlayRef | None`), `special_plays` (12 `SpecialSlot`, one per special category), `audible`, `map_filename`; `is_offense` / `is_defense`; `custom_special_plays` (the custom play of categories 1-10, a list). `validate()` raises `ValueError` on the first rule the plan breaks, naming the slot or field and the value.
- `CustomPlayRef`: `filename`, `play_category`, `special_category`, `user_category`, `name`. `StockPlayRef`: `play_name`, `map_offset`, `map_size`, the same three category bytes, `name`. `SpecialSlot`: `custom`, `stock`.
- `InvalidGamePlanError`: any structural deviation from the format, and any model rule a parsed file breaks; the conditions are the validity rules in [`formats/pln.md`](../formats/pln.md).
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
├── model.py       # GamePlan + validate(), PlayRef (CustomPlayRef | StockPlayRef), ProfileType
├── reader.py      # parse_gameplan, read_gameplan, InvalidGamePlanError
├── writer.py      # build_gameplan, write_gameplan
└── schema.py      # struct format strings for G95/J95/S98 blocks
```

`formats/pln.md` documents the on-disk byte layout independently of this code. The library follows the file-library conventions in [architecture.md](architecture.md#file-libraries).

### What this package does

- Parses `.pln` files into a typed, mutable in-memory model
- Validates structural correctness of the bytes (block magics, sizes, offsets, parity)
- Validates the model in one place, `GamePlan.validate()`, on read and before every write
- Serializes a `GamePlan` back to bytes that round-trip identically, and writes the file whole or not at all

### What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.pln` format
- Callers edit a `GamePlan` by assignment and read special slots as `special_plays[category - 1].custom` / `.stock`; a caller that wants two independent plans deep-copies one

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

Model (`GamePlan.validate()` raises `ValueError`; a parsed file that breaks one raises `InvalidGamePlanError`):
- `profile_type` is 0 or 1
- Exact slot counts: 64 normal, 12 special (`SpecialSlot(custom, stock)`, one per category)
- `custom` is `CustomPlayRef | None` and `stock` is `StockPlayRef | None`, each with `special_category` equal to its category
- Categories 11 (Run Clock) and 12 (Stop Clock) are stock-only: `custom` is None; offense requires their `stock`, defense forbids it
- Play `play_category` parity matches profile (offense odd, defense even)
- Normal-slot plays have `special_category == 0`
- Each play's category bytes are 0-255 and name a known category; a custom play's `filename` is ASCII without NUL; a stock play's `play_name` is at most 8 ASCII characters, its `map_offset` fits a u32 and its `map_size` a u16
- `audible` is `00 01 02 03` and `map_filename` is `STOCK98.MAP`, as the game writes them
- The play records fit the offsets table: each record's offset, counted from the table's start, is at most 65,535

### What this package does NOT do

- Resolve play names to play-pool records (lives in `playpool`)
- Parse individual `.ply` play files (lives in `fbpro98_play`)
- CLI argument parsing or text I/O (lives in the gameplan CLI layer)
- Enforce uniqueness of plays across slots — the binary format permits duplicates, and a permissive reader is required for inspecting quirky files.

### Testing

- `tests/unit/fbpro98_gameplan/test_model.py` — `validate()` on synthesized instances: every rule, each limit at the limit and one past it; editing by assignment
- `tests/unit/fbpro98_gameplan/test_reader.py` — real-fixture parsing + structural error paths via byte-corrupted fixture copies
- `tests/unit/fbpro98_gameplan/test_writer.py` — round-trip byte equality, edits by assignment read back, a refused write, no temp file left

The fixture `.pln` files in `tests/unit/fbpro98_gameplan/data/` are game-produced — they are the authoritative ground truth for any wire-format question.
