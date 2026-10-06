# fbpro98_lg2 — Test Matrix

Cases covered for the `.lg2` league file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_team()` = constructed bytes, `golden` = real `.lg2` in `data/` (`PNFL.lg2` custom, `NFLPI97.LG2` modern stock, `08_TEAMS.LG2` old stock). Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_lg2` → 34 passing.

## reader.py — `parse_lg2` / `read_lg2`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league team count | golden | 18 teams | `test_custom_league_team_count` | ☑ |
| Custom league files, incl. leftover text and a shared game plan | golden | teams 0, 5, 17 exact | `test_custom_league_team_files` `[P]` | ☑ |
| `read` returns `Lg2File`; `parse == read` | golden | equal | `test_read_returns_lg2_file_and_matches_parse` | ☑ |
| `read` accepts a `str` path | golden | equal to `Path` | `test_read_accepts_str_path` | ☑ |

### Stock leagues → `UnsupportedLg2Error`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Modern and old stock | golden | "Modern stock league" / "Old stock league" | `test_stock_league_rejected` `[P]` | ☑ |
| Stock folder on a later entry | make_team | read; `STOCK\…` or bare filename | `test_stock_folder_on_later_entry_is_read` `[P]` | ☑ |
| Stock folder on the second team | make_team | read | `test_stock_folder_on_second_team_is_read` | ☑ |
| `STOCK` without the full signature | make_team | read as custom | `test_stock_folder_without_full_signature_is_custom` `[P]` | ☑ |

### Check order: size, then stock, then fields
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Stock signature, size short by one | make_team | `InvalidLg2Error` "not a whole number" | `test_size_checked_before_stock` | ☑ |
| Stock signature, empty filename later | make_team | `UnsupportedLg2Error` | `test_stock_checked_before_fields` | ☑ |

### Limits → `InvalidLg2Error`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty file | bytes | "Empty file" | `test_empty_file_rejected` | ☑ |
| Size 4,192, 4,194 | make_team | "not a whole number" | `test_size_not_whole_team_records_rejected` `[P]` | ☑ |
| Size 4,193 (one team) | make_team | 1 team | `test_one_team_record_accepted` | ☑ |
| Folder 260 chars + NUL / 261 with no NUL | make_team | accepted / "No NUL in folder" | `test_folder_at_max_length_accepted` / `test_folder_without_nul_rejected` | ☑ |
| Filename 261 chars + NUL / 262 with no NUL | make_team | accepted / "No NUL in filename" | `test_filename_at_max_length_accepted` / `test_filename_without_nul_rejected` | ☑ |
| Filename 1 char / empty | make_team | accepted / "Empty filename" | `test_one_character_filename_accepted` / `test_empty_filename_rejected` | ☑ |

### Edge
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Later team with no files (all zeros) | make_team | "Empty filename" | `test_team_with_no_files_rejected` | ☑ |
| Non-ASCII byte | make_team | decoded as U+FFFD | `test_non_ascii_byte_decodes_as_replacement` | ☑ |
| Error names the path | make_team | "in league.lg2" | `test_error_names_the_path` | ☑ |
| Missing file | path | `OSError` propagates | `test_missing_file_raises_oserror` | ☑ |

## model.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Nested access | half → side → profile / gameplan | `test_nested_access` | ☑ |
| Frozen | assignment raises | `test_frozen` | ☑ |

## schema.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Field and record sizes | folder `0x105`, filename `0x106`, entry `0x20B`, 8 per team, trailer 9, team `0x1061` | `test_field_and_record_sizes` | ☑ |
| Stock signatures | modern `STOCK\0A\FBPRO97\STOCK\0`, old `\0` | `test_stock_signatures` | ☑ |
