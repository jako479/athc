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

`[convert-pdb]` in athc.toml (the base) with the league's league.toml table laid over it key by key; the `base` and `override` fixtures rewrite one file each.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Defaults (base with the PNFL order only) | folder | play_path the folder; options at their defaults; no deleted plays | `test_load_config_defaults` | ☑ |
| From the league folder | `league.toml` | play_path resolved | `test_load_config_from_league_folder` | ☑ |
| Needs a league | no league selected | `LeagueError` | `test_load_config_needs_a_league` | ☑ |
| Missing `play_path` | league without it | "Play pool folder is not set" naming `league.toml` | `test_missing_play_path_is_an_error` | ☑ |
| Category order in file order | the PNFL order in athc.toml | run/pass/defense enum members as listed | `test_category_order_in_file_order` | ☑ |
| Unlabeled category by game name | `"Razzle Dazzle Run"` | resolves | `test_unlabeled_category_goes_by_its_game_name` | ☑ |
| Labeled category by game name | `"Run Left"` with RL labeled | `ConfigFileError` "not a run category" | `test_labeled_category_by_game_name_is_unknown` | ☑ |
| Unknown name lists the valid ones | `"Nope"` | the whole line, sorted valid names, naming athc.toml | `test_unknown_name_lists_the_valid_ones` | ☑ |
| Empty list allowed | `run = []` | `()` | `test_empty_list_is_allowed` | ☑ |
| Wrong side | pass label under run / run under pass / offense under defense | error says which | `test_wrong_side_is_an_error` `[P]` | ☑ |
| Repeated name | `RL` twice | "listed twice" | `test_repeated_name_is_an_error` | ☑ |
| Not an array of strings | string, `[1]`, mixed | `[convert-pdb.category_order] run: Expected an array of strings.` | `test_list_must_be_an_array_of_strings` `[P]` | ☑ |
| Unknown key in the order / in `[convert-pdb]` | `special`, `zap`; `[convert-pdb.filters]`, `[convert-pdb.zap]` | `Unknown key(s): ... Valid: ...` naming athc.toml | `test_unknown_key_is_an_error` / `test_unknown_top_level_key_is_an_error` | ☑ |
| Every key from the base | options flipped, lists, `deleted_plays` in athc.toml only | all read; `deleted_plays_file` athc.toml | `test_every_key_from_the_base` | ☑ |
| No order anywhere / one list missing | no `category_order`; no `run` | every list `()`; that list `()` | `test_missing_lists_default_to_empty` / `test_a_missing_list_is_empty` | ☑ |
| No `deleted_plays` | none | empty; `deleted_plays_file` athc.toml | `test_missing_deleted_plays_is_empty` | ☑ |
| Options without / with the table | none; all three flipped | True / False / True; flipped | `test_workbook_options_default_without_section` / `test_load_config_reads_workbook_options` | ☑ |
| Every key from the league | nothing in athc.toml, everything in league.toml | all read; `deleted_plays_file` league.toml | `test_every_key_from_the_league` | ☑ |
| No athc.toml at all | league.toml only | the league's keys and the defaults | `test_league_alone_without_athc_toml` | ☑ |
| League overrides one option | each of the three options, base flipped | that option the league's, the other two the base's | `test_league_overrides_one_option_and_keeps_the_rest` `[P]` | ☑ |
| League overrides one list | `run`, `pass`, `defense` | that list the league's, the other two the base's | `test_league_overrides_one_list_and_keeps_the_rest` `[P]` | ☑ |
| League empty list | `run = []` | no run categories; pass and defense the base's | `test_league_empty_list_overrides_the_base` | ☑ |
| League `deleted_plays` | base `["A", "C"]`, league `["B"]` | `{"B"}`, replaced whole | `test_league_overrides_deleted_plays_whole` | ☑ |
| League option, base lists | one option in league.toml | both apply | `test_league_options_and_base_lists` | ☑ |
| Empty league tables | `[convert-pdb]`, `[convert-pdb.category_order]`, both | the base unchanged | `test_empty_league_table_keeps_the_base` `[P]` | ☑ |
| Overridden base value not checked | bad base list / option, league replaces it | loads with the league's | `test_overridden_base_list_is_not_checked` / `test_overridden_base_option_is_not_checked` | ☑ |
| Not a TOML boolean | `"true"`, `1`, `"maybe"` | `[convert-pdb] calculate_percentages: Expected true or false.` naming athc.toml | `test_workbook_option_rejects_non_booleans` `[P]` | ☑ |
| Bad option names its file | `"true"` in athc.toml / league.toml | the line names that file | `test_bad_option_names_the_base_file` / `test_bad_option_names_the_league_file` | ☑ |
| Bad list / unknown name names its file | `run = "RL"`; `"Nope"` in league.toml | the line names league.toml | `test_bad_list_names_its_file` / `test_unknown_name_names_its_file` | ☑ |
| Unknown key names its file | `zap` in `[convert-pdb]`; `special` in the order, league.toml | the line names league.toml | `test_unknown_key_names_its_file` / `test_unknown_order_key_names_its_file` | ☑ |
| Unknown keys in both files | `aaa` in athc.toml, `zap` in league.toml | one line: athc.toml and `aaa` only | `test_unknown_keys_in_both_files_name_one_file` | ☑ |
| Order written as a value | `category_order = 1` in league.toml / athc.toml | `[convert-pdb.category_order]: Must be a table.` naming that file | `test_order_written_as_a_value_names_its_file` / `test_order_written_as_a_value_in_the_base` | ☑ |
| `[convert-pdb]` written as a value | `convert-pdb = 1` in league.toml / athc.toml | `[convert-pdb]: Must be a table.` naming that file | `test_section_written_as_a_value_in_the_league_file` / `test_section_written_as_a_value_in_the_base` | ☑ |
| Deleted plays | `deleted_plays = ["atf0elob", "XY"]` | names as written | `test_deleted_plays_read_as_written` | ☑ |
| Deleted plays wrong type | string, `[1]`; a string in league.toml | `[convert-pdb] deleted_plays: Expected an array of strings.` naming its file | `test_deleted_plays_must_be_an_array_of_strings` `[P]` / `test_bad_deleted_plays_names_the_league_file` | ☑ |
| Deleted plays' file | from athc.toml, then from league.toml | `deleted_plays_file` is that file | `test_deleted_plays_file_is_where_the_list_came_from` | ☑ |
| `calculate_total_stats` | the old key | unknown key | `test_calculate_total_stats_is_an_unknown_key` | ☑ |
| Every shipped league loads | `config/{dev,release}` × PNFL/PCFL | 4/9/10 categories; ATF0ELOB deleted; from athc.toml | `test_shipped_league_loads` `[P]` | ☑ |

## workbook_creator + excel_workbook (read back with openpyxl)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Base sheets + run row | synth + pool | 5 sheets; team / label ("RM") / stats | `test_base_sheets_and_run_row` | ☑ |
| Run row with no attempts | play_count 0, category sheets on | zeros, no division error | `test_run_row_with_no_attempts_writes_zeros` | ☑ |
| Pass row: Screen + comp/att | synth + pool | "PSR"; "Screen"; att excludes sacks | `test_pass_row_screen_and_stats` | ☑ |
| Defense row: front Type | synth + pool | "RunRight"; `defensive_front` value; total calls | `test_defense_row_front_type` | ☑ |
| Unlabeled category shows its game name | synth + pool | "Razzle Dazzle Run" | `test_unlabeled_category_shows_its_game_name` | ☑ |
| Options sheet lists the order by label | — | B/C/D columns = run/pass/defense labels | `test_options_sheet_lists_the_order_by_label` | ☑ |
| Category order names cover their lists | — | each name spans its labels exactly: header just above, empty cell just below | `test_category_order_name_covers_its_list` `[P]` | ☑ |
| Highlight rule reads HighlightRow | `.xlsm` | `HighlightRow` starts at 0; every data sheet's rule is `ROW()=HighlightRow` | `test_highlight_rule_reads_highlight_row` | ☑ |
| Rows follow the category order | synth + pool | RL row before RM row | `test_rows_follow_the_category_order` | ☑ |
| Unlisted category left out | order with RL only | RM play absent | `test_unlisted_category_is_left_out` | ☑ |
| Deleted play skipped quietly | not in pool, 2 teams | no row; no warning; one info line | `test_deleted_play_is_skipped_quietly` | ☑ |
| Deleted play still in the pool | in pool, listed in another case, 2 teams, totals | no row; one "stale" warning with the file's spelling | `test_deleted_play_still_in_the_pool_is_skipped_with_a_warning` | ☑ |
| Run row: QB run Type | synth + pool | "QB run" | `test_qb_run_type` | ☑ |
| Percentages off for the run (`--no-percentages`) omits % columns | synth + pool | no "Fumble %" header | `test_skip_calcs_omits_percent_columns` | ☑ |
| % columns follow the run, not the setting | `calculate_percentages` false, run on | "Fumble %" header | `test_percent_columns_follow_the_run_not_the_setting` | ☑ |
| Totals add "Total Stats" team | synth + pool | summed team present | `test_totals_adds_total_stats_team` | ☑ |
| Category worksheets when enabled | synth + pool | "Run Categories" sheet + row | `test_category_worksheets_when_enabled` | ☑ |
| Special / unknown skipped | synth + pool | absent from sheets; "is not in the play pool" warning | `test_special_and_unknown_plays_skipped` | ☑ |
| Tendencies written | synth | 16 rows per team | `test_tendencies_written` | ☑ |
| Slot column from gameplan | synth + pool + pln | slot 0 → "1-1" | `test_slot_column_from_gameplan` | ☑ |
| Slot column hidden by its own plan | neither, plan 1 only, plan 2 only, both | hidden where absent | `test_slot_options_by_presence` `[P]` | ☑ |
| Slot 2 shows with plan 2 alone | synth + pool + pln as Slot 2 | Slot 1 hidden; Slot 2 "1-1" | `test_second_plan_alone_shows_slot_2` | ☑ |

Notes: grouping is by the play file's category, shown under the league's label (`PNFL_LABELS`) and sorted by the league's order (`PNFL_ORDER` in the conftest). Exact percentage-cell values aren't asserted (column presence + the underlying counts are).
