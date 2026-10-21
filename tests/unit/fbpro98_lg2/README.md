# fbpro98_lg2 — Test Matrix

Cases covered for the `.lg2` league file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_team()` = constructed bytes, `golden` = real `.lg2` in `data/` (`PNFL.lg2` custom, `NFLPI97.LG2` modern stock, `08_TEAMS.LG2` old stock). Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_lg2` → 38 passing.

## reader.py — `parse_lg2` / `read_lg2`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league team count | golden | 18 teams | `test_custom_league_team_count` | ☑ |
| Custom league files, incl. leftover text and a shared game plan | golden | teams 0, 5, 17 exact | `test_custom_league_team_files` `[P]` | ☑ |
| `read` returns `Lg2File`; `parse == read` | golden | equal | `test_read_returns_lg2_file_and_matches_parse` | ☑ |
| `read` accepts a `str` folder | golden | equal to `Path` | `test_read_accepts_str_league_dir` | ☑ |
| Custom league type | golden | `CUSTOM` | `test_custom_league_type` | ☑ |

### Stock leagues
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Modern stock type and team count | golden | `MODERN_STOCK`, 30 teams | `test_modern_stock_league_type_and_team_count` | ☑ |
| Modern stock files | golden | teams 0, 1, 29 exact, under `STOCK` | `test_modern_stock_league_team_files` `[P]` | ☑ |
| Old stock | golden | `OLD_STOCK`; 8 teams, same bare filenames | `test_old_stock_league` | ☑ |

### League type: the first entry's folder field decides
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Full modern signature / empty folder on entry 1 | make_team | `MODERN_STOCK` / `OLD_STOCK`; other entries keep their folder | `test_first_entry_decides_league_type` `[P]` | ☑ |
| Stock folder on a later entry | make_team | `CUSTOM`; `STOCK\…` or bare filename | `test_stock_folder_on_later_entry_is_read` `[P]` | ☑ |
| Stock folder on the second team | make_team | `CUSTOM` | `test_stock_folder_on_second_team_is_read` | ☑ |
| `STOCK` without the full signature, or one character past it | make_team | `CUSTOM` | `test_stock_folder_without_full_signature_is_custom` `[P]` | ☑ |

### Stock leagues get the same checks
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Stock signature, size short by one | make_team | `InvalidLg2Error` "not a whole number" | `test_stock_league_size_checked` | ☑ |
| Modern / old stock, empty filename later | make_team | `InvalidLg2Error` "Empty filename" | `test_stock_league_fields_checked` `[P]` | ☑ |

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
| Error names the path first | make_team | "league.lg2: ..." and `.path` | `test_error_names_the_path_first` | ☑ |
| Missing file | league + tmp folder | `OSError` naming `<league_dir>/<league>.lg2` | `test_missing_file_raises_oserror_for_built_path` | ☑ |

No `test_model.py` and no `test_schema.py`: the model has no logic, and the reader tests pin every constant.
