# fbpro98_profile — Test Matrix

Covers reader / model / writer / schema for the `.prf` coaching-profile library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). Ported from the pnfl suite + athc additions. **Implemented** — `pytest tests/unit/fbpro98_profile` → 154 passing. Status: ☑ done.

Inputs (`data/`): real `TST-OFF1/OFF2/DEF1/DEF2.prf`, `*-AUD.prf` (audibles on), `*-PL.prf` (gameplan-embedded), and `stock_profiles/*.PRF`. Error cases mutate real bytes.

## reader.py — `test_reader.py`

### Valid (pinned values across 4 fixtures + variants)
| Area | Status |
|---|---|
| `profile_type`, `field_goal_range`, `use_audibles`, situation counts | ☑ |
| Substitutions (all 8 groups) | ☑ |
| First/last `Situation` decoded game state; first/last `PatSituation` | ☑ |
| `stop_clock_situations`: count + first/last number (offense); empty (defense) | ☑ |
| `*-AUD` fixtures → `use_audibles is True` | ☑ |
| API surface: `read` returns `Profile`, `Situation` instances, `parse == read` | ☑ |

### Error (mutated bytes)
| Case | Status |
|---|---|
| `InvalidProfileError`: file too small; bad F95/I95 header; wrong F95/I95 data size; bad substitution pair; bad situation play_category/weight; F95/I95 field_goal_range + use_audibles out-of-range; invalid profile_type; nonzero reserved; F95↔I95 field_goal_range/use_audibles mismatch; bad/stock trailer byte; wrong trailer length | ☑ |
| `UnsupportedProfileError`: stock layout; real stock profile; embedded gameplan (count / G95-after-I95 / `*-PL` fixtures) | ☑ |
| Nonexistent path → `OSError` | ☑ |

## model.py — `test_model.py` (constructed)
| Area | Status |
|---|---|
| `SubstitutionPair`: valid; rejects out>in, out<0, in>100; equal allowed | ☑ |
| `SubstitutionSettings.default` = 80/90 | ☑ |
| `CategoryWeights`: valid; rejects play_category>max, weight>10, negative | ☑ |
| `Situation`: decode first/last; **round-trip every 1..2520**; reject out-of-range, 6-10/>10 yds inside DEF 5, mismatched number | ☑ |
| `PatSituation`: decode first/last; **round-trip every 1..60**; reject out-of-range, mismatched | ☑ |
| `Profile`: valid offense/defense; situations/pat wrong length; field_goal_range out-of-bounds + at-bounds | ☑ |
| `stop_clock_situations`: empty; only flagged; `(number, Situation)` pairs; excludes PAT | ☑ |

## writer.py — `test_writer.py` (round-trip + workflow)
| Area | Status |
|---|---|
| Byte-identical round-trip; `build_profile_bytes == file`; through-model | ☑ |
| Block sizes (F95/I95); trailer (offense 1 NUL, defense 2 NUL) | ☑ |
| Stop-clock bit packing (situation 372 weight1; PAT has none); I95 mirrors F95 fg-range/use_audibles | ☑ |
| Mutation round-trips (field_goal_range, use_audibles); `*-AUD` preserved | ☑ |
| Workflow: update existing in place; write new from scratch; reconstructed == fixture bytes (offense + defense) | ☑ |

## schema.py — `test_schema.py` *(added — pnfl had none)*
| Case | Status |
|---|---|
| Struct sizes; block IDs; data sizes; stock sizes; `STOP_CLOCK_BIT` / `WEIGHT_MASK` | ☑ |

## Known gaps
The reader's `"wrong parity"` branch isn't separately exercised — trailer-length validation runs first and likely makes it unreachable. The `"Invalid PAT situation record"` branch shares its shape with the regular situation-record test. Both low priority.
