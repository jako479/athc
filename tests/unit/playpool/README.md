# playpool — Test Matrix

Cases covered for the play-pool library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `make` = constructed `PlayFile`/record/filter; `tree` = curated play tree in `data/plays/` + `data/rules.toml`; `tmp`/`dict` = constructed rules. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/playpool` passes.

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
| `category` / `play_type` / `is_run` | make | from `PlayFile` | `test_category_and_play_type` | ☑ |
| `play_type` run/pass/None | str | "run" / "pass" / None | `test_play_type_function` | ☑ |
| Offensive `to_dict` (enum → value) | make | typed flags + `pass_logic` | `test_offensive_to_dict` | ☑ |
| Defensive `to_dict` | make | `defensive_front == "2-DL"` | `test_defensive_to_dict` | ☑ |
| Special-teams `to_dict` (no extra fields) | make | base keys only | `test_special_to_dict` | ☑ |
| `find_by_name` case-insensitive | make | hit; miss → None | `test_find_by_name` | ☑ |
| Duplicate name → warn, last wins | make | warning; last record | `test_duplicate_name_warns` | ☑ |

## pool.py — `read_play_pool` (folder + filename classification over `data/plays/`)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offensive plays classify | tree | category + screen/rollout/qb_draw/pass_logic | `test_offensive_examples` `[P]` | ☑ |
| Defensive plays classify | tree | category + `defensive_front` | `test_defensive_examples` `[P]` | ☑ |
| Special-teams play filed | tree | `SpecialTeamsPlayRecord` | `test_special_example` | ☑ |
| `find_by_name` across sides | tree | hits / miss | `test_find_across_sides` | ☑ |
| Invalid `.ply` skipped + warning | tree | warned; absent | `test_invalid_skipped` | ☑ |
| Side from folder, not filename | tmp | Defense folder wins over "Offense" in name | `test_side_from_folder_not_filename` | ☑ |
| Play outside side folders | tmp | skipped + warning | `test_play_outside_side_folders_skipped` | ☑ |
