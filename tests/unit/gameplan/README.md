# gameplan — Test Matrix

Tool-logic unit cases (rules loader, play-list writer, validators). Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). CLI cases live in [../../integration/README.md](../../integration/README.md).

One row per behavior. Input: `tmp` = constructed TOML; `shipped` = every `leagues/<league>/gameplan.toml` in `config/dev/` and `config/release/`; `make` = play records, pool and gameplan built in the test. `[P]` = parametrized. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/gameplan` passes.

## rules.py — `load_rules`

### Section labels (league labels from league.toml, else game names)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense label → full name | tmp | `[offense.RM]` → "Run Middle" | `test_offense_short_label_maps_to_full_name` | ☑ |
| Defense label → full name | tmp | `[defense.RunDazzle]` → "Razzle Dazzle Run" | `test_defense_short_label_maps_to_full_name` | ☑ |
| Unknown offense label | tmp | "not an offense category label" | `test_unknown_offense_label` | ☑ |
| Unknown defense label | tmp | "not a defense category label" | `test_unknown_defense_label` | ☑ |
| `offense` not a table | tmp | "[offense]: Must be a table." | `test_side_not_a_table_rejected` | ☑ |
| Section not a table | tmp | "[offense.RM]: Must be a table." | `test_section_not_a_table_rejected` | ☑ |
| League label without league labels | `CategoryLabels()` + `[offense.RM]` | "not an offense category label" | `test_league_label_section_needs_the_league_labels` | ☑ |
| Game name without league labels | `CategoryLabels()` + `[offense."Run Middle"]` | loads | `test_game_name_section_loads_without_league_labels` | ☑ |
| Game name of a labeled category | PNFL + `[offense."Run Middle"]` | "not an offense category label" | `test_game_name_section_rejected_when_league_labels_it` | ☑ |
| Unknown-label message lists league labels | PNFL + `[defense.Nonsense]` | message contains ", RunDazzle, " | `test_unknown_label_message_lists_the_league_labels` | ☑ |
| Game-name labels load | tmp | `[offense."Pass Long Left"]` etc. (3) | `test_offense_game_name_label_loads` `[P]` | ☑ |
| `User Specific` on both sides | tmp | offense and defense rules both load | `test_user_specific_label_loads_on_each_side` | ☑ |
| Game-name label on wrong side | tmp | "not a defense category label" | `test_game_name_label_on_wrong_side_is_rejected` | ☑ |
| Unknown-label message lists game names | tmp | message contains "Pass Long Left" | `test_unknown_label_message_lists_game_name_labels` | ☑ |
| Clock names in `required_special_categories` | tmp | → `{11, 12}` | `test_required_special_accepts_clock_categories` | ☑ |
| Unknown name in `required_special_categories` | tmp | "unknown name 'Spike'" | `test_required_special_rejects_unknown_name` | ☑ |
| All twelve special names | tmp | → `{1..12}` | `test_required_special_accepts_all_twelve_names` | ☑ |
| `required_special_categories` not a list | tmp | "must be a list" | `test_required_special_must_be_list` | ☑ |
| `required_special_categories` entry not a string | tmp | "entries must be strings" | `test_required_special_entries_must_be_strings` | ☑ |
| `custom_special_play_required` omitted / `true` | tmp | False / True | `test_custom_special_play_required_defaults_false` / `..._parses` | ☑ |
| `custom_special_play_required` not a bool | tmp | "must be a boolean" | `test_custom_special_play_required_must_be_bool` | ☑ |

### min_count / max_count
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `required`/`min_count` omitted → default | tmp | False / 0; cap-only rule valid | `test_required_and_min_count_default_when_omitted` | ☑ |
| Empty section rejected | tmp | "empty rule" | `test_empty_section_rejected` | ☑ |
| `required` must be bool | tmp | "must be a boolean" | `test_required_must_be_bool` | ☑ |
| `min_count` must be int | tmp | "must be an integer" | `test_min_count_must_be_int` | ☑ |
| `max_count` absent → None | tmp | None | `test_max_count_absent_is_none` | ☑ |
| `max_count` must be int | tmp | "must be an integer" | `test_max_count_must_be_int` | ☑ |
| A boolean is not a count | tmp, `min_count = true` | "must be an integer" | `test_count_rejects_a_boolean` | ☑ |

### caps gating
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Run cap on pass category | tmp | "unknown key" | `test_run_cap_rejected_on_pass` | ☑ |
| Pass cap on run category | tmp | "[offense.RM]: Unknown key(s): max_rollouts_count." | `test_pass_cap_rejected_on_run` | ☑ |
| Offense cap on defense category | tmp | "[defense.PassShort]: Unknown key(s): max_qb_runs_count." | `test_offense_cap_rejected_on_defense` | ☑ |

### one form per attribute
Each attribute (`qb_runs`, `rollouts`, `timed`, `two_dl`) takes exactly one of
`_count` / `_ratio` / `_percent`.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Any single form | tmp | that form parsed, the other two None | `test_one_form_of_one_attribute_accepted` `[P]` | ☑ |
| Two forms of one attribute | tmp | "at most one of" | `test_two_forms_of_one_attribute_rejected` `[P]` | ☑ |
| A form for each of two attributes | tmp | rollouts count + timed ratio: the whole rule | `test_two_attributes_take_one_form_each` | ☑ |

### value ranges
Counts (`min_count`, `max_count`, `max_<attr>_count`) >= 0; ratios in [0, 1];
percents in [0, 100]: limit ok + one outside. One key per validator: `min_count`
and `max_count` (the other counts share its validator), `max_timed_ratio`,
`max_timed_percent`.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Count at lower limit 0 | tmp | parsed as 0 | `test_count_zero_ok` `[P]` | ☑ |
| Count below 0 | tmp | ">= 0" | `test_count_negative_rejected` `[P]` | ☑ |
| Ratio at limits 0/1 / 1/1 | tmp | parsed | `test_ratio_in_range_ok` `[P]` | ☑ |
| Ratio below 0 / above 1 | tmp | "[0, 1]" | `test_ratio_out_of_range_rejected` `[P]` | ☑ |
| Ratio not a string | tmp | 'must be a string like "1/2"' | `test_ratio_must_be_string` | ☑ |
| Ratio not n/m | tmp, `"1"` / `"0.5"` | `Invalid fraction '...': Must be n/m, like "1/2".`, the whole line | `test_ratio_must_be_n_over_m` `[P]` | ☑ |
| Ratio not a fraction | tmp, `"half"` / `"1/0"` | "Invalid fraction '...'" | `test_ratio_not_a_fraction_rejected` `[P]` | ☑ |
| Percent at limits 0 / 100 | tmp | parsed | `test_percent_in_range_ok` `[P]` | ☑ |
| Percent below 0 / above 100 | tmp | "[0, 100]" | `test_percent_out_of_range_rejected` `[P]` | ☑ |
| Percent not an int | tmp | "must be an integer" | `test_percent_must_be_int` | ☑ |

### allowed categories
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Labels → game names, both sides | tmp | frozensets of game names | `test_allowed_categories_parse` | ☑ |
| Game name, even of an unlabeled category | PNFL + `"Pass Long Left"` | "not an offense category label" | `test_allowed_game_name_rejected` | ☑ |
| League label without league labels | `CategoryLabels()` + `"RM"` | "not an offense category label" | `test_allowed_needs_the_league_names` | ☑ |
| Unknown offense label | tmp | "not an offense category label" | `test_allowed_unknown_offense_label` | ☑ |
| Unknown defense label | tmp | "not a defense category label" | `test_allowed_unknown_defense_label` | ☑ |
| Not a list | tmp | "must be a list" | `test_allowed_must_be_list` | ☑ |
| Entry not a string | tmp | "entries must be strings" | `test_allowed_entries_must_be_strings` | ☑ |
| Absent → empty | tmp | empty frozensets | `test_allowed_absent_is_empty` | ☑ |
| Explicit `[]` → empty | tmp | empty frozenset | `test_allowed_empty_list_loads_empty` | ☑ |

### [profile_compatibility]
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Omitted → default | tmp | flag False | `test_profile_compatibility_defaults_when_omitted` | ☑ |
| Parses | tmp | flag as written | `test_profile_compatibility_parses` | ☑ |
| Unknown key | tmp | "unknown key" | `test_profile_compatibility_unknown_key` | ☑ |
| Non-bool | tmp | "must be a boolean" | `test_profile_compatibility_must_be_bool` | ☑ |
| Not a table | tmp | "Must be a table." | `test_profile_compatibility_must_be_table` | ☑ |
| Layering overrides the flag | tmp ×2 | later value wins | `test_layering_overrides_profile_compatibility` | ☑ |

### top-level keys
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `schema_version` is an unknown key | tmp | "(top): unknown key" | `test_schema_version_is_an_unknown_key` | ☑ |

### layering / paths
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty path list | — | "at least one" | `test_empty_paths_rejected` | ☑ |
| Later file replaces a category rule; other sections kept | tmp ×2 | whole rule replaced; the earlier file's other offense and defense rules stay | `test_layering_replaces_category_rule` | ☑ |
| Later file replaces an allowed list; omitted key keeps it | tmp ×2 | later list wins | `test_layering_replaces_allowed_list` | ☑ |
| Later file replaces the special keys; omitted key keeps it | tmp ×3 | later value wins | `test_layering_replaces_special_keys` | ☑ |
| UTF-8 BOM skipped | tmp | loads | `test_bom_is_skipped` | ☑ |
| Not valid TOML | tmp | "<path>: Not valid TOML: ..." | `test_invalid_toml_rejected` | ☑ |

### collect-all-errors
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Several problems in one file | tmp | all three reported | `test_collects_multiple_errors` | ☑ |
| A missing file, then a file with a bad value | — + tmp | each under its own path: "The system cannot find the file specified.", then ">= 0" | `test_collects_errors_across_files` | ☑ |

### shipped rules
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Every shipped league's rules load, with the labels in its league.toml | shipped | loads | `test_shipped_rules_load` `[P]` | ☑ |

## writer.py — `apply_normal_plays`, `apply_special_plays`

Each pool play carries real category bytes: Run Middle or Run Left for a normal
play, 0x01 (kicking) or 0x00 (receiving) for a special play.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Special category 11 play (no custom slot) | make | `InvalidPlayListError` "which has no custom slot" | `test_special_play_without_custom_slot_is_rejected` | ☑ |
| Special category 1 / 10 play (first / last custom slot) | make | placed in its slot; the plan otherwise unchanged | `test_special_play_in_a_custom_category_is_accepted` `[P]` | ☑ |
| Normal plays with a blank line | make | slots filled in order, the blank one empty | `test_normal_plays_fill_slots_in_order_with_blanks_empty` | ☑ |
| Special play listed for a category that has a custom | make | its category replaced; category 4's custom, blank line and clock stocks kept | `test_special_play_replaces_its_category_and_keeps_the_rest` | ☑ |
| Special play in a normal slot | make | `InvalidPlayListError` "'KICKPLY' is a special play and cannot go in a normal slot." | `test_special_play_in_a_normal_slot_is_rejected` | ☑ |
| Defensive play in an offense game plan | make | "'DEFPLAY' is a defensive play, but the game plan is offensive." | `test_defensive_play_in_an_offense_game_plan_is_rejected` | ☑ |
| Offensive play in a defense game plan | make | "'OFFPLAY' is an offensive play, but the game plan is defensive." | `test_offensive_play_in_a_defense_game_plan_is_rejected` | ☑ |
| Normal play in the specials list | make | "'RUNPLAY' is not a special play." | `test_normal_play_in_the_specials_list_is_rejected` | ☑ |
| Defensive special play in an offense game plan | make | "'DEFKICK' is a defensive special play, but the game plan is offensive." | `test_defensive_special_play_in_an_offense_game_plan_is_rejected` | ☑ |
| Offensive special play in a defense game plan | make | "'OFFKICK' is an offensive special play, but the game plan is defensive." | `test_offensive_special_play_in_a_defense_game_plan_is_rejected` | ☑ |
| Normal name in another case | make | the pool's play placed; the plan otherwise unchanged | `test_normal_play_name_matches_any_case` | ☑ |
| Several bad normal lines | make | each named by its line and slot; "2 invalid play(s)." | `test_every_bad_normal_line_is_reported_at_once` | ☑ |
| 64th line | make | read: a bad play there is reported (slot 16-4) | `test_normal_plays_fill_all_64_slots` | ☑ |
| 65th line | make | dropped, never read | `test_normal_plays_past_64_are_dropped` | ☑ |
| Special play listed twice, any case | make | "Duplicate special play 'kickply', already used for special category 2." | `test_duplicate_special_play_is_rejected_any_case` | ☑ |
| Two special plays for one category | make | "'KICKB' targets special category 2, already filled by another play." | `test_two_special_plays_for_one_category_are_rejected` | ☑ |
| Special play not in the pool | make | "'GHOST' is not in the play pool." | `test_special_play_not_in_the_pool_is_rejected` | ☑ |

## validators.py — `validate_gameplan`

Constructed records, pool and gameplan: the gameplan's slots hold the pool's plays, and the records carry typed playpool attributes. Each side has its own harness; offense gameplans also carry the two stock clock plays. A "fires" row checks the whole report: rule, message and category. Each count limit is tested at the limit and one past it; each cap form at its lowest value, 0, and the ratio and percent forms at their highest, 1 and 100%.

### Offense
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `min_count` one short (2 of 3) | make | "Offensive category 'Run Middle' has 2 plays; requires at least 3." | `test_offense_min_count_fires` | ☑ |
| `min_count` met exactly | make | no violation | `test_offense_min_count_clean_at_limit` | ☑ |
| Required category absent | make | "Required offensive category 'Run Middle' has no plays" | `test_offense_required_fires` | ☑ |
| `max_count` one past (3 of 2) | make | "Offensive category 'Run Middle' has 3 plays; allows at most 2." | `test_offense_max_count_fires` | ☑ |
| `max_count` met exactly | make | no violation | `test_offense_max_count_clean_at_limit` | ☑ |
| `max_count` of 0, one play | make | "Offensive category 'Run Middle' has 1 plays; allows at most 0." | `test_offense_max_count_of_zero_fires` | ☑ |
| Category outside the allowed list | make | "Offensive category 'Run Right' is not allowed; has 1 play(s)." | `test_offense_not_allowed_fires` | ☑ |
| Defense rules and allowed list | make | ignored | `test_offense_gameplan_ignores_defense_rules` | ☑ |
| `max_qb_runs_count` one past (2 of cap 1) | make | "... has 2 of 2 QB runs; allows at most 1." | `test_offense_max_qb_runs_count_fires` | ☑ |
| `max_qb_runs_count` met exactly (1 of cap 1) | make | no violation | `test_offense_max_qb_runs_count_clean` | ☑ |
| `max_rollouts_count` one past (2 of cap 1) | make | "... has 2 of 2 rollouts; allows at most 1." | `test_offense_max_rollouts_count_fires` | ☑ |
| `max_rollouts_count` met exactly (1 of cap 1) | make | no violation | `test_offense_max_rollouts_count_clean` | ☑ |
| `max_timed_ratio` exceeded (2/2 > 1/2) | make | "... has 2 of 2 timed passes; allows at most 1/2." | `test_offense_max_timed_ratio_fires` | ☑ |
| `max_timed_ratio` exactly at cap (1/2) | make | no violation | `test_offense_max_timed_ratio_clean` | ☑ |
| `max_timed_percent` exceeded (2/3 > 50%) | make | "... has 2 of 3 timed passes; allows at most 50%." | `test_offense_max_timed_percent_fires` | ☑ |
| `max_timed_percent` exactly at cap (1/2 = 50%) | make | no violation | `test_offense_max_timed_percent_clean_at_cap` | ☑ |

### Defense
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `min_count` one short (2 of 3), required or optional | make | "Defensive category 'Run Left' has 2 plays; requires at least 3." | `test_min_count_fires` `[P]` | ☑ |
| `min_count` met exactly | make | no violation | `test_min_count_clean_at_limit` | ☑ |
| Required category absent | make | "Required defensive category 'Pass Short' has no plays" | `test_defense_required_names_the_category` | ☑ |
| Optional empty category | make | no violation | `test_min_count_not_checked_when_category_empty` | ☑ |
| `max_count` one past (3 of 2) | make | "Defensive category 'Run Left' has 3 plays; allows at most 2." | `test_max_count_fires` | ☑ |
| `max_count` met exactly | make | no violation | `test_max_count_clean_at_limit` | ☑ |
| `max_count` of 0, one play | make | "Defensive category 'Run Left' has 1 plays; allows at most 0." | `test_max_count_of_zero_fires` | ☑ |
| Category outside the allowed list | make | "Defensive category 'User Specific' is not allowed; has 1 play(s)." | `test_not_allowed_names_the_category` | ☑ |
| Several categories outside the list | make | reported in name order | `test_not_allowed_reports_categories_in_name_order` | ☑ |
| Every category allowed | make | no violation | `test_allowed_clean_when_every_category_is_allowed` | ☑ |
| Empty allowed list | make | no violation | `test_allowed_empty_is_not_enforced` | ☑ |
| Offense rules and allowed list | make | ignored | `test_defense_gameplan_ignores_offense_rules` | ☑ |
| 2-DL front over cap (ratio) | make | "... has 2 of 2 2-DL plays; allows at most 1/2." | `test_two_dl_cap_fires` | ☑ |
| 2-DL front over cap (percent) | make | "... has 2 of 3 2-DL plays; allows at most 50%." | `test_two_dl_percent_cap_names_the_percent` | ☑ |
| 2-DL front exactly at cap (1 of 2 = 1/2) | make | no violation | `test_two_dl_cap_clean_with_other_front` | ☑ |
| 2-DL cap of 0 (count, ratio, percent), one 2-DL play | make | "... has 1 of 1 2-DL plays; allows at most 0." (`0%` for percent) | `test_two_dl_cap_of_zero_fires` `[P]` | ☑ |
| 2-DL cap of 0, no 2-DL play | make | no violation | `test_two_dl_cap_of_zero_clean_without_a_two_dl_play` `[P]` | ☑ |
| 2-DL cap of 1 or 100%, every play 2-DL | make | no violation | `test_two_dl_cap_at_its_highest_allows_every_play` `[P]` | ☑ |
| All issues reported | make | max_count, required, not allowed, in that order; the empty required category not also short of its minimum | `test_all_issues_reported_including_not_allowed` | ☑ |

### Special
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Required special missing, defense / offense | make | "Required special category 'Kick Return' has no play" / "'Punt'" | `test_special_category_required_fires` `[P]` | ☑ |
| Required special met by a custom or a stock play | make | no violation | `test_special_category_required_met_by_either_play` `[P]` | ☑ |
| Stock-only special, first / last category with a custom slot | make | "Special category 'Field Goal/PAT Defense' uses a stock play; a custom play is required" / "'Squib Return'" | `test_custom_special_play_required_fires` `[P]` | ☑ |
| Custom, stock and custom, or empty slot | make | no violation | `test_custom_special_play_required_clean` `[P]` | ☑ |
| Stock-only special, rule not set | make | no violation | `test_custom_special_play_not_required_by_default` | ☑ |
| Required clock category on offense | make | no violation (stock clock plays present) | `test_required_clock_category_satisfied_on_offense` | ☑ |
| Required clock category on defense | make | "Required special category 'Stop Clock' has no play" (the rules-file name) | `test_required_clock_category_fires_on_defense` | ☑ |
| Clock categories exempt from custom-required | make | no violation | `test_custom_special_play_required_ignores_clock_categories` | ☑ |

### Resolution (both sides)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Unresolved play | make | "Play 'GHOST' at slot 1 (1-1) is not in the play pool"; no category | `test_unresolved_play_message_names_the_play_and_its_slot` | ☑ |
| Unresolved play not counted | make, `max_count = 1` | only `UNRESOLVED_PLAY` | `test_unresolved_play_is_not_counted_in_its_category` | ☑ |
| Repeated play, any case, slots 5 and 64 | make | "Duplicate play 'rl0' at slot 5 (2-1) (already at slot 1 (1-1))", then slot 64 (16-4); the first not flagged | `test_duplicate_play_names_both_slots_any_case` | ☑ |
| Different plays | make | no violation | `test_different_plays_are_not_duplicates` | ☑ |
