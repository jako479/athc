# fbpro98_profile — Test Matrix

Cases covered for the `.prf` coaching-profile library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `golden` = the real game-produced profiles in `data/`: `TST-OFF1/OFF2/DEF1/DEF2.prf`, `TST-OFF1-AUD.prf` (OFF1 with audibles on), `TST-DEF1-AUD.prf` (DEF1 with audibles on and OFF1's situation 1), `TST-OFF1-PL.prf` / `TST-DEF1-PL.prf` (saved with an embedded game plan: `G95:` and `S98:` blocks between F95 and I95, then a 2- or 3-byte trailer) and the game-shipped `stock_profiles/OFF1.PRF` / `DEF1.PRF`; `mutated` = a golden's bytes changed at an offset from [prf.md](../../../docs/formats/prf.md) (the tests use the spec's literal offsets, not the schema's); `constructed` = a `Profile` built in the test. Golden expected values are the bytes at the spec's offsets. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_profile` → 152 passing.

No `test_schema.py`: the reader and writer tests pin every constant.

## reader.py — `test_reader.py`

### Valid files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Profile type, 4 files | golden | offense / defense | `test_profile_type` `[P]` | ☑ |
| Field goal range, 4 files | golden | 36 | `test_field_goal_range` `[P]` | ☑ |
| Use audibles, 6 files | golden | off; on for `*-AUD` | `test_use_audibles` `[P]` | ☑ |
| Substitutions, 4 files | golden | whole `SubstitutionSettings`; the other side's groups at 80/90 | `test_substitutions` `[P]` | ☑ |
| Situations 1 and 2520, 4 files | golden | weights and stop clock | `test_first_and_last_situation` `[P]` | ☑ |
| Weight 10 with stop clock; play category 0x1A | golden OFF2, situations 888 and 430 | whole record | `test_situation_record_at_the_limits` `[P]` | ☑ |
| PAT situations 1 and 60, 4 files | golden | Field Goal / PAT at weight 1 | `test_first_and_last_pat_situation` `[P]` | ☑ |
| Stop-clock situations, 4 files | golden | count, then the first and last whole records with their numbers; none on DEF1 | `test_stop_clock_situations` `[P]` | ☑ |
| `parse_profile` from bytes | golden | equals `read_profile` | `test_parse_profile_from_buffer_matches_read_profile` | ☑ |
| Error classes | — | `AthcError` subclasses | `test_profile_errors_are_athc_errors` `[P]` | ☑ |
| Error names the path first | empty file | "<path>: ..." and `.path` | `test_error_names_the_path_first` | ☑ |
| Missing file | tmp path | `OSError` | `test_nonexistent_path_raises_oserror` | ☑ |

### Invalid files → `InvalidProfileError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Too small for F95 / for I95 | 8 bytes / cut inside I95 | "too small" | `test_file_too_small_for_f95_rejected` / `test_file_too_small_for_i95_rejected` | ☑ |
| F95 ID / size; I95 ID / size | mutated | "Invalid header ... at 0x0" / "F95 data size"; "... at 0x3ca5" / "I95 data size" | `test_invalid_f95_header_rejected`, `test_wrong_f95_data_size_rejected`, `test_invalid_i95_header_rejected`, `test_wrong_i95_data_size_rejected` | ☑ |
| Substitution out > in | mutated QB pair | exactly `<buffer>: substitutions.quarterbacks.out_percent: Must be at most in_percent (50), got 99.` | `test_invalid_substitution_pair_rejected` | ☑ |
| Situation record: play category 0xFF; weight 11 under the stop-clock bit; weight 11 | mutated situation 1 | exactly `<buffer>: situation 1: <field>: Must be ..., got ....` | `test_invalid_situation_record_rejected` `[P]` | ☑ |
| PAT record: weight 1 with bit 7 set (no stop clock on PAT); weight 11 | mutated PAT 1 | exactly `<buffer>: PAT situation 1: weight1: Must be 0-10, got 129 / 11.` | `test_invalid_pat_situation_record_rejected` `[P]` | ☑ |
| Field goal range 5 and 50 in both blocks / 4 and 51 in both / 4 and 51 in I95 only | mutated | parsed / "F95 field_goal_range ... outside [5, 50]" / "I95 ..." | `test_field_goal_range_at_the_limits_accepted` `[P]` / `test_f95_field_goal_range_past_the_limits_rejected` `[P]` / `test_i95_field_goal_range_past_the_limits_rejected` `[P]` | ☑ |
| Use audibles 2 in F95 / in I95 | mutated | "F95 use_audibles 2" / "I95 use_audibles 2" | `test_f95_use_audibles_out_of_range_rejected` / `test_i95_use_audibles_out_of_range_rejected` | ☑ |
| Profile type 5; reserved 1 | mutated I95 | "profile_type 5" / "reserved" | `test_invalid_profile_type_rejected` / `test_nonzero_reserved_rejected` | ☑ |
| F95 and I95 disagree on the field goal range / use audibles | mutated I95 / F95 | "F95 ... != I95 ..." | `test_f95_i95_field_goal_range_mismatch_rejected` / `test_f95_i95_use_audibles_mismatch_rejected` | ☑ |
| Trailer byte 0xAB / stock 0x69 | mutated | "Trailer byte" | `test_invalid_trailer_byte_rejected` `[P]` | ☑ |
| Trailer one byte too long / too short, offense and defense | golden ± 1 byte | "Trailer length" | `test_wrong_trailer_length_rejected` `[P]` | ☑ |

### Unsupported variants → `UnsupportedProfileError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Stock layout | golden `OFF1.PRF`, `DEF1.PRF` | "Stock layout" | `test_real_stock_profile_rejected` `[P]` | ☑ |
| Embedded game plan as the game saves it | golden `*-PL` | "'G95:' before I95" | `test_real_embedded_game_plan_profile_rejected` `[P]` | ☑ |
| `G95:` / `J95:` / `S98:` in I95's place; game plan count 1; `G95:` / `J95:` / `S98:` after I95 | mutated | "before I95" / "blocks (1)" / "after I95" | `test_embedded_block_before_i95_rejected` `[P]`, `test_embedded_game_plan_count_rejected`, `test_embedded_block_after_i95_rejected` `[P]` | ☑ |

## model.py — `test_model.py` (constructed)
| Case | Expected | Test | Status |
|---|---|---|---|
| Edit by assignment (range, a situation's flag, a pair's value), then `validate()` | equal to a profile built that way | `test_edit_by_assignment_then_validate` | ☑ |
| Deep copy, then edit | the original unchanged | `test_deep_copy_edits_apart` | ☑ |
| `SubstitutionSettings.default` | every group 80/90, each its own object; `pairs()` in file order | `test_substitution_settings_default_uses_80_90`, `test_substitution_settings_default_gives_each_group_its_own_pair`, `test_substitution_settings_pairs_in_file_order` | ☑ |
| `Situation` / `PatSituation` fields | `stop_clock`, `category_weights` / `category_weights` only | `test_situation_holds_only_its_rules` | ☑ |
| `validate()`: profile type −1 / 2 | `ValueError` "profile_type: Must be 0 or 1, got ..." | `test_validate_rejects_a_profile_type_past_the_limits` `[P]` | ☑ |
| `validate()`: a pair 0/0, 0/100, 100/100, 50/50 | accepted | `test_substitution_pair_at_the_limits_accepted` `[P]` | ☑ |
| `validate()`: a pair out −1 / 101, in −1 / 101, out > in | `ValueError` naming `substitutions.quarterbacks.<field>` | `test_substitution_pair_past_the_limits_rejected` `[P]` | ☑ |
| `validate()`: play category 0x00 / 0x1A; weight 0 / 10 | accepted | `test_play_category_at_the_limits_accepted` `[P]`, `test_weight_at_the_limits_accepted` `[P]` | ☑ |
| `validate()`: play category −1 / 0x1B; weight −1 / 11; a PAT weight 11 | `ValueError` naming `situation 4: <field>` / `PAT situation 60: weight1` | `test_play_category_past_the_limits_rejected` `[P]`, `test_weight_past_the_limits_rejected` `[P]`, `test_pat_situation_weights_are_checked_too` | ☑ |
| `Profile.game_state` 1 and 2520; first and last cell of each yards-to-go group (1/35, 36/70, 71/98, 99/126); within a group 7/8; down start 127; minutes boundary 504/505 | game state from prf.md 2.3.4 | `test_game_state_decodes_the_layout_corners` `[P]` | ☑ |
| `Profile.game_state` 0 / 2521 | `ValueError` "[1, 2520]" | `test_game_state_rejects_numbers_past_limits` `[P]` | ☑ |
| `Profile.pat_game_state` 1 and 60; minutes boundary 15/16 | game state from prf.md 2.5.1 | `test_pat_game_state_decodes_the_layout_corners` `[P]` | ☑ |
| `Profile.pat_game_state` 0 / 61 | `ValueError` "[1, 60]" | `test_pat_game_state_rejects_numbers_past_limits` `[P]` | ☑ |
| `iter_situations` / `iter_pat_situations` | every slot once, in order, numbered from 1, with its game state and the list's own element | `test_iter_situations_walks_every_slot_in_order`, `test_iter_pat_situations_walks_every_slot_in_order` | ☑ |
| `iter_situations`, every slot the same `Situation` | numbers 1..2520, each slot's own game state | `test_iter_situations_numbers_slots_holding_the_same_situation` | ☑ |
| `Profile` offense / defense | `validate()` passes; `is_offense` / `is_defense` | `test_profile_accepts_valid_offense_construction`, `test_profile_accepts_valid_defense_construction` | ☑ |
| `validate()`: 2519 / 2521 situations; 59 / 61 PAT situations | `ValueError` | `test_profile_situations_wrong_length_raises` `[P]`, `test_profile_pat_situations_wrong_length_raises` `[P]` | ☑ |
| `validate()`: field goal range 4 / 51; 5 / 50 | `ValueError` / accepted | `test_profile_field_goal_range_past_the_limits_raises` `[P]` / `test_profile_field_goal_range_at_the_limits_accepted` `[P]` | ☑ |
| `stop_clock_situations`: none flagged; 5, 100 and 2520 flagged | `[]` / `[(5, state, s), (100, state, s), (2520, state, s)]` | `test_stop_clock_situations_empty_when_no_flags_set`, `test_stop_clock_situations_give_each_flagged_entry_its_number_and_state` | ☑ |

## writer.py — `test_writer.py`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Read, write, compare, 6 files | golden | byte-identical (block sizes, stop-clock bits, I95 mirror and trailer included) | `test_round_trip_byte_identity` `[P]` | ☑ |
| `build_profile` reproduces the file; no temp file left after a write | golden OFF1 | byte-identical; the folder holds the one file | `test_build_profile_reproduces_the_file`, `test_write_leaves_no_temp_file` | ☑ |
| `build_profile` / `write_profile` on an invalid profile | golden OFF1 edited past a limit | `ValueError`; nothing written | `test_build_refuses_an_invalid_profile`, `test_write_refuses_an_invalid_profile_and_writes_nothing` | ☑ |
| New offense / defense profile | constructed | reads back equal; trailer 1 / 2 NUL at 0x3CB7 | `test_write_new_profile_from_scratch` `[P]` | ☑ |
| One edit per field: field goal range, use audibles, a substitution pair, a situation (weights and stop clock), a PAT situation | golden OFF1, edited by assignment | reads back equal to the edited profile | `test_write_edited_profile` `[P]` | ☑ |
