# fbpro98_stats — Test Matrix

Cases covered for the `.dat` stats file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_dat()` = constructed bytes (records from `make_record()`, deleted slots from `make_deleted()`), `golden` = real files in `data/` from the 2047 PNFL season: `PNFL-after-week1.dat` (1,703 deleted slots) and its `PNFL-after-week1.lge`, `PNFL-after-week9.dat` (no deleted slots), `PNFL-after-week16.dat`, `PNFL-after-super-bowl.dat`; the last two are checked against `../fbpro98_lge/data/PNFL-after-week16.lge` and `PNFL-after-super-bowl.lge`. Golden expected values are the bytes at the offset each test names, or the `.lge`. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_stats` → 181 passing.

No `test_model.py` and no `test_schema.py`: the model has no logic, and the reader tests pin every constant (the builders use the spec's literal offsets, not the schema's).

## reader.py — `parse_stats` / `read_stats`

### Real files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `read` returns `StatsFile`; `parse == read` | golden | equal | `test_read_returns_stats_file_and_matches_parse` | ☑ |
| `read` accepts a `str` folder | golden | equal to `Path` | `test_read_accepts_str_league_dir` | ☑ |
| Every record read, 4 files | golden | the header's record count | `test_every_record_is_read` `[P]` | ☑ |
| Ids per block, 4 files | golden | hand-counted sizes | `test_block_sizes` `[P]` | ☑ |
| A quarterback's season and career | golden | whole `PlayerStats`, week 16 | `test_player_season_record` / `test_player_career_record` | ☑ |
| A player's last game, with a penalty | golden | whole `PlayerStats`, week 1 | `test_player_last_game_record` | ☑ |
| A career total past 32,767 | golden | player 550's passing yards read −22,826 | `test_career_total_past_32767_reads_negative` | ☑ |
| A team's season, own and opponents' | golden | whole `TeamStats`, every category | `test_team_and_opponents_season_record` `[P]` | ☑ |
| Players of the Game, week 1 | golden | ids 1-9 and the Player of the Week | `test_players_of_the_game_after_week_one` | ☑ |
| No Player of the Game after the Super Bowl | golden | empty | `test_no_players_of_the_game_after_the_super_bowl` | ☑ |
| Coach of the Year, 4 files | golden | 2, 2, 7, 7 | `test_coach_of_the_year` `[P]` | ☑ |
| All-Pro team | golden | 68 picks, three whole | `test_all_pro_team` | ☑ |
| Awards | golden | 84; the six of 2047 whole | `test_awards` | ☑ |
| Hall of Fame nominees, elected and not | golden | whole `HallOfFameNominee` | `test_hall_of_fame_nominee` `[P]` | ☑ |
| Season points, week 1 | golden + `.lge` | each team's points for and against | `test_season_points_match_the_lge_after_week_one` | ☑ |
| Last-game teams, week 16 and the Super Bowl | golden | all 18 / teams 4 and 17 | `test_last_game_block_holds_the_last_games_teams` `[P]` | ☑ |
| Last game, week 16 and the Super Bowl | golden + `.lge` | every team of the last week or round: opponent and both scores | `test_last_game_matches_the_lge` `[P]` | ☑ |
| Playoffs touch last game only | golden | season, career and honors unchanged | `test_playoffs_leave_season_and_career_unchanged` | ☑ |

### Header → `InvalidStatsError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Header alone (a fresh stock league) | make_dat | `StatsFile()` | `test_header_alone_is_an_empty_stats_file` | ☑ |
| 139 bytes | make_dat | "140-byte header" | `test_shorter_than_the_header_rejected` | ☑ |
| File end size − 2, size / size − 1 | make_dat | "File end" / accepted | `test_file_end_must_be_the_size_less_one` `[P]` | ☑ |
| Record size 19, 21 | make_dat | "Record size" | `test_record_size_must_be_20` `[P]` | ☑ |
| Slots end 138 / 139 | make_dat | "below" / accepted | `test_slots_end_below_the_header_rejected` | ☑ |
| Slots end 139 + 39, 139 + 41 / 139 + 40 | make_dat | "whole" / both records read | `test_slots_end_not_whole_records_rejected` `[P]` / `test_slots_end_at_whole_records_accepted` | ☑ |
| Slots end one byte and one slot past the file end / at its last byte | make_dat | "past" / accepted | `test_slots_running_past_the_file_end_rejected` `[P]` / `test_slots_end_at_whole_records_accepted` | ☑ |
| `0xFF` or `0x00` bytes after the slots | make_dat | ignored | `test_bytes_after_the_slots_ignored` `[P]` | ☑ |
| Records live + 1, live − 1 / live, with a deleted slot | make_dat | "Records" / both read | `test_record_count_must_match_live_slots` `[P]` / `test_record_count_of_live_slots_accepted` | ☑ |
| Two problems: file end and record size, record size and slots end, slots end and a slot, a slot and the record count | make_dat | the first in check order | `test_first_problem_in_check_order_reported` `[P]` | ☑ |
| Error names the path first | make_dat | "league.dat: ..." and `.path` | `test_error_names_the_path_first` | ☑ |
| Missing file | league + tmp folder | `OSError` naming `<league_dir>/<league>.dat` | `test_missing_file_raises_oserror_for_built_path` | ☑ |

### Records
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Categories 0-13 and 17, player and team | make_dat | each stat class; punting value 3 skipped | `test_player_category_decoded` / `test_team_category_decoded` `[P]` | ☑ |
| Each of the 7 blocks | make_dat | its own mapping, the rest empty | `test_each_block_fills_its_own_mapping` `[P]` | ☑ |
| Two categories, one id | make_dat | one `PlayerStats` | `test_records_of_one_id_group_together` | ☑ |
| `0xFFFF`, `0x8000`, `0x7FFF` | make_dat | −1, −32,768, 32,767 | `test_values_are_signed` `[P]` | ☑ |
| Field goal range `0x00FF`, `0xFF00` | make_dat | (255, 0), (0, 255) | `test_field_goal_range_bytes_read_unsigned` `[P]` | ☑ |
| Values past a category | make_dat | ignored | `test_values_past_a_category_are_ignored` | ☑ |
| Deleted slot holding a whole record | make_dat | not read | `test_deleted_slot_skipped` | ☑ |
| Ids 0, 65,535 | make_dat | keys | `test_ids_at_both_ends_are_keys` `[P]` | ☑ |
| Ids 7, 2, 5 | make_dat | keys 2, 5, 7 | `test_mappings_are_in_id_order` | ☑ |
| Categories 0 and 17 at each block's ends | make_dat | read | `test_stats_types_accepted` `[P]` | ☑ |
| One past each block, type 48, `0xFFFE` | make_dat | "not a stats type" at the slot | `test_other_types_rejected` `[P]` | ☑ |
| Same type and id twice / other id | make_dat | "repeats" / both read | `test_duplicate_record_rejected` / `test_same_type_other_id_accepted` | ☑ |
| Two bad slots | make_dat | the first one's problem | `test_first_problem_in_slot_order_reported` | ☑ |

### Categories 14-16 and honors
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Hall of Fame points, 3 player blocks | make_dat | `HallOfFamePoints` | `test_hall_of_fame_points_in_each_player_block` `[P]` | ☑ |
| Penalties, player last game | make_dat | count | `test_penalties_in_player_last_game` | ☑ |
| Nominee year elected 0 / 2047 | make_dat | `None` / 2047; value 0 ignored | `test_hall_of_fame_nominee_in_player_career` `[P]` | ☑ |
| First downs, downs, game details, 4 team blocks | make_dat | each class | `test_team_categories_14_to_16` `[P]` | ☑ |
| Score `0x1E18`, `0x00FF`, `0xFF00` | make_dat | (30, 24), (0, 255), (255, 0) | `test_game_score_split` `[P]` | ☑ |
| Possession `0x8001` | make_dat | −32,767 | `test_possession_past_32767_reads_negative` | ☑ |
| Player of the Game ids 1, 98, 99 / 0, 100 | make_dat | games 0, 97, `None` / "Player of the Game id" | `test_player_of_the_game` `[P]` / `test_player_of_the_game_id_out_of_range_rejected` `[P]` | ☑ |
| All-Pro ids `0x0001`, `0x04FF` / pick 5, position + 1 of 0, 4097 | make_dat | (0, 0, 0), (14, 15, 4) / "pick 5, above 4", "a position + 1 of 0", "pick 16, above 4" | `test_all_pro_pick_decoded` `[P]` / `test_all_pro_id_rejected` `[P]` | ☑ |
| Coach of the Year | make_dat | team number | `test_coach_of_the_year_decoded` | ☑ |
| Award codes 90-94, 99 / 89, 95, 98, 100 | make_dat | kind and conference / "Award id" | `test_award_decoded` `[P]` / `test_award_code_rejected` `[P]` | ☑ |
| Honors out of order | make_dat | each list in id order | `test_players_of_the_game_in_id_order` / `test_all_pro_in_id_order` / `test_awards_in_id_order` | ☑ |
| Edit by assignment | golden | a team's stats replaced, a category cleared, awards dropped | `test_stats_are_edited_by_assignment` | ☑ |
