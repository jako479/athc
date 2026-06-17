# fbpro98-profile — Architecture

Library that owns the FbPro '98 `.prf` coaching profile binary file format — reading and writing.

## Module layout

```
src/athc/fbpro98_profile/
├── __init__.py    # public API re-exports
├── model.py       # Profile, Situation, PatSituation, CategoryWeights,
│                  # SubstitutionSettings/Pair, ProfileType, bucket enums
├── schema.py      # struct.Struct layouts and block IDs for F95/I95
├── reader.py      # read_profile / parse_profile; InvalidProfileError, UnsupportedProfileError
└── writer.py      # write_profile / build_profile_bytes
```

The domain (`model.py`) owns the situation-number ↔ game-state mapping (see [specs/prf.md section 2.3.4](specs/prf.md#234-situation-number-layout) and [section 2.5.1](specs/prf.md#251-pat-situation-number-layout)); `Situation.from_situation_number` and `PatSituation.from_situation_number` are the factories. The reader translates its 0-based array index at the boundary (`idx + 1`) and delegates; the math itself never leaves the domain.

`reader.py` and `writer.py` are pure functions of the model and schema — they share no state, only types. Round-trip byte identity is enforced by tests against four game-produced `TST-*.prf` fixtures.

## What this package does

- Reads `.prf` files into a typed in-memory model and writes them back, including in-place updates of existing files and from-scratch construction.
- Validates structural correctness on read (block magics, sizes, redundant F95/I95 agreement, trailer length and bytes, file-size parity).
- Decodes situation numbers into game-state buckets; exposes `Profile.stop_clock_situations` for situations with the Stop-Clock flag set.

## What this package does NOT do

- Handle the older "stock" on-disk layout — `F95.size` ∈ {`0x3F69`, `0x4509`} → `UnsupportedProfileError`.
- Handle profiles saved with embedded game plans — `I95.num_game_plan_blocks ≠ 0` or G95/J95/S98 magic after I95 → `UnsupportedProfileError`.

See [specs/prf.md](specs/prf.md) sections 6-7 for the full reader validation and writer contract.

## Testing

- `tests/unit/fbpro98_profile/test_model.py` — model invariants on synthesized instances.
- `tests/unit/fbpro98_profile/test_reader.py` — real-fixture parsing pinned against expected metadata; structural-error paths.
- `tests/unit/fbpro98_profile/test_writer.py` — round-trip byte identity, mutation, and from-scratch construction.

Fixtures in `tests/unit/fbpro98_profile/data/` are game-produced and authoritative for any wire-format question. `.../data/stock_profiles/` holds real game-shipped stock profiles used only to confirm rejection.
