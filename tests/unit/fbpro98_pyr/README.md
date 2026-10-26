# fbpro98_pyr — Test Matrix

Cases covered for the `.pyr` player file library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized over variants. Input: `make_pyr()` = constructed bytes (plain records from `make_record()`, a header from `make_header()`, coded with the tests' own table and padded with placeholder players to 256 records so the ids reveal the whole table), `golden` = real `.pyr` in `data/`: `PNFL.pyr` (the PNFL's 2049 season after week 6, from `E:\PNFL\League - League Files\2049\49PNFL6`; the spec's sample, 9,192 players), `08_TEAMS.PYR` (the smallest stock league, 407 players), `NFLPI97R.PYR` (the stock league the spec names, 2,100 players; heights, weights and data in the unknown bytes) and `1994.PYR` (the old layout, 1,481 players; `FF FF` first in the header's and every record's unknown bytes), the stock files from `E:\SIERRA\FbPro98`. Golden expected values are the spec's worked examples and appendix, or the decoded bytes of the record each test names. `model` = a `PyrFile` built in Python. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/fbpro98_pyr` → 138 passing.

## reader.py — `parse_pyr` / `read_pyr`

### Real files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Custom league header and player count | golden | key `0xCE5F`, name `""`, unknown `00 00 00 00 00 00`; ids 100-9291 | `test_custom_league_header` | ☑ |
| Coding table | golden | the spec's appendix, all 256 entries | `test_custom_league_coding_table_matches_the_spec_appendix` | ☑ |
| The spec's worked example, each rating by name | golden | player 6283 whole | `test_custom_league_player` | ☑ |
| Actual above potential | golden | 7302: agility 81 potential, 83 actual | `test_actual_above_potential_is_read` | ☑ |
| Injuries, incl. a level past one byte | golden | the spec's three; the spec's `202 1 32 3` (1913) | `test_injuries` `[P]` | ☑ |
| Placeholders | golden | 3,258 `No One` with every rating 1, 191 `Delete Me`, 114 `2043 Draft` | `test_placeholders` | ☑ |
| Newest draft class | golden | 555 with height, all with weight and `00 ff ff 00 00 00`; 5565 whole | `test_newest_draft_class_has_height_weight_and_marker` | ☑ |
| Leftover text after the name's NUL | golden | 145 `Frank Ragnow`; `NFLPI97R` 208 `Karim Abdul-Jabbar` (non-ASCII leftovers) | `test_name_with_leftover_text_after_nul`, `test_leftover_bytes_after_nul_not_read` | ☑ |
| Group not matching the position | golden | 4603 `LB`, group 0 | `test_group_not_matching_the_position_is_read` | ☑ |
| Stock league header | golden | key `0xEE0F`, `SYNERGISTIC1`, unknown `00 ff ff 00 00 00`, 2,100 players; plain `0x00` written `0x0F` | `test_stock_league_header` | ☑ |
| Stock first and last player, data in the unknown bytes, eight distinct ratings by name | golden | 100 Todd Collins, 2199 Mallory McCoy whole | `test_stock_league_first_and_last_player` | ☑ |
| Plain byte written as itself | golden | table[122] = 122, table[149] = 149 | `test_plain_byte_written_as_itself_is_read` | ☑ |
| Smallest stock league | golden | key `0xB77D`, ids 100-506, first and last names | `test_smallest_stock_league` | ☑ |
| Every position and group appears | golden | `set(Position)`, `GROUPS` | `test_every_position_and_group_appears` | ☑ |
| Old stock layout | golden | key `0xACE2`, `SYNERGISTIC1`, header unknown `ff ff 00 00 00 00`; ids 100-1580; every player's unknown the same; no height or weight | `test_old_stock_layout_reads` | ☑ |
| `read` returns `PyrFile`; `parse == read` | golden | equal | `test_read_returns_pyr_file_and_matches_parse` | ☑ |
| `read` accepts a `str` folder | golden | equal to `Path` | `test_read_accepts_str_league_dir` | ☑ |
| Missing file | league + tmp folder | `OSError` naming `<league_dir>/<league>.pyr` | `test_missing_file_raises_oserror_for_built_path` | ☑ |

### Built files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Every field set, 256 players | make_pyr | the `Player` whole; a placeholder whole; the whole table | `test_built_file_parses` | ☑ |
| Header name filling its field / up to the NUL | make_pyr | `SYNERGISTIC1O` / `SYN` | `test_header_name_filling_its_field_read_whole`, `test_header_name_read_up_to_nul` | ☑ |
| Key 0, `0xFFFF` | make_pyr | read as is | `test_header_key_takes_any_value` `[P]` | ☑ |
| Header unknown bytes zeros, `00 ff ff 00 00 00`, `ff ff 00 00 00 00`, `01 02 03 04 05 06` | make_pyr | kept as read | `test_header_unknown_bytes_kept_as_read` `[P]` | ☑ |
| Player name filling its field (13, no NUL) | make_pyr | 13 characters, the next field untouched | `test_player_name_filling_its_field_read_whole` | ☑ |
| Non-ASCII byte | make_pyr | decoded as U+FFFD | `test_non_ascii_byte_decodes_as_replacement` | ☑ |

### Size → `InvalidPyrError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Empty file | bytes | "Empty file" | `test_empty_file_rejected` | ☑ |
| 1 and 59 bytes / 60 | make_pyr | "shorter than the 60-byte header" / no players, empty table | `test_file_shorter_than_header_rejected` `[P]`, `test_header_alone_parses` | ☑ |
| 61, 119, 121 bytes | make_pyr | "not the 60-byte header plus a whole number" | `test_size_not_whole_records_rejected` `[P]` | ☑ |
| 65,436 records / 65,437 | make_pyr | parsed / "at most 65436 fit" | `test_record_limit` | ☑ |

### Header → `InvalidPyrError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| First and last byte of each zero range set (0x02, 0x0E, 0x1C, 0x35) | make_pyr | "Header byte at 0x.. is 0xff, expected 0" | `test_header_zero_byte_rejected` `[P]` | ☑ |
| Bad header byte and size 61 | make_pyr | the size message | `test_size_checked_before_header` | ☑ |
| Bad header byte and a table conflict | make_pyr | the header message | `test_header_checked_before_table` | ☑ |

### Coding table → `InvalidPyrError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| One record of only the bytes its id reveals | make_pyr | parsed; a two-entry table | `test_one_record_file_parses` | ☑ |
| One unrevealed byte, in record 0 / record 1 | make_pyr | "Record 0 at 0x3c: byte 0x.. at 0x6e is not in the coding table the ids reveal" / "Record 1 at 0x78: ... at 0xaa" | `test_byte_the_ids_do_not_reveal_rejected` `[P]` | ☑ |
| 255 players and a rating of 99 / 256 | make_pyr | rejected at 0x58 / parsed | `test_255_players_cannot_reveal_rating_99` | ☑ |
| Plain id byte written two ways, in record 1 (revealed in 0) / record 157 (revealed in 156) | bytes | "Record 1 at 0x78: plain 0x00 is written as 0x.., but as 0x.. in record 0" / "Record 157 at 0x2508: plain 0x01 ... in record 156" | `test_plain_byte_written_two_ways_rejected` `[P]` | ☑ |
| One disk byte for two plain values | bytes | "0x.. stands for both 0x64 and 0x65" | `test_disk_byte_for_two_plain_values_rejected` | ☑ |
| Table conflict and a model error | bytes | the table message | `test_table_checked_before_the_model` | ☑ |

### The model's rules through the parser → `InvalidPyrError`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Rating 100 | make_pyr | "player 100: potential.acceleration: Must be 0-99, got 100" | `test_rating_100_rejected` | ☑ |
| Position 15 in record 0 / 1 | make_pyr | "Record 0 at 0x3c: 15 is not a valid Position" / "Record 1 at 0x78: ..." | `test_position_15_rejected` `[P]` | ☑ |
| Every position code 0-14 | make_pyr | its `Position` member, per the spec's table | `test_every_position_code_decoded` `[P]` | ☑ |
| Group 1 | make_pyr | "player 100: group: Must be one of 0, 10, 13, 14, 15, 16, 17, 18, 19, got 1" | `test_group_outside_the_table_rejected` | ☑ |
| Error names the path first | make_pyr | "league.pyr: ..." and `.path` | `test_error_names_the_path_first` | ☑ |
| No path given | bytes | "<buffer>: ..." and `.path` | `test_error_names_buffer_when_no_path_given` | ☑ |

## model.py — `PyrFile.validate()`

Each rule at its limit and one past it; `model` = a `PyrFile` built in Python.

| Case | Expected | Test | Status |
|---|---|---|---|
| Valid file; file without players | passes | `test_valid_file_passes`, `test_file_without_players_passes` | ☑ |
| Key 0 / `0xFFFF` / `0x10000` / −1; unknown 6 / 5, 7 bytes; name 13 / 14 | pass / "key: Must be 0-65535" / "unknown: Must be 6 bytes" / "name: Must be at most 13 characters" | `test_header_field_at_its_limit_accepted` `[P]`, `test_header_field_past_its_limit_rejected` `[P]` | ☑ |
| Partial coding table | passes | `test_partial_coding_table_accepted` | ☑ |
| Plain or disk value 256 / −1; two plain values on one disk byte | "coding_table key: Must be 0-255" / "coding_table[0x00]: Must be 0-255" / "coding_table: Plain 0x01 and 0x02 are both written as 0x3f" | `test_coding_table_rejected` `[P]` | ☑ |
| Keys not 100, 101, ... in order | "players: Must be keyed 100, 101, ... in order, got N at index i" | `test_players_not_keyed_from_100_in_order_rejected` `[P]` | ☑ |
| Key not its player's id | "players[100]: Holds player 101" | `test_player_key_not_its_id_rejected` | ☑ |
| Names 13 / 14 | pass / "player 100: first_name: Must be at most 13 characters" | `test_name_limits` `[P]` | ☑ |
| Ratings 0, 99 / 100, −1, both sets | pass / "player 100: potential.acceleration: Must be 0-99" | `test_rating_at_its_limit_accepted` `[P]`, `test_rating_past_its_limit_rejected` `[P]` | ☑ |
| Position as member or code 0, 14 / 15, −1 | pass / "player 100: position: Must be 0-14" | `test_position_as_member_or_code_accepted` `[P]`, `test_position_outside_the_codes_rejected` `[P]` | ☑ |
| Every group of the spec's table / 1, 9, 11, 12, 20, −1 | pass / "player 100: group: Must be one of ..." | `test_every_group_of_the_spec_table_accepted` `[P]`, `test_group_outside_the_spec_table_rejected` `[P]` | ☑ |
| Years, height 255 / 256; weight 65535 / 65536; −1 | pass / "player 100: years: Must be 0-255" | `test_numeric_field_limits` `[P]` | ☑ |
| Injury level 65535 / 65536; injury, week 255 / 256; −1 | pass / "player 100: injury.level: Must be 0-65535" | `test_injury_field_limits` `[P]` | ☑ |
| Unknown 5 or 7 bytes | "player 100: unknown: Must be 6 bytes" | `test_unknown_not_six_bytes_rejected` `[P]` | ☑ |
| Problem in the second player | names player 101 | `test_problem_in_a_later_player_names_that_player` | ☑ |
| Bad key and bad player | the key's message | `test_first_problem_in_file_order_reported` | ☑ |

No `test_schema.py`: the reader tests on real files pin every constant (the builder uses the spec's literal offsets, not the schema's).
