# fbpro98_lge — Test Matrix

Cases covered for the `.lge` league file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_chunks()` = constructed bytes (one team unless a shape is given), `golden` = real `.lge` in `data/` (`08_TEAMS.lge`, `10_TEAMS.LGE`, `12_TEAMS.LGE` one conference; `PNFL.lge` 18 teams, custom, 2049 after week 6; `NFLPA94.lge` 28; `NFLPI97R.LGE` 30; grouped by chunk kind: `NFLPA93E.LGE` 28, `_default.lge` 30; the PNFL's 2047 season: `PNFL-before-week1.lge`, `PNFL-after-week16.lge`, `PNFL-after-super-bowl.lge`; seasons' ends for the tie-breakers: `PNFL-2043-after-super-bowl.lge`, `PNFL-2046-after-super-bowl.lge`, `PNFL-2048-after-week16.lge`). Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_lge` → 135 passing.

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
| Unprintable tag | bytes | shown as hex | `test_unprintable_tag_shown_as_hex` | ☑ |
| Error names the path first | bytes | "league.lge: ..." and `.path` | `test_error_names_the_path_first` | ☑ |

### Standings
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Division order as on the game's season-end screen (2048) | golden | Miami above Buffalo on conference record, not points | `test_division_standings_match_the_games_season_end_screen` | ☑ |
| Division ties by division record, head-to-head, conference record | golden | 2043 and 2046 orders | `test_division_ties_follow_the_manuals_steps` | ☑ |
| Any teams of the file ranked | golden | 2048 wild cards Buffalo over Pittsburgh head-to-head | `test_ranked_orders_any_teams_of_the_file` | ☑ |
| `ranked` default covers the whole file | golden | all 18 teams, each once | `test_ranked_default_covers_every_team_of_the_file` | ☑ |
| Final regular season, incl. tie games | golden | records; wins + tie games = 144 | `test_final_regular_season_records` | ☑ |
| Conference order, ties broken by the manual's steps | golden | AFC and NFC order | `test_conference_standings_break_ties_by_the_manuals_steps` | ☑ |
| Built file: split series broken on division net points | make_chunks | winner by more first in division and conference | `test_built_standings_break_a_split_series_on_division_net_points` | ☑ |
| Grouped order, a played season with bye weeks | golden | real 1993 NFL records | `test_grouped_league_season_matches_the_real_1993_results` | ☑ |
| Playoff games not counted | golden | records after the Super Bowl = after week 16 | `test_playoff_games_do_not_count` | ☑ |
| Before week 1 | golden | all records zero; standings in file order | `test_before_week_one_records_are_zero_and_standings_keep_file_order` | ☑ |
| A win and an overtime tie | make_chunks | 1-0-1 31-24 / 0-1-1 24-31 | `test_record_counts_played_regular_season_games` | ☑ |
| Unplayed game, `0xFF` teams | make_chunks | skipped | `test_unplayed_games_skipped` | ☑ |
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
| Played playoff game with team 1 / N, team 0 / N+1 | make_chunks | read / "no team T (teams are 1-N)" | `test_played_playoff_game_with_first_and_last_team_read` `[P]` / `test_played_playoff_game_with_unknown_team_rejected` `[P]` | ☑ |

## model.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Nested access | conference → division → team | `test_nested_access` | ☑ |
| Official name, either part empty | `"Denver Broncos"`, `"Denver"`, `"Broncos"`, `""` | `test_official_name` `[P]` | ☑ |
| Frozen | assignment raises | `test_frozen` | ☑ |
| Record totals | games, win percentage (ties half, 0.0 with no games), point differential | `test_record_totals` `[P]` | ☑ |
| `ranked` orders from the games, not the records | winner first though listed second | `test_ranked_orders_from_the_files_games_not_the_records` | ☑ |
| `ranked` with no teams given | every team of the file | `test_ranked_defaults_to_every_team_of_the_file` | ☑ |
| `ranked` with an empty input | empty | `test_ranked_with_no_teams_is_empty` | ☑ |
| Game winner and loser | home win, away win, tie (None) | `test_game_winner_and_loser` `[P]` | ☑ |

## standings.py

Built seasons: three divisions, two conferences; `_win(a, b, by)`.

| Case | Expected | Test | Status |
|---|---|---|---|
| Percentage | tie half a win; 0 with no game | `test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero` | ☑ |
| Percentage first | 1-0, 0-0-1, 0-1-1 | `test_rank_by_percentage_first` | ☑ |
| Level teams | given order, either way round | `test_level_teams_keep_the_given_order` `[P]` | ☑ |
| Each step decides when the earlier ones are level | head-to-head; division record; conference record; net points in division games; net points in all games; strength of schedule | `test_head_to_head_breaks_a_tie`, `test_division_record_breaks_a_split_series`, `test_conference_record_breaks_equal_division_records`, `test_net_points_in_division_games_breaks_equal_records`, `test_net_points_in_all_games_breaks_equal_division_net_points`, `test_strength_of_schedule_breaks_everything_else_level` | ☑ |
| A step places one team | the rest start over at head-to-head | `test_a_step_that_places_one_team_restarts_for_the_rest` | ☑ |

## schema.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Chunk header and ids | `<4sI`, 8 bytes; `L03:` ... `S03:` | `test_chunk_header_and_ids` | ☑ |
| Chunk sizes | L03 89+, C03 and D03 29+, T03 171, R03 325 | `test_chunk_sizes` | ☑ |
| Field offsets | counts, names `0x04` (25), team name `0x36`, nickname `0x47` (17) | `test_field_offsets` | ☑ |
| Mask factor | `0x69` | `test_mask_factor` | ☑ |
| Schedule layout | 3-byte header, weeks at `0x00`, rounds at `0x01`, 6-byte game, played `0` | `test_schedule_layout` | ☑ |
