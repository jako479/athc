# fbpro98-gameplan — Architecture

Library that owns the FbPro '98 `.pln` gameplan binary file format end-to-end.

## Module layout

```
src/athc/fbpro98_gameplan/
├── __init__.py    # public API re-exports
├── model.py       # GamePlan, PlayRef (CustomPlayRef | StockPlayRef), ProfileType, invariants
├── reader.py      # parse_gameplan, read_gameplan, InvalidGamePlanError
├── writer.py      # build_gameplan_bytes, write_gameplan
└── schema.py      # struct format strings for G95/J95/S98 blocks
```

`specs/pln.md` documents the on-disk byte layout independently of this code.

## What this package does

- Parses `.pln` files into a typed in-memory model
- Validates structural correctness of the bytes (block magics, sizes, offsets, parity)
- Validates semantic correctness of the model (slot counts, stock-only clock categories by side, special-slot type/category alignment)
- Serializes a `GamePlan` back to bytes that round-trip identically
- Exposes a frozen, type-safe model for downstream consumers

## What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.pln` format
- All callers respect the immutability of `GamePlan` and use `with_normal_plays` / `with_custom_special_plays` for updates; special slots are read as `special_plays[category - 1].custom` / `.stock`

## What this package enforces

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

## What this package does NOT do

- Resolve play names to play-pool records (lives in `playpool`)
- Parse individual `.ply` play files (lives in `fbpro98_play`)
- CLI argument parsing or text I/O (lives in the gameplan CLI layer)
- Enforce uniqueness of plays across slots — the binary format permits duplicates, and a permissive reader is required for inspecting quirky files.

## Testing

- `tests/unit/fbpro98_gameplan/test_model.py` — `__post_init__` invariants on synthesized instances
- `tests/unit/fbpro98_gameplan/test_reader.py` — real-fixture parsing + structural error paths via byte-corrupted fixture copies
- `tests/unit/fbpro98_gameplan/test_writer.py` — round-trip byte equality + partial-update semantics of `with_normal_plays` / `with_custom_special_plays`

The fixture `.pln` files in `tests/data/` are game-produced — they are the authoritative ground truth for any wire-format question.
