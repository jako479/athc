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
| Pass caps parse | tmp | rollouts + timed fraction | `test_pass_caps_parse` | ☑ |

### value ranges (counts >= 0; percents in [0, 1])
Covers every count (`min_count`, `max_count`, `max_qb_draws`, `max_rollouts`) and
every percent (`max_timed_percent`, `max_two_dl_percent`): limit ok + one outside.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Count at lower limit 0 | tmp | loads | `test_count_zero_ok` `[P]` | ☑ |
| Count below 0 | tmp | ">= 0" | `test_count_negative_rejected` `[P]` | ☑ |
| Percent at limits 0 / 1 | tmp | parsed | `test_percent_in_range_ok` `[P]` | ☑ |
| Percent below 0 / above 1 | tmp | "[0, 1]" | `test_percent_out_of_range_rejected` `[P]` | ☑ |

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
| `max_qb_draws` exceeded | make | `CATEGORY_MAX_QB_DRAWS` | `test_offense_max_qb_draws_fires` | ☑ |
| `max_qb_draws` within limit | make | no violation | `test_offense_max_qb_draws_clean` | ☑ |
| `max_rollouts` exceeded | make | `CATEGORY_MAX_ROLLOUTS` | `test_offense_max_rollouts_fires` | ☑ |
| `max_rollouts` within limit | make | no violation | `test_offense_max_rollouts_clean` | ☑ |
| `max_timed_percent` exceeded | make | `CATEGORY_MAX_TIMED_PERCENT` | `test_offense_max_timed_percent_fires` | ☑ |
| `max_timed_percent` within limit | make | no violation | `test_offense_max_timed_percent_clean` | ☑ |

### Defense
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `min_count` short | make | `CATEGORY_MIN_COUNT` | `test_min_count_fires` | ☑ |
| Optional empty category | make | no min_count / required | `test_min_count_not_checked_when_category_empty` | ☑ |
| `max_count` exceeded | make | `CATEGORY_MAX_COUNT` | `test_max_count_fires` | ☑ |
| `max_count` within limit | make | no violation | `test_max_count_clean_within_limit` | ☑ |
| Disallowed category present | make | `CATEGORY_DISALLOWED` | `test_disallowed_fires` | ☑ |
| Disallowed category unused | make | no violation | `test_disallowed_clean_when_unused` | ☑ |
| 2-DL front over cap | make | `CATEGORY_MAX_TWO_DL_PERCENT` | `test_two_dl_cap_fires` | ☑ |
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
