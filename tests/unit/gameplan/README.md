# gameplan — Test Matrix

Tool-logic unit cases (rules loader). Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). CLI cases live in [../../integration/README.md](../../integration/README.md).

One row per behavior. Input: `tmp` = constructed TOML; `data` = shipped `release/rules/PNFL.gameplan.toml`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/gameplan` passes.

## rules.py — `load_rules`

### Short-name labels
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense label → full name | tmp | `[offense.RM]` → "Run Middle" | `test_offense_short_label_maps_to_full_name` | ☑ |
| Defense label → full name | tmp | `[defense.RunDazzle]` → "Run Dazzle" | `test_defense_short_label_maps_to_full_name` | ☑ |
| Unknown offense label | tmp | "not an offense category label" | `test_unknown_offense_label` | ☑ |
| Unknown defense label | tmp | "not a defense category label" | `test_unknown_defense_label` | ☑ |

### min_count / max_count
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `required`/`min_count` omitted → default | tmp | False / 0; cap-only rule valid | `test_required_and_min_count_default_when_omitted` | ☑ |
| Empty section rejected | tmp | "empty rule" | `test_empty_section_rejected` | ☑ |
| `required` must be bool | tmp | "must be a boolean" | `test_required_must_be_bool` | ☑ |
| `min_count` must be int | tmp | "must be an integer" | `test_min_count_must_be_int` | ☑ |
| `max_count` optional (offense) | tmp | parsed | `test_max_count_optional_offense` | ☑ |
| `max_count` optional (defense) | tmp | parsed | `test_max_count_optional_defense` | ☑ |
| `max_count` absent → None | tmp | None | `test_max_count_absent_is_none` | ☑ |
| `max_count` must be int | tmp | "must be an integer" | `test_max_count_must_be_int` | ☑ |

### caps gating
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Run cap on pass category | tmp | "unknown key" | `test_run_cap_rejected_on_pass` | ☑ |
| Pass caps parse | tmp | rollouts count + timed ratio | `test_pass_caps_parse` | ☑ |

### one form per attribute
Each attribute (`qb_draws`, `rollouts`, `timed`, `two_dl`) takes exactly one of
`_count` / `_ratio` / `_percent`.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Any single form | tmp | loads | `test_one_form_of_one_attribute_accepted` `[P]` | ☑ |
| Two forms of one attribute | tmp | "at most one of" | `test_two_forms_of_one_attribute_rejected` `[P]` | ☑ |

### value ranges
Counts (`min_count`, `max_count`, `max_<attr>_count`) >= 0; ratios in [0, 1];
percents in [0, 100]: limit ok + one outside. One test per shared validator.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Count at lower limit 0 | tmp | loads | `test_count_zero_ok` `[P]` | ☑ |
| Count below 0 | tmp | ">= 0" | `test_count_negative_rejected` `[P]` | ☑ |
| Ratio at limits 0 / 1 | tmp | parsed | `test_ratio_in_range_ok` `[P]` | ☑ |
| Ratio below 0 / above 1 | tmp | "[0, 1]" | `test_ratio_out_of_range_rejected` `[P]` | ☑ |
| Ratio not a string | tmp | 'must be a string like "1/2"' | `test_ratio_must_be_string` | ☑ |
| Percent at limits 0 / 100 | tmp | parsed | `test_percent_in_range_ok` `[P]` | ☑ |
| Percent below 0 / above 100 | tmp | "[0, 100]" | `test_percent_out_of_range_rejected` `[P]` | ☑ |
| Percent not an int | tmp | "must be an integer" | `test_percent_must_be_int` | ☑ |

### disallowed categories
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Parse offense + defense lists | tmp | frozensets | `test_disallowed_categories_parse` | ☑ |
| Unknown category | tmp | "unknown category" | `test_disallowed_unknown_category` | ☑ |
| Not a list | tmp | "must be a list" | `test_disallowed_must_be_list` | ☑ |
| Absent → empty | tmp | empty frozensets | `test_disallowed_absent_is_empty` | ☑ |

### layering / paths
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty path list | — | "at least one" | `test_empty_paths_rejected` | ☑ |
| Later file replaces a category rule | tmp ×2 | whole rule replaced | `test_layering_replaces_category_rule` | ☑ |

### shipped rules
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| PNFL rule set loads | data | counts + disallowed lists | `test_pnfl_rules_load` | ☑ |

## validators.py — `validate_gameplan`

Constructed gameplan + pool (records carry typed playpool attributes). Each side has its own harness; offense gameplans also carry the two required clock plays.

### Offense
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `min_count` short | make | `CATEGORY_MIN_COUNT` | `test_offense_min_count_fires` | ☑ |
| Required category absent | make | `CATEGORY_REQUIRED` | `test_offense_required_fires` | ☑ |
| `max_count` exceeded | make | `CATEGORY_MAX_COUNT` | `test_offense_max_count_fires` | ☑ |
| Disallowed category present | make | `CATEGORY_DISALLOWED` | `test_offense_disallowed_fires` | ☑ |
| `max_qb_draws_count` exceeded | make | `CATEGORY_MAX_QB_DRAWS` | `test_offense_max_qb_draws_count_fires` | ☑ |
| `max_qb_draws_count` within limit | make | no violation | `test_offense_max_qb_draws_count_clean` | ☑ |
| `max_rollouts_count` exceeded | make | `CATEGORY_MAX_ROLLOUTS` | `test_offense_max_rollouts_count_fires` | ☑ |
| `max_rollouts_count` within limit | make | no violation | `test_offense_max_rollouts_count_clean` | ☑ |
| `max_timed_ratio` exceeded | make | `CATEGORY_MAX_TIMED` | `test_offense_max_timed_ratio_fires` | ☑ |
| `max_timed_ratio` within limit | make | no violation | `test_offense_max_timed_ratio_clean` | ☑ |
| `max_timed_percent` exceeded (2/3 > 50%) | make | `CATEGORY_MAX_TIMED` | `test_offense_max_timed_percent_fires` | ☑ |
| `max_timed_percent` exactly at cap (1/2 = 50%) | make | no violation | `test_offense_max_timed_percent_clean_at_cap` | ☑ |

### Defense
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `min_count` short | make | `CATEGORY_MIN_COUNT` | `test_min_count_fires` | ☑ |
| Optional empty category | make | no min_count / required | `test_min_count_not_checked_when_category_empty` | ☑ |
| `max_count` exceeded | make | `CATEGORY_MAX_COUNT` | `test_max_count_fires` | ☑ |
| `max_count` within limit | make | no violation | `test_max_count_clean_within_limit` | ☑ |
| Disallowed category present | make | `CATEGORY_DISALLOWED` | `test_disallowed_fires` | ☑ |
| Disallowed category unused | make | no violation | `test_disallowed_clean_when_unused` | ☑ |
| 2-DL front over cap | make | `CATEGORY_MAX_TWO_DL` | `test_two_dl_cap_fires` | ☑ |
| 2-DL front under cap | make | no violation | `test_two_dl_cap_clean_with_other_front` | ☑ |
| All issues reported (incl. disallowed) | make | disallowed + max_count + required all present | `test_all_issues_reported_including_disallowed` | ☑ |

### Special
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Required special missing | make | `SPECIAL_CATEGORY_REQUIRED` | `test_special_category_required_fires` | ☑ |
| Stock-only special | make | `CUSTOM_SPECIAL_PLAY_REQUIRED` | `test_custom_special_play_required_fires` | ☑ |

### Resolution (both sides)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Unresolved play | make | `UNRESOLVED_PLAY` | `test_unresolved_play_fires` | ☑ |
