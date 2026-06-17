# profile — Test Matrix

Tool-logic unit cases (rules loader + validators). Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). CLI cases live in [../../integration/README.md](../../integration/README.md).

One row per behavior. `[P]` = parametrized. Input: `data/` real `.prf` + `profile_rules.toml`; `tmp` = constructed TOML; `make` = `ProfileRules` built in-test; `built` = synthetic `Profile` from `conftest.make_profile`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/profile` passes.

## rules.py — `load_rules`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid file loads all fields | data | audibles/min/subs/situations | `test_load_valid_full` | ☑ |
| `disallowed` → complement | data | allowed = universe − {PRD} | `test_disallowed_expands_to_complement` | ☑ |
| `mandatory` parsed | data | `( {PLR}, )` | `test_mandatory_parsed` | ☑ |
| `mandatory` flat list → AND | tmp | `( {RL}, {RM} )` | `test_mandatory_multiple_categories` | ☑ |
| Rule-level `min_categories` | tmp | `rule.min_categories == 3` | `test_min_categories_on_rule` | ☑ |
| Omitted buckets → None | tmp | all filters None | `test_omitted_buckets_are_none` | ☑ |
| Disallowed category lists | tmp | offense/defense code sets | `test_disallowed_categories_parse` | ☑ |
| `audibles_allowed` omitted → default | tmp | True (no audibles check) | `test_audibles_allowed_defaults_when_omitted` | ☑ |
| `min_categories` omitted → default | tmp | 0 (no baseline) | `test_min_categories_defaults_when_omitted` | ☑ |
| `min_categories` = 0 (lower limit) ok | tmp | min == 0 | `test_min_categories_zero_ok` | ☑ |
| Rule `min_categories` = 0 ok | tmp | rule min == 0 | `test_rule_min_categories_zero_ok` | ☑ |
| Substitutions: one group / all 8 | tmp | parsed into `substitutions` map | `test_substitutions_single_group` / `_all_groups` | ☑ |
| Substitutions omitted → empty (all optional) | tmp | `{}` | `test_substitutions_omitted_is_empty` | ☑ |
| Substitutions layering | tmp ×2 | later wins; groups accumulate | `test_substitutions_layering_override_and_accumulate` | ☑ |
| Sub percents at limits, every group | tmp | accepted (0/100, out=in) | `test_substitutions_percent_limits_ok` `[P]` | ☑ |
| Layering overrides `min_categories` | tmp ×2 | later value wins | `test_layering_overrides_scalar` | ☑ |
| Layering overrides `audibles_allowed` | tmp ×2 | later value wins | `test_layering_overrides_audibles` | ☑ |
| Five time buckets → distinct rules | tmp | one rule per `MinutesRemaining` | `test_all_time_buckets_match_distinctly` | ☑ |
| Shipped PNFL rules load | data | min/disallowed/situations | `test_pnfl_rules_load` | ☑ |

### Error → `RulesFileError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty path list | — | "at least one" | `test_empty_paths` | ☑ |
| TOML parse error | tmp | "TOML parse error" | `test_toml_parse_error` | ☑ |
| Negative `min_categories` | tmp | ">= 0" | `test_negative_min_categories_rejected` | ☑ |
| Negative rule `min_categories` | tmp | ">= 0" | `test_negative_rule_min_categories_rejected` | ☑ |
| Multiple problems collected (one file) | tmp | all 3 in `.errors` | `test_collects_multiple_errors` | ☑ |
| Multiple problems collected (across files) | tmp ×2 | both in `.errors` | `test_collects_errors_across_files` | ☑ |
| Unknown top-level key | tmp | "unknown key" | `test_unknown_top_key` | ☑ |
| Unknown situation key | tmp | "unknown key" | `test_unknown_situation_key` | ☑ |
| Situation has no constraint | tmp | "needs one of" | `test_situation_needs_constraint` | ☑ |
| Bad `time` value | tmp | "unknown value" | `test_bad_time` | ☑ |
| `allowed` + `disallowed` | tmp | "mutually exclusive" | `test_allowed_and_disallowed_exclusive` | ☑ |
| Unknown category | tmp | "unknown category" | `test_unknown_category` | ☑ |
| `mandatory` not a list | tmp | "must be a list" | `test_mandatory_must_be_list` | ☑ |
| `mandatory` unknown category | tmp | "unknown category" | `test_mandatory_unknown_category` | ☑ |
| Disallowed unknown name | tmp | "unknown name" | `test_disallowed_categories_unknown_name` | ☑ |
| Unknown field name | tmp | "unknown value" | `test_unknown_field_name` | ☑ |
| Sub percent below 0 / above 100 / out>in, every group | tmp | "[0, 100]" / "must be <=" | `test_substitutions_percent_invalid` `[P]` | ☑ |
| Sub missing out/in key | tmp | "requires" | `test_substitutions_missing_key` | ☑ |
| Sub unknown position | tmp | "unknown key" | `test_substitutions_unknown_position` | ☑ |
| Sub unknown pair key | tmp | "unknown key" | `test_substitutions_unknown_pair_key` | ☑ |
| `[substitutions]` not a table | tmp | "must be a table" | `test_substitutions_not_a_table` | ☑ |
| Sub position not a table | tmp | "must be a table" | `test_substitutions_position_not_a_table` | ☑ |
| Sub non-integer percent | tmp | "must be an integer" | `test_substitutions_non_integer` | ☑ |

## validators.py — `validate_profile`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Audibles fires when on | OFF-AUD + make | `AUDIBLES_UNCHECKED` | `test_audibles_fires` | ☑ |
| Audibles clean when off | OFF1 + make | no `AUDIBLES_UNCHECKED` | `test_audibles_passes_when_off` | ☑ |
| Audibles allowed → skip | OFF-AUD + make | no violation | `test_audibles_allowed_never_fires` | ☑ |
| Audibles omitted → no check either state | OFF1/OFF-AUD + tmp | no `AUDIBLES_UNCHECKED` | `test_audibles_omitted_allows_either_state` | ☑ |
| Substitution fires when mismatched, every group | built + make | `SUBSTITUTION` | `test_substitution_fires_when_mismatched` `[P]` | ☑ |
| Substitution clean when matched, every group | built + make | no violation | `test_substitution_passes_when_matched` `[P]` | ☑ |
| Substitution skipped on opposite side, every group | built + make | no violation | `test_substitution_skipped_on_other_side` `[P]` | ☑ |
| Substitution message names the group | built + make | "Quarterbacks", "70/80" | `test_substitution_message_names_group` | ☑ |
| Multiple groups each fire | built + make | two `SUBSTITUTION` | `test_substitution_multiple_groups_each_fire` | ☑ |
| No substitutions → no violation | OFF1 + make | no `SUBSTITUTION` | `test_no_substitutions_no_violation` | ☑ |
| Min-categories scales with threshold | OFF1 + make | higher min flags more | `test_min_categories_scales_with_threshold` | ☑ |
| Min-categories waived when all exempt | OFF1 + make | exempt-only situations waived | `test_min_categories_waived_when_all_exempt` | ☑ |
| Rule `min_categories` raises baseline | OFF1 + make | >5:00 lifted to 3 | `test_min_categories_rule_raises_baseline` | ☑ |
| Baseline wins over lower rule min | OFF1 + make | rule's 2 ignored under baseline 3 | `test_min_categories_baseline_wins_over_lower_rule` | ☑ |
| Not waived with a non-exempt category | built + make | min fires | `test_min_categories_not_waived_with_non_exempt_category` | ☑ |
| All-zero weights → 0 categories | built + make | min fires (never waived) | `test_min_categories_fires_on_all_zero_weights` | ☑ |
| No baseline → single category passes | built + make | no min violation | `test_no_minimum_passes_single_category` | ☑ |
| Rule minimum applies without baseline | built + make | >5:00 flagged, others not | `test_rule_minimum_applies_without_baseline` | ☑ |
| Matrix rule fires in non-OVER_FIVE bucket | built + make | flags TWO_TO_FIVE sit, not OVER_FIVE | `test_matrix_rule_fires_in_non_over_five_bucket` | ☑ |
| Omitted buckets match all | built + make | matches whole time bucket | `test_omitted_buckets_match_all` | ☑ |
| Multiple `mandatory` each required | built + make | flags missing one, not the satisfied one | `test_multiple_mandatory_categories_each_required` | ☑ |
| Disallowed category fires | built + make | `OFFENSE_DISALLOWED_CATEGORY` | `test_disallowed_category_fires` | ☑ |
| Disallowed category clean when unused | built + make | no violation | `test_disallowed_category_clean_when_unused` | ☑ |
| All issues reported (incl. disallowed) | built + make | disallowed + allowed + min all present | `test_all_issues_reported_including_disallowed` | ☑ |
| Full offense rules — specific | OFF1 + data | 18; allowed@1, mandatory@300, min@43 | `test_offense_full_rules` | ☑ |
| Full defense rules | DEF1 + data | 7, all min-categories | `test_defense_full_rules` | ☑ |

## compat.py — `check_gameplan_compatibility` (constructed `Profile` + `GamePlan`)
One row per behavior. Input: `built` = `Profile`/`GamePlan` constructed in-test.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense normal covered / missing | built | none / `MISSING_NORMAL_CATEGORY` (GLR) | `test_offense_normal_covered` / `_missing` | ☑ |
| Offense special covered / missing | built | none / `MISSING_SPECIAL_CATEGORY` (Punt) | `test_offense_special_covered` / `_missing` | ☑ |
| Stock-only special not enough | built | missing (custom required) | `test_special_stock_only_is_not_enough` | ☑ |
| Defense pass directions collapse | built | one "Pass Long" play covers L/M/R | `test_defense_pass_direction_collapses` | ☑ |
| Defense normal / special missing | built | `MISSING_NORMAL` (GLpass) / `MISSING_SPECIAL` (FG/PAT) | `test_defense_normal_missing` / `test_defense_special_missing` | ☑ |
| User Specific play covers nothing | built | RM still flagged | `test_user_specific_normal_play_covers_nothing` | ☑ |
| Clock / random skipped | built | no issues | `test_clock_and_random_categories_are_skipped` | ☑ |
| Zero-weight category ignored | built | no issue | `test_zero_weight_category_is_ignored` | ☑ |
| Multiple issues sorted (normal then special) | built | ascending codes | `test_multiple_issues_sorted_normal_then_special` | ☑ |
| PAT-only category checked | built | FG/PAT flagged | `test_pat_only_category_is_checked` | ☑ |
| Fully compatible | built | empty | `test_fully_compatible_returns_empty` | ☑ |
| Maps consistent with model tables | built | offense/defense names + special slots | `test_offense_normal_map_covers_all_offense_categories` / `test_defense_normal_map_covers_all_defense_categories` / `test_special_slot_map_matches_model_names` | ☑ |

## diff.py — `diff_profiles`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Identical → empty | built | `is_empty` | `test_identical_profiles_have_empty_diff` | ☑ |
| Profile type recorded | built | side preserved | `test_profile_type_recorded` | ☑ |
| FG range / audibles / sub change | built | one `ScalarChange` each | `test_field_goal_range_change` / `test_audibles_change` / `test_substitution_change` | ☑ |
| Stop-clock change | built | `SituationChange.stop` | `test_situation_stop_clock_change` | ☑ |
| Weight-only / category / multi-slot | built | `SlotChange` shapes | `test_situation_weight_only_change` / `_category_change` / `_multiple_slot_changes` | ☑ |
| Unchanged excluded | built | only changed kept | `test_unchanged_situations_excluded` | ☑ |
| PAT change | built | `pat` populated, no `stop` | `test_pat_change` | ☑ |
| Combined counts | built | profile + situation | `test_combined_changes_counts` | ☑ |
| Cross-side raises | built | `ValueError "cannot diff"` | `test_type_mismatch_raises` | ☑ |
| N-constant guard | built | sit 8 game state + baseline | `test_situation_n_game_state_and_baseline` | ☑ |

## display.py — labels
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense caps | code | `RM`, `PSL`, `PRD`, `GLR` | `test_offense_category_labels_are_caps` | ☑ |
| Defense words + collapse | code | `RunMiddle`; 3 dirs → `PassShort` | `test_defense_labels_words_and_collapse_directions` | ☑ |
| Code outside side → hex | code | `0x01`, `0x07`, `0x13` | `test_codes_outside_side_set_fall_back_to_hex` | ☑ |
| situation / pat label format | sit | `>5 1st 0-1 DEF5-35 Ahd8+`; `>5 Ahd1` | `test_situation_label_format` / `test_pat_label_format` | ☑ |
| sub label | str | `QB`, `DB` | `test_sub_label` | ☑ |
| Exhaustive labels (no KeyError) | built | 5 / 2 tokens each | `test_every_situation_and_pat_labels_without_keyerror` | ☑ |

## writer.py — `ProfileWriter.apply` (real `.prf` + mutated sources)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| stop-clock: replace all / idempotent / preserves weights | OFF1 | every situation's bit copied | `test_copy_stop_clock_replaces_every_situation` / `_idempotent_when_source_equals_target` / `_preserves_category_weights` | ☑ |
| No flags → target unchanged | OFF1 | `result == target` | `test_copy_no_flags_returns_target_unchanged` | ☑ |
| stop-clock on defense | DEF1 | bits copied | `test_copy_stop_clock_works_on_defense` | ☑ |
| sub-percent: replace / leave others | OFF1 | subs copied, rest intact | `test_copy_sub_percent_replaces_substitutions` / `_leaves_other_fields_alone` | ☑ |
| field-goal-range: replace / leave situations | OFF1 | FG copied, situations intact | `test_copy_field_goal_range_replaces_value` / `_leaves_situations_alone` | ☑ |
| fourth-down only / on defense | OFF1 / DEF1 | only 4th-down situations copied | `test_copy_fourth_down_copies_only_fourth_down_situations` / `_works_on_defense` | ☑ |
| goal-line only / both inside-5 buckets | OFF1 | only goal-line copied | `test_copy_goal_line_copies_only_goal_line_situations` / `_covers_both_inside_5_buckets` | ☑ |
| Combined flags independent | OFF1 | each field applied | `test_combined_flags_apply_each_independently` | ☑ |
| fourth-down + stop-clock combine | OFF1 | clean overlap | `test_fourth_down_and_stop_clock_combine_cleanly` | ☑ |
| Side mismatch raises (any flag / both types) | OFF1↔DEF1 | `ProfileTypeMismatchError` | `test_mismatch_raises_for_any_flag` `[P]` / `test_mismatch_error_carries_both_types` | ☑ |
