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
| No PATH given | — | usage error, exit 2 | `test_cli_requires_path` | ☑ |
| Violations | data + `--rules` | exit 1; "1 file(s) checked" | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + `--rules` | exit 1; "2 file(s) checked" | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + `--rules` | exit 1; counts | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Clean (mocked) | data + `--rules` | exit 0; "OK" | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp | exit 2; "does not exist" | `test_cli_missing_path` | ☑ |
| Malformed `.prf` | tmp + `--rules` | exit 2; "ERROR" printed | `test_cli_malformed_prf` | ☑ |
| Continues past bad file | tmp + `--rules` | exit 2; both lines printed | `test_cli_continues_past_bad` | ☑ |

## `athc profile check` — rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No rules configured | empty config | exit 2; "no rules configured" | `test_cli_no_rules` | ☑ |
| Rules from `athc.ini` | ini rule_files | exit 1 | `test_cli_rules_from_ini` | ☑ |
| `--rules` overrides ini | ini bogus + `--rules` | exit 1; bogus unused | `test_cli_rules_override_ini` | ☑ |
| `--rules` layering | two files | later overrides earlier | `test_cli_rules_layering` | ☑ |
| Bad rules TOML | `--rules` bad | exit 2; "TOML parse error" | `test_cli_bad_rules_toml` | ☑ |
| Missing rules file (ini / cli) | path | exit 2; path named | `test_cli_missing_rules` `[P]` | ☑ |
| Missing `--config` | path | exit 2; "config file not found" | `test_cli_missing_config` | ☑ |
| Malformed `athc.ini` | bad ini | exit 2 | `test_cli_malformed_ini` | ☑ |

## `athc profile check` — `--gameplan` compatibility
Real `TST-OFF1.prf`/`TST-DEF1.prf` + real `offense.pln`/`defense.pln`; clean `compat_{off,def}_clean.prf` fixtures for the exit-0 path. Goldens in `expected/compat_{offense,defense}.report.txt` (path normalized).
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| check_file offense reports compat | data | head "gameplan issue(s)"; GLR line; count 19 | `test_check_file_gameplan_offense_reports_compat` | ☑ |
| check_file defense reports compat | data | FG/PAT special line; count 8 | `test_check_file_gameplan_defense_reports_compat` | ☑ |
| check_file clean (empty rules) | data | `(0, "... gameplan compatible")` | `test_check_file_gameplan_clean` | ☑ |
| check_file side mismatch (both ways) | data | `(-1, "profile is X but gameplan is Y")` | `test_check_file_gameplan_side_mismatch` / `_defense` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal (path normalized) | `test_check_file_gameplan_matches_golden` `[P]` | ☑ |
| CLI offense / defense | data + `--gameplan` | exit 1; compat line | `test_cli_gameplan_offense_exit_1` / `_defense_exit_1` | ☑ |
| CLI clean | clean + empty rules | exit 0; "gameplan compatible" | `test_cli_gameplan_clean_exit_0` | ☑ |
| CLI side mismatch | data | exit 2; "profile is offense but gameplan is defense" | `test_cli_gameplan_side_mismatch_exit_2` | ☑ |
| CLI mixed sides continues | 2 files, 1 gameplan | exit 2; both lines; "2 file(s) checked" | `test_cli_gameplan_mixed_sides_continues` | ☑ |
| CLI gameplan missing / bad ext / malformed | tmp | exit 2; logged | `test_cli_gameplan_missing_file_exit_2` / `_bad_extension_exit_2` / `_malformed_exit_2` | ☑ |

## `athc profile check` — Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc profile check` | data + `--rules` | exit 1; report printed | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan check`

In [test_gameplan_check.py](test_gameplan_check.py). Inputs: real `data/offense.pln` (O_64_06a) + `data/defense.pln` (D_50_09), the curated `data/plays/` pool both resolve against, and the canonical `release/rules/PNFL.{gameplan,playpool}.toml`. Mirrors the pnfl `gameplan check` suite (collect / check_file / exit codes) and adds golden reports, pinned counts, pool build, and league/config resolution.

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
| Violations | data + flags | exit 1; "1 file(s) checked" | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + flags | exit 1; "2 file(s) checked" | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + flags | exit 1; counts | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Clean (mocked) | data + flags | exit 0; "OK" | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp + flags | exit 2; "does not exist" | `test_cli_missing_path` | ☑ |
| Malformed `.pln` | tmp + flags | exit 2; "ERROR" printed | `test_cli_malformed_pln` | ☑ |
| Continues past bad file | tmp + flags | exit 2; both lines printed | `test_cli_continues_past_bad` | ☑ |

## pool / rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing play path | bad `--play-path` | exit 2; "not a directory" | `test_cli_missing_play_path` | ☑ |
| Bad playpool rules TOML | bad `--playpool-rules` | exit 2 | `test_cli_bad_playpool_rules` | ☑ |
| No rules configured | path flags only | exit 2; "no rules configured" | `test_cli_no_rules` | ☑ |
| Bad rules TOML | bad `--rules` | exit 2; "TOML parse error" | `test_cli_bad_rules_toml` | ☑ |
| No league resolvable | no flags, no config | exit 2; "league" | `test_cli_no_league` | ☑ |
| Resolves from league `athc.ini` | ini league + `[gameplan]` | exit 1 | `test_cli_resolves_from_league_ini` | ☑ |
| Missing `--config` | path | exit 2; "config file not found" | `test_cli_missing_config` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc gameplan check` | data + flags | exit 1; report printed | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan list-normals` / `list-specials`

In [test_gameplan_list.py](test_gameplan_list.py). Reads `data/offense.pln` / `data/defense.pln` (no pool/rules/config); stdout compared to `expected/{offense,defense}_normals_{slot,name}.txt` and `expected/{offense,defense}_specials.txt`. File mode prepends a `:: <source>` header line.

## list-normals
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error, exit 2 | `test_normals_requires_path` | ☑ |
| Invalid `--sort` | data | usage error, exit 2 | `test_normals_rejects_invalid_sort` | ☑ |
| Stdout, slot order | data | 64 lines match fixture | `test_normals_stdout_offense_slot` / `..._defense_slot` | ☑ |
| Stdout, `--sort name` | data | sorted, blanks dropped | `test_normals_stdout_sort_name` | ☑ |
| File: header + plays | data + out | line 1 `::`, rest match | `test_normals_file_writes_header_and_plays` | ☑ |
| File: `--sort name` | data + out | rest match name fixture | `test_normals_file_sort_name` | ☑ |
| Refuse overwrite (no `-f`) | existing out | exit 1; file untouched | `test_normals_refuses_overwrite_without_force` | ☑ |
| Overwrite with `--force` | existing out | exit 0; rewritten | `test_normals_overwrites_with_force` | ☑ |
| Logs count + path | data + out | "Wrote 64 normal play(s)" | `test_normals_file_logs_count` | ☑ |
| Missing gameplan | tmp | exit 1; error logged | `test_normals_missing_gameplan` | ☑ |
| Malformed, file mode | tmp | exit 1; no file written | `test_normals_malformed_file_mode_no_output` | ☑ |

## list-specials
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error, exit 2 | `test_specials_requires_path` | ☑ |
| Stdout (source order) | data | lines match fixture | `test_specials_stdout_offense` / `..._defense` | ☑ |
| File: header + plays | data + out | line 1 `::`, rest match | `test_specials_file_writes_header_and_plays` | ☑ |
| Refuse overwrite (no `-f`) | existing out | exit 1; file untouched | `test_specials_refuses_overwrite_without_force` | ☑ |
| Logs count + path | data + out | "Wrote 6 special play(s)" | `test_specials_file_logs_count` | ☑ |
| Malformed, file mode | tmp | exit 1; no file written | `test_specials_malformed_file_mode_no_output` | ☑ |

---

# `athc gameplan find-play`

In [test_gameplan_find_play.py](test_gameplan_find_play.py). Pure helpers (`find_in_gameplan`, `format_hit_line`, `_join_slots`) on constructed gameplans; CLI tier on real `data/offense.pln` / `data/defense.pln` (`OR45RL01` @ 1-1 = Run Left, `SFFGXPAT` = Field Goal/PAT). No pool/rules/config.

## helpers (constructed gameplans)
| Case | Expected | Test | Status |
|---|---|---|---|
| English slot join (1 / 2 / 3+) | `A` / `A and B` / `A, B, and C` | `test_join_slots_*` | ☑ |
| No match / normal / multiple / case-insensitive | correct `(normal, special)` hits | `test_find_*` | ☑ |
| Custom special hit (1-based slot) | special hit | `test_find_matches_custom_special` | ☑ |
| Skips stock-special + clock slots | no hit | `test_find_skips_stock_special_slots` / `..._clock_slots` | ☑ |
| Hit line: 1 / 2 / 3 slots, category | composed line | `test_format_normal_*` | ☑ |
| Masks user_category bits 7-6 | category from low bits | `test_format_masks_high_user_category_bits` | ☑ |
| Offense vs defense table; special category | right table | `test_format_defense_normal_*` / `..._special_*` | ☑ |
| Unknown category | parens omitted | `test_format_unknown_category_omits_parens` | ☑ |

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No args / single arg | — | usage error, exit 2 | `test_cli_requires_args` / `test_cli_single_arg_is_rejected` | ☑ |
| Single file hit (normal / special) | data | slot + category; no summary | `test_cli_single_file_hit` / `test_cli_finds_custom_special` | ☑ |
| Single file miss | data | exit 1; "not found" | `test_cli_single_file_miss_exit_1` | ☑ |
| Case-insensitive | data | hit | `test_cli_single_file_case_insensitive` | ☑ |
| Multiple plays, all hit / one miss | data | exit 0 / 1 | `test_cli_multiple_plays_all_hit` / `test_cli_one_play_misses_exit_1` | ☑ |
| Directory: only matching file + summary | tmp | exit 0; footer | `test_cli_directory_hit_only_matching_file` | ☑ |
| Directory: no hits silent / `--verbose` | tmp | summary only / misses shown | `test_cli_directory_no_hits_*` / `..._verbose_*` | ☑ |
| Directory: instance/file counts | tmp | "Found N in M" | `test_cli_directory_summary_counts_multiple_hits` / `..._per_play_summary` | ☑ |
| Recursive subdir | tmp | exit 0; found | `test_cli_recursive_finds_in_subdir` | ☑ |
| Missing path / malformed `.pln` | tmp | exit 2 | `test_cli_missing_path_exit_2` / `test_cli_malformed_pln_exit_2` | ☑ |

---

# `athc gameplan set-normals`

In [test_gameplan_set_normals.py](test_gameplan_set_normals.py). Operates on a tmp copy of `data/offense.pln` with the curated pool (`--play-path` + `--playpool-rules`). Edits in place; `check` validates. Exit 0 = updated, 2 = error (nothing written).

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs gameplan / input-or-stdin / not both | — | usage error, exit 2 | `test_requires_gameplan` / `test_requires_input_or_stdin` / `test_rejects_input_and_stdin_together` | ☑ |
| Writes normals from file | tmp + flags | slot 0 set, rest cleared | `test_writes_from_file` | ☑ |
| Backup by default / `--no-backup` | tmp | one `.bak` = original / none | `test_creates_backup_by_default` / `test_no_backup_skips_backup` | ☑ |
| Logs "Updated" + "Backup:" | tmp | INFO line | `test_logs_backup_path` | ☑ |
| Skips `::` / strips ` ::` / `name::` fails | tmp | parsed / parsed / exit 2 | `test_skips_comment_lines` / `test_strips_inline_comments` / `test_inline_comment_requires_space` | ☑ |
| `-q` still updates; `--stdin` | tmp | exit 0; set | `test_quiet_still_updates` / `test_reads_from_stdin` | ☑ |
| Special-teams play rejected (untouched) | tmp | exit 2; "set-specials"; no `.bak` | `test_rejects_special_teams_play` | ☑ |
| Missing play aborts (untouched) | tmp | exit 2; no `.bak` | `test_missing_play_aborts` | ☑ |
| >64 plays / missing `.pln` / bad play-path | tmp | exit 2 | `test_too_many_plays_rejected` / `test_missing_pln` / `test_invalid_play_path` | ☑ |

# `athc gameplan set-specials`

In [test_gameplan_set_specials.py](test_gameplan_set_specials.py). Tmp copies of `offense.pln` / `defense.pln`. Merge semantics; bulk over file/dir/tree; wrong-side files skipped by size parity. Exit 0 = all updated, 1 = some failed, 2 = setup error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs target / input-or-stdin / not both / no `-q` | — | usage error, exit 2 | `test_requires_target` / `test_requires_input_or_stdin` / `test_rejects_input_and_stdin_together` / `test_no_quiet_option` | ☑ |
| Writes special from file; merge preserves others | tmp + flags | slot 1 set; rest intact | `test_writes_special_from_file` / `test_merge_preserves_other_categories` | ☑ |
| Backup by default / `--no-backup` | tmp | one `.bak` / none | `test_creates_backup_by_default` / `test_no_backup_skips_backup` | ☑ |
| Comments; `--stdin` | tmp | parsed; set | `test_skips_and_strips_comments` / `test_reads_from_stdin` | ☑ |
| Normal play / duplicate / >10 rejected (untouched) | tmp | exit 2 | `test_rejects_normal_play` / `test_rejects_duplicate_play` / `test_too_many_plays_rejected` | ☑ |
| Missing target | tmp | exit 2 | `test_missing_target` | ☑ |
| Directory top-level / recursive | tmp | "2 file(s) processed" | `test_directory_top_level_only` / `test_directory_recursive` | ☑ |
| Offense input skips defense files | tmp | "1 file(s) processed"; def untouched | `test_offense_input_skips_defense_files` | ☑ |
| Continues past a failed file | tmp | exit 1; 1 updated, 1 failed | `test_continues_past_failed_file` | ☑ |

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

In [test_profile_copy.py](test_profile_copy.py). Inputs: real `TST-OFF1/DEF1.prf` plus per-test mutated sources written to `tmp_path`. No rules (validate afterward with `check`). Mirrors the pnfl copy suite (`ProfileWriter` unit tests live in `tests/unit/profile/test_writer.py`).

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Usage errors (no SRC / no TARGET / no flag) | args | exit 2 | `test_cli_usage_errors_exit_2` `[P]` | ☑ |
| Copy stop-clock (offense / defense) | mutated src | exit 0; bits copied | `test_cli_copies_stop_clock_offense` / `_defense` | ☑ |
| Copy sub-percent / field-goal-range | mutated src | exit 0; field copied | `test_cli_copies_sub_percent` / `_field_goal_range` | ☑ |
| Goal-line + stop-clock combined | mutated src | exit 0; both applied | `test_cli_copies_goal_line_and_stop_clock_combined` | ☑ |
| Updated line + summary | mutated src | "updated (stop-clock)"; footer | `test_cli_prints_updated_line_and_summary` | ☑ |
| Reports backup name | mutated src | "backup target.prf.…" | `test_cli_reports_backup_name` | ☑ |

## backup / bulk / failures
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Backup by default / `--no-backup` | mutated src | `.bak` == original / none | `test_cli_creates_backup_by_default` / `test_cli_no_backup_skips_backup` | ☑ |
| Directory top-level / `-r` | dir | exit 0; 2 processed | `test_cli_directory_top_level_only` / `test_cli_directory_recursive` | ☑ |
| Offense source skips defense targets | dir mix | wrong side untouched | `test_cli_offense_source_skips_defense_targets` | ☑ |
| Single wrong-side target skipped | DEF1 target | exit 0; 0 processed; untouched | `test_cli_single_wrong_side_target_skipped` | ☑ |
| Continues past failed file | dir + bad | exit 1; 1 updated, 1 failed | `test_cli_continues_past_failed_file` | ☑ |
| Missing source / target | tmp | exit 1; target untouched | `test_cli_missing_source_exit_1` / `test_cli_missing_target_exit_1` | ☑ |

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
| Release `athc.ini` is valid | release | loads `(0.0, 1.0)` | `test_release_example_config_loads` | ☑ |
| Signature: missing / tuple / stable / changes / config-dir | tmp / config_dir | per change-detection | `test_signature_*` | ☑ |

## CLI
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--help` | — | exit 0; "Continue" | `test_cli_help_lists_continue` | ☑ |
| No config / explicit missing | config_dir / tmp | exit 1 | `test_cli_no_config_found` / `test_cli_explicit_missing_config` | ☑ |
| Runs, passes config path (stubbed) | tmp ini | exit 0; path forwarded | `test_cli_runs_with_config` | ☑ |
| Ctrl-C exits clean (stubbed) | tmp ini | exit 0 | `test_cli_keyboard_interrupt_exits_clean` | ☑ |

---

# `athc convert-pdb`

In [test_convert_pdb.py](test_convert_pdb.py). Input: real `data/2045-2047.pdb`; `--play-path` is an (often empty) `tmp_path`, so the workbook builds with populated Tendencies and empty play sheets — full workbook content is covered by `tests/unit/pdbtoexcel/test_workbook_creation.py`. Output read back with openpyxl. Exit 0 ok / 1 input or I/O error / 2 usage.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing second arg | one arg | usage error, exit 2 | `test_requires_both_args` | ☑ |
| Bad pdb / output extension | args | exit 2 | `test_bad_extension_exit_2` `[P]` | ☑ |
| Bad `.pln` extension | `-o plan.txt` | exit 2 | `test_bad_pln_extension_exit_2` | ☑ |
| Missing PDB file | tmp | exit 1; "file not found" | `test_missing_pdb_exit_1` | ☑ |
| Play path not a directory | file | exit 1; "play path is not a directory" | `test_play_path_not_a_directory_exit_1` | ☑ |
| Invalid PDB content | tmp | exit 1 | `test_invalid_pdb_content_exit_1` | ☑ |
| Produces `.xlsx` + sheets + tendencies | data + dir | exit 0; 5 sheets; 23x16 tendency rows | `test_produces_xlsx_with_sheets` | ☑ |
| Produces `.xlsm` | data + dir | exit 0; file written | `test_produces_xlsm` | ☑ |
| `--skip-calcs` / `--skip-totals` | data + dir | exit 0 | `test_skip_flags` `[P]` | ☑ |
| Real subprocess `athc convert-pdb` | data + dir | exit 0; file written | `test_entry_point_subprocess` | ☑ |

---

# `athc generate-schedule`

In [test_generate_schedule.py](test_generate_schedule.py). Slow (full solve) → `pytest -m slow`; not run by default. Runs the default `two-phase-rank` scheduler end-to-end via the CLI on the release `league.ini` + `nonconf_history.json`.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| CLI writes schedule + report | release data + flags | exit 0; non-empty `season.txt` + `season-report.txt` | `test_generate_schedule_writes_schedule_and_report` | ☑ |

---

# `athc.config` — league resolution (shared)

In [test_config.py](test_config.py). Direct tests of `load_league()`, the shared resolver every `--league` tool calls. Reads an isolated `athc.ini` (the `config_dir` fixture) → integration tier, not unit. Convention: `[league.NAME]`; bare sections (`[athc]`, `[gameplan]`) are not leagues. `gameplan` / `profile` also exercise resolution through their CLIs.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Explicit `--league` arg | `[league.PNFL]` | section dict | `test_resolves_explicit_league_arg` | ☑ |
| From `ATHC_LEAGUE` env | env + section | section dict | `test_resolves_from_env` | ☑ |
| From `[athc] default_league` | default + section | section dict | `test_resolves_from_default_league` | ☑ |
| Priority arg > env > default | all set | arg wins; env beats default | `test_arg_beats_env` / `test_env_beats_default_league` | ☑ |
| None resolvable → lists leagues | `league.*` + tool section | `LeagueError`; "Configured leagues: PNFL, PCFL" (prefix stripped, tool excluded) | `test_no_league_resolvable_lists_configured` | ☑ |
| Unknown league name | ask missing | `LeagueError` names `[league.PCFL]` | `test_unknown_league_errors` | ☑ |
| Misspelled prefix `[leagu.AFCL]` | typo'd section | no parse error; inert — unlisted, selecting it errors | `test_misspelled_prefix_section_is_inert` | ☑ |
| `[DEFAULT]` cascade + `%(key)s` | DEFAULT + league | PlayPath + RosterPath interpolated | `test_default_cascade_and_interpolation` | ☑ |

---

# `athc config`

In [test_config.py](test_config.py) (alongside the resolver tests above). Three thin commands over the settings file; editor / Explorer launches are mocked.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Group lists subcommands | `--help` | path / edit / reveal listed | `test_group_lists_subcommands` | ☑ |
| `path` prints the file path | config_dir | full `athc.ini` path | `test_path_prints_config_file` | ☑ |
| `reveal` selects the file | existing ini | `launch(<athc.ini>, locate=True)` | `test_reveal_selects_existing_file` | ☑ |
| `reveal` opens the folder if absent | config_dir | `launch(<dir>)` | `test_reveal_opens_folder_when_absent` | ☑ |
| `edit`, no `$EDITOR` → associated app | config_dir | file created; `launch(<athc.ini>)` | `test_edit_no_env_opens_associated_app` | ☑ |
| `edit`, `$EDITOR` set → editor | env set | `edit(filename=…)`; no launch | `test_edit_uses_editor_env` | ☑ |
| `edit` keeps existing file | existing ini | content unchanged | `test_edit_preserves_existing_file` | ☑ |
