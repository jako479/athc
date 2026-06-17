# fbpro98_play — Test Matrix

Cases covered for the `.ply` parser library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_ply()` = constructed bytes, `golden` = real `.ply` in `data/`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_play` passes.

## reader.py — `parse_play` / `read_play`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid buffer parses; all fields + per-slot header | make_ply | stream_length, 3 category bytes, 11 offsets, 11 headers correct | `test_parses_minimal_valid_buffer` | ☑ |
| Real file parses; whole-file structure | golden | exact offsets + player-header tuples | `test_reads_real_fixture_structure` `[P]` | ☑ |
| Real-file structural invariants | golden | `len==8+stream_length`, 11 offsets, offsets[0]==25, sorted, >0, headers in-bounds | `test_real_fixture_invariants` `[P]` | ☑ |
| Category names resolve on real files (4 branches) | golden | off/def normal + off/def special-teams | `test_*_category_name` (4) | ☑ |
| Default path sentinel | make_ply | `file_path == Path("<buffer>")` | `test_default_path_sentinel` | ☑ |
| Explicit path | make_ply | `file_path == Path(path)` | `test_explicit_path` | ☑ |
| `read_play` accepts str + PathLike | tmp_path | parses; `file_path` set | `test_read_play_accepts_str_and_pathlike` | ☑ |

### Error → `InvalidPlayFileError`
| Case | Input | Expected message | Test | Status |
|---|---|---|---|---|
| Buffer < 8 bytes (incl. empty) | make_ply | "File too small to contain P95 header" | `test_rejects_short_header` `[P]` | ☑ |
| Wrong block id | make_ply | "Invalid header '…' at 0x0" | `test_rejects_bad_block_id` | ☑ |
| Non-ASCII block id | make_ply | bad id decoded with replacement | `test_bad_block_id_non_ascii_decodes` | ☑ |
| `len != 8 + stream_length` (too large / small) | make_ply | "File size … does not match" | `test_rejects_size_mismatch` `[P]` | ☑ |
| Size matches but < 33 bytes | make_ply | "File too small to contain play metadata" | `test_rejects_missing_metadata` | ☑ |
| Player offset past EOF | make_ply | "File too small to contain player header at 0x…" | `test_rejects_offset_past_eof` | ☑ |

### Error → other (not `InvalidPlayFileError`)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `read_play` on missing file | path | `FileNotFoundError` propagates | `test_read_play_missing_file` | ☑ |

### Edge
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Smallest buffer that parses (last header ends at EOF) | make_ply | parses; boundary holds | `test_parses_minimal_valid_buffer` | ☑ |
| Player offset = 0 (header at data base) | make_ply | parses; header read | `test_zero_offset_parses` | ☑ |

## model.py — `PlayFile` properties & `category_name`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `is_offensive`/`is_defensive` by parity | PlayFile | odd `play_category` → offensive; even → defensive | `test_odd…_offensive` / `test_even…_defensive` `[P]` | ☑ |
| `is_special_teams` | PlayFile | `special_category != 0` → True; `0` → False | `test_is_special_teams` | ☑ |
| Offensive normal category names | PlayFile | every `OFFENSIVE_CATEGORIES` code → name | `test_offensive_category_name` `[P]` | ☑ |
| Defensive normal category names | PlayFile | every `DEFENSIVE_CATEGORIES` code → name | `test_defensive_category_name` `[P]` | ☑ |
| Offensive special-teams names | PlayFile | every ST-offensive code → name | `test_offensive_special_teams_names` `[P]` | ☑ |
| Defensive special-teams names | PlayFile | every ST-defensive code → name | `test_defensive_special_teams_names` `[P]` | ☑ |

### Edge / Error
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Unknown normal code | PlayFile | `category_name is None` (off & def) | `test_unknown_normal_code_is_none` | ☑ |
| Unknown special code | PlayFile | `category_name is None` | `test_unknown_special_category_is_none` | ☑ |
| High bits 7–6 ignored | PlayFile | `0xC9` resolves same as `0x09` (mask `& 0x3F`) | `test_high_bits_are_masked` | ☑ |
| User Specific `0xFF`/`0xFE` | PlayFile | resolves to `"User Specific"` (fixed: full-byte lookup before mask) | `test_user_specific_resolves` | ☑ |

## schema.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Struct sizes | header 8, offsets 22, metadata 3, player-header 4 | `test_struct_sizes` | ☑ |
| Derived offsets | metadata at `0x1E` (30); player-data base 8 | `test_derived_offsets` | ☑ |
| Block id | `ID_P95 == b"P95:"` | `test_block_id` | ☑ |

---

## Resolved finding

**User Specific (`0xFF`/`0xFE`).** `category_name` masked `user_category & 0x3F`, but the tables key User Specific at the full byte `0xFF`/`0xFE`, so it always returned `None` — never noticed because PNFL plays are never User Specific, and the tool is meant to be league-agnostic. Fixed in `model.py` to look up the full byte first, falling back to the masked base, so `0xFF`/`0xFE` resolve while ordinary codes still match. Covered by `test_user_specific_resolves`.
