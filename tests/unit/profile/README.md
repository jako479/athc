# profile — Test Matrix

Tool-logic unit cases (rules loader, validators, gameplan compatibility, diff, display labels, writer). Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). CLI cases live in [../../integration/README.md](../../integration/README.md).

One row per behavior. `[P]` = parametrized. Input: `data/` real `.prf` + `profile_rules.toml`; `tmp` = constructed TOML; `make` = `ProfileRules` built in-test; `built` = synthetic `Profile` from `conftest.make_profile`; `const` = module constants. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/profile` passes.

## rules.py — `load_rules`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid file loads every top-level part | data | audibles, min, compat flag, QB exact + 6 ranged groups, both allowed lists, 15 offense / 4 defense rules | `test_load_valid_full` | ☑ |
| `disallowed` parsed | data | disallowed = {PRD}, allowed None | `test_disallowed_parsed` | ☑ |
| `disallowed = []` forbids nothing | tmp | disallowed empty, allowed None | `test_disallowed_empty_list_forbids_nothing` | ☑ |
| `mandatory` parsed | data | `( {PLR}, )` | `test_mandatory_parsed` | ☑ |
| `mandatory` flat list → AND | tmp | `( {RL}, {RM} )` | `test_mandatory_multiple_categories` | ☑ |
| Rule-level `min_categories` | tmp | `rule.min_categories == 3` | `test_min_categories_on_rule` | ☑ |
| Omitted buckets → None | tmp | all filters None | `test_omitted_buckets_are_none` | ☑ |
| Every time / down / yards / fields value → its bucket | tmp | 5 + 4 + 4 + 5 values | `test_filter_value_selects_its_bucket` `[P]` | ☑ |
| Every situation category name → its codes | tmp | 13 offense, 10 defense; a defense pass name → all three directions | `test_situation_category_name_selects_its_codes` `[P]` | ☑ |
| Section `allowed = []` | tmp | empty set, not None | `test_situation_allowed_empty_list_is_an_empty_set` | ☑ |
| Allowed category lists: labels → codes, defense label → each code | tmp | `{RL, PSR}`; `PassShort` → all three pass-short codes | `test_allowed_categories_parse` | ☑ |
| Every category's league label → exactly its codes | tmp, one label per test | 16 offense, 10 defense categories | `test_allowed_list_label_stands_for_its_category_codes` `[P]` | ☑ |
| Allowed lists omitted / `[]` → not enforced | tmp | both empty | `test_allowed_categories_omitted_is_empty` / `_empty_list_is_empty` | ☑ |
| Layering: later allowed list replaces / `[]` clears / omitted keeps | tmp ×2 | whole result | `test_layering_replaces_allowed_list` / `test_layering_empty_list_clears_allowed` / `test_layering_omitted_keeps_allowed` | ☑ |
| `audibles_allowed` omitted → default | tmp | True (no audibles check) | `test_audibles_allowed_defaults_when_omitted` | ☑ |
| `min_categories` omitted → default | tmp | 0 (no baseline) | `test_min_categories_defaults_when_omitted` | ☑ |
| `min_categories` = 0 (lower limit) ok | tmp | min == 0 | `test_min_categories_zero_ok` | ☑ |
| Rule `min_categories` = 0 ok | tmp | rule min == 0 | `test_rule_min_categories_zero_ok` | ☑ |
| Substitutions: one group / all 8 | tmp | parsed into `substitutions` map | `test_substitutions_single_group` / `_all_groups` | ☑ |
| Sub min/max on both sides | tmp | `PercentBound(minimum, maximum)` per side | `test_substitutions_min_max_both_sides` | ☑ |
| Sub single key (each of 6, at 0 and 100) → rest unchecked | tmp | only that bound set | `test_substitutions_single_key_leaves_rest_unchecked` `[P]` | ☑ |
| Sub exact one side, range other | tmp | mixed bounds | `test_substitutions_exact_one_side_range_other` | ☑ |
| Sub min == max ok | tmp | accepted | `test_substitutions_min_equals_max_ok` | ☑ |
| Sub out vs in not checked for ranges | tmp | accepted | `test_substitutions_out_vs_in_not_checked_for_ranges` | ☑ |
| Substitutions omitted → empty (all optional) | tmp | `{}` | `test_substitutions_omitted_is_empty` | ☑ |
| Substitutions layering | tmp ×2 | later file replaces whole group; groups accumulate | `test_substitutions_layering_override_and_accumulate` | ☑ |
| Sub percents at limits | tmp | accepted (0/100, out=in) | `test_substitutions_percent_limits_ok` `[P]` | ☑ |
| Layering overrides `min_categories` | tmp ×2 | later value wins | `test_layering_overrides_scalar` | ☑ |
| Layering overrides `audibles_allowed` | tmp ×2 | later value wins | `test_layering_overrides_audibles` | ☑ |
| Layering: same side and name replaces the rule in place; other names accumulate; offense and defense apart | tmp ×2 | whole result | `test_layering_replaces_situation_rule_by_label` | ☑ |
| `[gameplan_compatibility]` omitted → default | tmp | flag False | `test_gameplan_compatibility_defaults_when_omitted` | ☑ |
| `[gameplan_compatibility]` parses | tmp | flag as written | `test_gameplan_compatibility_parses` | ☑ |
| `[gameplan_compatibility]` unknown key | tmp | "unknown key" | `test_gameplan_compatibility_unknown_key` | ☑ |
| `[gameplan_compatibility]` rejects the gameplan rules' flag | tmp | "unknown key" | `test_gameplan_compatibility_rejects_the_gameplan_rules_flag` | ☑ |
| `[gameplan_compatibility]` non-bool | tmp | "must be a boolean" | `test_gameplan_compatibility_must_be_bool` | ☑ |
| `gameplan_compatibility` not a table | tmp | "Must be a table." | `test_gameplan_compatibility_must_be_table` | ☑ |
| Layering overrides a compat flag | tmp ×2 | later value wins | `test_layering_overrides_gameplan_compatibility` | ☑ |
| Every shipped league's rules load | `config/dev/` + `config/release/` `leagues/<league>/profile.toml`, with the labels of the `league.toml` beside it | loads | `test_shipped_rules_load` `[P]` | ☑ |
| Shipped allowed lists ban the old categories | same | offense RDR, PLL, PLM + the four randoms; defense none | `test_shipped_rules_ban_the_old_categories` `[P]` | ☑ |
| UTF-8 BOM skipped | tmp | loads | `test_bom_is_skipped` | ☑ |

### Error → `RulesFileError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty path list | — | "at least one" | `test_empty_paths` | ☑ |
| Missing file | — | "<path>: The system cannot find the file specified." | `test_missing_file` | ☑ |
| TOML parse error | tmp | "Not valid TOML" | `test_toml_parse_error` | ☑ |
| Negative `min_categories` | tmp | ">= 0" | `test_negative_min_categories_rejected` | ☑ |
| Negative rule `min_categories` | tmp | ">= 0" | `test_negative_rule_min_categories_rejected` | ☑ |
| Multiple problems collected (one file) | tmp | all 3 in `.errors` | `test_collects_multiple_errors` | ☑ |
| Multiple problems collected (across files) | tmp | both in `.errors` | `test_collects_errors_across_files` | ☑ |
| Unknown top-level key | tmp | "unknown key" | `test_unknown_top_key` | ☑ |
| `schema_version` is an unknown top-level key | tmp | "unknown key" | `test_schema_version_is_an_unknown_key` | ☑ |
| Unknown situation key | tmp | "unknown key" | `test_unknown_situation_key` | ☑ |
| Situation has no constraint | tmp | "needs one of" | `test_situation_needs_constraint` | ☑ |
| Bad `time` value | tmp | "unknown value" | `test_bad_time` | ☑ |
| Filter not a string | tmp | "[offense.x].time: Must be a string." | `test_filter_must_be_a_string` | ☑ |
| `allowed` + `disallowed` | tmp | "Set at most one of allowed, disallowed." | `test_allowed_and_disallowed_exclusive` | ☑ |
| Unknown category | tmp | "unknown category" | `test_unknown_category` | ☑ |
| Category entry not a string | tmp | "[offense.x].allowed: Entries must be strings (got int)." | `test_category_entries_must_be_strings` | ☑ |
| `mandatory` not a list | tmp | "[offense.x].mandatory: Must be a list." | `test_mandatory_must_be_list` | ☑ |
| `disallowed` not a list | tmp | "[offense.x].disallowed: Must be a list." | `test_disallowed_must_be_list` | ☑ |
| `fields` empty | tmp | "[offense.x].fields: Must be a non-empty list." | `test_fields_must_be_a_non_empty_list` | ☑ |
| `mandatory` unknown category | tmp | "unknown category" | `test_mandatory_unknown_category` | ☑ |
| Allowed list: game name rejected | tmp | "'Razzle Dazzle Run' is not an offense category label. Valid: …" | `test_allowed_categories_reject_game_name` | ☑ |
| Allowed list: other side's label rejected | tmp | "'RL' is not a defense category label. Valid: …" | `test_allowed_categories_reject_unknown_defense_label` | ☑ |
| Allowed list: User Specific label rejected | tmp | "'US' is not an offense category label." | `test_allowed_categories_reject_user_specific_label` | ☑ |
| Allowed list: league with no labels | tmp | "… Valid: ." | `test_allowed_categories_without_league_labels` | ☑ |
| Allowed list not a list / non-string entry | tmp | "Must be a list." / "Entries must be strings." | `test_allowed_categories_must_be_list` / `_entries_must_be_strings` | ☑ |
| Unknown field name | tmp | "unknown value" | `test_unknown_field_name` | ☑ |
| Field entry not a string | tmp | "[offense.x].fields: Entries must be strings." | `test_field_entries_must_be_strings` | ☑ |
| `offense` / `defense` not a table | tmp | "[offense]: Must be a table." and "[defense]: Must be a table.", both collected | `test_side_must_be_a_table` `[P]` | ☑ |
| Section not a table | tmp | "[offense.x]: Must be a table." only | `test_situation_must_be_a_table` `[P]` | ☑ |
| Sub percent below 0 / above 100, every key | tmp | "<key>: must be in [0, 100]" | `test_substitutions_percent_out_of_range` `[P]` | ☑ |
| Sub exact + min/max on one side | tmp | "Set at most one of …" | `test_substitutions_exact_with_bound_same_side_rejected` `[P]` | ☑ |
| Sub min > max, either side | tmp | "`.min_…: Must be <= max_…`" | `test_substitutions_min_above_max_rejected` `[P]` | ☑ |
| Sub exact out one above in | tmp | "[substitutions].QB.out_percent: Must be <= in_percent (80), got 81." | `test_substitutions_out_above_in_rejected` | ☑ |
| Sub group with no key | tmp | "needs one of" | `test_substitutions_empty_group_rejected` | ☑ |
| Sub unknown position | tmp | "unknown key" | `test_substitutions_unknown_position` | ☑ |
| Sub unknown group key | tmp | "unknown key" | `test_substitutions_unknown_group_key` | ☑ |
| `[substitutions]` not a table | tmp | "Must be a table." | `test_substitutions_not_a_table` | ☑ |
| Sub position not a table | tmp | "Must be a table." | `test_substitutions_position_not_a_table` | ☑ |
| Sub non-integer, every key | tmp | "<key>: must be an integer" | `test_substitutions_non_integer` `[P]` | ☑ |
| Sub float / bool | tmp | "must be an integer" | `test_substitutions_float_or_bool_rejected` `[P]` | ☑ |

## validators.py — `validate_profile`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Audibles fires when on | OFF-AUD + make | only "Audibles must be unchecked." | `test_audibles_fires` | ☑ |
| Audibles clean when off | OFF1 + make | no `AUDIBLES_UNCHECKED` | `test_audibles_passes_when_off` | ☑ |
| Audibles allowed → skip | OFF-AUD + make | no violation | `test_audibles_allowed_never_fires` | ☑ |
| Audibles omitted → no check either state | OFF1/OFF-AUD + tmp | no `AUDIBLES_UNCHECKED` | `test_audibles_omitted_allows_either_state` | ☑ |
| Substitution fires when mismatched, every group | built + make | `SUBSTITUTION` | `test_substitution_fires_when_mismatched` `[P]` | ☑ |
| Substitution clean when matched, every group | built + make | no violation | `test_substitution_passes_when_matched` `[P]` | ☑ |
| Substitution skipped on opposite side, every group | built + make | no violation | `test_substitution_skipped_on_other_side` `[P]` | ☑ |
| Exact: each unmet side is its own violation | built + make | "Quarterbacks out_percent must be 70, got 80." + in line | `test_substitution_exact_reports_each_side` | ☑ |
| Exact: matched side silent | built + make | in line only | `test_substitution_exact_matched_side_is_silent` | ☑ |
| Range bounds: min-1, min, max, max+1 | built + make | ">= 70" at 69 / none at 70 and 80 / "<= 80" at 81 | `test_substitution_range_bounds_inclusive` `[P]` | ☑ |
| Min only / max only, at the bound and one past | built + make | fires at 84 / 86; clean at 85 | `test_substitution_min_only` / `_max_only` | ☑ |
| Unchecked side accepts any value | built + make | no violation | `test_substitution_unchecked_side_accepts_any_value` | ☑ |
| Exact one side + range other | built + make | one line per unmet side | `test_substitution_exact_and_range_mixed` | ☑ |
| Bound on defense group | built + make | fires on defense, skipped on offense | `test_substitution_bound_on_defense_group` | ☑ |
| Multiple groups each fire | built + make | two `SUBSTITUTION` | `test_substitution_multiple_groups_each_fire` | ☑ |
| No substitutions → no violation | OFF1 + make | no `SUBSTITUTION` | `test_no_substitutions_no_violation` | ☑ |
| Min-categories at the limit and one past | built + make | 2 categories: clean at min 2; every situation "has 2 …; requires 3." at min 3 | `test_min_categories_at_the_limit_and_one_past` `[P]` | ☑ |
| Weight 1 counts a category, weight 0 does not | built + make | flagged at weight 0 only | `test_weight_one_counts_a_category_and_weight_zero_does_not` `[P]` | ☑ |
| Rule `min_categories` raises the baseline where it matches, with or without one | built + make | exactly the 504 `>5:00` situations, "requires 3" | `test_rule_min_categories_raises_the_baseline_where_it_matches` `[P]` | ☑ |
| Baseline wins over lower rule | built + make | every situation "requires 3" | `test_min_categories_baseline_wins_over_lower_rule` | ☑ |
| Strictest of several matching rules wins | built + make | rules 2, 4, 3 → "requires 4" | `test_min_categories_strictest_matching_rule_wins` | ☑ |
| Waived only for exempt categories, each special and random code alone | built + make | waived: FG, punt (+ run clock on offense); fakes, randoms, a run not waived | `test_min_categories_waived_only_for_exempt_categories` `[P]` | ☑ |
| Exempt combination waived | built + make | punt+punt+kick waived at min 3 | `test_exempt_combination_waived` | ☑ |
| Exempt + non-exempt obeys minimum | built + make | punt+punt+PSL: fires @3, ok @2 | `test_exempt_plus_non_exempt_obeys_minimum` | ☑ |
| Not waived with a non-exempt category | built + make | min fires | `test_min_categories_not_waived_with_non_exempt_category` | ☑ |
| All-zero weights → 0 categories | built + make | min fires (never waived) | `test_min_categories_fires_on_all_zero_weights` | ☑ |
| No baseline → single category passes | built + make | no min violation | `test_no_minimum_passes_single_category` | ☑ |
| Matrix rule fires in non-OVER_FIVE bucket | built + make | flags TWO_TO_FIVE sit, not OVER_FIVE | `test_matrix_rule_fires_in_non_over_five_bucket` | ☑ |
| Omitted buckets match all | built + make | matches whole time bucket | `test_omitted_buckets_match_all` | ☑ |
| Multiple `mandatory` each required | built + make | situations 8-14 each flagged once, for the missing category only | `test_multiple_mandatory_categories_each_required` | ☑ |
| Same `mandatory` in two matching rules | built + make | one violation per situation | `test_mandatory_category_of_two_matching_rules_reported_once` | ☑ |
| Two matching rules' `allowed` intersect | built + make | RM+PSL and RM+PML → "uses disallowed categories: 0x0A, 0x0D", every situation | `test_two_matching_rules_allowed_intersect` | ☑ |
| Category outside the allowed list banned | built + make | "Situation N uses banned categories: 0x03", every situation | `test_category_outside_allowed_list_is_banned` | ☑ |
| Allowed list clean when every used category listed | built + make | no violation | `test_allowed_list_clean_when_every_used_category_is_listed` | ☑ |
| Empty allowed list enforces nothing, both sides | built + make | no violation | `test_empty_allowed_list_enforces_nothing` `[P]` | ☑ |
| Allowed list scope, every code of each side | built + make | offense 0x00-0x0F and 0x17-0x1A banned, 0x10-0x16 not; defense 0x00-0x0F banned, 0x10-0x15 not; under the side's rule name | `test_allowed_list_scope` `[P]` | ☑ |
| Rule `disallowed` fires only where the rule matches | built + make | sit 11 flagged, sit 515 not | `test_rule_disallowed_fires_only_where_the_rule_matches` | ☑ |
| Rule `disallowed` leaves unlabeled categories alone | built + make | Pass Long Left not flagged | `test_rule_disallowed_leaves_unlabeled_categories_alone` | ☑ |
| Rule `disallowed` + allowed list → one violation | built + make | "Situation 11 uses banned categories: 0x03, 0x0D" | `test_rule_disallowed_combines_with_allowed_list` | ☑ |
| Two matching rules' `disallowed` union | built + make | one violation listing both codes | `test_two_matching_rules_disallowed_union` | ☑ |
| All issues reported, under the profile's side | built + make | the side's disallowed, allowed, mandatory and min rule names | `test_all_issues_reported_under_the_profiles_side` `[P]` | ☑ |
| Full offense rules | OFF1 + data | 18, each situation and rule pinned | `test_offense_full_rules` | ☑ |
| Full defense rules | DEF1 + data | DL, LB, DB "out_percent must be <= 95, got 96." + 7 min-categories | `test_defense_full_rules` | ☑ |

## compat.py — `check_gameplan_compatibility` (constructed `Profile` + `GamePlan`)
One row per behavior. Input: `built` = `Profile`/`GamePlan` constructed in-test.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| A custom play of each category backs exactly its codes | built, profile using every normal code | the rest missing; defense pass plays cover all three directions | `test_custom_play_backs_exactly_its_categorys_codes` `[P]` | ☑ |
| Offense normal missing | built | "play category GLR (0x00) has no custom play in the game plan" | `test_offense_normal_missing` | ☑ |
| Each special code needs a custom play in its own slot | built | covered by its slot only; else "special category <name> has no custom special play …" | `test_special_category_needs_a_custom_play_in_its_slot` `[P]` | ☑ |
| Stock-only special not enough | built | missing (custom required) | `test_special_stock_only_is_not_enough` | ☑ |
| Defense: each unbacked pass direction its own issue | built | PassLong 0x07 and 0x09 | `test_defense_each_unbacked_direction_is_its_own_issue` | ☑ |
| Defense normal / special missing | built | `MISSING_NORMAL` (GLpass) / `MISSING_SPECIAL` (FG/PAT) | `test_defense_normal_missing` / `test_defense_special_missing` | ☑ |
| User Specific play covers nothing | built | RM still flagged | `test_user_specific_normal_play_covers_nothing` | ☑ |
| Clock / random skipped | built | no issues | `test_clock_and_random_categories_are_skipped` | ☑ |
| Category used from weight 1, not at weight 0 | built | GLR flagged at 1 only | `test_category_is_used_from_weight_one` `[P]` | ☑ |
| Multiple issues sorted (normal then special) | built | ascending codes | `test_multiple_issues_sorted_normal_then_special` | ☑ |
| PAT-only category checked | built | FG/PAT flagged | `test_pat_only_category_is_checked` | ☑ |
| Fully compatible | built | empty | `test_fully_compatible_returns_empty` | ☑ |

## compat.py — `gameplan_extra_categories` (gameplan categories the profile never uses)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Extra normal / special category reported | built | `EXTRA_NORMAL` (Goal Line Run, no code) / `EXTRA_SPECIAL` (FG/PAT) | `test_extra_offense_normal_category_reported` / `test_extra_special_category_reported` | ☑ |
| Used categories not reported | built | empty | `test_used_categories_are_not_reported` | ☑ |
| Defense direction collapse not false-flagged | built | one used dir ⇒ category not extra | `test_defense_direction_collapse_not_falsely_reported` | ☑ |
| Extra normals sorted by code | built | GLR before GLP | `test_extra_normal_sorted_by_code` | ☑ |
| Stock-only special is not extra | built | empty | `test_stock_special_play_is_not_an_extra` | ☑ |
| User Specific play is not extra | built | empty | `test_user_specific_play_is_not_an_extra` | ☑ |

## diff.py — `diff_profiles`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Identical → empty | built | `is_empty` | `test_identical_profiles_have_empty_diff` | ☑ |
| Profile type recorded, both sides | built | side preserved | `test_profile_type_recorded` `[P]` | ☑ |
| FG range / audibles / sub change | built | one `ScalarChange` each | `test_field_goal_range_change` / `test_audibles_change` / `test_substitution_change` | ☑ |
| Stop-clock change | built | the one `SituationChange`: number 8, label `>5 1st 0-1 DEF5-35 Ahd8+`, `stop` | `test_situation_stop_clock_change` | ☑ |
| Weight-only / category / multi-slot | built | the one `SituationChange` with its `SlotChange`s | `test_situation_weight_only_change` / `_category_change` / `_multiple_slot_changes` | ☑ |
| Unchanged excluded | built | only changed kept | `test_unchanged_situations_excluded` | ☑ |
| PAT change | built | the one PAT `SituationChange`: number 7, label `>5 Ahd1`, no `stop` | `test_pat_change` | ☑ |
| Combined counts | built | profile + situation | `test_combined_changes_counts` | ☑ |
| Cross-side raises | built | "Cannot compare a.prf (offense) with b.prf (defense)." with both paths; "Cannot compare offense with defense." with one or none | `test_type_mismatch_raises` `[P]` | ☑ |
| N-constant guard | built | sit 8 game state + baseline | `test_situation_n_game_state_and_baseline` | ☑ |

## display.py — labels
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Category label, every code of each side | code | offense caps, defense words with the pass directions collapsed; a code without a label → `0xNN` | `test_category_label_of_every_code` `[P]` | ☑ |
| Situation label, every situation | every walked game state | its five bucket labels in order | `test_situation_label_of_every_situation` | ☑ |
| PAT label, every PAT situation | every walked PAT game state | its two bucket labels | `test_pat_label_of_every_pat_situation` | ☑ |
| Sub label, every group | str | `OL` … `K` | `test_sub_label_of_every_group` | ☑ |

## writer.py — `ProfileWriter.apply` (real `.prf` + mutated sources)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| stop-clock: replace all (weights kept) / idempotent | OFF1 | every situation's bit copied | `test_copy_stop_clock_replaces_every_situation` / `_idempotent_when_source_equals_target` | ☑ |
| No flags → target unchanged | OFF1 | `result == target` | `test_copy_no_flags_returns_target_unchanged` | ☑ |
| stop-clock on defense | DEF1 | bits copied | `test_copy_stop_clock_works_on_defense` | ☑ |
| sub-percent: replaces only the substitutions | OFF1 | whole result | `test_copy_sub_percent_replaces_only_substitutions` | ☑ |
| field-goal-range: replaces only the range | OFF1 | whole result | `test_copy_field_goal_range_replaces_only_the_range` | ☑ |
| fourth-down only / on defense | OFF1 / DEF1 | only 4th-down situations copied | `test_copy_fourth_down_copies_only_fourth_down_situations` / `_works_on_defense` | ☑ |
| goal-line only, both inside-5 buckets | OFF1 | only goal-line copied | `test_copy_goal_line_copies_only_goal_line_situations` | ☑ |
| fourth-down / goal-line / both slot counts | OFF1 | 630 / 840 / 1260 situations copied | `test_copy_fourth_down_and_goal_line_slot_counts` `[P]` | ☑ |
| pat-logic: replaces only the PAT table / on defense / untouched without flag | OFF1 / DEF1 | PAT table copied, rest intact | `test_copy_pat_logic_replaces_only_the_pat_table` / `_works_on_defense` / `test_copy_without_pat_logic_leaves_pat_situations_alone` | ☑ |
| Combined flags independent | OFF1 | each field applied | `test_combined_flags_apply_each_independently` | ☑ |
| fourth-down + stop-clock combine | OFF1 | clean overlap | `test_fourth_down_and_stop_clock_combine_cleanly` | ☑ |
| Side mismatch raises before any copy | OFF1↔DEF1, no flags | `ProfileTypeMismatchError` with both types, "<target>: Cannot copy from <source> (offense) to a defense profile." | `test_mismatch_raises_before_any_copy` | ☑ |
