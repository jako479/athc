# fbpro98_gameplan — Test Matrix

Covers reader / model / writer / schema for the `.pln` gameplan library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). Ported from the pnfl suite + athc additions. **Implemented** — `pytest tests/unit/fbpro98_gameplan` → 88 passing. Status: ☑ done.

Inputs: real `offense.pln` / `defense.pln` in `data/` (+ `data/expected/*.txt` slot/name dumps); error cases mutate the real bytes (no hand-built `.pln`).

## reader.py — `test_reader.py`

### Valid (real fixtures)
| Area | Status |
|---|---|
| `profile_type` / `is_offense` / `is_defense` (offense + defense) | ☑ |
| Normal plays: exact slot layout + sorted by-name list vs `expected/*.txt` | ☑ |
| Custom special plays match expected | ☑ |
| Clock plays: offense both present (cat 11/12); defense none | ☑ |
| Normal plays: `special_category == 0`, correct side-of-ball parity | ☑ |
| Special plays: alternate custom/stock, correct `special_category` | ☑ |
| API surface: counts (64/20/2), views (10/10) + types, `parse == read`, `CustomPlay.name` strips dir/ext | ☑ |

### Error → `InvalidGamePlanError` (mutated bytes)
| Case | Status |
|---|---|
| File too small; bad G95 id; G95 past EOF; bad audible; offset out of range | ☑ |
| Missing null terminator; invalid stock flag | ☑ |
| Bad J95 id/size; invalid profile type; J95 count mismatch | ☑ |
| Bad S98 id/size/content; wrong parity; nonexistent path → `OSError` | ☑ |
| **J95-block-too-small; S98-header-too-small** | ☑ *(added — pnfl missed)* |

## model.py — `test_model.py` (constructed `GamePlan`)
| Area | Status |
|---|---|
| `__post_init__`: slot counts (normal/special/clock); clock presence by side; special custom/stock pairing; `special_category` alignment; side-of-ball parity (normal/special/clock); special-in-normal-slot | ☑ |
| Properties `is_offense`/`is_defense` | ☑ |
| Custom/stock special views (10 each, correct slots) | ☑ |
| `with_normal_plays` (new instance, padding, too-many) | ☑ |
| `with_custom_special_plays` (place by category, preserve stock, order-independent, partial, reject stock, out-of-range, duplicate) | ☑ |
| `CustomPlay.name` stem extraction `[P]` | ☑ |

## writer.py — `test_writer.py` (round-trip via real fixtures)
| Area | Status |
|---|---|
| Byte-identical round-trip (offense + defense); `build_gameplan_bytes == file` | ☑ |
| Round-trip preserves normal + special plays | ☑ |
| Empty slot → zero offset; `<64` pads; all 64 filled | ☑ |
| J95 counts updated on write; too-many entries raises | ☑ |

## schema.py — `test_schema.py` *(added — pnfl had none)*
| Case | Status |
|---|---|
| Struct sizes; block IDs; `DEFAULT_AUDIBLE` / `S98_EXPECTED_DATA` | ☑ |

## Known gaps
Two deep defensive reader branches — `"Truncated play header"` and `"Truncated stock play record"` — aren't exercised; reaching them needs surgical byte construction past the earlier checks. Low priority.
