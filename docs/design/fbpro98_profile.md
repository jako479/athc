# fbpro98-profile

Library for reading and writing Front Page Sports Football Pro '98 coaching profile (`.prf`) files.

## Features

- `.prf` reader and writer
- Typed `Situation` (2520) and `PatSituation` (60)
- `SubstitutionSettings` (8 position groups)
- Stop-clock situation filter
- In-memory codec (`parse_profile` / `build_profile_bytes`)
- Rejects stock layout and embedded-gameplan variants

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_profile import read_profile, write_profile

profile = read_profile("TST-OFF1.prf")

profile.profile_type           # ProfileType.OFFENSE / DEFENSE
profile.field_goal_range       # int, 5-50
profile.use_audibles           # bool
profile.substitutions          # SubstitutionSettings (8 position groups)
profile.situations             # tuple of 2520 Situation
profile.pat_situations         # tuple of 60 PatSituation
profile.stop_clock_situations  # ((situation_number, Situation), ...) — situations with Stop-Clock set

# Save back to disk (update in place or write new path)
import dataclasses
modified = dataclasses.replace(profile, field_goal_range=45)
write_profile(modified, "TST-OFF1.prf")
```

`parse_profile(buffer)` is the bytes-in entry point; `build_profile_bytes(profile)` is the bytes-out entry point. `read_profile` and `write_profile` wrap file I/O.

## API

- `read_profile(path)` reads a `.prf` and returns a `Profile`; `write_profile(profile, path)` writes one. `parse_profile(buffer, path)` and `build_profile_bytes(profile)` are the bytes-in / bytes-out pair, `path` only naming the source in errors (`<path>: <reason>`).
- `Profile`: `profile_type` (`ProfileType.OFFENSE` / `DEFENSE`), `substitutions` (a `SubstitutionSettings` of eight `SubstitutionPair`s, each `out_percent` / `in_percent`; `SubstitutionSettings.default()` is the game's 80/90 for every group), `situations` (2520 `Situation`), `pat_situations` (60 `PatSituation`), `field_goal_range`, `use_audibles`; `is_offense` / `is_defense`; `stop_clock_situations`.
- `Situation`: `situation_number`, `minutes_remaining`, `down`, `yards_to_go`, `field_position`, `point_spread`, `stop_clock`, `category_weights`. `PatSituation`: `situation_number`, `minutes_remaining`, `point_spread`, `category_weights`. Both have `from_situation_number`. `CategoryWeights`: `play_category1` / `weight1` through `play_category3` / `weight3`. The buckets are the enums `MinutesRemaining`, `Down`, `YardsToGo`, `FieldPosition`, `PointSpread`, `PatMinutesRemaining` and `PatPointSpread`; `OFFENSE_DISPLAY_CATEGORIES` / `DEFENSE_DISPLAY_CATEGORIES` are the category codes the game labels on each side.
- `InvalidProfileError`: malformed bytes; the conditions are the validity rules in [`formats/prf.md`](../formats/prf.md).
- `UnsupportedProfileError`: a structurally valid profile in a variant the library does not handle:
  - **Stock layout** — the older format of game-shipped profiles (`OFF1.PRF`, `DEF1.PRF`), detected by an F95 size of `0x3F69` or `0x4509`. Re-saving a stock profile in the game converts it to the saved layout (`0x3C9D`).
  - **Embedded game plans** — a profile saved with game plans appended after I95, detected by a non-zero I95 game plan block count or a `G95:` / `J95:` / `S98:` ID after I95.
- The writer never emits either variant. It rebuilds every byte from the model, mirrors the field goal range and use audibles into I95, packs the Stop Clock flag into bit 7 of weight 1 and ends with the NUL trailer; `write_profile(read_profile(p), q)` reproduces `p` byte for byte.

## Testing

```bash
pytest
```

## How it works

### Module layout

```
src/athc/fbpro98_profile/
├── __init__.py    # public API re-exports
├── model.py       # Profile, Situation, PatSituation, CategoryWeights,
│                  # SubstitutionSettings/Pair, ProfileType, bucket enums
├── schema.py      # struct.Struct layouts and block IDs for F95/I95
├── reader.py      # read_profile / parse_profile; InvalidProfileError, UnsupportedProfileError
└── writer.py      # write_profile / build_profile_bytes
```

The domain (`model.py`) owns the situation-number ↔ game-state mapping (see [formats/prf.md section 2.3.4](../formats/prf.md#234-situation-number-layout) and [section 2.5.1](../formats/prf.md#251-pat-situation-number-layout)); `Situation.from_situation_number` and `PatSituation.from_situation_number` are the factories. The reader translates its 0-based array index at the boundary (`idx + 1`) and delegates; the math itself never leaves the domain.

`reader.py` and `writer.py` are pure functions of the model and schema — they share no state, only types. Round-trip byte identity is enforced by tests against four game-produced `TST-*.prf` fixtures.

### What this package does

- Reads `.prf` files into a typed in-memory model and writes them back, including in-place updates of existing files and from-scratch construction.
- Validates structural correctness on read (block magics, sizes, redundant F95/I95 agreement, trailer length and bytes, file-size parity).
- Decodes situation numbers into game-state buckets; exposes `Profile.stop_clock_situations` for situations with the Stop-Clock flag set.

### What this package does NOT do

- Handle the older "stock" on-disk layout — `F95.size` ∈ {`0x3F69`, `0x4509`} → `UnsupportedProfileError`.
- Handle profiles saved with embedded game plans — `I95.num_game_plan_blocks ≠ 0` or G95/J95/S98 magic after I95 → `UnsupportedProfileError`.

See [formats/prf.md](../formats/prf.md) sections 6-7 for the full reader validation and writer contract.

### Testing

- `tests/unit/fbpro98_profile/test_model.py` — model invariants on synthesized instances.
- `tests/unit/fbpro98_profile/test_reader.py` — real-fixture parsing pinned against expected metadata; structural-error paths.
- `tests/unit/fbpro98_profile/test_writer.py` — round-trip byte identity, mutation, and from-scratch construction.

Fixtures in `tests/unit/fbpro98_profile/data/` are game-produced and authoritative for any wire-format question. `.../data/stock_profiles/` holds real game-shipped stock profiles used only to confirm rejection.
