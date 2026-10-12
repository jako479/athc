# fbpro98_lge — Test Matrix

Cases covered for the `.lge` league file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_chunks()` = constructed bytes (one team unless a shape is given), `golden` = real `.lge` in `data/` (`08_TEAMS.lge`, `10_TEAMS.LGE`, `12_TEAMS.LGE` one conference; `PNFL.lge` 18 teams, custom; `NFLPA94.lge` 28; `NFLPI97R.LGE` 30; grouped by chunk kind: `NFLPA93E.LGE` 28, `_default.lge` 30; the PNFL's 2047 season: `PNFL-before-week1.lge`, `PNFL-after-week16.lge`, `PNFL-after-super-bowl.lge`). Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_lge` → 107 passing.

## reader.py — `parse_lge` / `read_lge`

### Normal
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league, whole model, incl. leftover text after NULs | golden | every name and record in `PNFL.lge` | `test_custom_league` | ☑ |
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
| Division order as on the game's Week Seven screen | golden | `PNFL.lge` order | `test_division_standings_match_the_game` | ☑ |
| Final regular season, incl. tie games | golden | records; wins + tie games = 144 | `test_final_regular_season_records` | ☑ |
| Conference order, ties broken by point differential | golden | AFC and NFC order | `test_conference_standings_break_ties_by_point_differential` | ☑ |
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

## model.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Nested access | conference → division → team | `test_nested_access` | ☑ |
| Official name, either part empty | `"Denver Broncos"`, `"Denver"`, `"Broncos"`, `""` | `test_official_name` `[P]` | ☑ |
| Frozen | assignment raises | `test_frozen` | ☑ |
| Record totals | games, win percentage (ties half, 0.0 with no games), point differential | `test_record_totals` `[P]` | ☑ |
| Rank by win percentage | 9-6-1, 9-7, 8-7-1 | `test_division_standings_rank_by_win_percentage_counting_ties_as_half` | ☑ |
| Equal win percentage | 7-7-2 (+10) above 8-8 (+3) | `test_equal_win_percentage_ranked_by_point_differential` | ☑ |
| Level teams | file order | `test_level_teams_keep_file_order` | ☑ |
| Conference standings | ranked across divisions | `test_conference_standings_rank_across_divisions` | ☑ |

## schema.py

| Case | Expected | Test | Status |
|---|---|---|---|
| Chunk header and ids | `<4sI`, 8 bytes; `L03:` ... `S03:` | `test_chunk_header_and_ids` | ☑ |
| Chunk sizes | L03 89+, C03 and D03 29+, T03 171, R03 325 | `test_chunk_sizes` | ☑ |
| Field offsets | counts, names `0x04` (25), team name `0x36`, nickname `0x47` (17) | `test_field_offsets` | ☑ |
| Mask factor | `0x69` | `test_mask_factor` | ☑ |
| Schedule layout | 3-byte header, weeks at `0x00`, rounds at `0x01`, 6-byte game, played `0` | `test_schedule_layout` | ☑ |
