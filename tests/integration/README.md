# Integration — Test Matrix

CLI end-to-end cases. Convention in [../../docs/design/testing-integration.md](../../docs/design/testing-integration.md).

One row per behavior. `[P]` = parametrized. Input: `data/` real `.prf` + rules; `tmp` = constructed. Exit: 0 clean / 1 violations / 2 I/O or no rules. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/integration` passes.

## `athc profile check` — `collect_files`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Single file | tmp | `[file]`, no errors | `test_collect_single_file` | ☑ |
| Directory, top level only | tmp | top `.prf` only | `test_collect_directory_top_level` | ☑ |
| Directory, recursive | tmp | whole tree | `test_collect_directory_recursive` | ☑ |
| Missing path | tmp | "does not exist" error | `test_collect_missing_path` | ☑ |
| Non-`.prf` file | tmp | "not a .prf file" | `test_collect_non_prf` | ☑ |
| Empty directory | tmp | "no .prf files" | `test_collect_empty_dir` | ☑ |
| Dedupes repeats | tmp | one entry | `test_collect_dedupes` | ☑ |
| Glob expands / filters / no-match | tmp | matched `.prf` only | `test_collect_glob` `[P]` | ☑ |

## `athc profile check` — `check_file`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense violations format | data | head + indented details; "offense", "FG range" | `test_check_file_offense_format` | ☑ |
| Defense violations format | data | "defense" head | `test_check_file_defense_format` | ☑ |
| Clean (validate mocked) | data | `(0, "... OK ...")` | `test_check_file_clean` | ☑ |
| Malformed `.prf` | tmp | `(-1, "... ERROR ...")` | `test_check_file_malformed` | ☑ |
| **Pinned counts (real)** | data | OFF1 = 18, DEF1 = 7 | `test_check_file_pinned_counts` `[P]` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal report (path normalized) | `test_check_file_matches_golden` `[P]` | ☑ |

## `athc profile check` — command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No path given | — | usage error, exit 2 | `test_cli_requires_path` | ☑ |
| `--rules` removed | option | exit 2; "No such option" | `test_cli_rules_option_removed` | ☑ |
| Violations | data + league | exit 1; "1 file(s) checked" | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + league | exit 1; "2 file(s) checked" | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + league | exit 1; counts | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Clean (mocked) | data + league | exit 0; "OK" | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp | exit 2; "does not exist" | `test_cli_missing_path` | ☑ |
| Malformed `.prf` | tmp + league | exit 2; "ERROR" printed | `test_cli_malformed_prf` | ☑ |
| Continues past bad file | tmp + league | exit 2; both lines printed | `test_cli_continues_past_bad` | ☑ |

The "league" input is a selected league folder whose `rules/profile.toml` is the test rules file.

## `athc profile check` — rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No league configured | empty config | exit 2; "no league selected" | `test_cli_no_league` | ☑ |
| League folder without rules | `leagues/<NAME>/` | exit 2; "no rules configured" | `test_cli_no_rules_in_league_folder` | ☑ |
| Rules from the league folder | `leagues/<NAME>/rules/profile.toml` + `[athc] league` | exit 1 | `test_cli_rules_from_league_folder` | ☑ |
| `--league` picks the folder | two leagues | exit 1 | `test_cli_league_flag_picks_folder` | ☑ |
| `profile_rules` list | relative to the league folder | exit 1 | `test_cli_profile_rules_list_relative_to_league_folder` | ☑ |
| `profile_rules` layering | base + overlay | later overrides earlier | `test_cli_rules_layering` | ☑ |
| Bad rules TOML | league `rules/profile.toml` bad | exit 2; "TOML parse error" | `test_cli_bad_rules_toml` | ☑ |
| Missing listed rules file | `profile_rules` → absent file | exit 2; path named | `test_cli_missing_rules` | ☑ |
| Malformed `athc.ini` | bad ini | exit 2 | `test_cli_malformed_ini` | ☑ |

## `athc profile check` — `--gameplan` compatibility
Real `TST-OFF1.prf`/`TST-DEF1.prf` + real `offense.pln`/`defense.pln`; clean `compat_{off,def}_clean.prf` fixtures for the exit-0 path. Goldens in `expected/compat_{offense,defense}.report.txt` (path normalized).
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| check_file offense reports compat | data | head "gameplan issue(s)"; GLR line; count 19 | `test_check_file_gameplan_offense_reports_compat` | ☑ |
| check_file defense reports compat | data | FG/PAT special line; count 12 | `test_check_file_gameplan_defense_reports_compat` | ☑ |
| check_file reverse counts | data | 4 extra `gameplan:` lines; count 12 | `test_check_file_gameplan_reverse_counts` | ☑ |
| check_file clean both ways (mocked) | data | bare `(0, "... gameplan compatible")` | `test_check_file_gameplan_clean` | ☑ |
| check_file reverse only fails | data | count 10; `0 violation(s), 10 gameplan issue(s)` | `test_check_file_gameplan_reverse_only_fails` | ☑ |
| check_file side mismatch (both ways) | data | `(-1, "profile is X but gameplan is Y")` | `test_check_file_gameplan_side_mismatch` / `_defense` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal (path normalized) | `test_check_file_gameplan_matches_golden` `[P]` | ☑ |
| CLI offense / defense | data + `--gameplan` | exit 1; compat line | `test_cli_gameplan_offense_exit_1` / `_defense_exit_1` | ☑ |
| CLI clean (mocked) | clean + league with compat-only rules | exit 0; "gameplan compatible" | `test_cli_gameplan_clean_exit_0` | ☑ |
| CLI reverse fails | clean + league with compat-only rules | exit 1; `gameplan:` line | `test_cli_gameplan_reverse_exit_1` | ☑ |
| CLI side mismatch | data | exit 2; "profile is offense but gameplan is defense" | `test_cli_gameplan_side_mismatch_exit_2` | ☑ |
| CLI mixed sides continues | 2 files, 1 gameplan | exit 2; both lines; "2 file(s) checked" | `test_cli_gameplan_mixed_sides_continues` | ☑ |
| CLI gameplan missing / bad ext / malformed | tmp | exit 2; logged | `test_cli_gameplan_missing_file_exit_2` / `_bad_extension_exit_2` / `_malformed_exit_2` | ☑ |

## `athc profile check` — Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc profile check` | data + league | exit 1; report printed | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan check`

In [test_gameplan_check.py](test_gameplan_check.py). Inputs: real `data/offense.pln` (O_64_06a) + `data/defense.pln` (D_50_09), the curated `data/plays/` pool both resolve against, and the test rules `data/gameplan_rules.toml` + `data/playpool_rules.toml`. Covers collect / check_file / exit codes, golden reports, pinned counts, pool build, and league/config resolution.

## `collect_files`
Same eight cases as profile (single / top level / recursive / missing / non-`.pln` / empty / dedupes / glob), with `.pln`.

## `check_file`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense violations format | data | head + indented details; "offense", "normal" | `test_check_file_offense_format` | ☑ |
| Defense violations format | data | "defense" head | `test_check_file_defense_format` | ☑ |
| Clean (validate mocked) | data | `(0, "... OK ...")` | `test_check_file_clean` | ☑ |
| Malformed `.pln` | tmp | `(-1, "... ERROR ...")` | `test_check_file_malformed` | ☑ |
| **Pinned counts (real)** | data | offense = 3, defense = 1 | `test_check_file_pinned_counts` `[P]` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal report (path normalized) | `test_check_file_matches_golden` `[P]` | ☑ |

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error, exit 2 | `test_cli_requires_path` | ☑ |
| Removed options rejected | `--play-path`, `--playpool-rules`, `--rules` | exit 2; "No such option" | `test_cli_removed_options_are_rejected` `[P]` | ☑ |
| Violations | data + league | exit 1; "1 file(s) checked" | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + league | exit 1; "2 file(s) checked" | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + league | exit 1; counts | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Clean (mocked) | data + league | exit 0; "OK" | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp + league | exit 2; "does not exist" | `test_cli_missing_path` | ☑ |
| Malformed `.pln` | tmp + league | exit 2; "ERROR" printed | `test_cli_malformed_pln` | ☑ |
| Continues past bad file | tmp + league | exit 2; both lines printed | `test_cli_continues_past_bad` | ☑ |

The "league" input is a selected league folder holding the test pool (`play_path`), `rules/playpool.toml` and `rules/gameplan.toml`.

## pool / rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing play path | league `play_path` absent | exit 2; "not a directory" | `test_cli_missing_play_path` | ☑ |
| Bad playpool rules TOML | league `rules/playpool.toml` bad | exit 2 | `test_cli_bad_playpool_rules` | ☑ |
| League folder without rules | `--league` + folder | exit 2; "no rules configured" | `test_cli_no_rules_in_league_folder` | ☑ |
| Bad rules TOML | league `rules/gameplan.toml` bad | exit 2; "TOML parse error" | `test_cli_bad_rules_toml` | ☑ |
| No league resolvable | no config | exit 2; "league" | `test_cli_no_league` | ☑ |
| Resolves from the league folder | `[athc] league` + `leagues/<NAME>/` | exit 1 | `test_cli_resolves_from_league_folder` | ☑ |
| `gameplan_rules` list | base + overlay | exit 1 | `test_cli_gameplan_rules_list_layers_in_order` | ☑ |
| Listed rules file missing | `gameplan_rules` → absent file | exit 2; path named | `test_cli_missing_listed_rules_file_is_reported` | ☑ |
| League playpool rules apply | league | exit 1; "timed passes" | `test_cli_league_playpool_rules_apply` | ☑ |
| `play_path` override keeps league playpool rules | `load_config(play_path=…)` | league's `rules/playpool.toml` | `test_load_config_play_path_alone_reads_league_playpool_rules` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc gameplan check` | data + league | exit 1; report printed | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan list-normals` / `list-specials`

In [test_gameplan_list.py](test_gameplan_list.py). Reads `data/offense.pln` / `data/defense.pln` (no pool/rules/config); stdout compared to `expected/{offense,defense}_normals_{slot,name}.txt` and `expected/{offense,defense}_specials.txt`. File mode prepends a `:: <source>` header line.

## list-normals
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error, exit 2 | `test_normals_requires_path` | ☑ |
| Invalid `--sort` | data | usage error, exit 2 | `test_normals_rejects_invalid_sort` | ☑ |
| Help uses lowercase names | `--help` | `gameplan [output_file]`; no capitals | `test_normals_help_uses_lowercase_names` | ☑ |
| `--force` / `--output` removed | option | exit 2; "No such option" | `test_normals_removed_options_rejected` `[P]` | ☑ |
| Default: `<name>.normals.txt` next to the `.pln` | tmp copy | header + plays | `test_normals_default_writes_next_to_gameplan` | ☑ |
| `-` prints, slot order | data | 64 lines match fixture | `test_normals_dash_offense_slot` / `..._defense_slot` | ☑ |
| `-` prints, `--sort name` | data | sorted, blanks dropped | `test_normals_dash_sort_name` | ☑ |
| Output file: header + plays | data + out | line 1 `::`, rest match | `test_normals_file_writes_header_and_plays` | ☑ |
| Output file: `--sort name` | data + out | rest match name fixture | `test_normals_file_sort_name` | ☑ |
| Existing file replaced | existing out | exit 0; rewritten | `test_normals_overwrites_existing_file` | ☑ |
| Logs count + path | data + out | "Wrote 64 normal play(s)" | `test_normals_file_logs_count` | ☑ |
| Missing gameplan | tmp | exit 1; error logged | `test_normals_missing_gameplan` | ☑ |
| Malformed, output file | tmp | exit 1; no file written | `test_normals_malformed_file_mode_no_output` | ☑ |

## list-specials
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error, exit 2 | `test_specials_requires_path` | ☑ |
| Help uses lowercase names | `--help` | `gameplan [output_file]`; no capitals | `test_specials_help_uses_lowercase_names` | ☑ |
| `--force` / `--output` removed | option | exit 2; "No such option" | `test_specials_removed_options_rejected` `[P]` | ☑ |
| Default: `<name>.specials.txt` next to the `.pln` | tmp copy | header + plays | `test_specials_default_writes_next_to_gameplan` | ☑ |
| `-` prints (source order) | data | lines match fixture | `test_specials_dash_offense` / `..._defense` | ☑ |
| Output file: header + plays | data + out | line 1 `::`, rest match | `test_specials_file_writes_header_and_plays` | ☑ |
| Existing file replaced | existing out | exit 0; rewritten | `test_specials_overwrites_existing_file` | ☑ |
| Logs count + path | data + out | "Wrote 6 special play(s)" | `test_specials_file_logs_count` | ☑ |
| Malformed, output file | tmp | exit 1; no file written | `test_specials_malformed_file_mode_no_output` | ☑ |

---

# `athc gameplan find-play`

In [test_gameplan_find_play.py](test_gameplan_find_play.py). Pure helpers (`find_in_gameplan`, `format_hit_line`) on constructed gameplans; CLI tier on real `data/offense.pln` / `data/defense.pln` and tmp-written constructed gameplans. Normal hits read `'OR45RL01' found in slots 1-3, 16-2` (no category); special hits read `'BCFGPAT' found in special slot 1 (Field Goal/PAT)`. Misses always print `not found`. No pool/rules/config.

## helpers (constructed gameplans)
| Case | Expected | Test | Status |
|---|---|---|---|
| find: no match / normal / case-insensitive | correct `(normal, special)` hits | `test_find_no_match_returns_empty` / `test_find_matches_normal_slot` / `test_find_case_insensitive` | ☑ |
| find: one play in many slots / many plays in one gameplan | hits | `test_find_multiple_in_one_gameplan` / `test_find_multiple_different_plays` | ☑ |
| find: custom special; skips stock-special + clock | special hit / no hit | `test_find_matches_custom_special` / `test_find_skips_stock_special_slots` / `..._clock_slots` | ☑ |
| Format — normal in 1 slot (singular, no category) | `'OR45RL01' found in slot 1-1` | `test_format_normal_one_slot` | ☑ |
| Format — normal in 2 / 3 slots (plural, comma-separated) | `'DUP' found in slots 1-1, 2-2` / `…, 16-4` | `test_format_normal_two_slots` / `test_format_normal_three_slots` | ☑ |
| Format — offense / defense special (long cat at the end) | `… found in special slot N (cat)` | `test_format_offense_special` / `test_format_defense_special` | ☑ |

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No args / single arg | — | usage error, exit 2 | `test_cli_requires_args` / `test_cli_single_arg_is_rejected` | ☑ |
| `--verbose` (removed) | data | usage error, exit 2 | `test_cli_verbose_option_is_rejected` | ☑ |
| Wildcard `path` (matching files present) | tmp | usage error, exit 2; not expanded | `test_cli_wildcard_path_is_rejected` | ☑ |
| Single file hit (normal / special) | data | slot(s); special adds category; no summary | `test_cli_single_file_hit` / `test_cli_finds_custom_special` | ☑ |
| Single file miss | data | exit 1; "not found" | `test_cli_single_file_miss_exit_1` | ☑ |
| Case-insensitive | data | hit | `test_cli_single_file_case_insensitive` | ☑ |
| Several plays over a dir; one play in 2 slots of a gameplan that holds 2 of them; summary | tmp | exit 0; per-play "Found N in M" | `test_cli_multiple_plays_all_hit` | ☑ |
| Multiple plays, one found (grep rule) | data | exit 0 | `test_cli_one_play_found_exit_0` | ☑ |
| Multiple plays, none found | data | exit 1 | `test_cli_no_play_found_exit_1` | ☑ |
| Directory: hit in one file, miss in the other | tmp | exit 0; hit + `not found` lines; footer | `test_cli_directory_reports_hit_and_miss_per_file` | ☑ |
| Directory: no hits | tmp | exit 1; `not found` + footer | `test_cli_directory_misses_are_reported` | ☑ |
| Directory: instance/file counts | tmp | "Found N in M"; exit 0 when any play found | `test_cli_directory_summary_counts_multiple_hits` / `..._per_play_summary` | ☑ |
| Recursive subdir | tmp | exit 0; found | `test_cli_recursive_finds_in_subdir` | ☑ |
| Missing path / malformed `.pln` | tmp | exit 2 | `test_cli_missing_path_exit_2` / `test_cli_malformed_pln_exit_2` | ☑ |

---

# `athc gameplan set-normals`

In [test_gameplan_set_normals.py](test_gameplan_set_normals.py). Operates on a tmp copy of `data/offense.pln` with the curated pool (a selected league whose `play_path` is `data/plays`, with its `rules/playpool.toml`). Edits in place, no backup; `check` validates. Exit 0 = updated, 1 = error (nothing written), 2 = usage.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs gameplan / input_file | — | usage error, exit 2 | `test_requires_gameplan` / `test_requires_input_file` | ☑ |
| Removed options rejected | `--stdin`, `--no-backup`, `--play-path`, `--playpool-rules` | exit 2; "No such option" | `test_removed_options_rejected` `[P]` | ☑ |
| Writes normals from file | tmp | slot 0 set, rest cleared | `test_writes_from_file` | ☑ |
| Slot path starts with the play pool's folder name | tmp | `<pool folder>\Offense\RL\<play>.ply` | `test_slot_path_starts_with_play_pool_folder` | ☑ |
| No backup | tmp | "Updated"; no `.bak` | `test_writes_no_backup` | ☑ |
| Skips `::` / strips ` ::` / `name::` fails | tmp | parsed / parsed / exit 1 | `test_skips_comment_lines` / `test_strips_inline_comments` / `test_inline_comment_requires_space` | ☑ |
| `-q` still updates; `-` reads the console | tmp | exit 0; set | `test_quiet_still_updates` / `test_dash_reads_from_console` | ☑ |
| Special-teams play rejected (untouched) | tmp | exit 1; "set-specials" | `test_rejects_special_teams_play` | ☑ |
| Missing play aborts (untouched) | tmp | exit 1 | `test_missing_play_aborts` | ☑ |
| >64 plays / missing `.pln` / league `play_path` missing | tmp | exit 1 | `test_too_many_plays_rejected` / `test_missing_pln` / `test_invalid_play_path` | ☑ |

# `athc gameplan set-specials`

In [test_gameplan_set_specials.py](test_gameplan_set_specials.py). Tmp copies of `offense.pln` / `defense.pln`, with the curated pool from a selected league (`play_path` = `data/plays`, its `rules/playpool.toml`). Merge semantics; bulk over file/dir/tree; wrong-side files skipped by size parity; no backup. Exit 0 = all updated, 1 = some failed, 2 = setup error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs path / input_file / no `-q` | — | usage error, exit 2 | `test_requires_path` / `test_requires_input_file` / `test_no_quiet_option` | ☑ |
| Removed options rejected | `--stdin`, `--no-backup`, `--play-path`, `--playpool-rules` | exit 2; "No such option" | `test_removed_options_rejected` `[P]` | ☑ |
| Writes special from file; merge preserves others | tmp | slot 1 set; rest intact | `test_writes_special_from_file` / `test_merge_preserves_other_categories` | ☑ |
| No backup | tmp | no `.bak`; no backup note | `test_writes_no_backup` | ☑ |
| Comments; `-` reads the console | tmp | parsed; set | `test_skips_and_strips_comments` / `test_dash_reads_from_console` | ☑ |
| Normal play / duplicate / >10 rejected (untouched) | tmp | exit 2 | `test_rejects_normal_play` / `test_rejects_duplicate_play` / `test_too_many_plays_rejected` | ☑ |
| Missing target / league `play_path` missing | tmp | exit 2 | `test_missing_target` / `test_invalid_play_path` | ☑ |
| Directory top-level / recursive | tmp | "2 file(s) processed" | `test_directory_top_level_only` / `test_directory_recursive` | ☑ |
| Offense input skips defense files | tmp | "1 file(s) processed"; def untouched | `test_offense_input_skips_defense_files` | ☑ |
| Continues past a failed file | tmp | exit 1; 1 updated, 1 failed | `test_continues_past_failed_file` | ☑ |

---

# `athc gameplan replace-play`

In [test_gameplan_replace_play.py](test_gameplan_replace_play.py). `replace_in_gameplan` / `format_replacement_lines` helpers on constructed offense/defense gameplans; CLI tier on tmp copies of `offense.pln` (`OR45RL01` @ 1-1) and constructed gameplans written to tmp, against the curated pool (a selected league whose `play_path` is `data/plays`). Finds the target like `find-play` (normal + custom-special, case-insensitive), swaps each hit for `replacement` (must be in the pool), backs up like `set-normals`. A play's normal hits collapse to one line, slots bracketed in order at the end — `'OLD' (cat) replaced with 'NEW' (cat) [1-3][4-2]`; specials print one line each — `Replaced 'OLD' (cat) in special slot N with 'NEW' (cat)`; short category. The GamePlan model validates each swap (side; special category). No rules. Exit 0 = clean, 1 = nothing replaced or some files failed, 2 = setup error.

## `replace_in_gameplan` (constructed gameplans)
| Case | Expected | Test | Status |
|---|---|---|---|
| No match → unchanged | no hits; same gameplan | `test_replace_no_match_unchanged` | ☑ |
| Offense normal, multiple slots; bystander kept | hits @ 0/5/63; all swapped | `test_replace_offense_normal_multiple_slots` | ☑ |
| Defense normal; bystander kept | hit @ 0; swapped | `test_replace_defense_normal` | ☑ |
| Offense special slot; others preserved | special hit @ 1; other special intact | `test_replace_offense_special` | ☑ |
| Defense special slot; others preserved | special hit @ 2; other special intact | `test_replace_defense_special` | ☑ |
| Case-insensitive target | hit @ 7 | `test_replace_case_insensitive_target` | ☑ |
| Special into a normal-slot hit | `ValueError` | `test_replace_special_into_normal_raises` | ☑ |
| Wrong special category | `ValueError` | `test_replace_wrong_special_category_raises` | ☑ |
| Wrong-side replacement | `ValueError` | `test_replace_wrong_side_raises` | ☑ |

## `format_replacement_lines` (short category; normal vs special phrasing)
| Case | Expected | Test | Status |
|---|---|---|---|
| Normal slot line | `'OLDRUN' (RL) replaced with 'NEWRUN' (RM) [1-1]` | `test_format_lines_normal_slot` | ☑ |
| Many normal slots → one line, bracketed in order at end | `'DUP' (RM) replaced with 'NEW' (RM) [1-3][4-2]` | `test_format_lines_multiple_normal_slots` | ☑ |
| Special slot line | `Replaced … (Field Goal/PAT) in special slot 1 with …` | `test_format_lines_special_slot` | ☑ |

## command — usage / replacement resolution (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No args / no PATH | — | usage error, exit 2 | `test_cli_requires_args` / `test_cli_requires_path` | ☑ |
| One PLAY only (4th positional rejected) | data + flags | usage error, exit 2 | `test_cli_rejects_multiple_plays` | ☑ |
| `-q` not offered | tmp + flags | usage error, exit 2 | `test_cli_no_quiet_option` | ☑ |
| Replacement not in pool | tmp + flags | exit 2; "not found in the play pool" | `test_cli_replacement_not_in_pool_exit_2` | ☑ |
| Replacement case-insensitive | data + flags | exit 0; resolves | `test_cli_replacement_case_insensitive` | ☑ |

## command — single file
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Replaces a normal play in multiple slots; bystander kept | tmp + flags | all set; one line `'OLDRUN' (RL) replaced with … [1-1][2-2][16-4]` | `test_cli_single_file_replaces_normal` | ☑ |
| Replaces a custom-special play; others kept | tmp + flags | other special intact; `… in special slot 1 with …` | `test_cli_single_file_replaces_special` | ☑ |
| Case-insensitive target | data + flags | replaced | `test_cli_single_file_target_case_insensitive` | ☑ |
| Miss (untouched) | data + flags | exit 1; "not found"; unchanged | `test_cli_single_file_miss_exit_1` | ☑ |

## command — no backups
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No backup written or reported | data | no `.bak`; no backup line | `test_writes_no_backup` | ☑ |
| `--no-backup` removed | option | exit 2; "No such option" | `test_no_backup_option_removed` | ☑ |

## command — directory / tree
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Directory updates matching files + summary | tmp + flags | exit 0; "replaced 2 … in 2 gameplan(s)" | `test_cli_directory_updates_matching_files` | ☑ |
| Other-side file has no hit → untouched | tmp + flags | exit 0; "in 1 gameplan(s)"; def unchanged | `test_cli_directory_leaves_other_side_untouched` | ☑ |
| No hits anywhere | tmp + flags | exit 1; "replaced 0 … in 0 gameplan(s)" | `test_cli_directory_no_hits_exit_1` | ☑ |
| Recursive subdir | tmp + flags | exit 0; replaced | `test_cli_recursive_replaces_in_subdir` | ☑ |

## command — validation / errors (target left untouched)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Special replacement for a normal hit | tmp + flags | exit 1; failed; no `.bak`; unchanged | `test_cli_replacement_special_for_normal_fails` | ☑ |
| Wrong-side replacement | tmp + flags | exit 1; failed; no `.bak`; unchanged | `test_cli_replacement_wrong_side_fails` | ☑ |
| Wrong special category | tmp + flags | exit 1; failed; no `.bak`; unchanged | `test_cli_replacement_wrong_special_category_fails` | ☑ |
| Missing PATH | tmp + flags | exit 2; "does not exist" | `test_cli_missing_path_exit_2` | ☑ |
| Malformed `.pln` | tmp + flags | exit 1; "failed" | `test_cli_malformed_pln_exit_1` | ☑ |
| League `play_path` missing | tmp | exit 2; "not a directory" | `test_cli_invalid_play_path_exit_2` | ☑ |
| `--play-path` removed | option | exit 2; "No such option" | `test_cli_play_path_option_removed` | ☑ |
| Continues past a failed file | tmp + flags | exit 1; 1 replaced, 1 failed | `test_cli_continues_past_failed_file` | ☑ |

---

# `athc profile diff`

In [test_profile_diff.py](test_profile_diff.py). Inputs: real `TST-OFF1/OFF2/DEF1.prf` plus a synthetic `diff_base.prf` / `diff_modified.prf` pair (the modified one touches every differable field). Goldens in `expected/diff_{all_fields,identical}.{txt,csv}` (paths normalized). No rules needed.

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs two PATHs | one path | usage error, exit 2 | `test_cli_requires_two_paths` | ☑ |
| Identical | OFF1 ×2 | exit 0; "are identical." | `test_cli_identical_exit_0` | ☑ |
| Differs | OFF1 vs OFF2 | exit 1; head + `[situations]` + summary | `test_cli_differs_exit_1` | ☑ |
| Cross-side | OFF1 vs DEF1 | exit 2; "cannot diff" | `test_cli_cross_side_exit_2` | ☑ |
| Missing / malformed input | tmp | exit 2 | `test_cli_missing_path_exit_2` / `test_cli_malformed_prf_exit_2` | ☑ |

## `--output`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `.txt` equals stdout | OFF1 vs OFF2 | file == no-`-o` stdout; stdout empty | `test_output_txt_matches_stdout` | ☑ |
| `.txt` identical | OFF1 ×2 | exit 0; "are identical." | `test_output_txt_identical_exit_0` | ☑ |
| `.csv` rows + CRLF | base/mod | `\r\n`; provenance + header + rows | `test_output_csv_rows_and_crlf` | ☑ |
| Unknown extension | `.json` | exit 2; no file written | `test_output_unknown_extension_exit_2` | ☑ |
| Write failure | bad dir | exit 2 | `test_output_write_failure_exit_2` | ☑ |
| **Golden `.txt`/`.csv` (all fields / identical)** | base/mod ↔ expected | byte-equal (path normalized) | `test_all_fields_output_matches_golden` `[P]` / `test_identical_output_matches_golden` `[P]` | ☑ |

## render / render_csv (direct)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `_infer_format` | name | txt / csv / None | `test_infer_format` `[P]` | ☑ |
| Defense direction → hex (txt / csv) | built diff | `0x0D ... 0x0F`; `0x0D:3` cells | `test_render_defense_direction_shows_hex` / `test_render_csv_defense_direction_hex` | ☑ |
| CSV slot cells | built diff | `RM:3`→`RM:8`, `RM:3`→`RR:3` | `test_render_csv_slot_cell_formats` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc profile diff` | OFF1 vs OFF2 | exit 1; report printed | `test_entry_point_subprocess` | ☑ |

---

# `athc profile copy`

In [test_profile_copy.py](test_profile_copy.py). Inputs: real `TST-OFF1/DEF1.prf` plus per-test mutated sources written to `tmp_path`. No rules (validate afterward with `check`). `ProfileWriter` unit tests live in `tests/unit/profile/test_writer.py`.

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Usage errors (no source / no target / no flag) | args | exit 2 | `test_cli_usage_errors_exit_2` `[P]` | ☑ |
| Help uses lowercase names | `--help` | `source target`; no capitals | `test_cli_help_uses_lowercase_names` | ☑ |
| Copy stop-clock (offense / defense) | mutated src | exit 0; bits copied | `test_cli_copies_stop_clock_offense` / `_defense` | ☑ |
| Copy sub-percent / field-goal-range | mutated src | exit 0; field copied | `test_cli_copies_sub_percent` / `_field_goal_range` | ☑ |
| Goal-line + stop-clock combined | mutated src | exit 0; both applied | `test_cli_copies_goal_line_and_stop_clock_combined` | ☑ |
| Updated line + summary | mutated src | "updated (stop-clock)"; footer | `test_cli_prints_updated_line_and_summary` | ☑ |

## no backups / bulk / failures
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No backup written or reported | mutated src | no `.bak`; no backup note | `test_cli_writes_no_backup` | ☑ |
| `--no-backup` removed | option | exit 2; "No such option" | `test_cli_no_backup_option_removed` | ☑ |
| Directory top-level / `-r` | dir | exit 0; 2 processed | `test_cli_directory_top_level_only` / `test_cli_directory_recursive` | ☑ |
| Offense source skips defense targets | dir mix | wrong side untouched | `test_cli_offense_source_skips_defense_targets` | ☑ |
| Single wrong-side target skipped | DEF1 target | exit 0; 0 processed; untouched | `test_cli_single_wrong_side_target_skipped` | ☑ |
| Continues past failed file | dir + bad | exit 1; 1 updated, 1 failed | `test_cli_continues_past_failed_file` | ☑ |
| Missing source / target | tmp | exit 1; target untouched | `test_cli_missing_source_exit_1` / `test_cli_missing_target_exit_1` | ☑ |

---

# `athc check-ppp`

In [test_check_ppp.py](test_check_ppp.py). Same real `.prf` / `.pln` / pool as `profile check` and `gameplan check`; every rule comes from a tmp league folder (`league` / `full_league` fixtures), since check-ppp has no options. Reports are compared to the existing `profile check` / `gameplan check` goldens in `expected/` (path normalized). Exit 0 clean / 1 findings / 2 error.

## arguments
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No file | — | usage error, exit 2 | `test_cli_requires_a_file` | ☑ |
| Third file | 3 files | usage error, exit 2 | `test_cli_rejects_a_third_file` | ☑ |

## one file
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Profile only = `profile check` | data | exit 1; golden + summary | `test_cli_profile_only_matches_profile_check` `[P]` | ☑ |
| Profile only clean (mocked) | data | exit 0; OK line | `test_cli_profile_only_clean_exit_0` | ☑ |
| Profile only needs no gameplan config | league w/o play_path or gameplan rules | exit 1 | `test_cli_profile_only_needs_no_gameplan_config` | ☑ |
| Gameplan only = `gameplan check` | data | exit 1; golden + summary | `test_cli_gameplan_only_matches_gameplan_check` `[P]` | ☑ |
| Gameplan only clean (mocked) | data | exit 0; OK line | `test_cli_gameplan_only_clean_exit_0` | ☑ |
| Gameplan only needs no profile rules | league w/o profile rules | exit 1 | `test_cli_gameplan_only_needs_no_profile_rules` | ☑ |

## both files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Both = `profile check --gameplan` + `gameplan check` (both settings on) | OFF1 + offense.pln / DEF1 + defense.pln | exit 1; both goldens + one summary | `test_cli_both_matches_existing_reports` `[P]` | ☑ |
| Unused gameplan categories are info | DEF1 + defense.pln, unused-categories setting off | exit 1; 1 `gameplan:` line, 4 `gameplan info:` lines not counted | `test_cli_unused_gameplan_categories_are_info` | ☑ |
| Order does not matter | gameplan first | same stdout | `test_cli_file_order_does_not_matter` | ☑ |
| Clean both (mocked) | clean profile, info mocked | exit 0; two OK lines | `test_cli_both_clean_exit_0` | ☑ |
| Unused gameplan categories alone | clean profile, flags off, gameplan mocked | exit 0; 10 `gameplan info:` lines | `test_cli_unused_gameplan_categories_alone_exit_0` | ☑ |
| Cross-check follows the league settings | each setting combination | missing categories count only when required; unused ones count when required, else 4 info lines | `test_cli_cross_check_follows_league_settings` `[P]` | ☑ |
| Side mismatch, both ways | OFF1 + defense.pln / DEF1 + offense.pln | exit 2; mismatch line only, no checks, no summary | `test_cli_side_mismatch_stops_the_checks` `[P]` | ☑ |

## input and file errors
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing file | tmp | exit 2; "path does not exist"; no stdout | `test_cli_missing_file` | ☑ |
| Every input error reported | missing + `.txt` | both logged | `test_cli_reports_every_input_error` | ☑ |
| Wrong extension | `.txt` | exit 2; "not a .prf or .pln file" | `test_cli_wrong_extension` | ☑ |
| Directory | tmp dir | exit 2; "not a file" | `test_cli_directory_is_not_a_file` | ☑ |
| Extension case-insensitive | `.PRF` + `.PLN` | exit 1 | `test_cli_extension_is_case_insensitive` | ☑ |
| Second file of a kind | 2 `.prf` / 2 `.pln` | exit 2; first still checked | `test_cli_second_file_of_a_kind_is_an_error` `[P]` | ☑ |
| Continues past bad input | OFF1 + `.txt` | exit 2; OFF1 golden | `test_cli_continues_past_bad_input` | ☑ |
| Malformed `.prf` / `.pln` | tmp | exit 2; ERROR line | `test_cli_malformed_file` `[P]` | ☑ |
| File of the other kind | profile as `.pln`, gameplan as `.prf` | exit 2; ERROR line | `test_cli_file_of_the_other_kind_is_an_error` `[P]` | ☑ |
| Bad profile, gameplan still checked | tmp + data | exit 2; gameplan golden | `test_cli_bad_profile_still_checks_gameplan` | ☑ |
| Bad gameplan, profile still checked | data + tmp | exit 2; profile golden, no cross-check | `test_cli_bad_gameplan_still_checks_profile` | ☑ |
| Both unreadable | tmp | exit 2; both ERROR lines | `test_cli_both_unreadable_reports_both` | ☑ |

## league / rules config
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No league | empty config | exit 2; "no league selected" logged once | `test_cli_no_league` | ☑ |
| Rules from `[athc] league` | league folder | exit 1 | `test_cli_rules_from_league_set_in_athc_ini` | ☑ |
| No profile / gameplan rules | league folder | exit 2; "no rules configured"; no `--rules` hint; neither file checked | `test_cli_no_profile_rules_in_league` / `test_cli_no_gameplan_rules_in_league` | ☑ |
| Rules error still reports side mismatch | no profile rules; OFF1 + defense.pln | exit 2; mismatch line only, no summary | `test_cli_rules_error_still_reports_side_mismatch` | ☑ |
| Config error still reports mismatch / unreadable file | no league | exit 2; mismatch line / ERROR line; no summary | `test_cli_config_error_still_reports_side_mismatch` / `test_cli_config_error_still_reports_unreadable_file` | ☑ |
| Every config error reported | no rules, bad play path | all three logged | `test_cli_reports_every_config_error` | ☑ |
| No `play_path` / not a directory | league folder | exit 2; no `--play-path` hint | `test_cli_no_play_path` / `test_cli_play_path_not_a_directory` | ☑ |
| Bad rules TOML | profile / gameplan | exit 2; "TOML parse error"; neither file checked | `test_cli_bad_rules_toml` `[P]` | ☑ |
| Bad playpool rules | league folder | exit 2 | `test_cli_bad_playpool_rules` | ☑ |
| Rule lists in `league.ini` | `profile_rules` + `gameplan_rules` | exit 1 | `test_cli_rule_lists_in_league_ini` | ☑ |
| Listed rules file missing | `*_rules` → absent file | exit 2; path named | `test_cli_missing_listed_rules_file` `[P]` | ☑ |
| Malformed `athc.ini` | bad ini | exit 2; athc.ini named | `test_cli_malformed_ini` | ☑ |

## --league and registration
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--league` beats `athc.ini` | two leagues | exit 1 | `test_league_flag_beats_athc_ini` | ☑ |
| `ATHC_LEAGUE` is ignored | env + folder, no `[athc] league` | exit 2; "no league selected" | `test_athc_league_env_is_ignored` | ☑ |
| Unknown league | `--league NOPE` | exit 2; "not found" | `test_league_flag_unknown_folder` | ☑ |
| Listed in `athc --help` | — | "check-ppp" shown | `test_root_help_lists_check_ppp` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc check-ppp` | data + league | exit 1; summary printed | `test_entry_point_subprocess` | ☑ |
| Errors go to stderr | missing file | exit 2; stdout empty; stderr names the file | `test_entry_point_errors_go_to_stderr` | ☑ |

---

# `athc autocontinue`

In [test_autocontinue.py](test_autocontinue.py). Config-driven (`athc.ini [autocontinue]`); the pyautogui watch loop is manual-only, so the CLI is tested with `auto_continue` stubbed (nothing touches the screen). `config_dir` fixture isolates `ATHC_CONFIG_DIR`.

## config / signature
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid INI loads both settings | tmp ini | `Config(0.5, 2.5)` | `test_load_config_reads_valid_ini` | ☑ |
| No file / explicit missing | config_dir / tmp | `ConfigError` | `test_load_config_errors_when_no_config_found` / `..._explicit_path_missing` | ☑ |
| Explicit path works w/o default | tmp ini | loads | `test_load_config_succeeds_with_explicit_path_when_no_default` | ☑ |
| Missing setting / bad value / missing section | tmp ini | `ConfigError` | `test_load_config_errors_on_missing_setting` / `..._invalid_value` / `..._missing_section` | ☑ |
| `hot_corner`: missing → on / parses bools / bad value | tmp ini | enabled / parsed / `ConfigError` | `test_hot_corner_defaults_enabled_when_missing` / `..._parses_boolean` `[P]` / `..._invalid_value_errors` | ☑ |
| Signature: missing / tuple / stable / changes / config-dir | tmp / config_dir | per change-detection | `test_signature_*` | ☑ |

## CLI
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--help` | — | exit 0; "Continue" | `test_cli_help_lists_continue` | ☑ |
| No config / explicit missing | config_dir / tmp | exit 1 | `test_cli_no_config_found` / `test_cli_explicit_missing_config` | ☑ |
| Runs, passes config path (stubbed) | tmp ini | exit 0; path forwarded | `test_cli_runs_with_config` | ☑ |
| `--hot-corner/--no-hot-corner` forwarded (else None) | tmp ini | value passed to core | `test_cli_forwards_hot_corner_override` `[P]` | ☑ |
| Ctrl-C exits clean (stubbed) | tmp ini | exit 0 | `test_cli_keyboard_interrupt_exits_clean` | ☑ |
| Missing dependency (pyautogui) | `sys.modules` stub | exit 2; names module | `test_cli_missing_dependency_exits_2` | ☑ |

---

# `athc convert-pdb`

In [test_convert_pdb.py](test_convert_pdb.py). Input: real `data/2045-2047.pdb`; a selected league with no rules whose `play_path` is an empty `tmp_path` folder, so the workbook builds with populated Tendencies and empty play sheets — full workbook content is covered by `tests/unit/pdbtoexcel/test_workbook_creation.py`. Output read back with openpyxl. Exit 0 ok / 1 input or I/O error / 2 usage.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing second arg | one arg | usage error, exit 2 | `test_requires_both_args` | ☑ |
| Bad pdb / output extension | args | exit 2 | `test_bad_extension_exit_2` `[P]` | ☑ |
| Bad `.pln` extension | `-o plan.txt` | exit 2 | `test_bad_pln_extension_exit_2` | ☑ |
| Removed options rejected | `--play-path`, `--playpool-rules`, `--skip-totals` | exit 2; "No such option" | `test_removed_options_are_rejected` `[P]` | ☑ |
| Missing PDB file | tmp | exit 1; "file not found" | `test_missing_pdb_exit_1` | ☑ |
| Play path not a directory | league `play_path` is a file | exit 1; "play path is not a directory" | `test_play_path_not_a_directory_exit_1` | ☑ |
| Invalid PDB content | tmp | exit 1 | `test_invalid_pdb_content_exit_1` | ☑ |
| Produces `.xlsx` + sheets + tendencies | data + dir | exit 0; 5 sheets; 23x16 tendency rows | `test_produces_xlsx_with_sheets` | ☑ |
| Produces `.xlsm` | data + dir | exit 0; file written | `test_produces_xlsm` | ☑ |
| `--skip-calcs` | data + dir | exit 0 | `test_skip_calcs` | ☑ |
| Real subprocess `athc convert-pdb` | data + dir | exit 0; file written | `test_entry_point_subprocess` | ☑ |

---

# `athc generate-schedule`

In [test_generate_schedule.py](test_generate_schedule.py). Slow (a full solve per league) → `pytest -m slow`; not run by default. One test parametrized over two test leagues — `divisions` (2026) and `conferences` (2029). For each it installs committed, test-owned inputs into the config dir as `leagues/<league>/` — `data/<league>.<season>.ini` as `standings/<season>.league.ini` and the frozen `data/<league>.scheduler.toml` as `rules/scheduler.toml` — then runs the scheduler end-to-end via the CLI (`athc generate-schedule --league <league>`) at a fixed seed (no `--time-limit`; the rules file drives the solve). **Golden regression**: validates the produced schedule against every rule that applies to that league (`schedule_validation.py`, the one validator), cross-checks that the `.html` schedule encodes the same games as the `.txt`, recomputes the report's ranks/SOS, then asserts the three output files byte-match the league's goldens in `expected/` (`schedule_<season>.*`; report run-info fields normalized). Depends on the fixed `solver_workers` reproducibility contract. Regenerate both golden sets with `python -m tests.integration.test_generate_schedule --bless`.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Schedule follows every rule + matches golden, per league | `leagues/<league>/standings/<season>.league.ini`; `--league`, `--season --seed` | exit 0; all rules pass; 3 files byte-equal to that league's `expected/` goldens | `test_generate_schedule_matches_golden[divisions]` / `[conferences]` | ☑ |

---

# `athc.config` — league resolution (shared)

In [test_config.py](test_config.py). Direct tests of `load_league_config()` / `load_league()`, the shared resolver every `--league` tool calls. Reads an isolated `athc.ini` and `leagues/<NAME>/league.ini` (the `config_dir` / `make_league` fixtures) → integration tier, not unit. A league is a folder under `leagues/`; `[athc] league` names the default. `gameplan` / `profile` also exercise resolution through their CLIs.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Explicit `--league` arg | `leagues/<NAME>/league.ini` | `[league]` dict | `test_resolves_explicit_league_arg` | ☑ |
| From `[athc] league` | key + folder | `[league]` dict | `test_resolves_from_configured_league` | ☑ |
| `LeagueConfig` name / dir / values | folder | as on disk; missing `league.ini` → `{}` | `test_league_config_names_folder` / `test_missing_league_ini_gives_empty_values` | ☑ |
| Relative paths in `league.ini` | `play_path = plays` | resolved against the league folder | `test_path_resolves_relative_against_league_dir` | ☑ |
| Fixed rules file / rule list | `rules/gameplan.toml`, `gameplan_rules` | fixed file when present, else `()`; list replaces it in order | `test_rules_file_only_when_present` / `test_rule_files_*` | ☑ |
| None resolvable → lists folders | two folders | `LeagueError`; names `athc config set league`; "Available: <both names, sorted>" | `test_no_league_resolvable_lists_available` / `test_no_league_and_no_folders` | ☑ |
| Unknown league name | ask missing | `LeagueError` "not found"; lists folders | `test_unknown_league_errors` | ☑ |
| Blank `league =` | key empty | "no league selected" | `test_empty_league_key_is_no_league` | ☑ |
| Path segments in a name (`..`, `a\b`) | bad names | `LeagueError` "not found" | `test_league_dir_rejects_path_segments` `[P]` | ☑ |
| Blank name (`""`, `"   "`) | blank | `LeagueError` "not found" (never the `leagues/` folder itself) | `test_league_dir_rejects_blank_names` `[P]` | ☑ |
| `resolve_league()` returns the name | arg / key; none; unknown | name; `LeagueError` | `test_resolve_league_returns_the_explicit_name` / `test_resolve_league_falls_back_to_configured` / `test_resolve_league_errors_*` | ☑ |
| Blank `--league` arg | `"   "` + `[athc] league` | configured league used | `test_resolve_league_blank_arg_is_no_arg` | ☑ |
| Malformed `athc.ini` / `league.ini` | bad INI | `ConfigFileError` names the file | `test_malformed_athc_ini_errors` / `test_malformed_league_ini_errors` | ☑ |
| `%` in `league.ini` | `%LOCALAPPDATA%` value | `ConfigFileError` names the file | `test_percent_in_league_ini_is_config_file_error` | ☑ |
| `%(key)s` interpolation | inside `league.ini` | resolved | `test_interpolation_within_league_ini` | ☑ |

## `--league` (per command)

In [test_cli_root.py](test_cli_root.py). `--league` is an option on each league-aware command (the shared `league_option`), not on the root group.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Root `--help` has no `--league` | `athc --help` | exit 0; `--league` absent | `test_root_help_has_no_league` | ☑ |
| Root rejects `--league` | `athc --league <NAME> profile check` | exit 2; "No such option" | `test_root_rejects_league` | ☑ |
| Every league-aware command takes `--league` | `--help` per command | `--league name` shown | `test_league_commands_take_league` `[P]` | ☑ |
| `-h` on every command and group | `-h` per command | exit 0; "Usage:" | `test_short_help_option_on_every_command` `[P]` | ☑ |
| Usage line lists each option | `-h` on the root, a group and several commands | exact usage line | `test_usage_lists_each_option` `[P]` | ☑ |
| Long usage wraps between options | `convert-pdb -h` | several lines; no option split | `test_long_usage_wraps_between_options` | ☑ |
| Help uses lowercase names | `--help` on `config set`, `convert-pdb`, `gameplan check`, `find-play`, `replace-play`, `set-normals`, `set-specials`, `generate-schedule`, `profile check`, `profile diff`, `check-ppp` | lowercase names; no capitals | `test_help_uses_lowercase_names` `[P]` | ☑ |
| Each command passes `--league` on | `--league NOPE` per command | non-zero; "league 'NOPE' not found" | `test_league_flag_reaches_the_command` `[P]` | ☑ |
| `--league` after the command reaches `profile check` | two leagues | exit 1 (the other league's rules used) | `test_league_flag_picks_profile_rules` | ☑ |
| `ATHC_LEAGUE` is ignored | env set, no `[athc] league` | exit 2; "no league selected" | `test_root_ignores_athc_league_env` | ☑ |

## `athc config set`

In [test_config_set.py](test_config_set.py). `set_config_value` rewrites `athc.ini` through ConfigUpdater; the CLI validates the key and the league folder.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Update keeps comments | commented ini | value changed; every comment kept | `test_set_updates_value_and_keeps_comments` | ☑ |
| Missing key / section / file | partial or no ini | created in place | `test_set_adds_missing_key` / `test_set_adds_missing_section` / `test_set_creates_missing_file` | ☑ |
| CLI sets league | folder exists | exit 0; "Set league = <NAME>" | `test_cli_sets_league` | ☑ |
| CLI unknown league | no folder | exit 2; "not found"; file untouched | `test_cli_rejects_unknown_league` | ☑ |
| CLI blank league | `""` | exit 2; "not found"; file untouched | `test_cli_rejects_blank_league` | ☑ |
| CLI malformed `athc.ini` | `[athc` broken | exit 2; names athc.ini; no traceback; file left as written | `test_cli_malformed_ini_is_clean_error` | ☑ |
| CLI unknown key | `colour` | exit 2; names known keys | `test_cli_rejects_unknown_key` | ☑ |
| Help / group listing | `--help` | lists `league` / `set` | `test_cli_help_lists_known_keys` / `test_group_lists_set` | ☑ |

## shipped `config/release/`

`ATHC_CONFIG_DIR` is pointed at `config/release/` itself (the `release_config_dir` fixture), so `athc.ini` and every `leagues/<NAME>/` are read exactly as installed. Every league folder runs the same tests: each loader must load, and every rule file it resolves must exist.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| At least one league ships | config/release/ | league folders found | `test_release_ships_leagues` | ☑ |
| `[athc] league` names a shipped league | config/release/ | loads | `test_release_selected_league_loads` | ☑ |
| Every league | config/release/ | play_path set; standings folder present | `test_release_league_loads` `[P]` | ☑ |
| `[autocontinue]` | config/release/ | loads | `test_release_autocontinue_section_loads` | ☑ |
| gameplan, every league | config/release/ | loads; playpool rules and rule files exist | `test_release_gameplan_config_loads` `[P]` | ☑ |
| profile, every league | config/release/ | loads; rule files exist | `test_release_profile_config_loads` `[P]` | ☑ |
| convert-pdb, every league | config/release/ | loads; playpool rules exist; a `play_path` override alone gets the league's file | `test_release_convert_pdb_config_loads` `[P]` | ☑ |
| `[convert-pdb]` defaults | config/release/ | spelled out in `athc.ini` | `test_release_convert_pdb_defaults` | ☑ |
| scheduler, every league | config/release/ | tunables load; every standings file resolves | `test_release_scheduler_files_load` `[P]` | ☑ |
| `config/dev/` mirrors `config/release/` | both | same `athc.ini`, `league.ini`, rules and standings files | `test_dev_mirrors_release_layout` | ☑ |

---

# `athc config`

In [test_config.py](test_config.py) (alongside the resolver tests above). Thin commands over the settings file; app / Explorer launches are mocked.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Group lists subcommands | `--help` | path / edit / reveal listed | `test_group_lists_subcommands` | ☑ |
| `path` prints the file path | config_dir | full `athc.ini` path | `test_path_prints_config_file` | ☑ |
| `reveal` selects the file | existing ini | `launch(<athc.ini>, locate=True)` | `test_reveal_selects_existing_file` | ☑ |
| `reveal` opens the folder if absent | config_dir | `launch(<dir>)` | `test_reveal_opens_folder_when_absent` | ☑ |
| `edit` opens the default app | config_dir | file created; `launch(<athc.ini>)` | `test_edit_opens_associated_app` | ☑ |
| `edit` ignores `$VISUAL`/`$EDITOR` | both set | `launch(<athc.ini>)`; no `edit` | `test_edit_ignores_editor_env` | ☑ |
| `edit` keeps existing file | existing ini | content unchanged | `test_edit_preserves_existing_file` | ☑ |
