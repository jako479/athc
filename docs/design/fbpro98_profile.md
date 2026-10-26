# fbpro98-profile

Library for reading and writing Front Page Sports Football Pro '98 coaching profile (`.prf`) files.

## Features

- `.prf` reader and writer
- Typed `Situation` (2520) and `PatSituation` (60), edited by assignment
- Game state decoded from a situation's place in the profile
- `SubstitutionSettings` (8 position groups)
- Stop-clock situation filter
- In-memory codec (`parse_profile` / `build_profile`)
- One `validate()` for every rule the format imposes
- Rejects stock layout and embedded-gameplan variants
- Atomic writes

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
profile.situations             # list of 2520 Situation; situations[number - 1]
profile.pat_situations         # list of 60 PatSituation
profile.iter_situations()      # (number, GameState, Situation) for every slot
profile.stop_clock_situations  # [(number, GameState, Situation), ...] — situations with Stop-Clock set
Profile.game_state(8)          # GameState of situation 8

# Edit by assignment, then save back (in place or to a new path)
profile.field_goal_range = 45
profile.situations[7].stop_clock = True
profile.substitutions.quarterbacks.out_percent = 70
profile.validate()             # optional: write_profile runs it first
write_profile(profile, "TST-OFF1.prf")
```

`parse_profile(buffer)` is the bytes-in entry point; `build_profile(profile)` is the bytes-out entry point. `read_profile` and `write_profile` wrap file I/O. Nothing is checked until `validate()` runs, so a profile may be edited in several steps; `write_profile` (through `build_profile`) runs it first and writes nothing when it fails, and writes the file whole: the bytes go to a temp file beside it, swapped in once complete.

## API

- `read_profile(path)` reads a `.prf` and returns a `Profile`; `write_profile(profile, path)` writes one atomically. `parse_profile(buffer, path)` and `build_profile(profile)` are the bytes-in / bytes-out pair, `path` only naming the source in errors (`<path>: <reason>`).
- `Profile`: `profile_type` (`ProfileType.OFFENSE` / `DEFENSE`), `substitutions` (a `SubstitutionSettings` of eight `SubstitutionPair`s, each `out_percent` / `in_percent`; `SubstitutionSettings.default()` is the game's 80/90 for every group, each its own object; `pairs()` walks the groups in file order), `situations` (2520 `Situation`), `pat_situations` (60 `PatSituation`), `field_goal_range`, `use_audibles`; `is_offense` / `is_defense`; `iter_situations()` / `iter_pat_situations()`; `stop_clock_situations`. `validate()` raises `ValueError` on the first rule the profile breaks, naming the record or field and the value.
- `Situation`: `stop_clock`, `category_weights`. `PatSituation`: `category_weights`. A situation's number is its place in the list, from 1.
- `Profile.game_state(number)` decodes a situation number (1-2520) into a `GameState`: `minutes_remaining`, `down`, `yards_to_go`, `field_position`, `point_spread`. `Profile.pat_game_state(number)` decodes a PAT number (1-60) into a `PatGameState`: `minutes_remaining`, `point_spread`. A number outside the range raises `ValueError`.
- `iter_situations()` / `iter_pat_situations()` walk every slot in order as `(number, state, situation)`. `stop_clock_situations` is the walk's entries with Stop Clock set.
- `CategoryWeights`: `play_category1` / `weight1` through `play_category3` / `weight3`. The buckets are the enums `MinutesRemaining`, `Down`, `YardsToGo`, `FieldPosition`, `PointSpread`, `PatMinutesRemaining` and `PatPointSpread`; `OFFENSE_DISPLAY_CATEGORIES` / `DEFENSE_DISPLAY_CATEGORIES` are the category codes the game labels on each side.
- `InvalidProfileError`: malformed bytes, and any model rule a parsed file breaks; the conditions are the validity rules in [`formats/prf.md`](../formats/prf.md).
- `UnsupportedProfileError`: a structurally valid profile in a variant the library does not handle:
  - **Stock layout** — the older format of game-shipped profiles (`OFF1.PRF`, `DEF1.PRF`), detected by an F95 size of `0x3F69` or `0x4509`. Re-saving a stock profile in the game converts it to the saved layout (`0x3C9D`).
  - **Embedded game plans** — a profile saved with a game plan holds a G95 + S98 pair where a plain profile's I95 sits, then I95; detected by a non-zero I95 game plan block count or a `G95:` / `J95:` / `S98:` ID in I95's place or after it.
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
├── model.py       # Profile + validate(), Situation, PatSituation, GameState, PatGameState,
│                  # CategoryWeights, SubstitutionSettings/Pair, ProfileType,
│                  # bucket enums
├── schema.py      # struct.Struct layouts and block IDs for F95/I95
├── reader.py      # read_profile / parse_profile; InvalidProfileError, UnsupportedProfileError
└── writer.py      # write_profile / build_profile
```

The library follows the file-library conventions in [architecture.md](architecture.md#file-libraries). A situation is its place in the profile: `Profile.game_state` and `Profile.pat_game_state` in `model.py` hold the number-to-game-state mapping (see [formats/prf.md section 2.3.4](../formats/prf.md#234-situation-number-layout) and [section 2.5.1](../formats/prf.md#251-pat-situation-number-layout)), and the walks use them. A `Situation` stores no number or game state; the reader builds each from its record's bytes alone.

`reader.py` and `writer.py` are pure functions of the model and schema — they share no state, only types. Round-trip byte identity is enforced by tests against six game-produced `TST-*.prf` fixtures.

### What this package does

- Reads `.prf` files into a typed, mutable in-memory model and writes them back, including in-place updates of existing files and from-scratch construction; a write is whole or nothing.
- Validates structural correctness on read (block magics, sizes, redundant F95/I95 agreement, trailer length and bytes), then the model in one place, `Profile.validate()`: the profile type; 2520 situations and 60 PAT situations; the field goal range 5-50; each substitution pair 0-100 with out at most in; each record's play categories 0x00-0x1A and weights 0-10. The same `validate()` runs before every write.
- Decodes situation numbers into game-state buckets; walks the situations with their numbers and game states; exposes `Profile.stop_clock_situations` for situations with the Stop-Clock flag set.

### What this package does NOT do

- Handle the older "stock" on-disk layout — `F95.size` ∈ {`0x3F69`, `0x4509`} → `UnsupportedProfileError`.
- Handle profiles saved with embedded game plans — `I95.num_game_plan_blocks ≠ 0` or G95/J95/S98 magic in I95's place or after I95 → `UnsupportedProfileError`.

See [formats/prf.md](../formats/prf.md) sections 6-7 for the full reader validation and writer contract.

### Testing

- `tests/unit/fbpro98_profile/test_model.py` — `validate()` on synthesized instances: every rule, each limit at the limit and one past it; editing by assignment.
- `tests/unit/fbpro98_profile/test_reader.py` — real-fixture parsing pinned against expected metadata; structural-error paths.
- `tests/unit/fbpro98_profile/test_writer.py` — round-trip byte identity, edits by assignment read back, from-scratch construction, a refused write, no temp file left.

Fixtures in `tests/unit/fbpro98_profile/data/` are game-produced and authoritative for any wire-format question. `.../data/stock_profiles/` holds real game-shipped stock profiles used only to confirm rejection.
