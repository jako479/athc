# fbpro98_gameplan — Test Matrix

Covers reader / model / writer / schema for the `.pln` gameplan library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). **Implemented** — `pytest tests/unit/fbpro98_gameplan` → 96 passing. Status: ☑ done.

Inputs: real `offense.pln` / `defense.pln` in `data/` (+ `data/expected/*.txt` slot/name dumps); error cases mutate the real bytes (no hand-built `.pln`).

## reader.py — `test_reader.py`

### Valid (real fixtures)
| Area | Status |
|---|---|
| `profile_type` / `is_offense` / `is_defense` (offense + defense) | ☑ |
| Normal plays: exact slot layout + sorted by-name list vs `expected/*.txt` | ☑ |
| Custom special plays match expected | ☑ |
| Clock categories 11/12: offense stock `RUNCLOCK` / `STOPCLOK`, no custom; defense empty | ☑ |
| Normal plays: `special_category == 0`, correct side-of-ball parity | ☑ |
| Special slots: typed custom/stock, each carrying its category | ☑ |
| API surface: counts (64/12), `custom_special_plays` (10, custom-or-None), `parse == read`, `CustomPlayRef.name` strips dir/ext | ☑ |

### Error → `InvalidGamePlanError` (mutated bytes)
| Case | Status |
|---|---|
| File too small; bad G95 id; G95 past EOF; bad audible; offset out of range | ☑ |
| Missing null terminator; invalid stock flag | ☑ |
| Bad J95 id/size; invalid profile type; J95 count mismatch | ☑ |
| Bad S98 id/size/content; wrong parity; nonexistent path → `OSError` | ☑ |
| **J95-block-too-small; S98-header-too-small** | ☑ |
| Unrecognized play category; custom record in a clock slot | ☑ |

## model.py — `test_model.py` (constructed `GamePlan`)
| Area | Status |
|---|---|
| `__post_init__`: slot counts (normal 64; special 12, 11 and 13 rejected); stock-only clock categories by side; custom/stock typing; `special_category` alignment; side-of-ball parity (normal/special); special-in-normal-slot | ☑ |
| Properties `is_offense`/`is_defense` | ☑ |
| `custom_special_plays` view (10, correct slots) | ☑ |
| `with_normal_plays` (new instance, padding, too-many) | ☑ |
| `with_custom_special_plays` (place by category, preserve stock and clock slots, order-independent, clears uncovered, reject stock, range ends 1/10 accepted and 0/11 rejected, duplicate) | ☑ |
| `CustomPlayRef.name` stem extraction `[P]` | ☑ |

## writer.py — `test_writer.py` (round-trip via real fixtures)
| Area | Status |
|---|---|
| Byte-identical round-trip (offense + defense); `build_gameplan_bytes == file` | ☑ |
| Round-trip preserves normal + special plays | ☑ |
| Empty slot → zero offset; `<64` pads; all 64 filled | ☑ |
| J95 counts updated on write; too-many entries raises | ☑ |

## schema.py — `test_schema.py`
| Case | Status |
|---|---|
| Struct sizes; block IDs; `DEFAULT_AUDIBLE` / `S98_EXPECTED_DATA` | ☑ |

## Known gaps
Two deep defensive reader branches — `"Truncated play header"` and `"Truncated stock play record"` — aren't exercised; reaching them needs surgical byte construction past the earlier checks. Low priority.
