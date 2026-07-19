# playpool — Test Matrix

Cases covered for the play-pool library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `make` = constructed `PlayFile`/record/filter; `tree` = the curated PNFL tree in `data/plays/`, plus the same files copied into a flat and a non-PNFL tree (conftest fixtures `pnfl_pool` / `flat_pool` / `nonpnfl_pool`); `rel` = a play's path relative to the pool root; `tmp`/`dict` = constructed input. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/playpool` passes.

## rules.py — `load_rules` / `build_rules`

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Test rules load | tree | filters populated; regex compiled | `test_load_test_rules` | ☑ |
| Build from dict; absent section empty | dict | `FilenameFilter()` | `test_build_from_dict` | ☑ |
| Only schema_version → all empty | tmp | `PlaypoolRules()` | `test_missing_section_is_empty` | ☑ |
| Unknown section | tmp | "unknown section" | `test_unknown_section` | ☑ |
| Unknown key in section | tmp | "unknown key" | `test_unknown_key` | ☑ |
| Wrong value type | tmp | "must be a list of strings" | `test_bad_value_type` | ☑ |
| Section not a table | tmp | "must be a table" | `test_section_not_a_table` | ☑ |
| Bad regex | tmp | "invalid regex" | `test_bad_regex` | ☑ |
| Two bad regexes both reported | tmp | both in `.errors` | `test_two_bad_regexes_both_reported` | ☑ |
| All problems collected at once | tmp | 5 errors, each kind present | `test_collects_multiple_errors` | ☑ |
| TOML parse error | tmp | "TOML parse error" | `test_toml_parse_error` | ☑ |
| Missing file | path | `RulesFileError` | `test_missing_file` | ☑ |
| Shipped PNFL rules load | data | timed include + qb regex | `test_pnfl_rules_load` | ☑ |

## rules.py — `FilenameFilter.matches` (case-sensitive; vetoes win)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `suffix_any` match | make | hit / miss | `test_suffix_any_match` | ☑ |
| `suffix_none` vetoes a suffix hit | make | not matched | `test_suffix_none_vetoes` | ☑ |
| `include` forces on (no suffix) | make | matched | `test_include_forces_on` | ☑ |
| `exclude` vetoes | make | excluded off; other on | `test_exclude_vetoes` | ☑ |
| `regex_any` | make | by 2nd char | `test_regex_any` | ☑ |
| Case-sensitive include + suffix | make | exact case only | `test_case_sensitive` | ☑ |
| **Timed + rollout both** (TR suffix) | tree | both attrs | `test_rollout_and_timed_both` | ☑ |
| **Timed-by-suffix but excluded → rollout only** | tree | timed off, rollout on | `test_timed_excluded_still_rollout` | ☑ |

## records.py — record classes

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `category` (enum member) from the file | make | `OffensiveCategory.RUN_MIDDLE`, `is_run` | `test_category` | ☑ |
| Offensive `to_dict` (category → long name) | make | `screen` + `pass_logic` | `test_offensive_to_dict` | ☑ |
| Defensive `to_dict` | make | `defensive_front == "2-DL"` | `test_defensive_to_dict` | ☑ |
| Special-teams `to_dict` (no extra fields) | make | base keys only | `test_special_to_dict` | ☑ |
| `find_by_name` case-insensitive | make | hit; miss → None | `test_find_by_name` | ☑ |
| Duplicate name → warn, last wins | make | warning; last record | `test_duplicate_name_warns` | ☑ |

## pool.py — file-driven classification (identical across PNFL / non-PNFL / flat)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offensive: category + rollout/qb_draw/pass_logic | tree | same in all 3 layouts | `test_offensive_file_driven` `[P]` | ☑ |
| `screen` only from a PNFL `Screens/` folder | tree | True in PNFL, else False | `test_screen_only_from_pnfl_folder` `[P]` | ☑ |
| Defensive: category; `defensive_front` PNFL-only | tree | front in PNFL, else None | `test_defensive_file_driven` `[P]` | ☑ |
| Special-teams play filed | tree | `SpecialTeamsPlay` | `test_special_file_driven` `[P]` | ☑ |
| `find_by_name` across sides | tree | hits / miss | `test_find_across_sides` `[P]` | ☑ |
| Consistent trees emit no warning | tree | no "play in" | `test_no_warnings_on_consistent_trees` `[P]` | ☑ |
| Invalid `.ply` skipped + warning | tree | warned; absent | `test_invalid_skipped` | ☑ |
| Flat loose play classified from file | tmp | offensive; not skipped | `test_flat_play_classified_from_file` | ☑ |

## pool.py — `folder_warnings` (recognized PNFL folder vs the play file)

Warning = `<reason>: <path-from-pool-root>`. Wrong side reported alone; category checked only when the side matches; unrecognized folders never warn.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Wrong side, file wins (end-to-end) | tmp | defensive record + side warning | `test_wrong_side_folder_file_wins_and_warns` | ☑ |
| Wrong category, file wins (end-to-end) | tmp | file category + category warning | `test_wrong_category_folder_warns` | ☑ |
| Defensive play in offense tree | rel | side warning | `test_warn_defensive_play_in_offense_tree` | ☑ |
| Offensive play in defense (3-4) tree | rel | side warning | `test_warn_offensive_play_in_defense_tree` | ☑ |
| Special play in a side tree | rel | side warning | `test_warn_special_play_in_side_tree` | ☑ |
| Offense category mismatch (PSL in PML) | rel | category warning | `test_warn_offense_category_mismatch` | ☑ |
| Defense category mismatch | rel | category warning | `test_warn_defense_category_mismatch` | ☑ |
| `User Specific` in a category folder | rel | category warning | `test_warn_user_specific_in_category_folder` | ☑ |
| Wrong side suppresses category warning | rel | side warning only | `test_wrong_side_reported_alone` | ☑ |
| Consistent folder | rel | no warning | `test_no_warn_when_consistent` | ☑ |
| Loose / side-root / non-PNFL (incl. User Specific) | rel | no warning | `test_no_warn_loose_or_unrecognized` `[P]` | ☑ |
