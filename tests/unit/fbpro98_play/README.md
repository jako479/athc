# fbpro98_play — Test Matrix

Cases covered for the `.ply` parser library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_ply()` = constructed bytes, `golden` = real `.ply` in `data/`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_play` passes.

## reader.py — `parse_play` / `read_play`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid buffer parses; all fields + per-slot header | make_ply | stream_length, 3 category bytes, 11 offsets, 11 headers correct, empty logic | `test_parses_minimal_valid_buffer` | ☑ |
| Real file parses; whole-file structure | golden | exact offsets + player-header tuples | `test_reads_real_fixture_structure` `[P]` | ☑ |
| Real-file structural invariants | golden | `len==8+stream_length`, 11 offsets, offsets[0]==25, sorted, >0, headers in-bounds | `test_real_fixture_invariants` `[P]` | ☑ |
| Logic boxes decode byte for byte | golden | `SF1YemTy` QB: pre-snap box, then a box with Timed pass + two commands | `test_decodes_player_logic` | ☑ |
| Every real player has logic | golden | 11 `PlayerLogic`s, each with an after-snap box | `test_every_fixture_player_has_logic` `[P]` | ☑ |
| Built logic decodes | make_ply | boxes in order; commands with 2, 1 and 0 arguments | `test_decodes_built_logic` | ☑ |
| Bytes after the logic | make_ply | ignored; logic still read | `test_bytes_after_the_logic_are_ignored` | ☑ |
| Category names resolve on real files (4 branches) | golden | off/def normal + off/def special-teams | `test_*_category_name` (4) | ☑ |
| Default path sentinel | make_ply | `file_path == Path("<buffer>")` | `test_default_path_sentinel` | ☑ |
| Explicit path | make_ply | `file_path == Path(path)` | `test_explicit_path` | ☑ |
| `read_play` accepts str + PathLike | tmp_path | parses; `file_path` set | `test_read_play_accepts_str_and_pathlike` | ☑ |

### Error → `InvalidPlayFileError`

Every damaged file gets one message, "The play file is invalid or corrupted."; only a wrong block id and an unrecognized category say what they found.

| Case | Input | Expected message | Test | Status |
|---|---|---|---|---|
| Known invalid real file | golden (`PS7Xmids.ply`) | exactly `<path>: The play file is invalid or corrupted.` | `test_rejects_known_invalid_fixture` | ☑ |
| Buffer < 8 bytes (incl. empty) | make_ply | "The play file is invalid or corrupted." | `test_rejects_short_header` `[P]` | ☑ |
| Wrong block id | make_ply | "Invalid header '…' at 0x0" | `test_rejects_bad_block_id` | ☑ |
| Non-ASCII block id | make_ply | bad id decoded with replacement | `test_bad_block_id_non_ascii_decodes` | ☑ |
| `len != 8 + stream_length` (too large / small) | make_ply | "The play file is invalid or corrupted." | `test_rejects_size_mismatch` `[P]` | ☑ |
| Size matches but < 33 bytes | make_ply | "The play file is invalid or corrupted." | `test_rejects_missing_metadata` | ☑ |
| Player offset past EOF | make_ply | "The play file is invalid or corrupted." | `test_rejects_offset_past_eof` | ☑ |
| Record too short for its logic (one byte short, no after-snap list, header only) | make_ply | "The play file is invalid or corrupted." | `test_rejects_truncated_player_record` `[P]` | ☑ |
| Box count past the record | golden, count + 1 | "The play file is invalid or corrupted." | `test_rejects_box_count_past_the_record` | ☑ |
| Player offset = 0 (record on top of the offsets table) | make_ply | "The play file is invalid or corrupted." | `test_zero_offset_is_rejected` | ☑ |
| Unrecognized category (`read_play`) | make_ply | "Unrecognized play category in …" + file name | `test_read_play_rejects_unknown_category` | ☑ |

### Error → other (not `InvalidPlayFileError`)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `read_play` on missing file | path | `FileNotFoundError` propagates | `test_read_play_missing_file` | ☑ |

### Edge
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Smallest buffer that parses (last record's empty lists end at EOF) | make_ply | parses; boundary holds | `test_parses_minimal_valid_buffer` | ☑ |

## model.py — `PlayFile` properties & `category_name`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `is_offensive`/`is_defensive` by parity | PlayFile | odd `play_category` → offensive; even → defensive | `test_odd…_offensive` / `test_even…_defensive` `[P]` | ☑ |
| `is_special_teams` | PlayFile | `special_category != 0` → True; `0` → False | `test_is_special_teams` | ☑ |
| Offensive normal category names | PlayFile | every `OffensiveCategory` member → long name | `test_offensive_category_name` `[P]` | ☑ |
| Defensive normal category names | PlayFile | every `DefensiveCategory` member → long name | `test_defensive_category_name` `[P]` | ☑ |
| Offensive special-teams names | PlayFile | every `SpecialOffensiveCategory` member → long name | `test_offensive_special_teams_names` `[P]` | ☑ |
| Defensive special-teams names | PlayFile | every `SpecialDefensiveCategory` member → long name | `test_defensive_special_teams_names` `[P]` | ☑ |

### Edge / Error
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Unknown normal code | PlayFile | `category is UNKNOWN_CATEGORY`; `category_name == "Unknown"` (off & def) | `test_unknown_normal_code_is_unknown` | ☑ |
| Unknown special code | PlayFile | `category is UNKNOWN_CATEGORY` | `test_unknown_special_category_is_unknown` | ☑ |
| High bits 7–6 ignored | PlayFile | `0xC9` resolves same as `0x09` (mask `& 0x3F`) | `test_high_bits_are_masked` | ☑ |
| User Specific `0xFF`/`0xFE` | PlayFile | resolves to `"User Specific"` (fixed: full-byte lookup before mask) | `test_user_specific_resolves` | ☑ |

## model.py — category enum & `resolve_category`

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `PlayFile.category` → enum member | PlayFile | member; `category_name == category.long` | `test_category_returns_enum_member` | ☑ |
| `long` is the game name | enum | `Pass Short Right`; `Run Left`; `Punt` | `test_long_is_the_game_name` | ☑ |
| No league label on the enum | enum | no `short` attribute (labels are `CategoryLabels`) | `test_category_has_no_league_label` | ☑ |
| `is_run` / `is_pass` from the long name | enum | run/pass/neither | `test_is_run_is_pass` | ☑ |
| `resolve_category` picks side + special table | bytes | offense/defense/special-off/special-def; clock `0x0B`/`0x0C` offense only | `test_resolve_category_picks_side_and_special`, `test_clock_categories_are_offense_only` | ☑ |
| `resolve_category` mask + unknown | bytes | `0xC9`→Run Middle, `0xFF`→User Specific, `0x3F`→`UNKNOWN_CATEGORY` | `test_resolve_category_mask_and_unknown` | ☑ |

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
| Margin on both sides | 100 / 101 outside, right (Move to) and left (box spot) | False / True | `test_rollout_margin_on_both_sides` `[P]` | ☑ |
| Spots after the pass | moves out after a Timed pass | False | `test_rollout_counts_spots_up_to_the_pass_only` | ☑ |
| Move to with no arguments | bare Move to, then Timed pass | False | `test_rollout_ignores_a_move_to_with_no_arguments` | ☑ |
| Pre-snap spots | wide before the snap, inside at the snap | False | `test_rollout_reads_from_the_snap_on` | ☑ |
| No pass | QB moves out, then runs | False | `test_rollout_needs_a_pass` | ☑ |
| No line | QB moves out, no C, G or T | False | `test_rollout_needs_a_line` | ☑ |
| Edge is the outermost C, G or T | unbalanced lines (a guard or the center outermost on the left); QB 100 / 101 outside on each side | False / True | `test_rollout_edges_are_the_outermost_linemen` `[P]` | ☑ |
| Pocket QB behind an unbalanced line | the same two lines; QB checks receivers from 0 | False | `test_pocket_qb_behind_an_unbalanced_line_is_no_rollout` `[P]` | ☑ |
| A TE is not part of the line | tackles -300, 300, TE 400; QB to 400 | True | `test_a_tight_end_is_not_part_of_the_line` | ☑ |
| No QB | HB runs, moves out and throws | all False | `test_no_qb_means_no_offense_attributes` | ☑ |
| Two QBs | the second QB throws wide / runs | either QB counts | `test_any_qb_counts` | ☑ |
| Run defense front from down linemen | Run Left, 2-5 DT/DE | None, 3-4, 4-3, None | `test_run_defense_front_from_down_linemen` `[P]` | ☑ |
| Pass defense front from down linemen | Pass Short, 1-3 DT/DE | None, 2-DL, None | `test_pass_defense_front_from_down_linemen` `[P]` | ☑ |
| 3-4 / 4-3 only on Run Left, Middle, Right | each, 3 / 4 / 2 DL | 3-4, 4-3, None | `test_3_4_and_4_3_are_run_left_middle_right_fronts` `[P]` | ☑ |
| 2-DL only on pass plays | Pass Short, Medium, Long, Dazzle, Goal Line Pass; 2 / 3 / 4 DL | 2-DL, None, None | `test_2_dl_is_a_pass_front` `[P]` | ☑ |
| No front on other defenses | Run Dazzle, Goal Line Run, User Specific; 2-4 DL | None | `test_no_front_for_other_defenses` `[P]` | ☑ |
| Offense attributes on defense / special teams | QB Run, Move to, Timed pass | all False | `test_offense_attributes_only_on_normal_offense` | ☑ |
| Front on offense / special teams | 3 DT | None | `test_front_only_on_normal_defense` | ☑ |
| No logic | PlayFile without `player_logic` | all False / None | `test_no_logic_means_no_attributes` | ☑ |
| Real offensive plays | golden | timed / rollout / QB run per play | `test_offensive_attributes_of_real_plays` `[P]` | ☑ |
| Real defensive plays | golden | 2-DL, 3-4, 4-3; FG/PAT defense None | `test_defensive_front_of_real_plays` `[P]` | ☑ |

## labels.py — `CategoryLabels` (a league's offense/defense labels)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Tables → members | game name → label | `offense` / `defense` keyed by enum member | `test_from_tables_maps_game_names_to_members` | ☑ |
| `label()` | labeled / unlabeled / special | league label; game name; game name | `test_label_is_league_label_else_game_name` | ☑ |
| No labels | `CategoryLabels()` | game names; `*_by_label` → None | `test_no_labels_uses_game_names_everywhere` | ☑ |
| `*_by_label` per side | label, other side's label, game name | member; None; None | `test_by_label_resolves_within_its_side` | ☑ |
| Same label both sides | `RR` offense + defense | each side resolves its own | `test_same_label_on_both_sides_is_allowed` | ☑ |
| Label equals other side's game name | defense `"Pass Short Right"` | accepted | `test_label_may_equal_the_other_sides_game_name` | ☑ |
| Rejected tables | unknown key; non-string / empty / blank label; own-side game name; duplicate | `ValueError` naming the entry | `test_from_tables_rejects` `[P]` | ☑ |

## schema.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Struct sizes | header 8, offsets 22, metadata 3, player-header 4, box count 2, box 6, command 2, argument 2 | `test_struct_sizes` | ☑ |
| Derived offsets | metadata at `0x1E` (30); player-data base 8 | `test_derived_offsets` | ☑ |
| Block id | `ID_P95 == b"P95:"` | `test_block_id` | ☑ |
| Codes | Move to, Timed pass, Check receivers, Run; G, T, C, QB, DT, DE | `test_codes` | ☑ |

---

## Resolved finding

**User Specific (`0xFF`/`0xFE`).** `category_name` masked `user_category & 0x3F`, but the tables key User Specific at the full byte `0xFF`/`0xFE`, so it always returned `None`. Fixed in `model.py` to look up the full byte first, falling back to the masked base, so `0xFF`/`0xFE` resolve while ordinary codes still match. Covered by `test_user_specific_resolves`.
