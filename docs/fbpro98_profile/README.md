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
- `InvalidProfileError`: malformed bytes; the conditions are the validity rules in [`specs/prf.md`](specs/prf.md).
- `UnsupportedProfileError`: a structurally valid profile in a variant the library does not handle:
  - **Stock layout** — the older format of game-shipped profiles (`OFF1.PRF`, `DEF1.PRF`), detected by an F95 size of `0x3F69` or `0x4509`. Re-saving a stock profile in the game converts it to the saved layout (`0x3C9D`).
  - **Embedded game plans** — a profile saved with game plans appended after I95, detected by a non-zero I95 game plan block count or a `G95:` / `J95:` / `S98:` ID after I95.
- The writer never emits either variant. It rebuilds every byte from the model, mirrors the field goal range and use audibles into I95, packs the Stop Clock flag into bit 7 of weight 1 and ends with the NUL trailer; `write_profile(read_profile(p), q)` reproduces `p` byte for byte.

## Testing

```bash
pytest
```
