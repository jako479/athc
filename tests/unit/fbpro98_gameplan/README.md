# fbpro98_gameplan — Test Matrix

Covers reader / model / writer for the `.pln` gameplan library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). **Implemented** — `pytest tests/unit/fbpro98_gameplan` → 96 passing. Status: ☑ done. `[P]` = parametrized.

Inputs: game-saved `offense.pln` / `defense.pln` in `data/` (+ `data/expected/*_normal_by_slot.txt`, the 64-slot name dumps); the error tests mutate or cut a copy of the offense bytes (`offense_bytes` in `conftest.py`). `both_sides` in `conftest.py` runs a test on both files.

## reader.py — `test_reader.py`

### Valid (both fixtures unless noted)
| Area | Status |
|---|---|
| `profile_type` per side | ☑ |
| Normal plays: exact slot layout vs `expected/*_normal_by_slot.txt` | ☑ |
| Custom special plays of categories 1-10 (expected names inline) | ☑ |
| Clock categories 11/12: offense `RUNCLOCK` / `STOPCLOK` stock records in full; defense empty | ☑ |
| `parse_gameplan(bytes) == read_gameplan(path)`; `InvalidGamePlanError` is an `AthcError` | ☑ |

### Error → `InvalidGamePlanError`
| Case | Status |
|---|---|
| Path first in the message; audible bytes printed as hex; nonexistent path → `OSError` | ☑ |
| Truncation at each block's limit and one byte short `[P]`: header + offsets, G95 past EOF, J95, S98 header, S98 data past EOF | ☑ |
| G95 size one past EOF; exactly EOF passes on to the J95 check `[P]` | ☑ |
| Truncated play header; truncated stock play record (G95 end moved into the last record) | ☑ |
| Bad G95 / J95 / S98 block id, each naming its offset | ☑ |
| Play offset below the records; at the G95 end | ☑ |
| Missing null terminator; stock flag 2; unrecognized play category; custom record in a clock slot (model error wrapped, `<buffer>` path) | ☑ |
| J95 size 6 / 8 `[P]`; profile type 2; J95 count mismatch | ☑ |
| S98 size 11 / 13 `[P]`; S98 content | ☑ |
| Wrong parity, offense and defense `[P]` | ☑ |

## model.py — `test_model.py` (constructed `GamePlan`)
| Area | Status |
|---|---|
| `__post_init__`: slot counts (normal 63 / 65 and special 11 / 13 rejected `[P]`); stock-only clock categories by side; custom/stock typing; `special_category` alignment; side-of-ball parity (normal/special); special-in-normal-slot | ☑ |
| Properties `is_offense` / `is_defense` | ☑ |
| `custom_special_plays` view (10 entries, correct slots) | ☑ |
| `with_normal_plays` (pads to 64; 65 rejected) | ☑ |
| `with_custom_special_plays` (place by category, preserve stock and clock slots, order-independent, clears uncovered, reject stock, range ends 1 / 10 accepted and 0 / 11 rejected `[P]`, duplicate) | ☑ |
| `CustomPlayRef.name` stem extraction `[P]` | ☑ |

## writer.py — `test_writer.py`
| Area | Status |
|---|---|
| `build_gameplan_bytes` reproduces the file; `write_gameplan` round trip byte-identical; `with_normal_plays` round trip (both fixtures) | ☑ |
| Special plays survive a normal-plays write | ☑ |
| Empty slot → zero offset in the offsets table; `<64` pads; all 64 filled | ☑ |
| J95 counts follow the normal plays; a stock play in a normal slot counts as stock; custom special plays set the special count | ☑ |
| Pad to the side's parity (offense even, defense odd) `[P]` | ☑ |

No `test_schema.py`: the reader and writer tests pin every constant.
