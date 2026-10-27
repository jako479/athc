# fbpro98_lge — Test Matrix

Cases covered for the `.lge` league file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_chunks()` = constructed bytes (one team unless a shape is given; `make_roster_data()` builds one R03), `golden` = real `.lge` in `data/` (`08_TEAMS.lge`, `10_TEAMS.LGE`, `12_TEAMS.LGE` one conference; `PNFL.lge` 18 teams, custom, 2049 after week 6; `NFLPA94.lge` 28; `NFLPI97R.LGE` 30; grouped by chunk kind: `NFLPA93E.LGE` 28, `_default.lge` 30; the PNFL's 2047 season: `PNFL-before-week1.lge`, `PNFL-after-week16.lge`, `PNFL-after-super-bowl.lge`; seasons' ends for the tie-breakers: `PNFL-2043-after-super-bowl.lge`, `PNFL-2046-after-super-bowl.lge`, `PNFL-2048-after-week16.lge`). Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_lge` → 220 passing.

## reader.py — `parse_lge` / `read_lge`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league, whole tree, incl. leftover text after NULs | golden | every name and record in `PNFL.lge` | `test_custom_league` | ☑ |
| Teams in file order | golden | `LgeFile.teams`, team N at index N - 1 | `test_teams_are_in_file_order` | ☑ |
| Teams per division, every league size, both chunk orders | golden | 8, 10, 12, 18, 28, 30 teams | `test_league_shape` `[P]` | ☑ |
| Stock conference and division names | golden | `"American"`, `"Eastern"`, ...; `""` with one conference | `test_stock_league_names` `[P]` | ☑ |
| Stock teams, incl. a 16-character name and leftover text | golden | official names | `test_stock_league_teams` `[P]` | ☑ |
| `read` returns `LgeFile`; `parse == read` | golden | equal | `test_read_returns_lge_file_and_matches_parse` | ☑ |
| `read` accepts a `str` folder | golden | equal to `Path` | `test_read_accepts_str_league_dir` | ☑ |
| Missing file | league + tmp folder | `OSError` naming `<league_dir>/<league>.lge` | `test_missing_file_raises_oserror_for_built_path` | ☑ |
| Built file, every chunk at its exact size | make_chunks | one conference, division, team | `test_built_file_parses` | ☑ |
| Grouped order, incl. a division with no teams | make_chunks | same as nested | `test_grouped_order_reads_like_nested` `[P]` | ☑ |
| Grouped order, a roster missing | make_chunks | "Expected R03 ..., found S03" | `test_grouped_order_missing_roster_rejected` | ☑ |

### Names
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Text after the NUL ignored | make_chunks | `"AFC"`, `"West"`, `"Denver"`, `"Broncos"` | `test_names_read_up_to_nul` | ☑ |
| Name filling its field (25 / 17 characters, no NUL) | make_chunks | whole field, not the next field | `test_names_filling_their_field_read_whole` | ☑ |
| Mask keyed by the chunk's team number 0, 1, 30, 255 | make_chunks | names read | `test_team_number_in_chunk_keys_the_mask` `[P]` | ☑ |
| Non-ASCII byte | make_chunks | decoded as U+FFFD | `test_non_ascii_byte_decodes_as_replacement` | ☑ |

### Limits → `InvalidLgeError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty file | bytes | "Empty file" | `test_empty_file_rejected` | ☑ |
| Chunk one byte short or long: L03 89/91, C03 and D03 29/31, T03 170/172, R03 324/326 | make_chunks | "is N bytes, expected M" | `test_chunk_one_byte_off_its_size_rejected` `[P]` | ☑ |
| Counted chunk 28 bytes / 29 with no children | make_chunks | "expected at least 29" / division with no teams | `test_counted_chunk_shorter_than_its_fixed_part_rejected` / `test_counted_chunk_of_just_its_fixed_part_accepted` | ☑ |
| Header 1 and 7 bytes / 8 bytes with no data | make_chunks | "cut short" / passes framing, fails on S03 size | `test_chunk_header_cut_short_rejected` `[P]` / `test_bare_chunk_header_passes_framing` | ☑ |
| Chunk one byte past the end / size u32 max | make_chunks / bytes | "runs past the end of the file" | `test_chunk_running_past_end_rejected` / `test_huge_chunk_size_rejected` | ☑ |
| One byte after the schedule | make_chunks | "Unexpected data" | `test_data_after_schedule_rejected` | ☑ |

### Chunk order → `InvalidLgeError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Each chunk kind missing | make_chunks | "Expected X chunk at ..., found Y" / "found the end of the file" | `test_missing_chunk_rejected` `[P]` | ☑ |
| League counts 2 conferences, file has 1 | make_chunks | "Expected C03 ..., found S03" | `test_fewer_conferences_than_counted_rejected` | ☑ |
| League counts 1 conference, file has 2 | make_chunks | "Expected S03 ..., found C03" | `test_more_conferences_than_counted_rejected` | ☑ |
| Division counts 2 teams, file has 1 | make_chunks | "Expected T03 ..., found S03" | `test_fewer_teams_than_counted_rejected` | ☑ |
| Division counts 1 team, file has 2 | make_chunks | "Expected S03 ..., found T03" | `test_more_teams_than_counted_rejected` | ☑ |
| Conference counts 1 division, file has 2 | make_chunks | "Expected S03 ..., found D03" | `test_more_divisions_than_counted_rejected` | ☑ |
| Unprintable or non-ASCII tag | bytes | shown as hex | `test_unprintable_or_non_ascii_tag_shown_as_hex` `[P]` | ☑ |
| Error names the path first | bytes | "league.lge: ..." and `.path` | `test_error_names_the_path_first` | ☑ |
| No path given | bytes | "<buffer>: ..." and `.path` | `test_error_names_buffer_when_no_path_given` | ☑ |

### Standings
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Division order as on the game's season-end screen (2048) | golden | Miami above Buffalo on conference record, not points | `test_division_standings_match_the_games_season_end_screen` | ☑ |
| Division ties by division record, head-to-head, conference record | golden | 2043 and 2046 orders, the manual's steps by hand | `test_division_ties_follow_the_manuals_steps` | ☑ |
| Any teams of the file ranked | golden | 2048 wild cards Buffalo over Pittsburgh head-to-head | `test_ranked_orders_any_teams_of_the_file` | ☑ |
| Final regular season, incl. tie games | golden | records; wins + tie games = 144 | `test_final_regular_season_records` | ☑ |
| Conference order, ties broken by the manual's steps | golden | AFC and NFC order | `test_conference_standings_break_ties_by_the_manuals_steps` | ☑ |
| Built file: split series broken on division net points | make_chunks | winner by more first in division and conference | `test_built_standings_break_a_split_series_on_division_net_points` | ☑ |
| Grouped order, a played season with bye weeks | golden | real 1993 NFL records | `test_grouped_league_season_matches_the_real_1993_results` | ☑ |
| Playoff games not counted | golden | records after the Super Bowl = after week 16 | `test_playoff_games_do_not_count` | ☑ |
| Before week 1 | golden | all records zero; standings in file order | `test_before_week_one_records_are_zero_and_standings_keep_file_order` | ☑ |
| A win and an overtime tie | make_chunks | 1-0-1 31-24 / 0-1-1 24-31 | `test_record_counts_played_regular_season_games` | ☑ |
| Unplayed game, `0xFF` teams | make_chunks | skipped; empty week, 1 unplayed | `test_unplayed_games_skipped_and_counted` | ☑ |
| Week with 0 games | make_chunks | empty week, 0 unplayed | `test_week_with_no_games_read_as_empty` | ☑ |
| Played playoff game | make_chunks | skipped | `test_playoff_games_skipped` | ☑ |
| Played game with team 1 / N, team 0 / N+1 | make_chunks | counted / "no team T (teams are 1-N)" | `test_played_game_with_first_and_last_team_accepted` `[P]` / `test_played_game_with_unknown_team_rejected` `[P]` | ☑ |
| Schedule 2 bytes / 3 (header alone) | make_chunks | "expected at least 3" / parsed | `test_schedule_shorter_than_its_header_rejected` / `test_built_file_parses` | ☑ |
| Schedule one byte or one week short / exact | make_chunks | "cut short in week 1" / parsed | `test_schedule_cut_short_in_a_week_rejected` `[P]` | ☑ |
| One byte after the last week | make_chunks | "data after the last week" | `test_schedule_with_data_after_the_last_week_rejected` | ☑ |

### Games
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Season over | golden | 16 weeks of 9 games; rounds of 4, 2, 1; Miami over Minnesota 14-10; 0 unplayed | `test_games_and_playoffs_after_the_super_bowl` | ☑ |
| Regular season over | golden | three empty rounds; 7 unplayed | `test_no_playoff_game_before_the_playoffs` | ☑ |
| Before week 1 | golden | 16 empty weeks; 151 unplayed | `test_no_game_before_week_one` | ☑ |
| Games name the file's team objects | golden | 54 games after six weeks; records = two per game | `test_games_reference_the_file_teams` | ☑ |
| Tie | make_chunks | `winner` and `loser` None | `test_tied_game_has_no_winner_or_loser` | ☑ |
| Unplayed playoff game with teams set | make_chunks | skipped, counted | `test_unplayed_playoff_game_skipped_and_counted` | ☑ |
| Played playoff game with team 1 / N, team 0 / N+1 | make_chunks | read / "week 2: No team T (teams are 1-N)", numbered on from the regular season | `test_played_playoff_game_with_first_and_last_team_read` `[P]` / `test_played_playoff_game_with_unknown_team_rejected` `[P]` | ☑ |

### Rosters
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league roster, every slot filled | golden | Denver (team 5): assigned[0] = 6283 #6, injured_reserve[9] = 6404 #80, 63 players, the permutation, no camp, the spec's 60-byte table | `test_custom_league_roster` | ☑ |
| Empty slots are None, not players | golden | Jacksonville: open_inactive[6] (slot 53) and injured_reserve[7-9] (slots 61-63) None, every other slot filled; 59 players, the last at injured_reserve[6] | `test_empty_slots_are_none_and_not_players` | ☑ |
| Roster team numbers 1..N, both chunk orders | golden | every real file | `test_roster_team_numbers_run_in_file_order` `[P]` | ☑ |
| No real file has a camp set up | golden | every team's table zero | `test_no_real_file_has_a_training_camp_set_up` `[P]` | ☑ |
| `team_of` | golden | Denver's assigned[0], Jacksonville's open_inactive[0]; unknown id and 0 → None | `test_team_of_rostered_and_unknown_ids` | ☑ |
| Grouped order pairs roster k with team k | make_chunks | last team's roster number = N | `test_grouped_order_reads_like_nested` `[P]` | ☑ |
| Every field at its offset, slots 1 and 63, id and jersey at their maxima | make_chunks | assigned[0], injured_reserve[9], permutation, camp rows in order, unknown bytes as written; `players` skips the empty slots | `test_roster_fields_read_at_their_offsets` | ☑ |
| Slots split into the status groups at their boundaries | make_chunks | a player in slots 1, 34, 35, 46, 47, 53, 54 and 63 lands at each group's first and last index | `test_slots_split_into_the_status_groups_at_their_boundaries` | ☑ |
| Empty slot with a jersey byte | make_chunks | None | `test_empty_slot_is_none_whatever_its_jersey_byte` | ☑ |
| Mask keyed by the roster's own u16 number 0, 1, 255, 256, 65535 | make_chunks | number and player read; not checked against the team's | `test_roster_team_number_in_chunk_keys_the_mask` `[P]` | ☑ |
| Camp row totalling 100 / a byte 101 / a row totalling 101 | make_chunks | read as is; `validate()` passes / rejects / rejects (the messages are model.py's rows) | `test_camp_read_as_is_and_checked_only_by_validate` `[P]` | ☑ |

No real file has a training camp set up, so the camp's offset and row order are pinned only by the builder, which places the fields with the reader's own constants.

## model.py

`model` = an `LgeFile` built in Python; `validate()` rules each at their limit and one past it.

| Case | Expected | Test | Status |
|---|---|---|---|
| `teams` walks conferences, divisions and teams in order | four teams over two conferences | `test_teams_walks_conferences_divisions_and_teams_in_order` | ☑ |
| Edit by assignment | a record's wins changed, a player put on injured reserve, a team removed from its division | `test_lge_is_edited_by_assignment` | ☑ |
| `players` | the filled slots of the four groups in slot order, empty ones skipped | `test_players_lists_the_filled_slots_in_slot_order` | ☑ |
| `team_of`, an id on two teams; unknown id and 0 | the first team in file order; None | `test_team_of_finds_the_first_team_in_file_order`, `test_team_of_unknown_or_empty_id_is_none` `[P]` | ☑ |
| Valid file; file without teams | passes | `test_valid_file_passes`, `test_file_without_teams_passes` | ☑ |
| Team number 0 / 65535 / 65536, −1; permutation 10 / 9, 11 bytes; unknown 60 / 59, 61; camp 8 / 7, 9 rows | pass / "team 1: roster: team_number: Must be 0-65535" / "permutation: Must be 10 bytes" / "unknown: Must be 60 bytes" / "training camp: Must be 8 rows" | `test_roster_field_at_its_limit_accepted` `[P]`, `test_roster_field_past_its_limit_rejected` `[P]` | ☑ |
| Each status group one slot short or long (33, 35 / 11, 13 / 6, 8 / 9, 11) | "Assigned: Must be 34 slots" and the rest, named as on the screen; at its size = the valid roster | `test_group_size_off_by_one_rejected` `[P]` | ☑ |
| Player id 1, 65535 / 0, 65536; jersey 0, 255 / 256, −1; in a later group | pass / "Assigned slot 1: player_id: Must be 1-65535" / "Assigned slot 1: jersey: Must be 0-255" / "Injured Reserve slot 10: jersey: ..." (slots counted from 1) | `test_player_field_at_its_limit_accepted` `[P]`, `test_player_field_past_its_limit_rejected` `[P]` | ☑ |
| Camp row of 7 or 9 values | "training camp: QB: Must be 8 values" | `test_camp_row_length_off_by_one_rejected` `[P]` | ☑ |
| Camp byte 100 / 101, −1 | pass / "training camp: P/K: ST: Must be 0-100" | `test_camp_byte_at_its_limit_accepted`, `test_camp_byte_past_its_limit_rejected` `[P]` | ☑ |
| Camp row totalling 100 / 101 | pass / "training camp: QB: Must total at most 100, got 101" | `test_camp_row_total_at_its_limit_accepted`, `test_camp_row_total_past_its_limit_rejected` | ☑ |
| Problem in the second team, its roster numbered 7 | "team 2: roster: Assigned: Must be 34 slots, got 0" (its position, not the roster's number) | `test_problem_in_a_later_team_names_that_team` | ☑ |
| Bad team 1 and bad team 2 | team 1's message | `test_first_problem_in_file_order_reported` | ☑ |
| Official name, either part empty | `"Denver Broncos"`, `"Denver"`, `"Broncos"`, `""` | `test_official_name` `[P]` | ☑ |
| Record totals | games, win percentage (ties half, 0.0 with no games), point differential | `test_record_totals` `[P]` | ☑ |
| `ranked` orders from the games, not the records | winner first though listed second | `test_ranked_orders_from_the_files_games_not_the_records` | ☑ |
| `ranked` with no teams given | every team of the file | `test_ranked_defaults_to_every_team_of_the_file` | ☑ |
| `ranked` with an empty input | empty | `test_ranked_with_no_teams_is_empty` | ☑ |
| Game winner and loser | home win, away win, tie (None) | `test_game_winner_and_loser` `[P]` | ☑ |

## _standings.py

Built seasons: three divisions, two conferences; `_win(a, b, by)`.

| Case | Expected | Test | Status |
|---|---|---|---|
| Percentage | tie half a win; 0 with no game | `test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero` | ☑ |
| Percentage first | 1-0, 0-0-1, 0-1-1 | `test_rank_by_percentage_first` | ☑ |
| Level teams | given order, either way round | `test_level_teams_keep_the_given_order` `[P]` | ☑ |
| Each step decides when the earlier ones are level | head-to-head; division record; conference record; net points in division games; net points in all games; strength of schedule, each opponent once | `test_head_to_head_breaks_a_tie`, `test_division_record_breaks_a_split_series`, `test_conference_record_breaks_equal_division_records`, `test_net_points_in_division_games_breaks_equal_records`, `test_net_points_in_all_games_breaks_equal_division_net_points`, `test_strength_of_schedule_counts_each_opponent_once` | ☑ |
| A step places one team | the rest start over at head-to-head | `test_a_step_that_places_one_team_restarts_for_the_rest` | ☑ |

No `test_schema.py`: the reader tests pin every constant.
