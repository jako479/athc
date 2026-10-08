# pdbtoexcel — Test Matrix

Tool-logic unit cases. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). CLI cases: [../../integration/README.md](../../integration/README.md).

One row per behavior. `[P]` = parametrized. Input: `real` = `2045-2047.pdb` + `.plays.json` snapshot; `synth` = constructed PDB bytes (`write_pdb`); `pool` = injected fake `PlayPool` (`make_record`/`make_pool`); `pln` = real `offense.pln`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/pdbtoexcel` passes.

## pdb.py — `PDB` parser
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real file matches snapshot | real | normalized plays == JSON | `test_real_pdb_matches_snapshot` | ☑ |
| Real tendencies + sample plays | real | 23 tendencies; known keys | `test_real_pdb_tendencies_and_samples` | ☑ |
| Bad record-type byte | synth | `InvalidPDBError` | `test_invalid_data_type_raises` | ☑ |
| Duplicate (team, play) merges | synth | counts summed via `+=` | `test_duplicate_play_merges` | ☑ |
| RENAMED_PLAYS rewritten | synth | new name keyed | `test_renamed_play_is_rewritten` | ☑ |
| RUNCLOCK/STOPCLOK skipped | synth | not stored | `test_clock_plays_skipped` | ☑ |
| `PLAY_DATA` `+=` / `is_valid` | — | merge sums; empty invalid | `test_play_data_iadd_and_is_valid` | ☑ |
| `convert_invalid_play_data` | synth + pool | misclassified run → pass; yards → sacks | `test_convert_invalid_moves_misclassified_run_to_pass` | ☑ |

## config.py
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Default order uses game names | — | run/pass/defense game cats; no overlap | `test_default_category_order_uses_game_names` | ☑ |
| Defaults (league folder, no league.ini) | folder | play_path ""; options True; rules None | `test_load_config_defaults` | ☑ |
| From the league folder | `league.ini` + `playpool.toml` | play_path / playpool_rules resolved | `test_load_config_from_league_folder` | ☑ |
| Needs a league | no league selected | `LeagueError` | `test_load_config_needs_a_league` | ☑ |
| `playpool.toml` next to athc.ini ignored | `<config dir>/playpool.toml`, no league file | `None` | `test_playpool_toml_next_to_athc_ini_is_ignored` | ☑ |
| No rules anywhere | folder only | `None` | `test_no_playpool_rules_anywhere_is_none` | ☑ |
| Workbook options from `[convert-pdb]` | athc.ini + folder | all three flipped | `test_load_config_reads_workbook_options` | ☑ |
| Workbook options without the section | folder | True / False / True | `test_workbook_options_default_without_section` | ☑ |
| configparser booleans accepted | `1/yes/true/on`, `0/no/false/off`, any case | parsed | `test_workbook_option_accepts_configparser_booleans` `[P]` | ☑ |
| Other boolean spelling | `maybe` | `ConfigFileError` names the key | `test_workbook_option_rejects_other_values` | ☑ |
| `calculate_total_stats` no longer read | leftover key, bad value | ignored; no such option | `test_calculate_total_stats_is_no_longer_read` | ☑ |

## workbook_creator + excel_workbook (read back with openpyxl)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Base sheets + run row | synth + pool | 5 sheets; team/category/stats | `test_base_sheets_and_run_row` | ☑ |
| Pass row: Screen + comp/att | synth + pool | "Screen"; att excludes sacks | `test_pass_row_screen_and_stats` | ☑ |
| Defense row: front Type | synth + pool | `defensive_front` value; total calls | `test_defense_row_front_type` | ☑ |
| Run row: QB draw Type | synth + pool | "QB draw" | `test_qb_draw_type` | ☑ |
| `--skip-calcs` omits % columns | synth + pool | no "Fumble %" header | `test_skip_calcs_omits_percent_columns` | ☑ |
| Totals add "Total Stats" team | synth + pool | summed team present | `test_totals_adds_total_stats_team` | ☑ |
| Category worksheets when enabled | synth + pool | "Run Categories" sheet + row | `test_category_worksheets_when_enabled` | ☑ |
| Special-teams / unknown skipped | synth + pool | absent from sheets | `test_special_teams_and_unknown_plays_skipped` | ☑ |
| Tendencies written | synth | 16 rows per team | `test_tendencies_written` | ☑ |
| Slot column from gameplan | synth + pool + pln | slot 0 → "1-1" | `test_slot_column_from_gameplan` | ☑ |

Notes: grouping is by **game category** (not `pool_category`). Exact percentage-cell values aren't asserted (column presence + the underlying counts are).
