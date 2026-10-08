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
| Defaults (league folder with labels + order only) | folder | play_path ""; options True; rules None; no deleted plays | `test_load_config_defaults` | ☑ |
| From the league folder | `league.toml` + `playpool.toml` | play_path / playpool_rules resolved | `test_load_config_from_league_folder` | ☑ |
| Needs a league | no league selected | `LeagueError` | `test_load_config_needs_a_league` | ☑ |
| `playpool.toml` next to athc.ini ignored | `<config dir>/playpool.toml`, no league file | `None` | `test_playpool_toml_next_to_athc_ini_is_ignored` | ☑ |
| Category order in file order | PNFL `pdbtoexcel.toml` | run/pass/defense enum members as listed | `test_category_order_in_file_order` | ☑ |
| Unlabeled category by game name | `"Razzle Dazzle Run"` | resolves | `test_unlabeled_category_goes_by_its_game_name` | ☑ |
| Labeled category by game name | `"Run Left"` with RL labeled | `ConfigFileError` "not a run category" | `test_labeled_category_by_game_name_is_unknown` | ☑ |
| Unknown name lists the valid ones | `"Nope"` | error with sorted valid names | `test_unknown_name_lists_the_valid_ones` | ☑ |
| Empty list allowed | `run = []` | `()` | `test_empty_list_is_allowed` | ☑ |
| Wrong side | pass label under run / run under pass / offense under defense | error says which | `test_wrong_side_is_an_error` `[P]` | ☑ |
| Repeated name | `RL` twice | "listed twice" | `test_repeated_name_is_an_error` | ☑ |
| Missing key / table | no `defense` / no `[category_order]` | "missing" | `test_missing_key_is_an_error` / `test_missing_table_is_an_error` | ☑ |
| Table written as a value | `category_order = 1` / `deleted_plays = 1` | "must be a table" | `test_table_written_as_a_value_is_an_error` `[P]` | ☑ |
| Not an array of strings | string, `[1]`, mixed | "expected an array of strings" | `test_list_must_be_an_array_of_strings` `[P]` | ☑ |
| Unknown key / table | `special`, `[filters]` | "unknown key" | `test_unknown_key_is_an_error` / `test_unknown_table_is_an_error` | ☑ |
| Missing file | no `pdbtoexcel.toml` | "not found" | `test_missing_file_is_an_error` | ☑ |
| Bad TOML / BOM | malformed; `utf-8-sig` | error names the file; BOM loads | `test_bad_toml_is_an_error` / `test_bom_is_skipped` | ☑ |
| Deleted plays | `[deleted_plays] names` | names as written; absent → empty | `test_deleted_plays_read_as_written` / `test_deleted_plays_table_without_names_is_empty` | ☑ |
| Deleted plays wrong type / key | string, `[1]`; `plays` | error | `test_deleted_plays_must_be_an_array_of_strings` `[P]` / `test_deleted_plays_unknown_key_is_an_error` | ☑ |
| Every shipped league loads | `config/{dev,release}` × PNFL/PCFL | 4/9/10 categories; ATF0ELOB deleted | `test_shipped_league_loads` `[P]` | ☑ |
| Workbook options from `[convert-pdb]` | athc.ini + folder | all three flipped | `test_load_config_reads_workbook_options` | ☑ |
| Workbook options without the section | folder | True / False / True | `test_workbook_options_default_without_section` | ☑ |
| configparser booleans accepted | `1/yes/true/on`, `0/no/false/off`, any case | parsed | `test_workbook_option_accepts_configparser_booleans` `[P]` | ☑ |
| Other boolean spelling | `maybe` | `ConfigFileError` names the key | `test_workbook_option_rejects_other_values` | ☑ |
| `calculate_total_stats` no longer read | leftover key, bad value | ignored; no such option | `test_calculate_total_stats_is_no_longer_read` | ☑ |

## workbook_creator + excel_workbook (read back with openpyxl)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Base sheets + run row | synth + pool | 5 sheets; team / label ("RM") / stats | `test_base_sheets_and_run_row` | ☑ |
| Run row with no attempts | play_count 0, category sheets on | zeros, no division error | `test_run_row_with_no_attempts_writes_zeros` | ☑ |
| Pass row: Screen + comp/att | synth + pool | "PSR"; "Screen"; att excludes sacks | `test_pass_row_screen_and_stats` | ☑ |
| Defense row: front Type | synth + pool | "RunRight"; `defensive_front` value; total calls | `test_defense_row_front_type` | ☑ |
| Unlabeled category shows its game name | synth + pool | "Razzle Dazzle Run" | `test_unlabeled_category_shows_its_game_name` | ☑ |
| Options sheet lists the order by label | — | H/I/J columns = run/pass/defense labels | `test_options_sheet_lists_the_order_by_label` | ☑ |
| Rows follow the category order | synth + pool | RL row before RM row | `test_rows_follow_the_category_order` | ☑ |
| Unlisted category left out | order with RL only | RM play absent | `test_unlisted_category_is_left_out` | ☑ |
| Deleted play skipped quietly | not in pool, 2 teams | no row; no warning; one info line | `test_deleted_play_is_skipped_quietly` | ☑ |
| Deleted play still in the pool | in pool, listed in another case, 2 teams, totals | no row; one "stale" warning with the file's spelling | `test_deleted_play_still_in_the_pool_is_skipped_with_a_warning` | ☑ |
| Run row: QB draw Type | synth + pool | "QB draw" | `test_qb_draw_type` | ☑ |
| `--skip-calcs` omits % columns | synth + pool | no "Fumble %" header | `test_skip_calcs_omits_percent_columns` | ☑ |
| Totals add "Total Stats" team | synth + pool | summed team present | `test_totals_adds_total_stats_team` | ☑ |
| Category worksheets when enabled | synth + pool | "Run Categories" sheet + row | `test_category_worksheets_when_enabled` | ☑ |
| Special-teams / unknown skipped | synth + pool | absent from sheets; "Play file not found" warning | `test_special_teams_and_unknown_plays_skipped` | ☑ |
| Tendencies written | synth | 16 rows per team | `test_tendencies_written` | ☑ |
| Slot column from gameplan | synth + pool + pln | slot 0 → "1-1" | `test_slot_column_from_gameplan` | ☑ |

Notes: grouping is by the play file's category, shown under the league's label (`PNFL_LABELS`) and sorted by the league's order (`PNFL_ORDER` in the conftest). Exact percentage-cell values aren't asserted (column presence + the underlying counts are).
