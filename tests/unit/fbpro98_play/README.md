# fbpro98_play — Test Matrix

Cases covered for the `.ply` parser library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_ply()` = constructed bytes, `golden` = real `.ply` in `data/`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_play` passes.

## reader.py — `parse_play` / `read_play`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Smallest buffer that parses (11 header-only records with empty box lists) | make_ply | stream_length 113, the 3 category bytes, 11 offsets, 11 headers, empty logic | `test_parses_minimal_valid_buffer` | ☑ |
| Real file parses; whole-file structure | golden (10) | exact stream_length, category bytes, offsets and player headers | `test_reads_real_fixture_structure` `[P]` | ☑ |
| Logic boxes decode byte for byte | golden | `SF1YemTy` QB: pre-snap box, then a box with Timed pass + two commands | `test_decodes_player_logic` | ☑ |
| Every real player has logic | golden (10) | 11 `PlayerLogic`s, each with an after-snap box | `test_every_fixture_player_has_logic` `[P]` | ☑ |
| Built logic decodes | make_ply | boxes in order; commands with 2, 1 and 0 arguments | `test_decodes_built_logic` | ☑ |
| Bytes after the logic | make_ply | ignored; logic still read | `test_bytes_after_the_logic_are_ignored` | ☑ |
| Unrecognized category (`parse_play`) | make_ply | parses; `category is UNKNOWN_CATEGORY` | `test_parse_play_keeps_an_unknown_category` | ☑ |
| Default path sentinel | make_ply | `file_path == Path("<buffer>")` | `test_default_path_sentinel` | ☑ |
| Explicit path | make_ply | `file_path == Path(path)` | `test_explicit_path` | ☑ |
| `read_play` accepts str + PathLike | tmp_path | parses; `file_path` set | `test_read_play_accepts_str_and_pathlike` | ☑ |

### Real plays end to end
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Category names (4 branches) | golden | offense / defense normal: Goal Line Pass, Run Middle; offense / defense special: Kickoff, Field Goal/PAT Defense | `test_offensive_normal_category_name`, `test_defensive_normal_category_name`, `test_offensive_special_category_name`, `test_defensive_special_category_name` | ☑ |
| Offensive attributes | golden (5) | timed pass / rollout / QB run per play; no front | `test_offensive_attributes_of_real_plays` `[P]` | ☑ |
| Defensive front | golden (4) | 2-DL, 3-4, 4-3; FG/PAT defense with 2 down linemen None; no offense attributes | `test_defensive_front_of_real_plays` `[P]` | ☑ |

### Error → `InvalidPlayFileError`

Every damaged file gets one message, "The play file is invalid or corrupted."; only a wrong block id and an unrecognized category say what they found. Both sides of a size limit share that message, so each limit is probed one byte past it.

| Case | Input | Expected message | Test | Status |
|---|---|---|---|---|
| Empty real file (`PS7Xmids.ply`, zero bytes) | golden | exactly `<path>: The play file is invalid or corrupted.` | `test_rejects_empty_real_file` | ☑ |
| Buffer < 8 bytes (0, 3, 7) | bytes | "The play file is invalid or corrupted." | `test_rejects_short_header` `[P]` | ☑ |
| Wrong block id | make_ply | exactly `<buffer>: Invalid header 'XXXX' at 0x0.` | `test_rejects_bad_block_id` | ☑ |
| Non-ASCII block id | make_ply | exactly `<buffer>: Invalid header '����' at 0x0.` (replacement characters) | `test_bad_block_id_non_ascii_decodes` | ☑ |
| Size field one off (114 / 112 for a 113-byte body) | make_ply | "The play file is invalid or corrupted." | `test_rejects_size_mismatch` `[P]` | ☑ |
| Size matches, 32 bytes (one short of the category bytes) | bytes | "The play file is invalid or corrupted." | `test_rejects_missing_metadata` | ☑ |
| Player header one byte past EOF | make_ply | "The play file is invalid or corrupted." | `test_rejects_offset_past_eof` | ☑ |
| Player offset 24, one below the first record byte (25 is the minimal buffer) | make_ply | "The play file is invalid or corrupted." | `test_rejects_offset_inside_the_header` | ☑ |
| Record too short for its logic (one byte short, no after-snap list, header only) | make_ply | "The play file is invalid or corrupted." | `test_rejects_truncated_player_record` `[P]` | ☑ |
| Box count past the record | golden, count + 1 | "The play file is invalid or corrupted." | `test_rejects_box_count_past_the_record` | ☑ |
| Unrecognized category (`read_play`) | tmp_path | exactly `<path>: Unrecognized play category (play_category=0x01, special_category=0x00, user_category=0x3F).`; `.path` set | `test_read_play_rejects_unknown_category` | ☑ |

### Error → other (not `InvalidPlayFileError`)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `read_play` on missing file | path | `FileNotFoundError` propagates | `test_read_play_missing_file` | ☑ |

## model.py — `PlayFile` side and category

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `is_offensive` / `is_defensive` by parity | PlayFile | odd `play_category` → offensive; even → defensive | `test_odd_play_category_is_offensive`, `test_even_play_category_is_defensive` `[P]` | ☑ |
| `is_special` | PlayFile | `special_category != 0` → True; `0` → False | `test_is_special` | ☑ |
| `category` / `category_name` | PlayFile | the enum member and its `long` | `test_category_returns_enum_member` | ☑ |
| Unrecognized code | PlayFile | `category is UNKNOWN_CATEGORY`; `category_name == "Unknown"` | `test_category_name_of_an_unrecognized_code_is_unknown` | ☑ |
| `is_run` / `is_pass` from the long name | enum | run / pass / neither (User Specific) | `test_is_run_is_pass` | ☑ |

## model.py — `resolve_category`

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Every member resolves from its code | the bytes of each member of the 4 enums | that member (side from the play byte's parity; the special table, else the side's table) | `test_resolve_category_names_every_member` `[P]` | ☑ |
| Bits 7–6 ignored | `0xC9` offense, `0xC8` defense | Run Middle | `test_high_bits_are_masked` | ☑ |
| User Specific is a full-byte code | `0xFF` offense, `0xFE` defense | `USER_SPECIFIC` | `test_user_specific_is_a_full_byte_code` | ☑ |
| Unknown normal code | `0x3F` offense, `0x3E` defense | `UNKNOWN_CATEGORY` | `test_unknown_normal_code` `[P]` | ☑ |
| Unknown special code | offense `0x0D` (one past Stop Clock); defense `0x0B`, `0x0C` (no clock plays) | `UNKNOWN_CATEGORY` | `test_unknown_special_code` `[P]` | ☑ |

## model.py — play attributes

Constructed plays: tackles at x -300 and 300 unless a row says otherwise; margin 100.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Timed pass is the QB's | QB Timed pass / Check receivers | True / False | `test_timed_pass_is_the_qbs_timed_pass` | ☑ |
| Another player's Timed pass | HB Timed pass | False | `test_timed_pass_needs_the_qb` | ☑ |
| Timed pass before the snap | QB Timed pass in a pre-snap box only | False | `test_timed_pass_reads_from_the_snap_on` | ☑ |
| QB run is the QB's Run | QB Run / HB Run | True / False | `test_qb_run_is_the_qbs_run` | ☑ |
| QB run before the snap | QB Run in a pre-snap box only | False | `test_qb_run_reads_from_the_snap_on` | ☑ |
| Timed and rollout at once | QB moves out, then Timed pass | both True | `test_a_play_can_be_timed_and_a_rollout` | ☑ |
| Margin on both sides, and the caller's margin | margin 100: 100 / 101 outside, right (Move to) and left (box spot); margin 200: 200 / 201 outside | False / True | `test_rollout_margin_on_both_sides` `[P]` | ☑ |
| Spots after the pass | moves out after a Timed pass | False | `test_rollout_counts_spots_up_to_the_pass_only` | ☑ |
| Move to with no arguments | bare Move to, then Timed pass | False | `test_rollout_ignores_a_move_to_with_no_arguments` | ☑ |
| Pre-snap spots | wide before the snap, inside at the snap | False | `test_rollout_reads_from_the_snap_on` | ☑ |
| No pass | QB moves out, then runs | False | `test_rollout_needs_a_pass` | ☑ |
| No line | QB moves out; no C, G or T, or linemen with no after-snap box | False | `test_rollout_needs_a_line` `[P]` | ☑ |
| Edge is the outermost C, G or T | unbalanced lines (a guard or the center outermost on the left); QB 100 / 101 outside on each side | False / True | `test_rollout_edges_are_the_outermost_linemen` `[P]` | ☑ |
| Pocket QB behind an unbalanced line | the same two lines; QB checks receivers from 0 | False | `test_pocket_qb_behind_an_unbalanced_line_is_no_rollout` `[P]` | ☑ |
| A TE is not part of the line | tackles -300, 300, TE 450; QB to 401 | True | `test_a_tight_end_is_not_part_of_the_line` | ☑ |
| No QB | HB runs, moves out and throws | all False | `test_no_qb_means_no_offense_attributes` | ☑ |
| Two QBs | the second QB throws wide / runs | either QB counts | `test_any_qb_counts` | ☑ |
| Run defense front from down linemen | Run Left, Middle, Right × 2-5 DT/DE | None, 3-4, 4-3, None | `test_run_defense_front_from_down_linemen` `[P]` | ☑ |
| Pass defense front from down linemen | Pass Short, Medium, Long, Dazzle, Goal Line Pass × 1-3 DT/DE | None, 2-DL, None | `test_pass_defense_front_from_down_linemen` `[P]` | ☑ |
| No front on other defenses | Razzle Dazzle Run, Goal Line Run, User Specific, unrecognized `0x3E` × 2-4 DL | None | `test_no_front_for_other_defenses` `[P]` | ☑ |
| Offense attributes on defense / special plays | QB Run, Move to, Timed pass on a defense / a Fake FG Pass | all False | `test_offense_attributes_only_on_normal_offense` `[P]` | ☑ |
| Front on offense / special plays | 3 DT on an offense / a Kick Return | None | `test_front_only_on_normal_defense` `[P]` | ☑ |
| No logic | PlayFile without `player_logic` | all False / None | `test_no_logic_means_no_attributes` | ☑ |

## labels.py — `CategoryLabels` (a league's offense/defense labels)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Tables → members | game name → label | `offense` / `defense` keyed by enum member | `test_from_tables_maps_game_names_to_members` | ☑ |
| `label()` | labeled / unlabeled / special | league label; game name; game name | `test_label_is_league_label_else_game_name` | ☑ |
| No labels | `CategoryLabels()` | game names; `*_by_label` → None | `test_no_labels_uses_game_names_everywhere` | ☑ |
| `*_by_label` per side | label, other side's label, game name | member; None; None | `test_by_label_resolves_within_its_side` | ☑ |
| Same label both sides | `RR` offense + defense | each side resolves its own | `test_same_label_on_both_sides_is_allowed` | ☑ |
| Label equals other side's game name | defense `"Pass Short Right"` | accepted | `test_label_may_equal_the_other_sides_game_name` | ☑ |
| Rejected tables | unknown key; non-string / empty / blank label; own-side game name; duplicate | `ConfigFileError`; the whole message, naming the table and the entry | `test_from_tables_rejects` `[P]` | ☑ |
| The file in the message | `path` given | `<path>: [categories.offense] …`; `.path` set | `test_from_tables_names_the_file` | ☑ |

No `test_schema.py`: the reader tests pin every constant.
