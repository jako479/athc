# Integration — Test Matrix

CLI end-to-end cases. Convention in [../../docs/testing-integration.md](../../docs/testing-integration.md).

One row per behavior. `[P]` = parametrized. Input: `data/` real `.prf` + rules; `tmp` = constructed. Exit: 0 done / 1 findings / 2 error / 130 Ctrl-C. Expected names the stream: results, `OK` / `SKIP` lines and tallies on stdout; progress, `WARN` / `FAIL` lines and Click's usage text on stderr. A stream of one line is pinned whole (`== "...\n"`); a substring only picks a line out of many. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/integration` passes.

## `athc profile check` — `collect_files`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Single file | tmp | `[file]`, no errors | `test_collect_single_file` | ☑ |
| Directory, top level only | tmp | top `.prf` only | `test_collect_directory_top_level` | ☑ |
| Directory, recursive | tmp | whole tree | `test_collect_directory_recursive` | ☑ |
| Missing path | tmp | "does not exist" error | `test_collect_missing_path` | ☑ |
| Non-`.prf` file | tmp | "not a .prf file" | `test_collect_non_prf` | ☑ |
| Empty directory | tmp | no files, no errors; warning "No .prf files." | `test_collect_empty_dir_is_a_warning` | ☑ |
| Dedupes repeats | tmp | one entry | `test_collect_dedupes` | ☑ |
| Glob expands / filters / no-match | tmp | matched `.prf` only | `test_collect_glob` `[P]` | ☑ |

## `athc profile check` — `check_file`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense violations format | data | head + indented details; "offense", "FG range" | `test_check_file_offense_format` | ☑ |
| Defense violations format | data | "defense" head | `test_check_file_defense_format` | ☑ |
| Clean (validate mocked) | data | `(0, "<path>: <side>, ...")` | `test_check_file_clean` | ☑ |
| Malformed `.prf` | tmp | raises `InvalidProfileError` naming the file; the loop catches it | `test_check_file_malformed_raises` | ☑ |
| **Pinned counts (real)** | data | OFF1 = 18, DEF1 = 7 | `test_check_file_pinned_counts` `[P]` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal report (path normalized) | `test_check_file_matches_golden` `[P]` | ☑ |

## `athc profile check` — command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No path given | cwd + league | current directory checked; `-r` recurses; empty dir: exit 0, stderr `WARN .: No .prf files.`, stdout the tally | `test_cli_no_path_checks_current_directory` / `test_cli_no_path_recursive` / `test_cli_no_path_empty_directory` | ☑ |
| `--rules` removed | option | exit 2; stderr: Click's "No such option" | `test_cli_rules_option_removed` | ☑ |
| `--gameplan` removed | option | exit 2; stderr: Click's "No such option" | `test_cli_gameplan_option_rejected` | ☑ |
| Violations | data + league | exit 1; stdout: headline, details, "1 file(s) checked" tally | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + league | exit 1; stdout: "2 file(s) checked" tally | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + league | exit 1; stdout tally | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Wildcard PATH | `Off*.prf` in tmp + league | athc expands it: the two matches only; exit 1; "2 file(s) checked" | `test_cli_wildcard_path` | ☑ |
| Clean (mocked) | data + league | exit 0; stdout: `OK   <file>: ...` and the tally | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; stdout: the tally | `test_cli_missing_path` | ☑ |
| Malformed `.prf` | tmp + league | exit 2; stderr: `FAIL <file>: ...` | `test_cli_malformed_prf` | ☑ |
| Continues past bad file | tmp + league | exit 2; stderr: `FAIL` for the bad file; stdout: the good file's line and the tally | `test_cli_continues_past_bad` | ☑ |
| Help screens | `--help` on `profile check` / `profile`; bare `profile` | stdout == the plan's screen (78 columns); bare group: its help on stderr, exit 2 | `test_help_screen` / `test_group_help_screen` / `test_bare_group_shows_its_help_on_stderr` | ☑ |
| A profile key | `off2`, `team = 'Denver'` | that file checked; "1 file(s) checked" | `test_cli_key_checks_that_file` | ☑ |
| Two keys | `off1 def1` | exit 1; both files, in order; "2 file(s) checked, 2 with violations, 0 failed" | `test_cli_two_keys` | ☑ |
| Key among paths | DEF1, `off1`, OFF1 | reports in PATH order | `test_cli_key_keeps_path_order` | ☑ |
| Missing key file | `off2 off1`, DEN-OFF2 deleted | exit 2; stderr: `FAIL <file>: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .prf file.`; off1 checked; "1 failed" | `test_cli_missing_key_file_counts_failed` | ☑ |
| No PATH, `team` set | cwd + league | the current folder, not the team's files | `test_cli_no_path_with_team_set` | ☑ |
| `--team` with a key | `def1 --team Raiders` | Las Vegas's file | `test_cli_team_option_with_a_key` | ☑ |
| `--team` with no PATH | `--team Denver` | exit 2; stderr ends `Error: --team requires a profile key (off1, def1, off2 or def2).` | `test_cli_team_option_without_path` | ☑ |

The "league" input is a selected league folder whose `profile.toml` is the test rules file. The key rows use `build_teams` from [conftest.py](conftest.py): Denver and Las Vegas with their four profiles at their league locations, run from an empty folder.

## `athc profile check` — rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No league configured | empty config | exit 2; stderr: `FAIL League is not set ...` | `test_cli_no_league` | ☑ |
| League folder without rules | `leagues/<NAME>/` | exit 2; stderr: `FAIL No rules configured ...` | `test_cli_no_rules_in_league_folder` | ☑ |
| Rules from the league folder | `leagues/<NAME>/profile.toml` + `[athc] league` | exit 1 | `test_cli_rules_from_league_folder` | ☑ |
| `--league` picks the folder | two leagues | exit 1 | `test_cli_league_flag_picks_folder` | ☑ |
| `profile_rules` list | relative to the league folder | exit 1 | `test_cli_profile_rules_list_relative_to_league_folder` | ☑ |
| `profile_rules` layering | base + overlay | later overrides earlier | `test_cli_rules_layering` | ☑ |
| Bad rules TOML | league `profile.toml` bad | exit 2; stderr: `FAIL <file>: Not valid TOML: ...` | `test_cli_bad_rules_toml` | ☑ |
| Missing listed rules file | `profile_rules` → absent file | exit 2; stderr: `FAIL` naming the path | `test_cli_missing_rules` | ☑ |
| Malformed `athc.ini` | bad ini | exit 2; stderr: `FAIL` naming athc.ini | `test_cli_malformed_ini` | ☑ |

## `athc profile check` — Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc profile check` | data + league | exit 1; report on stdout | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan check`

In [test_gameplan_check.py](test_gameplan_check.py). Inputs: real `data/offense.pln` (O_64_06a) + `data/defense.pln` (D_50_09), the curated `data/plays/` pool both resolve against, and the test rules `data/gameplan_rules.toml`. Covers collect / check_file / exit codes, golden reports, pinned counts, pool build, league/config resolution, and the game plan keys.

## `collect_files`
Same eight cases as profile (single / top level / recursive / missing / non-`.pln` / empty / dedupes / glob), with `.pln`, plus a wildcard with no match: warning `Off*.pln: No .pln files match.` (`test_collect_glob_without_a_match_is_a_warning`).

## `check_file`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offense violations format | data | head + indented details; "offense", "normal" | `test_check_file_offense_format` | ☑ |
| Defense violations format | data | "defense" head | `test_check_file_defense_format` | ☑ |
| Clean (validate mocked) | data | `(0, "<path>: <side>, ...")` | `test_check_file_clean` | ☑ |
| Malformed `.pln` | tmp | raises `InvalidGamePlanError` naming the file; the loop catches it | `test_check_file_malformed_raises` | ☑ |
| **Pinned counts (real)** | data | offense = 3, defense = 1 | `test_check_file_pinned_counts` `[P]` | ☑ |
| **Golden report (real)** | data ↔ expected | byte-equal report (path normalized) | `test_check_file_matches_golden` `[P]` | ☑ |

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | cwd + league | current directory checked; `-r` recurses; empty dir: exit 0, stderr `WARN .: No .pln files.`, stdout the tally | `test_cli_no_path_checks_current_directory` / `test_cli_no_path_recursive` / `test_cli_no_path_empty_directory` | ☑ |
| Removed options rejected | `--play-path`, `--playpool-rules`, `--rules` | exit 2; stderr: Click's "No such option" | `test_cli_removed_options_are_rejected` `[P]` | ☑ |
| Violations | data + league | exit 1; stdout: headline, details, "1 file(s) checked" tally | `test_cli_violations_exit_1` | ☑ |
| Multiple files | data + league | exit 1; stdout: "2 file(s) checked" tally | `test_cli_multiple_files` | ☑ |
| Directory / `-r` | tmp + league | exit 1; stdout tally | `test_cli_directory` / `test_cli_recursive` | ☑ |
| Wildcard PATH | `Off*.pln` in tmp + league | athc expands it: the two matches only; exit 1; "2 file(s) checked" | `test_cli_wildcard_path` | ☑ |
| Clean (mocked) | data + league | exit 0; stdout: `OK   <file>: ...` and the tally | `test_cli_clean_exit_0` | ☑ |
| Missing path | tmp + league | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; stdout: the tally | `test_cli_missing_path` | ☑ |
| Locked file, batch goes on | two files; the reader raises `PermissionError` for one | exit 2; stderr: `FAIL <file>: Access is denied.`; tally `2 file(s) checked, 1 with violations, 1 failed` | `test_cli_locked_file_is_access_denied_and_the_batch_goes_on` | ☑ |
| Bug in one file, batch goes on | two files; the reader raises `RuntimeError` for one | exit 2; stderr: `FAIL <file>: Unexpected error. See <log> for details.`; the other checked; the log holds the line at `ERROR`, then the traceback | `test_cli_bug_in_one_file_keeps_the_batch_going` | ☑ |
| Malformed `.pln` | tmp + league | exit 2; stderr: `FAIL <file>: ...` | `test_cli_malformed_pln` | ☑ |
| Continues past bad file | tmp + league | exit 2; stderr: `FAIL` for the bad file; stdout: the good file's line and the tally | `test_cli_continues_past_bad` | ☑ |

The "league" input is a selected league folder holding the test pool (`play_path`) and `gameplan.toml`.

## pool / rules / config resolution
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing play path | league `play_path` absent | exit 2; stderr: `FAIL <play path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` | `test_cli_missing_play_path` | ☑ |
| League folder without rules | `--league` + folder | exit 2; stderr: `FAIL No rules configured ...` | `test_cli_no_rules_in_league_folder` | ☑ |
| Rules file with two problems | league `gameplan.toml` with two errors | exit 2; stderr: two `FAIL <gameplan.toml>: ...` lines, each a sentence; both logged | `test_cli_rules_file_with_two_problems_is_two_fail_lines` | ☑ |
| Bad rules TOML | league `gameplan.toml` bad | exit 2; stderr: `FAIL <file>: Not valid TOML: ...` | `test_cli_bad_rules_toml` | ☑ |
| No league resolvable | no config | exit 2; stderr: `FAIL League is not set ...` | `test_cli_no_league` | ☑ |
| Resolves from the league folder | `[athc] league` + `leagues/<NAME>/` | exit 1 | `test_cli_resolves_from_league_folder` | ☑ |
| `gameplan_rules` list | base + overlay | exit 1 | `test_cli_gameplan_rules_list_layers_in_order` | ☑ |
| Listed rules file missing | `gameplan_rules` → absent file | exit 2; stderr: `FAIL` naming the path | `test_cli_missing_listed_rules_file_is_reported` | ☑ |
| Attribute caps apply (attributes from the play files) | league | exit 1; stdout: "timed passes" | `test_cli_attribute_caps_apply` | ☑ |

## game plan keys and `--team`

The "team" input is a built league (`lg2_league`) whose one team, Denver, names its game plans `OFF1.pln`, `DEF1.pln`, `OFF2.pln`, `DEF2.pln`; the first two are at its league location.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| A key | `off1`, `team = Denver` | that game plan checked; `1 file(s) checked` | `test_cli_key_checks_that_game_plan` | ☑ |
| A key and a path | `DEF1`, a `.pln`, `def1` | left to right, each file once; `2 file(s) checked` | `test_cli_key_and_a_path` | ☑ |
| A key's game plan missing | `off2 off1` | exit 2; stderr ends `FAIL <folder>\OFF2.pln: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .pln file.`; tally `1 failed` | `test_cli_key_missing_is_a_failed_item` | ☑ |
| `--team` with a key | `off1 --team Broncos`, no `team` | that game plan checked | `test_cli_key_team_option` | ☑ |
| A key, no team | `off1`, no `team` | exit 2; stderr: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or a .pln file.` | `test_cli_key_team_not_set` | ☑ |
| `--team` without a key | no PATH / a file / a folder | exit 2; stderr ends `Error: --team requires a game plan key (off1, def1, off2 or def2).`; stdout empty | `test_cli_team_without_a_key_is_a_usage_error` `[P]` | ☑ |
| Folder / file named `off1` | in the cwd | the folder searched / exit 2, `FAIL off1: Not a .pln file.`, the tally | `test_cli_folder_named_like_a_key_is_searched` / `test_cli_file_named_like_a_key_is_that_file` | ☑ |
| Four keys only | `def1` / `off3` | that game plan / exit 2, `FAIL off3: The system cannot find the file specified.` | `test_cli_four_keys_only` `[P]` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc gameplan check` | data + league | exit 1; report on stdout | `test_entry_point_subprocess` | ☑ |

---

# `athc gameplan list-normals` / `list-specials`

In [test_gameplan_list.py](test_gameplan_list.py). Reads `data/offense.pln` / `data/defense.pln` (no pool or rules; `list-normals` reads a selected league carrying the PNFL category labels, set up by an autouse fixture); stdout compared to `expected/{offense,defense}_normals_{slot,name,category}.txt` and `expected/{offense,defense}_specials.txt`. File mode prepends a `:: <source>` header line. The key rows use a built league (`.lg2`/`.lge` in tmp: Denver's `OFF1.pln`, `DEF1.pln`, `OFF2.pln`, `DEF2.pln` at its league location; Las Vegas's never there); `list-specials` reads the league only for a key. The categories the real files lack (Pass Long Left/Middle, Razzle Dazzle Run, User Specific) come from a constructed offense gameplan written to tmp.

## list-normals
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error on stderr, exit 2 | `test_normals_requires_path` | ☑ |
| Invalid `--sort` | data | usage error on stderr, exit 2 | `test_normals_rejects_invalid_sort` | ☑ |
| Help uses uppercase names | `--help` | stdout: `[OPTIONS] GAME_PLAN [OUTPUT_FILE]`; no `GAMEPLAN` / `OUTPUT_PATH` | `test_normals_help_uses_uppercase_names` | ☑ |
| `--force` / `--output` removed | option | exit 2; stderr: Click's "No such option" | `test_normals_removed_options_rejected` `[P]` | ☑ |
| Default: `<name>.normals.txt` next to the `.pln` | tmp copy | header + plays | `test_normals_default_writes_next_to_gameplan` | ☑ |
| `-` prints, slot order | data | stdout: 64 lines match fixture | `test_normals_dash_offense_slot` / `..._defense_slot` | ☑ |
| `-` prints, `--sort name` | data | stdout: sorted, blanks dropped | `test_normals_dash_sort_name` | ☑ |
| `-` prints, `--sort category` | data | stdout: grouped under `:: <label>` headers, league order, blanks dropped | `test_normals_dash_sort_category_offense` / `..._defense` | ☑ |
| `--sort category`: no league label | tmp (constructed) | game-name headers; Pass Long L/M before PLR, Razzle Dazzle Run before PRD, User Specific last; no header for an empty category; slot order within | `test_normals_sort_category_game_name_without_label` | ☑ |
| `--sort category`: league without labels | league.toml rewritten | every header a game name | `test_normals_sort_category_without_league_labels` | ☑ |
| `--league` picks the league | second league | that league's labels | `test_normals_league_option_picks_league` | ☑ |
| No league set | athc.ini without league | exit 2; stderr: `FAIL League is not set ...`; stdout empty | `test_normals_no_league_exit_2` | ☑ |
| Malformed league.toml | bad TOML | exit 2; stderr: `FAIL <league.toml>: ...` | `test_normals_bad_league_toml_exit_2` | ☑ |
| Output file: header + plays | data + out | line 1 `::`, rest match | `test_normals_file_writes_header_and_plays` | ☑ |
| Output file: `--sort name` | data + out | rest match name fixture | `test_normals_file_sort_name` | ☑ |
| Output file: `--sort category` | data + out | rest match category fixture | `test_normals_file_sort_category` | ☑ |
| `--sort category` count skips headers | data + out | stdout: `OK   <file>: 64 normal play(s)` | `test_normals_file_sort_category_counts_plays_not_headers` | ☑ |
| Existing file replaced | existing out | exit 0; rewritten | `test_normals_overwrites_existing_file` | ☑ |
| Missing folder created | `lists\plays.txt`, no `lists\` | exit 0; file written | `test_normals_creates_missing_folder` | ☑ |
| Missing folders created in full | `lists\2049\plays.txt`, no `lists\` | exit 0; whole chain created | `test_normals_creates_missing_folders_in_full` | ☑ |
| Output folder is a file | `lists` is a file | exit 2; stderr: `FAIL` naming the folder | `test_normals_output_folder_is_a_file_exit_2` | ☑ |
| Logs count + path | data + out | stdout: `OK   <file>: 64 normal play(s)` | `test_normals_file_logs_count` | ☑ |
| Missing gameplan | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; stdout empty | `test_normals_missing_gameplan` | ☑ |
| Malformed, output file | tmp | exit 2; stderr: `FAIL ...`; no file written | `test_normals_malformed_file_mode_no_output` | ☑ |

## list-specials
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No PATH given | — | usage error on stderr, exit 2 | `test_specials_requires_path` | ☑ |
| Help uses uppercase names | `--help` | stdout: `[OPTIONS] GAME_PLAN [OUTPUT_FILE]`; no `GAMEPLAN` / `OUTPUT_PATH` | `test_specials_help_uses_uppercase_names` | ☑ |
| `--force` / `--output` removed | option | exit 2; stderr: Click's "No such option" | `test_specials_removed_options_rejected` `[P]` | ☑ |
| Default: `<name>.specials.txt` next to the `.pln` | tmp copy | header + plays | `test_specials_default_writes_next_to_gameplan` | ☑ |
| `-` prints (source order) | data | stdout: lines match fixture | `test_specials_dash_offense` / `..._defense` | ☑ |
| Output file: header + plays | data + out | line 1 `::`, rest match | `test_specials_file_writes_header_and_plays` | ☑ |
| Existing file replaced | existing out | exit 0; rewritten | `test_specials_overwrites_existing_file` | ☑ |
| Missing folder created | `lists\spec.txt`, no `lists\` | exit 0; file written | `test_specials_creates_missing_folder` | ☑ |
| Missing folders created in full | `lists\2049\spec.txt`, no `lists\` | exit 0; whole chain created | `test_specials_creates_missing_folders_in_full` | ☑ |
| Logs count + path | data + out | stdout: `OK   <file>: 6 special play(s)` | `test_specials_file_logs_count` | ☑ |
| Missing gameplan | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; stdout empty | `test_specials_missing_gameplan` | ☑ |
| Malformed, output file | tmp | exit 2; stderr: `FAIL ...`; no file written | `test_specials_malformed_file_mode_no_output` | ☑ |

## arguments, `--league` and game plan keys
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No GAME_PLAN | — (both) | exit 2; stderr ends `Error: Missing argument 'GAME_PLAN'.` | `test_bare_is_missing_game_plan` `[P]` | ☑ |
| Extra argument | `list-normals <pln> out.txt extra` | exit 2; stderr ends `Error: Got unexpected extra argument (extra).`; nothing written | `test_normals_extra_argument_rejected` | ☑ |
| `--team` with a path | `<pln> - --team Denver` (both) | exit 2; stderr ends `Error: --team requires a game plan key (off1, def1, off2 or def2).` | `test_team_with_a_path_is_a_usage_error` `[P]` | ☑ |
| list-specials `--league` with a path | that league's league.toml broken | exit 0; nothing read from it | `test_specials_league_with_a_path_reads_nothing_from_it` | ☑ |
| list-specials `--league NOPE` with a path | — | exit 2; stderr: `FAIL League 'NOPE' not found ...`; stdout empty | `test_specials_league_that_does_not_exist_fails_even_with_a_path` | ☑ |
| list-specials, a path, no athc.ini | — | exit 0 | `test_specials_path_without_any_settings` | ☑ |
| list-specials, a key, no league selected | `off1` | exit 2; stderr: `FAIL League is not set ...` | `test_specials_key_needs_a_league` | ☑ |
| Each key, any case | `off1` / `def1` / `off2` / `DEF2` | `<name>.normals.txt` beside the game plan; stdout `OK   <full path>: N normal play(s)` | `test_normals_key_writes_beside_the_game_plan` `[P]` | ☑ |
| A key to the console | `list-specials def1 -` | stdout: the defense fixture | `test_specials_key_to_the_console` | ☑ |
| Two keys, one shared game plan | `off1`, then `off2` (both `OFF.pln`) | the same `OFF.normals.txt` written twice | `test_two_keys_one_shared_game_plan_write_one_file_twice` | ☑ |
| A key from `ppp_path` | `off1`; `ppp_path` holds `off1.PLN` | found without case; `off1.normals.txt` in `ppp_path` | `test_key_from_ppp_path` | ☑ |
| A key, `--team` another team | `off1 - --team "Las Vegas"` | exit 2; stderr: `FAIL <folder>\RAIDEROFF.pln: The system cannot find the file specified.` (no hint) | `test_key_team_option_names_another_team` | ☑ |
| A key's game plan missing at your league location | `off2 -` | exit 2; stderr: `FAIL <folder>\OFF2.pln: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .pln file.`; stdout empty | `test_key_missing_at_your_league_location` | ☑ |
| Same, team folder absent | `off1 -` | the path phrase, same hint | `test_key_missing_folder_is_the_path_phrase` | ☑ |
| Same, in `ppp_path` | `off1 -`, empty `ppp_path` | exit 2; stderr: `FAIL <ppp_path>\OFF1.pln: The system cannot find the file specified.` (no hint) | `test_key_missing_in_ppp_path` | ☑ |
| A key, no team / no `path` | `off1 -` | exit 2; stderr: `FAIL <league.toml>: Team is not set. ... or pass --team or a .pln file.` / `League files folder is not set. ... or pass a .pln file.` | `test_key_team_not_set` / `test_key_path_not_set` | ☑ |
| Folder / file named `off1` | in the cwd | exit 2, `FAIL off1: Access is denied.` / that file listed | `test_folder_named_like_a_key_is_that_folder` / `test_file_named_like_a_key_is_that_file` | ☑ |
| Four keys only | `def2` / `off3` | listed / exit 2, `FAIL off3: The system cannot find the file specified.` | `test_four_keys_only` `[P]` | ☑ |

---

# `athc gameplan find-play`

In [test_gameplan_find_play.py](test_gameplan_find_play.py). Pure helpers (`find_in_gameplan`, `format_hit_line`) on constructed gameplans; CLI tier on real `data/offense.pln` / `data/defense.pln` and tmp-written constructed gameplans, through `--path`; the team tier on `pnfl_league` (`PNFL.lg2` + `PNFL.lge`, Denver's and Las Vegas's 2049 plans at their league locations) or a built league (`lg2_league`). Normal hits read `'OR45RL01' found in slots 1-3, 16-2` (no category); special hits read `'BCFGPAT' found in special slot 1 (Field Goal/PAT)`. A single game plan without the play prints `not found`; a set prints nothing for a miss. No pool or rules; with a path no league either. The team rows stand for all three batch commands.

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
| No args | — | usage error on stderr, exit 2 | `test_cli_requires_args` | ☑ |
| Bare | — | exit 2; stderr ends `Error: Missing argument 'PLAY...'.` | `test_cli_bare_is_missing_play` | ☑ |
| `--path .` with `-r`; empty folder | tmp (cwd) | recursive hit + summary; empty folder: exit 1, stderr `WARN .: No .pln files.` | `test_cli_single_arg_recursive` / `test_cli_single_arg_empty_directory_exit_1` | ☑ |
| Every argument is a play | two plays + `--path .` | exit 0; both found in the cwd file | `test_cli_every_argument_is_a_play` | ☑ |
| `--verbose` (removed) | data | usage error on stderr, exit 2 | `test_cli_verbose_option_is_rejected` | ☑ |
| Wildcard `--path` | `Off*.pln` in tmp | athc expands it: the two matches, then the tally, as a folder; exit 0 | `test_cli_wildcard_path_works_like_a_folder` | ☑ |
| Single file hit (normal / special) | data | stdout: slot(s); special adds category; no summary | `test_cli_single_file_hit` / `test_cli_finds_custom_special` | ☑ |
| Single file miss | data | exit 1; stdout: `<file>: 'play' not found` | `test_cli_single_file_miss_exit_1` | ☑ |
| Case-insensitive | data | hit | `test_cli_single_file_case_insensitive` | ☑ |
| Several plays over a dir; one play in 2 slots of a gameplan that holds 2 of them; summary | tmp | exit 0; stdout: per-play "found N instance(s) in M game plan(s)" | `test_cli_multiple_plays_all_hit` | ☑ |
| Multiple plays, one found (grep rule) | data | exit 0 | `test_cli_one_play_found_exit_0` | ☑ |
| Multiple plays, none found | data | exit 1 | `test_cli_no_play_found_exit_1` | ☑ |
| Directory: hit in one file, miss in the other | tmp | exit 0; stdout: hit line only; no `not found` line; footer | `test_cli_directory_reports_hits_only` | ☑ |
| Directory: no hits | tmp | exit 1; stdout: the tally only | `test_cli_directory_with_no_hits_prints_only_the_tally` | ☑ |
| Directory: instance/file counts | tmp | stdout: "found N instance(s) in M game plan(s)"; exit 0 when any play found | `test_cli_directory_summary_counts_multiple_hits` / `..._per_play_summary` | ☑ |
| Recursive subdir | tmp | exit 0; found | `test_cli_recursive_finds_in_subdir` | ☑ |
| Missing path / malformed `.pln` | tmp | exit 2; stderr: `FAIL <path>: ...`; stdout empty (no tally) | `test_cli_missing_path_exit_2` / `test_cli_malformed_pln_exit_2` | ☑ |

## `--league`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| With a path: resolved, nothing read | `--path <pln> --league <other>`, its league.toml broken | exit 0; the hit | `test_league_with_a_path_reads_nothing_from_it` | ☑ |
| `--league NOPE` with a path | — | exit 2; stderr: `FAIL League 'NOPE' not found ...`; stdout empty | `test_league_that_does_not_exist_fails_even_with_a_path` | ☑ |
| A path, no settings at all | no athc.ini | exit 0 | `test_path_without_any_settings` | ☑ |
| Default scope, no league selected | — | exit 2; stderr: `FAIL League is not set ...` | `test_default_scope_needs_a_league` | ☑ |

## your team's game plans (the three batch commands)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Default scope: your team's four | `team = Denver`; a `.pln` in the cwd | the hits among Denver's four at their league location, `.lg2` order, then the tally; the cwd not searched | `test_default_scope_is_your_teams_game_plans` | ☑ |
| Default scope from `ppp_path` | `ppp_path` = a copy of Denver's folder | the two offense hits from `ppp_path`; no `WARN` | `test_default_scope_from_ppp_path` | ☑ |
| `ppp_path` names without case; relative `ppp_path` | lowercase copies; `ppp_path = 'mine'` | found, shown as the folder spells them; under the league folder | `test_ppp_path_names_ignore_case` / `test_relative_ppp_path_is_in_the_league_folder` | ☑ |
| `ppp_path` missing / a file | — | exit 2; stderr: `FAIL <ppp_path>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER'.` / `The directory name is invalid. ...`; stdout empty | `test_ppp_path_not_a_folder` `[P]` | ☑ |
| Shared game plan once | `--team "Las Vegas"` | the hit in `RAIDEROFF.pln`, searched once; `RAIDERDEF.pln` prints nothing; then the tally | `test_shared_game_plan_once` | ☑ |
| Each key, any case | `--path off1` / `def1` / `off2` / `def2` / `OFF1` / `Def2` | that `.lg2` entry; one file, no tally | `test_key_is_one_game_plan` `[P]` | ☑ |
| Two keys, one shared game plan | `--path off1` / `off2`, `--team "Las Vegas"` | both `RAIDEROFF.pln` | `test_two_keys_one_shared_game_plan` | ☑ |
| Four keys only | `--path def2` / `off3` | `DEN-DGP2.pln` / exit 2, `FAIL off3: The system cannot find the file specified.` | `test_four_keys_only` `[P]` | ☑ |
| Folder / file named `off1` | in the cwd | the folder searched, with the tally / exit 2, `FAIL off1: Not a .pln file.` | `test_folder_named_like_a_key_is_searched` / `test_file_named_like_a_key_is_that_file` | ☑ |
| Team by name, nickname, both, any case | `team` or `--team`: `Denver`, `Broncos`, `Denver Broncos`, `dENVER bRONCOS` | Denver's two offense hits | `test_team_by_name_nickname_or_both` `[P]` | ☑ |
| `team` / `--team` matches no team | `Denvr` | exit 2; stderr: `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: ...` / `Error: Invalid value for '--team': no team named 'Denvr'. Teams: ...` | `test_team_matches_no_team` / `test_team_option_matches_no_team` | ☑ |
| `team` matches two teams | `New York` (built `.lge`) | exit 2; stderr: `FAIL <league.toml>: [league] team: 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | `test_team_matches_two_teams` | ☑ |
| `--team` match count: one / none / two | `Giants` / `Raiders` / `New York` | accepted / `Error: Invalid value for '--team': ...` | `test_team_option_match_count` `[P]` | ☑ |
| `team` blank / an array | `'  '` / `['Denver']` | exit 2; `Team is not set. ... or pass --team or --path.` / `[league] team: Expected a string, got an array.` | `test_team_blank_is_not_set` / `test_team_array` | ☑ |
| `--team` beats `team` | `team = Denver`, `--team "Las Vegas"` | Las Vegas's game plans | `test_team_option_beats_team` | ☑ |
| `ppp_path` is for your team | `ppp_path` set; `--team Broncos` / `--team "Las Vegas"` | from `ppp_path` / at the league location | `test_ppp_path_is_for_your_team` `[P]` | ☑ |
| `--team` without your team | `team` unset / `Denvr`; `ppp_path` set | `--team Denver` at the league location; no `FAIL` | `test_team_option_without_your_team` `[P]` | ☑ |
| Team not set | no `team`, no `path`: default scope / `--path off1` | exit 2; stderr: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or --path.` / `... or a .pln file.` | `test_team_not_set` `[P]` | ☑ |
| `path` not set | `team` set: default scope / `--path off1` | exit 2; stderr: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --path.` / `... or pass a .pln file.` | `test_path_not_set` `[P]` | ☑ |
| `--team` with a path | `--path` a file / `.` / `*.pln` | exit 2; stderr ends `Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.`; stdout empty | `test_team_with_a_path_is_a_usage_error` `[P]` | ☑ |
| `.lge` / `.lg2` missing; stock league | built league | exit 2; stderr: `FAIL <file>: The system cannot find the file specified.` / `FAIL <lg2>: Stock league not supported.` | `test_lge_missing` / `test_lg2_missing` / `test_stock_league` | ☑ |
| Team counts: equal / one fewer / one more | 2 / 1 / 3 `.lg2` teams, 2 `.lge` teams | accepted / `FAIL <lg2>: Lists N team(s), but test_league.lge has 2.` | `test_league_team_counts` `[P]` | ☑ |
| League location: one game plan missing | `DEN-OGP2.pln` removed | exit 2; stderr: `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.`; the other three searched | `test_league_one_game_plan_missing` | ☑ |
| League location: `-r` ignored | `-r` | the same output | `test_league_recursive_is_ignored` | ☑ |
| League location: none, your team | folder absent / empty | exit 2; stderr: `FAIL <folder>: The system cannot find the path specified.` / `No Denver game plans.`, then ` Run 'athc config set ppp_path FOLDER' or pass --path.`; stdout: the zero tally | `test_league_no_game_plans_for_your_team` `[P]` | ☑ |
| League location: none, another team | `--team "Las Vegas"`, folder absent / empty | the same line, no hint | `test_league_no_game_plans_for_another_team` `[P]` | ☑ |
| League location: none / one there | 0 / 1 of the four | the one folder line / a `FAIL` per missing game plan, no folder line | `test_league_no_game_plans_limit` `[P]` | ☑ |
| `ppp_path`: one game plan missing | `DEN-OGP2.pln` removed | exit 0; stderr: `WARN <ppp_path>\DEN-OGP2.pln: The system cannot find the file specified.` | `test_ppp_path_one_game_plan_missing` | ☑ |
| `ppp_path`: none / one there | 0 / 1 of the four | exit 1, `WARN <ppp_path>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.`, zero tally / a `WARN` per missing game plan | `test_ppp_path_no_game_plans_limit` `[P]` | ☑ |
| `ppp_path`: each name once | Las Vegas, empty `ppp_path` | `... The league file names RAIDEROFF.pln, RAIDERDEF.pln.` | `test_ppp_path_no_game_plans_names_each_once` | ☑ |
| `ppp_path` tree (`-r`) | `week1` all four, `week2` one | each folder on its own; `WARN`s for `week2`'s missing three only; one tally | `test_ppp_path_tree` | ☑ |
| `ppp_path` tree with none / no `-r` | empty subfolders / the four in a subfolder | one `WARN` for the whole tree, exit 1 / subfolders not searched: the scope `WARN` | `test_ppp_path_tree_with_no_game_plans` / `test_ppp_path_without_recursive_skips_subfolders` | ☑ |
| A key's game plan missing | `--path off1`: your league location / `--team "Las Vegas"` / `ppp_path` | exit 2; `FAIL <file>: The system cannot find the file specified.` with ` Run 'athc config set ppp_path FOLDER' or pass a .pln file.` / no hint / no hint; no tally | `test_key_missing_at_your_league_location` / `test_key_missing_for_another_team` / `test_key_missing_in_ppp_path` | ☑ |

---

# `athc gameplan set-normals`

In [test_gameplan_set_normals.py](test_gameplan_set_normals.py). Operates on a tmp copy of `data/offense.pln` with the curated pool (a selected league whose `play_path` is `data/plays`). Edits in place, no backup; `check` validates. The key rows add a built `.lg2`/`.lge` (Denver's game plans named after their keys, `OFF1.pln` there) to that league. Exit 0 = updated, 2 = usage or error (nothing written).

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs gameplan / play_list | — | usage error on stderr, exit 2 | `test_requires_gameplan` / `test_requires_play_list` | ☑ |
| Bare / a key alone | — / `off1` | exit 2; stderr ends `Error: Missing argument 'GAME_PLAN'.` / `'INPUT_FILE'.` | `test_bare_is_missing_game_plan` / `test_key_alone_is_missing_input_file` | ☑ |
| Extra argument | `<pln> plays.txt extra` | exit 2; stderr ends `Error: Got unexpected extra argument (extra).` | `test_extra_argument_rejected` | ☑ |
| A `.pln` as the play list | `<pln> offense.pln` | exit 2; stderr: `FAIL <list>: Not a valid play list.`; untouched | `test_play_list_not_text` | ☑ |
| `--team` with a path | `<pln> plays.txt --team Denver` | exit 2; stderr ends `Error: --team requires a game plan key (off1, def1, off2 or def2).` | `test_team_with_a_path_is_a_usage_error` | ☑ |
| Removed options rejected | `--stdin`, `--no-backup`, `--play-path`, `--playpool-rules` | exit 2; stderr: Click's "No such option" | `test_removed_options_rejected` `[P]` | ☑ |
| Writes normals from file | tmp | slot 0 set, rest cleared | `test_writes_from_file` | ☑ |
| List saved with a BOM | UTF-8 with BOM | first play placed | `test_a_list_saved_with_a_bom_reads_its_first_play` | ☑ |
| Slot path starts with the play pool's folder name | tmp | `<pool folder>\Offense\RL\<play>.ply` | `test_slot_path_starts_with_play_pool_folder` | ☑ |
| No backup | tmp | stdout: `OK` line; no `.bak` | `test_writes_no_backup` | ☑ |
| Skips `::` / strips ` ::` / `name::` fails | tmp | parsed / parsed / exit 2 | `test_skips_comment_lines` / `test_strips_inline_comments` / `test_inline_comment_requires_space` | ☑ |
| `-q` rejected; `-` reads the console | tmp | exit 2, stderr ends `Error: No such option '-q'.`, untouched / exit 0, set | `test_quiet_is_rejected` / `test_dash_reads_from_console` | ☑ |
| `-` input errors name no file | tmp | exit 2; stderr: `FAIL line 1: ...`, no `- ` | `test_dash_input_errors_name_no_file` | ☑ |
| Error lines name the real line | `-` with CRLF, a blank and a `::` line / a file | `FAIL line 3: ...` / `FAIL <list>: line 4: ... (slot 1-2).` | `test_dash_input_line_is_the_real_line` / `test_file_input_line_is_the_real_line` | ☑ |
| Special-teams play rejected (untouched) | tmp | exit 2; stderr: `FAIL` naming set-specials | `test_rejects_special_teams_play` | ☑ |
| Missing play aborts (untouched) | tmp | exit 2; stderr: `FAIL` | `test_missing_play_aborts` | ☑ |
| >64 plays / league `play_path` missing | tmp | exit 2; stderr: `FAIL` | `test_too_many_plays_rejected` / `test_invalid_play_path` | ☑ |
| 64 plays accepted; >64 from the console | tmp | exit 0, `OK   <file>: updated (64 normal play(s))` / exit 2, `FAIL Too many plays (65). The most is 64.` | `test_as_many_plays_as_slots_accepted` / `test_too_many_plays_from_the_console_names_no_file` | ☑ |
| Missing `.pln` / missing play list | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.` only | `test_missing_pln` / `test_missing_play_list` | ☑ |
| A key | `off1 plays.txt`, `team = Denver` | Denver's `OFF1.pln` set; stdout `OK   <full path>: updated (1 normal play(s))` | `test_key_sets_your_game_plan` | ☑ |
| A key's game plan missing | `off2 plays.txt` | exit 2; stderr: `FAIL <folder>\OFF2.pln: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .pln file.` | `test_key_missing_names_the_game_plan` | ☑ |
| Setup order: a path | `<pln>` + 65 plays, no league selected | the `Too many plays` line; no league read | `test_too_many_plays_with_a_path_fail_before_the_league` | ☑ |
| Setup order: a key | `off1` + 65 plays, no `team` | `FAIL <league.toml>: Team is not set. ... or pass --team or a .pln file.`, before the list | `test_key_reads_the_league_before_the_list` | ☑ |

# `athc gameplan set-specials`

In [test_gameplan_set_specials.py](test_gameplan_set_specials.py). Tmp copies of `offense.pln` / `defense.pln`, with the curated pool from a selected league (`play_path` = `data/plays`). Merge semantics; your team's four by default, `--path` for a file, key, folder, tree or wildcard; wrong-side files skipped by size parity; no backup. The team rows add a built `.lg2`/`.lge` (Denver's game plans named after their keys, all four there) to that league. Exit 0 = all updated, 2 = usage, setup error or a failed file.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs INPUT_FILE / a `.pln` as the list / no `-q` | — / `<pln>` alone / `-q` | exit 2: `Error: Missing argument 'INPUT_FILE'.` / `FAIL <pln>: Not a valid play list.`, untouched / usage error | `test_requires_input_file` / `test_play_list_not_text` / `test_no_quiet_option` | ☑ |
| Extra argument | `spec.txt extra` | exit 2; stderr ends `Error: Got unexpected extra argument (extra).` | `test_extra_argument_rejected` | ☑ |
| Removed options rejected | `--stdin`, `--no-backup`, `--play-path`, `--playpool-rules` | exit 2; stderr: Click's "No such option" | `test_removed_options_rejected` `[P]` | ☑ |
| Writes special from file; merge preserves others | tmp | slot 1 set; rest intact | `test_writes_special_from_file` / `test_merge_preserves_other_categories` | ☑ |
| List saved with a BOM | UTF-8 with BOM | first play placed | `test_a_list_saved_with_a_bom_reads_its_first_play` | ☑ |
| No backup | tmp | no `.bak`; no backup note | `test_writes_no_backup` | ☑ |
| Comments; `-` reads the console | tmp | parsed; set | `test_skips_and_strips_comments` / `test_dash_reads_from_console` | ☑ |
| `-` input errors name no file | tmp | exit 2; stderr: `FAIL line 1: ...`, no `- ` | `test_dash_input_errors_name_no_file` | ☑ |
| A play a game plan cannot take | file / `-` | exit 2; stderr: `FAIL <pln>: 'NOPEPLAY' is not in the play pool (<list> line 3).` / `(play list line 1).` | `test_gameplan_problem_names_the_gameplan_and_the_list_line` / `test_gameplan_problem_from_the_console` | ☑ |
| Normal play / duplicate / >10 rejected (untouched) | tmp | exit 2; stderr: `FAIL ...` | `test_rejects_normal_play` / `test_rejects_duplicate_play` / `test_too_many_plays_rejected` | ☑ |
| 10 plays pass the count | tmp | past the count (here to the duplicate check) | `test_as_many_plays_as_slots_pass_the_count` | ☑ |
| Missing target / league `play_path` missing | tmp | exit 2 | `test_missing_target` / `test_invalid_play_path` | ☑ |
| Missing play list | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.` only | `test_missing_play_list` | ☑ |
| Directory top-level / recursive | tmp | stdout: "2 file(s) processed" tally | `test_directory_top_level_only` / `test_directory_recursive` | ☑ |
| Offense input skips defense files | tmp | "1 file(s) processed"; def untouched | `test_offense_input_skips_defense_files` | ☑ |
| Continues past a failed file | tmp | exit 2; stderr: `FAIL` for the bad file; stdout tally: 1 updated, 1 failed | `test_continues_past_failed_file` | ☑ |
| Wildcard `--path` | `Off*.pln` in tmp | the match only; `1 file(s) processed, 1 updated, 0 skipped, 0 failed` | `test_wildcard_path` | ☑ |
| Setup order: the list before the league | 11 plays, no league selected | `FAIL <list>: Too many plays (11). The most is 10.` | `test_too_many_plays_fail_before_the_league` | ☑ |
| Default scope: your team's four | offense list, `team = Denver`; four game plans / one per side | `OK` for the offense ones, `SKIP <file>: defense game plan` for the others, `.lg2` order; `4 file(s) processed, 2 updated, 2 skipped, 0 failed` / `2 file(s) processed, 1 updated, 1 skipped, 0 failed` | `test_default_scope_is_your_teams_game_plans` `[P]` | ☑ |
| A key keeps its tally | `--path off2` | the `OK` line; `1 file(s) processed, 1 updated, 0 skipped, 0 failed` | `test_key_keeps_its_tally` | ☑ |
| `ppp_path` with none of the four | empty `ppp_path` | exit 0; the scope `WARN`; zero tally | `test_ppp_path_with_no_game_plans` | ☑ |
| League location: one missing | `DEF2.pln` removed | exit 2; `FAIL <folder>\DEF2.pln: ...`; `3 file(s) processed, 2 updated, 1 skipped, 1 failed` | `test_league_location_missing_game_plan_counts_as_failed` | ☑ |
| `--team` with a path | `--path <pln> --team Denver` | exit 2; stderr ends `Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.` | `test_team_with_a_path_is_a_usage_error` | ☑ |

---

# `athc gameplan replace-play`

In [test_gameplan_replace_play.py](test_gameplan_replace_play.py). `pick_replacement`, `replace_in_gameplan` / `format_replacement_lines` helpers on constructed offense/defense gameplans; CLI tier on constructed gameplans written to tmp (one holding `OR45RL01` @ 1-1 for the plain swaps) and tmp copies of `offense.pln` where nothing is swapped, against the curated pool (a selected league whose `play_path` is `data/plays`); the team rows add a built `.lg2`/`.lge` (Denver's game plans named after their keys). The location is `--path`; nothing else is positional. Finds the target like `find-play` (normal + custom-special, case-insensitive), swaps each hit for the first replacement (each must be in the pool) not already in the game plan and with which it passes `check`. A play's normal hits collapse to one line, slots bracketed in order at the end — `'OLD' (cat) replaced with 'NEW' (cat) [1-3][4-2]`; specials print one line each — `Replaced 'OLD' (cat) in special slot N with 'NEW' (cat)`; short category; a skipped replacement is a `SKIP` line. The GamePlan model validates each swap (side; special category). Rules from the league's `gameplan.toml` when present. Exit 0 = clean, 1 = nothing replaced or no valid replacement, 2 = usage, setup error or a failed file.

## `pick_replacement` (constructed gameplans, curated pool)
| Case | Expected | Test | Status |
|---|---|---|---|
| First replacement already in the game plan | skipped; second used | `test_pick_skips_play_already_in_gameplan` | ☑ |
| First replacement breaks a rule | skipped with the `check` text; second used | `test_pick_skips_play_breaking_a_rule` | ☑ |
| None fits | no update; both skipped | `test_pick_none_fits` | ☑ |
| Play not in the gameplan | nothing | `test_pick_no_hits` | ☑ |
| Plan still fails `check` after the swap | skipped with the `check` text; none fits | `test_pick_plan_still_failing_check_is_not_replaced` | ☑ |
| Swap fixes what made the plan fail | used | `test_pick_swap_that_fixes_the_plan_is_used` | ☑ |
| Play replaced by itself | not "already in the game plan" | `test_pick_play_replaced_by_itself` | ☑ |
| Model refuses the only replacement | `refused`, the model's text | `test_pick_model_refusal_keeps_the_text_for_one_replacement` | ☑ |
| Model refuses a later one of several | `refused` names it; earlier skips kept | `test_pick_refused_later_replacement_named_and_skips_kept` | ☑ |
| Defense: first already in the game plan | skipped; second used | `test_pick_defense_skips_play_already_in_gameplan` | ☑ |

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
| Error names the path first | special into a normal hit, `Path("x.pln")` | `AthcError` text starts `x.pln: Normal slot 0 ...`; `.path` set | `test_replace_error_names_the_path_first` | ☑ |

## `format_replacement_lines` (short category; normal vs special phrasing)
| Case | Expected | Test | Status |
|---|---|---|---|
| Normal slot line | `'OLDRUN' (RL) replaced with 'NEWRUN' (RM) [1-1]` | `test_format_lines_normal_slot` | ☑ |
| Many normal slots → one line, bracketed in order at end | `'DUP' (RM) replaced with 'NEW' (RM) [1-3][4-2]` | `test_format_lines_multiple_normal_slots` | ☑ |
| Special slot line | `Replaced … (Field Goal/PAT) in special slot 1 with …` | `test_format_lines_special_slot` | ☑ |

## command — usage / replacement resolution (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No args / one name | — / `OLD` | exit 2; stderr ends `Error: Missing argument 'PLAY'.` / has `Missing argument 'REPLACEMENT...'.` | `test_cli_requires_args` / `test_cli_bare_is_missing_play` / `test_cli_one_name_is_usage_error` | ☑ |
| Every name is a play | a replacement that is also a folder in the cwd; `--path <pln>` | exit 0; replaced with it | `test_cli_every_name_is_a_play` | ☑ |
| A replacement listed again, any case | `NEW new OTHER` | one `SKIP` for `NEW`, then `OTHER` used / the tally names `NEW` once | `test_cli_repeated_replacement_tried_once` / `test_cli_repeated_replacement_named_once_in_the_tally` | ☑ |
| Every replacement must be in the pool | data + flags | exit 2; stderr: `FAIL` "is not in the play pool"; unchanged | `test_cli_every_replacement_must_be_in_pool` | ☑ |
| `-q` not offered | tmp + flags | usage error on stderr, exit 2 | `test_cli_no_quiet_option` | ☑ |
| Replacement not in pool | tmp + flags | exit 2; stderr: `FAIL` "is not in the play pool" | `test_cli_replacement_not_in_pool_exit_2` | ☑ |
| Replacement case-insensitive | data + flags | exit 0; resolves | `test_cli_replacement_case_insensitive` | ☑ |

## command — single file
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Replaces a normal play; bystander kept | tmp + flags | `'OLDRUN' (RL) replaced with … [1-1]` | `test_cli_single_file_replaces_normal` | ☑ |
| Play in several slots | tmp + flags | the duplicates fail `check`: `SKIP` lines, not replaced; exit 1; unchanged | `test_cli_play_in_several_slots_not_replaced` | ☑ |
| Output without league labels | league.toml with no `[categories]` | `(Run Left)` / `(Run Middle)` | `test_cli_output_uses_game_names_without_league_labels` | ☑ |
| Replaces a custom-special play; others kept | tmp + flags | other special intact; `… in special slot 1 with …` | `test_cli_single_file_replaces_special` | ☑ |
| Case-insensitive target | data + flags | replaced | `test_cli_single_file_target_case_insensitive` | ☑ |
| Miss (untouched) | data + flags | exit 1; stdout: "not found"; unchanged | `test_cli_single_file_miss_exit_1` | ☑ |

## command — backup replacements and league rules
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| First already in the game plan | constructed | `SKIP … already in the game plan`, then `OK` with the second; exit 0 | `test_cli_backup_used_when_first_already_in_plan` | ☑ |
| First breaks a `gameplan.toml` rule | constructed; `[offense.RM] max_count = 0` | `SKIP … fails check: [Run Middle] …`, then `OK`; exit 0 | `test_cli_backup_used_when_first_breaks_rule` | ☑ |
| Rollout cap uses the play file | constructed; `[offense.PSL] max_rollouts_count = 0` | the rollout (AF1AwagR) skipped, the other used | `test_cli_rollout_cap_uses_the_play_file` | ☑ |
| Swap across categories, both landing on their limits | constructed; `[offense.PSL] min_count = 1`, `[offense.PML] max_count = 2` | `OK … (PSL) replaced with … (PML)`; exit 0 | `test_cli_cross_category_swap_within_limits` | ☑ |
| Swap across categories leaves the losing category short | constructed; `[offense.PSL] min_count = 2` | `SKIP … requires at least 2.`, not replaced; exit 1; unchanged | `test_cli_cross_category_swap_leaves_losing_category_short` | ☑ |
| None fits, single file | constructed | `SKIP` lines, `<file>: 'OLDRUN' not replaced, no valid replacement`; exit 1; unchanged | `test_cli_no_valid_replacement_single_file` | ☑ |
| None fits in one of two | tmp dir | tally `… 0 failed, 1 not replaced`; exit 1 | `test_cli_directory_counts_not_replaced` | ☑ |
| Later replacement refused by the model | constructed | `SKIP` line, then `FAIL <file>: 'NEW' does not fit: …`; exit 2; unchanged | `test_cli_refused_later_replacement_names_it` | ☑ |
| Wildcard `--path` | tmp `*.pln` | athc expands it; works like a folder: tally, miss silent | `test_cli_wildcard_path_works_like_a_folder` | ☑ |
| Malformed `gameplan.toml` | league | exit 2; `FAIL <gameplan.toml>: TOML parse error …`; unchanged | `test_cli_bad_rules_file_exit_2` | ☑ |

## command — no backups
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No backup written or reported | data | no `.bak`; no backup line | `test_writes_no_backup` | ☑ |
| `--no-backup` removed | option | exit 2; stderr: Click's "No such option" | `test_no_backup_option_removed` | ☑ |

## command — directory / tree
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Directory updates matching files + summary | tmp + flags | exit 0; stdout tally "replaced 2 … in 2 game plan(s)" | `test_cli_directory_updates_matching_files` | ☑ |
| Other-side file has no hit → untouched | tmp + flags | exit 0; stdout tally "in 1 game plan(s)"; def unchanged | `test_cli_directory_leaves_other_side_untouched` | ☑ |
| No hits anywhere | tmp + flags | exit 1; stdout tally "replaced 0 … in 0 game plan(s)" | `test_cli_directory_no_hits_exit_1` | ☑ |
| Recursive subdir | tmp + flags | exit 0; replaced | `test_cli_recursive_replaces_in_subdir` | ☑ |

## command — validation / errors (target left untouched)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Special replacement for a normal hit | tmp + flags | exit 2; stderr: `FAIL`; no `.bak`; unchanged | `test_cli_replacement_special_for_normal_fails` | ☑ |
| Wrong-side replacement | tmp + flags | exit 2; stderr: `FAIL`; no `.bak`; unchanged | `test_cli_replacement_wrong_side_fails` | ☑ |
| Wrong special category | tmp + flags | exit 2; stderr: `FAIL`; no `.bak`; unchanged | `test_cli_replacement_wrong_special_category_fails` | ☑ |
| Missing `--path` file | tmp + flags | exit 2; stderr: `FAIL <path>: ...`; no tally | `test_cli_missing_path_exit_2` | ☑ |
| Malformed `.pln` | tmp + flags | exit 2; stderr: `FAIL <file>: ...` | `test_cli_malformed_pln_exit_2` | ☑ |
| League `play_path` missing | tmp | exit 2; stderr: `FAIL <play path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` | `test_cli_invalid_play_path_exit_2` | ☑ |
| `--play-path` removed | option | exit 2; stderr: Click's "No such option" | `test_cli_play_path_option_removed` | ☑ |
| Continues past a failed file | tmp + flags | exit 2; stderr: `FAIL` for the bad file; stdout tally: 1 replaced, 1 failed | `test_cli_continues_past_failed_file` | ☑ |

## command — your team's game plans
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Default scope | `team = Denver`; `OLDRUN` in `OFF1.pln` and `OFF2.pln`; a plan in the cwd | the two offense plans replaced in `.lg2` order, misses silent, tally `replaced 2 instance(s) in 2 game plan(s)`; the cwd plan untouched | `test_cli_default_scope_is_your_teams_game_plans` | ☑ |
| Shared game plan once | off1 = off2 = `OFF.pln` | one `OK` line; `replaced 1 instance(s) in 1 game plan(s)` | `test_cli_shared_game_plan_once` | ☑ |
| A key is one file | `--path off2` / `DEF1` | the `OK` line / `<file>: 'OLDRUN' not found`, exit 1; no tally; off1 untouched | `test_cli_key_is_one_file` `[P]` | ☑ |
| League location: one missing | `OFF2.pln` removed | exit 2; `FAIL <folder>\OFF2.pln: ...`; tally `1 failed` | `test_cli_league_location_missing_game_plan_counts_as_failed` | ☑ |
| `ppp_path` with none of the four | empty `ppp_path` | exit 1; the scope `WARN`; zero tally | `test_cli_ppp_path_with_no_game_plans` | ☑ |
| `--team` typo before the pool | `--team Denvr` | exit 2; no pool `WARN`; `Error: Invalid value for '--team': no team named 'Denvr'. ...` | `test_cli_team_typo_shows_before_the_pool` | ☑ |
| `--team` with a path | `--path <pln> --team Denver` | exit 2; stderr ends `Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.` | `test_cli_team_with_a_path_is_a_usage_error` | ☑ |

---

# `athc profile diff`

In [test_profile_diff.py](test_profile_diff.py). Inputs: real `TST-OFF1/OFF2/DEF1.prf` plus a synthetic `diff_base.prf` / `diff_modified.prf` pair (the modified one touches every differable field). Goldens in `expected/diff_{all_fields,identical}.{txt,csv}` (paths normalized). No rules needed. Key rows use `build_teams` from [conftest.py](conftest.py).

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Needs two PATHs | one path | usage error on stderr, exit 2 | `test_cli_requires_two_paths` | ☑ |
| Identical | OFF1 ×2 | exit 0; stdout: "are identical." | `test_cli_identical_exit_0` | ☑ |
| Differs | OFF1 vs OFF2 | exit 1; stdout: head + `[situations]` + summary | `test_cli_differs_exit_1` | ☑ |
| Cross-side | OFF1 vs DEF1 | exit 2; stderr: `FAIL Cannot compare <a> (offense) with <b> (defense).`; stdout empty | `test_cli_cross_side_exit_2` | ☑ |
| Missing / malformed input | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.` / `FAIL <file>: ...` | `test_cli_missing_path_exit_2` / `test_cli_malformed_prf_exit_2` | ☑ |
| Help screen | `--help` | stdout == the plan's screen (78 columns) | `test_help_screen` | ☑ |
| Operand count | 0 / 1 / 2 / 3 operands | 2 accepted; else exit 2: `Missing argument 'PROFILE1'.` / `Missing argument 'PROFILE2'.` / `Got unexpected extra argument (<x>).` | `test_cli_takes_two_operands` `[P]` | ☑ |
| Two keys | `off1 off2` | exit 1; stdout starts `<DEN-OFF1> -> <DEN-OFF2>` | `test_cli_two_keys` | ☑ |
| Key and a file | `off1 <OFF2>` | exit 1; the report names the key's file | `test_cli_key_and_a_file` | ☑ |
| Missing key file | `off1 off2`, DEN-OFF2 deleted | exit 2; stderr: `FAIL <file>: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .prf file.`; stdout empty | `test_cli_missing_key_file` | ☑ |
| `--team` with two files | OFF1 OFF2 `--team Denver` | exit 2; stderr ends `Error: --team requires a profile key (off1, def1, off2 or def2).`; stdout empty | `test_cli_team_option_with_two_files` | ☑ |
| `--league` with two files | broken athc.ini and league.toml | exit 0; neither read | `test_cli_league_option_with_two_files_reads_nothing_else` | ☑ |

## `--output`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `.txt` equals stdout | OFF1 vs OFF2 | file == no-`-o` stdout; stdout empty | `test_output_txt_matches_stdout` | ☑ |
| `.txt` identical | OFF1 ×2 | exit 0; stdout: "are identical." | `test_output_txt_identical_exit_0` | ☑ |
| `.csv` rows + CRLF | base/mod | `\r\n`; provenance + header + rows | `test_output_csv_rows_and_crlf` | ☑ |
| Unknown extension | `.json` | exit 2; stderr ends `Error: Invalid value for '-o' / '--output': must have a .txt or .csv extension.`; no file written | `test_output_unknown_extension_is_a_usage_error` | ☑ |
| Missing folder created | `reports\report.csv`, no `reports\` | exit 1; file written | `test_output_creates_missing_folder` | ☑ |
| Missing folders created in full | `reports\2049\report.txt`, no `reports\` | exit 1; whole chain created | `test_output_creates_missing_folders_in_full` | ☑ |
| Write failure | folder is a file | exit 2; stderr: `FAIL ...` | `test_output_write_failure_exit_2` | ☑ |
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
| Real subprocess `athc profile diff` | OFF1 vs OFF2 | exit 1; report on stdout | `test_entry_point_subprocess` | ☑ |

---

# `athc profile copy`

In [test_profile_copy.py](test_profile_copy.py). Inputs: real `TST-OFF1/DEF1.prf` plus per-test mutated sources written to `tmp_path`. No rules (validate afterward with `check`). `ProfileWriter` unit tests live in `tests/unit/profile/test_writer.py`. Key rows use `build_teams` from [conftest.py](conftest.py).

## command (CliRunner)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Usage errors (no source / no target / no flag) | args | exit 2 | `test_cli_usage_errors_exit_2` `[P]` | ☑ |
| No copy option | SOURCE TARGET | exit 2; stderr ends `Error: At least one copy option is required (--stop-clock, --substitutions, --field-goal-range, --fourth-down, --goal-line, --pat-logic).` | `test_cli_no_copy_flag_is_a_sentence` | ☑ |
| TARGET count | 0 / 1 targets | one accepted; none: exit 2, `Missing argument 'TARGET...'.` | `test_cli_takes_one_or_more_targets` `[P]` | ☑ |
| No SOURCE | `--stop-clock` only | exit 2; `Missing argument 'SOURCE'.` | `test_cli_missing_source_argument` | ☑ |
| `--sub-percent` removed | option | exit 2; stderr: Click's "No such option '--sub-percent'" | `test_cli_sub_percent_option_removed` | ☑ |
| Help screen | `--help` | stdout == the plan's screen (78 columns) | `test_help_screen` | ☑ |
| Help uses uppercase names | `--help` | stdout: `[OPTIONS] SOURCE TARGET...`; no `source target` | `test_cli_help_uses_uppercase_names` | ☑ |
| Wildcard TARGET | `Off*.prf` in tmp | athc expands it: the two matches updated, the other untouched; exit 0 | `test_cli_wildcard_target` | ☑ |
| Copy stop-clock (offense / defense) | mutated src | exit 0; bits copied | `test_cli_copies_stop_clock_offense` / `_defense` | ☑ |
| Copy substitutions / field-goal-range | mutated src | exit 0; field copied; stdout: "updated (substitutions)" | `test_cli_copies_sub_percent` / `_field_goal_range` | ☑ |
| Goal-line + stop-clock combined | mutated src | exit 0; both applied | `test_cli_copies_goal_line_and_stop_clock_combined` | ☑ |
| Copy pat-logic / help lists it | mutated src / `--help` | exit 0; PAT table copied; stdout: "updated (pat-logic)" | `test_cli_copies_pat_logic` / `test_cli_help_lists_pat_logic` | ☑ |
| Updated line + summary | mutated src | stdout: `OK   <file>: updated (stop-clock)`; tally | `test_cli_prints_updated_line_and_summary` | ☑ |

## no backups / bulk / failures
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No backup written or reported | mutated src | no `.bak`; no backup note | `test_cli_writes_no_backup` | ☑ |
| `--no-backup` removed | option | exit 2; stderr: Click's "No such option" | `test_cli_no_backup_option_removed` | ☑ |
| Directory top-level / `-r` | dir | exit 0; stdout tally: 2 processed | `test_cli_directory_top_level_only` / `test_cli_directory_recursive` | ☑ |
| Offense source skips defense targets | dir mix | wrong side untouched | `test_cli_offense_source_skips_defense_targets` | ☑ |
| Single wrong-side target skipped | DEF1 target | exit 0; 0 processed; untouched | `test_cli_single_wrong_side_target_skipped` | ☑ |
| Continues past failed file | dir + bad | exit 2; stderr: `FAIL` for the bad file; stdout tally: 1 updated, 1 failed | `test_cli_continues_past_failed_file` | ☑ |
| Missing source / target | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; target untouched | `test_cli_missing_source_exit_2` / `test_cli_missing_target_exit_2` | ☑ |
| Target in a missing folder | tmp | exit 2; folder not created | `test_cli_missing_target_folder_not_created_exit_2` | ☑ |

## profile keys
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| 1st half to 2nd half | `off1 off2 --stop-clock` | exit 0; stdout: `OK   <DEN-OFF2>: updated (stop-clock)` and the tally; bits copied | `test_cli_key_to_key` | ☑ |
| File to two keys | `new.prf off1 off2 --substitutions` | exit 0; both `updated (substitutions)`; subs copied | `test_cli_file_to_two_keys` | ☑ |
| Offense key to defense keys | `off1 def1` / `off1 def1 def2` | exit 0; one `SKIP <file>: defense profile` per target; untouched | `test_cli_offense_key_to_defense_keys` `[P]` | ☑ |
| Key onto itself | `off1 off1` | exit 0; `SKIP <file>: the source profile` | `test_cli_key_onto_itself` | ☑ |
| Folder and key | `<folder> off2` | exit 0; the folder's files sorted, then off2's | `test_cli_folder_and_key` | ☑ |
| Key repeated | `off2 OFF2` | one update; "1 file(s) processed" | `test_cli_key_repeated_once` | ☑ |
| Missing key target | `off2 off1`, DEN-OFF2 deleted | exit 2; stderr: `FAIL <file>: ... or pass a .prf file.`; off1 updated; "1 failed" | `test_cli_missing_key_target_counts_failed` | ☑ |
| Missing key source | `off1 off2`, DEN-OFF1 deleted | exit 2; the `FAIL` line with the hint; stdout empty; target untouched | `test_cli_missing_key_source_touches_nothing` | ☑ |

---

# Profile keys (`profile check`, `diff`, `copy`)

In [test_team.py](test_team.py). `build_teams` in [conftest.py](conftest.py) builds the selected league with Denver, then Las Vegas (with `lg2_league` and `team`), each with its four profiles (`DEN-OFF1.prf` and the rest, copies of the TST files) at its league location; runs start in an empty folder. The `test_profile_*` modules import these helpers from conftest.py too. The team-name matching limits are check-ppp's tests of the same resolver.

## which operand is a key
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Each key, any case | `OFF1` / `Def1` / `oFF2` / `def2` | Denver's file for that key | `test_each_key_in_any_case` `[P]` | ☑ |
| Other words | `off` / `o1` / `off0` / `off3` | exit 2; stderr: `FAIL <word>: The system cannot find the file specified.` | `test_other_words_are_paths` `[P]` | ☑ |
| Extension or separator | `off1.prf` / `.\off1` | a missing path: the same line | `test_an_extension_or_a_separator_makes_a_path` `[P]` | ☑ |
| A file named `off1` | check / copy target / diff / copy source | exit 2; `FAIL off1: Not a .prf file.` (check, copy target); the reader's line (diff, copy source) | `test_a_file_named_like_a_key_is_that_file` `[P]` | ☑ |
| A folder named `off1` | check / empty / copy target | its `.prf` checked; `WARN off1: No .prf files.`, exit 0; its files updated | `test_check_a_folder_named_like_a_key` / `test_check_an_empty_folder_named_like_a_key` / `test_copy_into_a_folder_named_like_a_key` | ☑ |
| A folder named `off1` as one profile | diff / copy source | exit 2; stderr: `FAIL off1: Access is denied.` | `test_one_profile_from_a_folder_named_like_a_key` `[P]` | ☑ |
| Run from another folder | `off1` folder elsewhere | the key: Denver's file | `test_a_key_run_from_another_folder` | ☑ |

## where a key's profile is
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `ppp_path` | `off1 def2`, absolute `ppp_path` | the files in `ppp_path` | `test_ppp_path_holds_your_profiles` | ☑ |
| Relative `ppp_path` | `ppp_path = 'mine'` | under the league folder | `test_relative_ppp_path_is_under_the_league_folder` | ☑ |
| `ppp_path` with `--team` | `--team` naming the `team` team / another team / `team` unset / `team` matching none | `ppp_path` / that team's league location / Denver's league location (last two) | `test_ppp_path_with_team_option` `[P]` | ☑ |
| `--team` beats `team` | `team = 'Denver'`, `--team "Las Vegas"` | Las Vegas's file | `test_team_option_beats_team` | ☑ |
| `ppp_path` not a folder | missing / a file | exit 2; stderr: `FAIL <ppp_path>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER'.` / `The directory name is invalid.` with the same ending; stdout empty | `test_ppp_path_must_be_a_folder` `[P]` | ☑ |

## a key whose profile is not there
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Your team, league location | `off2` by `team` / `--team Broncos` | exit 2; stderr: `FAIL <file>: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .prf file.` | `test_missing_at_your_league_location_has_the_hint` `[P]` | ☑ |
| Its folder missing too | Denver's folder deleted | the path phrase, with the hint | `test_missing_folder_is_the_path_phrase` | ☑ |
| Another team | `--team Raiders` | the file phrase, no hint | `test_missing_for_another_team_has_no_hint` | ☑ |
| In `ppp_path` | empty `ppp_path` | `FAIL <ppp_path>\DEN-OFF2.prf: The system cannot find the file specified.`, no hint | `test_missing_in_ppp_path_has_no_hint` | ☑ |

## setup
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Team not set | a key run of check / diff / copy | exit 2; stderr: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or a .prf file.`; stdout empty | `test_team_not_set` `[P]` | ☑ |
| Team before `path` | neither set | the "Team is not set" line | `test_team_not_set_shows_before_path` | ☑ |
| `--team`, `team` unset | `--team Denver` | Denver's file | `test_team_option_with_team_unset` | ☑ |
| Setup before the files | `diff nope.prf off1`, `team` unset | the "Team is not set" line, not the missing file | `test_setup_comes_before_the_files` | ☑ |
| `path` not set | a key run of check / diff / copy | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass a .prf file.` | `test_path_not_set` `[P]` | ☑ |
| `.lge` missing | a key run of check / diff / copy | `FAIL <lge>: The system cannot find the file specified.` | `test_lge_missing` `[P]` | ☑ |
| Stock `.lg2` | a key run of check / diff / copy | `FAIL <lg2>: Stock league not supported.` | `test_stock_lg2` `[P]` | ☑ |
| `team` matches no team | `Denvr` | `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: ...` | `test_team_matches_no_team` | ☑ |
| `--team` matches no team | `--team Denvr` | `Error: Invalid value for '--team': no team named 'Denvr'. Teams: ...` | `test_team_option_matches_no_team` | ☑ |
| `team` an array | `['Denver']` | `FAIL <league.toml>: [league] team: Expected a string, got an array.` | `test_team_array` | ☑ |

## --team and --league
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--team` with no key | check: no PATH / a path / a wildcard; diff; copy | exit 2; stderr ends `Error: --team requires a profile key (off1, def1, off2 or def2).`; stdout empty | `test_team_option_needs_a_key` `[P]` | ☑ |
| `--league NOPE` | plain and key runs of check / diff / copy | exit 2; the league-not-found line | `test_unknown_league` `[P]` | ☑ |
| No league, plain files | no athc.ini, no league folder | diff and copy run, exit 0 | `test_plain_files_need_no_league` | ☑ |

---

# `athc check-ppp`

In [test_check_ppp.py](test_check_ppp.py). Same real `.prf` / `.pln` / pool as `profile check` and `gameplan check`; every rule comes from a tmp league folder (`build_league` in [conftest.py](conftest.py), `full_league`). Folder cases copy the TST files under their own names into tmp folders and build the `.lg2` from name pairs, with a `.lge` of real team names beside it (`lg2_league`, `team`, `lge` in conftest.py), so the goldens still apply; a pair whose files are never on disk prints nothing. The real-data cases use `pnfl_league` (conftest.py). Reports are compared to the existing `profile check` / `gameplan check` goldens in `expected/` (path normalized). Exit 0 clean / 1 findings / 2 error.

## arguments
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No path, no team | `full_league` | exit 2; stderr: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or --all-teams.` | `test_cli_requires_a_path` | ☑ |
| One file | profile / game plan alone | exit 2; stderr: `FAIL <path>: No game plan given. Run 'athc profile check' to check a profile alone.` (the game plan's names `athc gameplan check`); stdout empty | `test_cli_one_file_is_an_error` `[P]` | ☑ |
| One file of another kind | `plan.txt` | exit 2; stderr: `FAIL <path>: The directory name is invalid. Pass one profile and one game plan, or a folder.`; stdout empty | `test_cli_one_file_of_another_kind_is_an_error` | ☑ |
| One missing path | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the path specified.` | `test_cli_one_missing_path` | ☑ |
| Third path | 3 files | usage error on stderr, exit 2 | `test_cli_rejects_a_third_path` | ☑ |
| Path count | 2, 3, 4 paths | two are a pair; `Error: Got unexpected extra argument (x).` / `arguments (x y).`, exit 2 | `test_cli_path_count` `[P]` | ☑ |
| `--team` with `--all-teams` | both flags | exit 2; `Error: --team and --all-teams cannot be used together.` | `test_cli_team_and_all_teams_together` | ☑ |
| A team flag with two files | `--team` / `--all-teams` + a pair | exit 2; `Error: --team and --all-teams cannot be used with files.` | `test_cli_team_flag_with_two_files` `[P]` | ☑ |
| Help | `--help` | `[OPTIONS] [PATH]...`, `--team NAME`, `-a, --all-teams` | `test_help_shows_the_team_options` | ☑ |
| Usage line | `-h` | `[OPTIONS] [PATH]...` | `test_usage_is_clicks_own` (test_cli_root.py) | ☑ |
| Examples | `--help` | `athc check-ppp`, `athc check-ppp handed-in` | `test_examples_close_the_help` (test_cli_help.py) | ☑ |

## both files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Both = `profile check --gameplan` + `gameplan check` (both settings on) | OFF1 + offense.pln / DEF1 + defense.pln | exit 1; stdout: both goldens + one tally | `test_cli_both_matches_existing_reports` `[P]` | ☑ |
| Unused gameplan categories are info | DEF1 + defense.pln, unused-categories setting off | exit 1; 1 `game plan:` line, 4 `game plan info:` lines not counted | `test_cli_unused_gameplan_categories_are_info` | ☑ |
| Order does not matter | gameplan first | same stdout | `test_cli_file_order_does_not_matter` | ☑ |
| Clean both (mocked) | clean profile, info mocked | exit 0; stdout: two `OK` lines | `test_cli_both_clean_exit_0` | ☑ |
| Unused gameplan categories alone | clean profile, flags off, gameplan mocked | exit 0; 10 `game plan info:` lines | `test_cli_unused_gameplan_categories_alone_exit_0` | ☑ |
| Cross-check follows the league settings | each setting combination | missing categories count only when required; unused ones count when required, else 4 info lines | `test_cli_cross_check_follows_league_settings` `[P]` | ☑ |
| Side mismatch, both ways | OFF1 + defense.pln / DEF1 + offense.pln | exit 2; stderr: the mismatch `FAIL` line only; stdout empty | `test_cli_side_mismatch_stops_the_checks` `[P]` | ☑ |

## input and file errors
Argument errors check nothing, since both files are required.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing file | tmp + offense.pln | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.`; stdout empty | `test_cli_missing_file` | ☑ |
| Every input error reported | missing + `.txt` | both `FAIL` lines on stderr | `test_cli_reports_every_input_error` | ☑ |
| Wrong extension | OFF1 + `.txt` | exit 2; stderr: `FAIL <file>: not a .prf or .pln file`; stdout empty | `test_cli_wrong_extension` | ☑ |
| Directory next to a file | tmp dir + offense.pln | exit 2; stderr: `FAIL <path>: Access is denied.`; stdout empty | `test_cli_directory_next_to_a_file_is_not_a_file` | ☑ |
| Extension case-insensitive | `.PRF` + `.PLN` | exit 1 | `test_cli_extension_is_case_insensitive` | ☑ |
| Second file of a kind | 2 `.prf` / 2 `.pln` | exit 2; stderr: `FAIL` "pass one profile and one game plan"; stdout empty | `test_cli_second_file_of_a_kind_is_an_error` `[P]` | ☑ |
| Bad input checks nothing | OFF1 + `.txt` | exit 2; stderr: `FAIL`; stdout empty | `test_cli_bad_input_checks_nothing` | ☑ |
| File of the other kind | profile as `.pln`, gameplan as `.prf` | exit 2; stderr: `FAIL` line | `test_cli_file_of_the_other_kind_is_an_error` `[P]` | ☑ |
| Bad profile, gameplan still checked | tmp + data | exit 2; gameplan golden | `test_cli_bad_profile_still_checks_gameplan` | ☑ |
| Bad gameplan, profile still checked | data + tmp | exit 2; profile golden, no cross-check | `test_cli_bad_gameplan_still_checks_profile` | ☑ |
| Bad gameplan, clean profile (mocked) | data + tmp | exit 2; stdout: plain `OK` line; stderr: `FAIL` line | `test_cli_bad_gameplan_clean_profile_is_ok` | ☑ |
| Both unreadable | tmp | exit 2; both `FAIL` lines on stderr | `test_cli_both_unreadable_reports_both` | ☑ |

## league / rules config
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No league | empty config | exit 2; stderr: `FAIL League is not set ...`, once | `test_cli_no_league` | ☑ |
| Rules from `[athc] league` | league folder | exit 1 | `test_cli_rules_from_league_set_in_athc_ini` | ☑ |
| No profile / gameplan rules | league folder | exit 2; stderr: `FAIL No rules configured ...`; no `--rules` hint; neither file checked | `test_cli_no_profile_rules_in_league` / `test_cli_no_gameplan_rules_in_league` | ☑ |
| Rules error stops before the files | no profile rules; OFF1 + defense.pln | exit 2; stderr: `FAIL No rules configured ...` only, no mismatch line; stdout empty | `test_cli_rules_error_stops_before_the_files` | ☑ |
| Config error stops before the files | no league; OFF1 + broken.pln | exit 2; stderr: `FAIL League is not set ...` only; stdout empty | `test_cli_config_error_stops_before_the_files` / `test_cli_first_config_error_stops_the_run` | ☑ |
| No `play_path` / not a directory | league folder | exit 2; stderr: `FAIL`; no `--play-path` hint | `test_cli_no_play_path` / `test_cli_play_path_not_a_directory` | ☑ |
| Bad rules TOML | profile / gameplan | exit 2; stderr: `FAIL <file>: Not valid TOML: ...`; neither file checked | `test_cli_bad_rules_toml` `[P]` | ☑ |
| Rule lists in `league.toml` | `profile_rules` + `gameplan_rules` arrays | exit 1 | `test_cli_rule_lists_in_league_toml` | ☑ |
| Listed rules file missing | `*_rules` → absent file | exit 2; stderr: `FAIL` naming the path | `test_cli_missing_listed_rules_file` `[P]` | ☑ |
| Malformed `athc.ini` | bad ini | exit 2; stderr: `FAIL` naming athc.ini | `test_cli_malformed_ini` | ☑ |
| Two files need no `path` | `full_league` (none set) | every two-file case above | — | ☑ |

## a directory: the league file's pairs
Every case passes `--all-teams` unless it says otherwise; the tally adds `missing` and `team(s) with no files`.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Pairs in `.lg2` order, as two-file mode prints them | offense + defense pairs | exit 1; four goldens, offense first; "4 file(s)" | `test_dir_checks_each_pair_in_league_file_order` | ☑ |
| Clean (mocked) | clean profile + offense.pln | exit 0; stdout: two `OK` lines + tally | `test_dir_clean_exit_0` | ☑ |
| Teams in `.lg2` order | defense team, then offense team | defense goldens first | `test_dir_teams_in_league_file_order` | ☑ |
| 2nd-half pairs | both pairs in 2nd-half slots | exit 1; "4 file(s)" | `test_dir_second_half_pairs` | ☑ |
| Names ignore case | `.lg2` upper, file lower | exit 1; "2 file(s)" | `test_dir_names_ignore_case` | ☑ |
| Half a pair | profile without its gameplan | the profile checked alone; `WARN <dir>\offense.pln: The system cannot find the file specified.`; `1 missing` | `test_dir_half_a_pair_is_skipped` | ☑ |
| Unlisted files ignored | extra `.prf` / `.pln` | only the listed pair | `test_dir_unlisted_files_are_ignored` | ☑ |
| Shared gameplan once | one gameplan, two profiles | gameplan report once; 2nd profile's report = two-file mode's | `test_dir_shared_gameplan_is_reported_once` | ☑ |
| Profile in two pairs | one profile, two gameplans | profile reported twice; "4 file(s)" | `test_dir_profile_in_two_pairs_is_reported_twice` | ☑ |
| Same pair twice | two teams list it | checked once | `test_dir_same_pair_twice_is_checked_once` | ☑ |
| `.lg2` folders ignored | other folder in `.lg2` | exit 1 | `test_dir_league_file_folders_are_ignored` | ☑ |
| Subfolders not searched | pair in a subfolder | exit 0; stderr: `WARN <dir>: No files for 1 team(s): Denver.`; stdout: the tally | `test_dir_subfolders_are_not_searched` | ☑ |
| Empty directory | tmp | exit 0; stderr: the `WARN` "No files for 1 team(s)" line; stdout: the tally | `test_dir_empty` | ☑ |
| Unreadable directory | walk error | skipped silently, so the `WARN` "No files for 1 team(s)" line on stderr; exit 0 | `test_dir_unreadable_directory_has_no_pairs` | ☑ |
| Side mismatch is that pair's error | OFF1 + defense.pln, then DEF1 + defense.pln | exit 2; stderr: the mismatch `FAIL` line; stdout: DEF1 + defense goldens, tally | `test_dir_side_mismatch_is_that_pairs_error` | ☑ |
| Unreadable file | broken.prf + offense.pln | exit 2; stderr: `FAIL` line; stdout: offense golden | `test_dir_unreadable_file` | ☑ |
| Unreadable shared gameplan | two profiles, one broken.pln | exit 2; one `FAIL` line on stderr; both profiles on stdout | `test_dir_unreadable_shared_gameplan_is_reported_once` | ☑ |
| Expected error naming no file | stub check raises `AthcError` | exit 2; `FAIL <profile> + <gameplan>: <reason>` | `test_dir_expected_error_in_a_pair_is_its_fail_line` | ☑ |
| Setup error stops before the pairs / files | no profile rules | exit 2; stderr: `FAIL No rules configured ...` only; stdout empty | `test_dir_setup_error_stops_before_the_pairs` / `test_dir_setup_error_stops_before_the_files` | ☑ |
| No league | empty config | exit 2; stderr: `FAIL League is not set ...`, once | `test_dir_no_league` | ☑ |
| No `path` | `full_league` | exit 2; stderr: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass the folder.` | `test_dir_no_path` | ☑ |
| `team` read first | no `team`, `path` or profile rules; no team flag | exit 2; stderr: the "Team is not set" line only | `test_dir_first_setup_error_stops_the_run` | ☑ |
| Bad league file | invalid bytes | exit 2; stderr: `FAIL` with the library message naming the file | `test_dir_bad_league_file` | ☑ |
| Stock league file | old / modern stock `.lg2` | exit 2; stderr: `FAIL <file>: Stock league not supported.`; stdout empty | `test_dir_stock_league_file` `[P]` | ☑ |
| League file missing | `path` folder without `<league>.lg2` | exit 2; stderr: `FAIL` naming the file | `test_dir_league_file_missing` | ☑ |
| Relative `path` | `lg2` folder (`.lg2` and `.lge`) inside the league folder | exit 1 | `test_dir_relative_path_is_in_the_league_folder` | ☑ |

## a folder: missing files and teams with none
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Missing partner keeps the code | clean game plan, its profile missing | exit 0; `WARN` for the profile; `1 missing` | `test_dir_missing_partner_keeps_the_code` | ☑ |
| Shared game plan missing once | two profiles, their game plan missing | one `WARN`; both profiles checked alone | `test_dir_shared_gameplan_missing_once` | ☑ |
| Whole pair missing | defense pair absent | nothing for it; `0 missing` | `test_dir_whole_pair_missing_prints_nothing` | ☑ |
| Missing file in the league file's spelling | `.lg2` upper case, profile missing | `WARN <dir>\TST-OFF1.PRF: ...`; the found file in its on-disk spelling | `test_dir_missing_file_in_league_file_spelling` | ☑ |
| Your team with no files | other teams' files present / folder empty | exit 0; `WARN <dir>: No Las Vegas files. The league file names ...`; no team flag | `test_dir_your_team_with_no_files` `[P]` | ☑ |
| Each name once | Las Vegas (one game plan per side) | the names line lists `RAIDEROFF.pln` and `RAIDERDEF.pln` once | `test_dir_no_files_names_each_file_once` | ☑ |
| `--all-teams`: one line | 3 teams, one with files | `WARN <dir>: No files for 2 team(s): Denver, Jacksonville.`; `2 team(s) with no files` | `test_dir_all_teams_with_no_files_on_one_line` | ☑ |
| `--all-teams`, real league | `Denver (Brian)` | the 17 other teams in `.lge` order | `test_dir_all_teams_real_league` | ☑ |
| The tree is the scope | files in `week1`, `-r` | no "No Denver files" line; for another team one line naming the top folder | `test_tree_is_the_scope_for_no_files` | ☑ |

## a tree (`-r`)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Pairs in subfolders | pair in `week1` | exit 1; "2 file(s)" | `test_tree_finds_pairs_in_subfolders` | ☑ |
| Folder order | top, `_x`, `a week`, `a week\z`, `B week` | that order (by name, ignoring case; depth first), not the file system's | `test_tree_folder_order` | ☑ |
| Pair split across folders | profile on top, gameplan in a subfolder | each half checked alone in its own folder, its partner a `WARN`; `2 missing`; exit 1 | `test_tree_pair_split_across_folders_is_not_found` | ☑ |

## league files
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `.lge` missing | `.lge` deleted | exit 2; `FAIL <league>.lge: The system cannot find the file specified.` | `test_league_lge_missing` | ☑ |
| `.lg2` errors first | bad / stock `.lg2`, `.lge` missing | the `.lg2` line, no `.lge` line | `test_league_lg2_errors_come_first` `[P]` | ☑ |
| Team counts | `.lg2` of 2 / 1 / 3 teams, `.lge` of 2 | equal accepted; `FAIL <lg2>: Lists 1 team(s), but test_league.lge has 2.` (and 3) | `test_league_team_counts` `[P]` | ☑ |

## the team
`pnfl_league` unless it says otherwise; `team` added to its `league.toml`.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Name, nickname, both, any case | `team` / `--team` | Denver's 8 files at the league location | `test_team_by_name_nickname_or_both` `[P]` | ☑ |
| `team` matches no team | `Denvr` | `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: <every team>.` | `test_team_matches_no_team` | ☑ |
| `--team` matches no team | `Denvr` | `Error: Invalid value for '--team': no team named 'Denvr'. Teams: ...` | `test_team_option_matches_no_team` | ☑ |
| `team` matches two teams | built `.lge`, two New York teams | `FAIL <league.toml>: [league] team: 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | `test_team_matches_two_teams` | ☑ |
| Match count | `--team` Giants / Raiders / New York | one match accepted; none and two rejected (usage errors) | `test_team_option_match_count` `[P]` | ☑ |
| Blank `team` | `'  '` | the "Team is not set" line | `test_team_blank_is_not_set` | ☑ |
| `team` an array | `['Denver']` | `FAIL <league.toml>: [league] team: Expected a string, got an array.` | `test_team_array` | ☑ |
| `--team` beats `team` | `team = 'Denver'`, `--team "Las Vegas"` | Las Vegas's files | `test_team_option_beats_team` | ☑ |
| `--team` without your team | `team` unset / matching no team | `--team Denver` checks Denver at the league location | `test_team_option_without_your_team` `[P]` | ☑ |

## where the files come from
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `ppp_path` | `team` + `ppp_path` | the files there | `test_source_ppp_path` | ☑ |
| League locations | `team`, no `ppp_path` | the files where the league file puts them; three-field tally | `test_source_league_locations_without_ppp_path` | ☑ |
| `.` | the current folder, `ppp_path` set | the files there, by name | `test_source_current_folder` | ☑ |
| A folder | `ppp_path` set elsewhere | the folder's files | `test_source_folder` | ☑ |
| `ppp_path` for your team only | `--team Broncos` / `--team "Las Vegas"` / `--all-teams` | `ppp_path` / league locations / league locations | `test_source_ppp_path_is_for_your_team` `[P]` | ☑ |
| Relative `ppp_path` | `mine` | under the league folder | `test_source_relative_ppp_path` | ☑ |
| `ppp_path` not a folder | missing / a file | exit 2; `FAIL <ppp_path>: <Windows' phrase> Run 'athc config set ppp_path FOLDER'.` | `test_source_ppp_path_not_a_folder` `[P]` | ☑ |

## the league locations
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| One file missing | `DEN-OGP2.pln` deleted | exit 2; `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.`; `DEN-OFF2.prf` checked alone; `1 failed` | `test_league_one_file_missing` | ☑ |
| Shared game plan missing once | `RAIDEROFF.pln` deleted | one `FAIL` line; `1 failed` | `test_league_shared_gameplan_missing_once` | ☑ |
| `-r` ignored | `-r` | the same files | `test_league_recursive_is_ignored` | ☑ |
| Your team with no files | folder absent / empty | exit 2; one `FAIL <folder>: <path phrase or No Denver files.> Run 'athc config set ppp_path FOLDER' or pass the folder.`; `1 failed` | `test_league_no_files_for_your_team` `[P]` | ☑ |
| No hint for other teams | `--all-teams` / another team | the line without the hint; `--all-teams` adds `1 team(s) with no files` | `test_league_no_files_without_the_hint` `[P]` | ☑ |
| Unreadable subfolder | walk error on one folder | skipped silently; the rest checked; exit 1 | `test_tree_unreadable_folder_is_skipped` | ☑ |
| `-r` with two files | OFF1 + offense.pln | ignored; exit 1 | `test_tree_flag_with_two_files_is_ignored` | ☑ |

## real league data
`pnfl_league`: `data/PNFL.lg2` and `tests/unit/fbpro98_lge/data/PNFL.lge` (the PNFL league files, copied in as the test league's) and `data/ppp/2049/Plans/`: Denver's week 6 files, and the same files renamed to Las Vegas's names (one gameplan per side for both halves), also copied where the league file puts them.
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Every team folder | `--all-teams -r data/ppp` | no ERROR; 8 Denver + 6 Las Vegas files in `.lg2` order | `test_real_tree_checks_every_team_folder` | ☑ |
| Reads as two-file mode | `--all-teams -r data/ppp` | each pair's lines = two-file mode's; shared gameplan once | `test_real_tree_reads_as_two_file_mode` | ☑ |
| One team folder | `--team Denver`, `Denver (Brian)` | its 8 files | `test_real_team_folder_alone` | ☑ |

## --league and registration
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--league` beats `athc.ini` | two leagues | exit 1 | `test_league_flag_beats_athc_ini` | ☑ |
| `--league` picks the league files too | two leagues, one folder, a `.lg2` and `.lge` named after each; `--all-teams` | the other league's pairs | `test_league_flag_picks_the_league_file` | ☑ |
| `ATHC_LEAGUE` is ignored | env + folder, no `[athc] league` | exit 2; stderr: `FAIL League is not set ...` | `test_athc_league_env_is_ignored` | ☑ |
| Unknown league | `--league NOPE` | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_league_flag_unknown_folder` | ☑ |
| Listed in `athc --help` | — | stdout: "check-ppp" shown | `test_root_help_lists_check_ppp` | ☑ |

## Packaging check (real subprocess)
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real subprocess `athc check-ppp` | data + league | exit 1; tally on stdout; only `WARN` lines on stderr | `test_entry_point_subprocess` | ☑ |
| Errors go to stderr | missing file | exit 2; stdout empty; stderr: `FAIL <path>: The system cannot find the file specified.`; the run log holds the `FAIL` line and `exit 2` | `test_entry_point_errors_go_to_stderr` | ☑ |

---

# `athc playpool check`

In [test_playpool_check.py](test_playpool_check.py). Loads the pool the way the other commands do and prints its warnings, word for word, as findings. With no FOLDER it checks the league's `play_path`, and a missing or unset `play_path` gets the `Run 'athc config set play_path FOLDER'` hint; a FOLDER is checked instead and `play_path` is never read. A FOLDER needs no league, but a league that resolves (`--league` / `[athc] league`) still names the category folders (the `labeled_league` fixture: the selected league with the PNFL labels and no `play_path`). Exit 0 clean / 1 issues / 2 setup error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Clean tree | folder | exit 0; stdout: "<folder>: 1 play(s) checked, 0 issue(s)" | `test_clean_exit_0` | ☑ |
| Issues printed word for word | `labeled_league` + misfiled + duplicate | exit 1; stdout: both lines, blank, summary | `test_issues_print_word_for_word_exit_1` | ☑ |
| Named league must exist | folder + `--league NOPE` | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_dir_with_unknown_league_option_exit_2` | ☑ |
| Malformed league.toml with a folder | bad TOML + folder | exit 2; stderr: `FAIL` naming the file | `test_dir_with_malformed_league_toml_exit_2` | ☑ |
| No league: folder names mean nothing | misfiled play, no league | exit 0; 0 issues | `test_dir_without_league_knows_no_category_folders` | ☑ |
| Invalid file is an issue | bad `.ply` | exit 1; stdout: "<path>: <reason> Skipped." | `test_invalid_file_is_an_issue` | ☑ |
| Issues are results, not warnings | `labeled_league` + misfiled | exit 1; issues on stdout; stderr empty | `test_issues_are_results_not_warnings` | ☑ |
| Folder needs no league | no athc.ini, no leagues | exit 0 | `test_play_dir_needs_no_league` | ☑ |
| Default is the league's `play_path` | `[athc] league` | exit 0; path in summary | `test_default_is_current_league_play_path` | ☑ |
| `--league` picks another league | two leagues | other league's path | `test_league_option_picks_another_league` | ☑ |
| A FOLDER never reads `play_path` | league `play_path` missing on disk / an array + clean FOLDER | exit 0; no `FAIL`; the FOLDER in the summary | `test_folder_run_never_reads_play_path` `[P]` | ☑ |
| No folder and no league | empty config | exit 2; stderr: `FAIL League is not set ...` | `test_no_league_exit_2` | ☑ |
| League without `play_path` | league folder only | exit 2; stderr: `FAIL <league.toml>: Play pool folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` | `test_league_without_play_path_exit_2` | ☑ |
| League `play_path` not a folder | no FOLDER; `play_path` missing / a file | exit 2; stdout empty; stderr: `FAIL <play_path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` (`The directory name is invalid.` for a file) | `test_league_play_path_not_a_folder_gets_the_hint` `[P]` | ☑ |
| Folder missing | no such path | exit 2; stderr: `FAIL <path>: The system cannot find the path specified.`; stdout empty | `test_missing_play_dir_is_not_found_exit_2` | ☑ |
| Folder is a file | file | exit 2; stderr: `FAIL <path>: The directory name is invalid.`; stdout empty | `test_play_dir_not_a_directory_exit_2` | ☑ |
| Two FOLDERs | two clean folders | exit 2; stdout empty; stderr ends `Error: Got unexpected extra argument (<folder>).` | `test_two_folders_are_a_usage_error` | ☑ |
| No wildcard in FOLDER | `plays*` beside a `plays` folder | exit 2; stdout empty; stderr: `FAIL plays*: The system cannot find the path specified.` | `test_wildcard_folder_is_not_expanded` | ☑ |
| Read error while loading | pool reader raises | exit 2; stderr: `FAIL` with the message | `test_read_error_exit_2` | ☑ |
| Help screens | `--help` on `playpool` and `playpool check`, 78 wide as an 80-column console | exit 0; stdout: the whole screen, Examples last | `test_help_screen` `[P]` | ☑ |

---

# `athc autocontinue`

In [test_autocontinue.py](test_autocontinue.py). Config-driven (`athc.ini [autocontinue]`); the pyautogui watch loop is manual-only, so the CLI is tested with `auto_continue` stubbed (nothing touches the screen). `config_dir` fixture isolates `ATHC_CONFIG_DIR`. Exit 0 done (Ctrl-C is the normal stop) / 2 error.

## config / signature
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Valid INI loads both settings | tmp ini | `Config(0.5, 2.5)` | `test_load_config_reads_valid_section` | ☑ |
| No file | config_dir | `ConfigFileError` | `test_load_config_errors_when_no_config` | ☑ |
| Missing section / setting / bad value | tmp ini | `ConfigFileError` | `test_load_config_errors_when_section_missing` / `..._on_missing_setting` / `..._on_invalid_value` | ☑ |
| `hot_corner`: missing → on / parses bools / bad value | tmp ini | enabled / parsed / `ConfigFileError` | `test_hot_corner_defaults_enabled_when_missing` / `..._parses_boolean` `[P]` / `..._invalid_value_errors` | ☑ |
| Signature: missing / tuple / stable / changes | tmp | per change-detection | `test_signature_*` | ☑ |

## CLI
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--help` | — | exit 0; stdout: "Continue" | `test_cli_help_describes_continue` | ☑ |
| No config | config_dir | exit 2; stderr: `FAIL <athc.ini>: No [autocontinue] section. Add one, or set ATHC_CONFIG_DIR.` | `test_cli_no_config_exits_2` | ☑ |
| Missing dependency (pyautogui) | `sys.modules` stub | exit 2; stderr: `FAIL Missing pyautogui. Reinstall athc.` | `test_cli_missing_dependency_exits_2` | ☑ |
| Runs (stubbed) | tmp ini | exit 0; stub called | `test_cli_runs_with_config` | ☑ |
| `--hot-corner/--no-hot-corner` forwarded (else None) | tmp ini | value passed to the loop | `test_cli_forwards_hot_corner_override` `[P]` | ☑ |
| Ctrl-C exits clean (stubbed) | tmp ini | exit 0; stdout: `Shutting down AutoContinue` | `test_cli_keyboard_interrupt_exits_clean` | ☑ |
| Loop status through the callbacks | stub calls `progress` and `warn` | exit 0; stderr: the status line, then `WARN ...`; stdout: `Shutting down AutoContinue` | `test_loop_status_goes_to_stderr_through_the_callbacks` | ☑ |
| Missing button image | tmp ini; image path in an empty folder | exit 2 before watching; stderr: `FAIL <image>: The system cannot find the file specified. Reinstall athc.` | `test_cli_missing_button_image_exits_2_before_watching` | ☑ |

## button image and screen
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Shipped image loads | `continue_button.png` | one-channel (grayscale) image | `test_the_shipped_button_image_loads_in_grayscale` | ☑ |
| Missing image | tmp path | `AthcError`: `<image>: The system cannot find the file specified. Reinstall athc.` | `test_a_missing_button_image_fails_and_says_to_reinstall` | ☑ |
| Unreadable image | tmp file, not an image | `AthcError`: `<image>: Cannot read the image. Reinstall athc.` | `test_an_unreadable_button_image_fails_and_says_to_reinstall` | ☑ |
| The loaded image is searched for | stub matcher | gets the loaded image | `test_the_loaded_button_image_is_what_the_screen_is_searched_for` | ☑ |
| Screen hidden | stub matcher raises `OSError` | `The screen is locked, a screensaver is on, or Remote Desktop is disconnected. Retrying in 60 seconds.`; sleeps 60 | `test_screen_grab_failure_warns_and_backs_off` | ☑ |
| Config changes are said once each | first config, then one changed value | "MouseMoveDuration set to …", "DelayBeforeContinue set to …" | `test_config_changes_are_said_through_the_callback` | ☑ |
| Focus gating | window titles | the game title matches, case-insensitive substring | `test_game_has_focus_matches_title` `[P]` | ☑ |

---

# `athc convert-pdb`

In [test_convert_pdb.py](test_convert_pdb.py). Input: real `data/2045-2047.pdb`. Most cases use a selected league with the PNFL labels and order (`league_toml()` + `write_pdbtoexcel_toml`), whose `play_path` is an empty `tmp_path` folder, so the workbook builds with populated Tendencies and empty play sheets. **Golden regression**: the real `.pdb` converted against the curated `data/plays/` pool, the PNFL labels and order, both game plans (`-o`/`-d`) and the category worksheets on; every sheet's cells (read back with openpyxl, floats rounded to 6 places) must equal `expected/2045-2047.workbook.json`, one row per line. Regenerate with `python -m tests.integration.test_convert_pdb --bless`. Per-row behavior on constructed data is in `tests/unit/pdbtoexcel/test_workbook_creation.py`. Slot-column cases use `lg2_league` (a built `.lg2` and `.lge` with `offense.pln` and `defense.pln` as Denver's four game plans) or `pnfl_league` (the real 2049 league file and plans). Exit 0 done (warnings keep 0) / 2 usage or error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Help screen | `athc convert-pdb --help`, 78 columns | stdout equals the agreed screen, Examples last | `test_help_screen` | ☑ |
| No arguments | none | exit 2; stderr ends `Error: Missing argument 'PDB_FILE'.` | `test_no_arguments_is_missing_pdb_file` | ☑ |
| Bad pdb / output extension | args | usage error on stderr, exit 2 | `test_bad_extension_exit_2` `[P]` | ☑ |
| Extension error is a sentence | `in.txt` | stderr ends `Error: Invalid value for 'PDB_FILE': must have a .pdb extension.` | `test_bad_extension_is_a_sentence` | ☑ |
| `OUTPUT_FILE` not a workbook | `-`, a folder, a second `.pdb` | exit 2; stderr ends `Error: Invalid value for 'OUTPUT_FILE': must have a .xlsx or .xlsm extension.` | `test_output_file_must_be_a_workbook` `[P]` | ☑ |
| Bad `.pln` extension | `-o plan.txt` | usage error on stderr, exit 2 | `test_bad_pln_extension_exit_2` | ☑ |
| `-o2` / `-d2` not `.pln` | `-o2 plan.txt`, `-d2 plan.txt` | exit 2; hint `'-o2' / '--pln-off-2'` (`'-d2' / '--pln-def-2'`) | `test_second_plan_option_takes_a_pln_only` `[P]` | ☑ |
| Game plan key under `-o` | `-o off1` | exit 2; the `.pln` extension error | `test_plan_option_takes_no_game_plan_key` | ☑ |
| Removed options rejected | `--play-path`, `--playpool-rules`, `--skip-calcs` | exit 2; stderr: Click's "No such option" | `test_removed_options_are_rejected` `[P]` | ☑ |
| Missing PDB file | tmp | exit 2; stderr: `FAIL <path>: The system cannot find the file specified.` | `test_missing_pdb_exit_2` | ☑ |
| Wildcard matching nothing | `*.pdb` in an empty folder | exit 2; stderr: `FAIL *.pdb: The system cannot find the file specified.` | `test_wildcard_that_matches_nothing_is_a_missing_file` | ☑ |
| PDB is a folder | `x.pdb\` | exit 2; stderr: `FAIL <path>: Access is denied.` | `test_folder_given_for_the_pdb_exit_2` | ☑ |
| Play path not a directory | league `play_path` is a file | exit 2; stderr: `FAIL <path>: The directory name is invalid. Run 'athc config set play_path FOLDER'.`; `play_dir`, called by the command, raises `ConfigFileError` | `test_play_path_not_a_directory_exit_2` / `test_play_path_not_a_directory_is_a_config_error` | ☑ |
| Play path missing | `play_path` names no folder | exit 2; stderr: `FAIL <path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` | `test_play_path_missing_exit_2` | ☑ |
| No `play_path` | league folder without it | exit 2; stderr: `FAIL <league.toml>: Play pool folder is not set. Run 'athc config set play_path FOLDER'.`; no workbook | `test_no_play_path_exit_2` | ☑ |
| Missing `pdbtoexcel.toml` | league folder without it | exit 2; stderr: `FAIL` "pdbtoexcel.toml: The system cannot find the file specified." | `test_missing_pdbtoexcel_toml_exit_2` | ☑ |
| Output folder missing, one level | `reports\w1.xlsx`, no `reports\` | exit 0; folder created; file written | `test_missing_output_folder_created` | ☑ |
| Output folders missing, several levels | `reports\2049\w1.xlsx`, no `reports\` | exit 0; whole chain created; file written | `test_missing_output_folders_created_in_full` | ☑ |
| Output folder is a file | `reports` is a file | exit 2; stderr: `FAIL ...`; nothing written | `test_output_folder_is_a_file_exit_2` | ☑ |
| Workbook can't be written | output path is a folder | exit 2; last stderr line `FAIL <file>: ...`; no "unexpected error" | `test_unwritable_workbook_is_a_fail_line_not_a_bug` | ☑ |
| Invalid PDB content | tmp | exit 2; stderr: `FAIL <file>: invalid data type ...` | `test_invalid_pdb_content_exit_2` | ☑ |
| Produces `.xlsx` + sheets + tendencies | data + dir | exit 0; 5 sheets; 23x16 tendency rows | `test_produces_xlsx_with_sheets` | ☑ |
| Produces `.xlsm` | data + dir | exit 0; file written | `test_produces_xlsm` | ☑ |
| Default output | `GameLogs\49W6.pdb` alone | exit 0; `GameLogs\49W6.xlsm` written; `Creating` and `OK` name it | `test_default_output_is_beside_the_pdb` | ☑ |
| Default output replaced | `49W6.xlsm` already there | exit 0; a workbook again | `test_default_output_replaces_an_existing_one` | ☑ |
| Bare PDB name | `49W6.pdb` in the current folder | exit 0; `49W6.xlsm` there; stdout: `OK   49W6.xlsm: 0 play(s)` | `test_bare_pdb_name_writes_into_the_current_folder` | ☑ |
| `OUTPUT_FILE` wins | `reports\week6.xlsx` | exit 0; that file; no `.xlsm` beside the PDB | `test_output_file_given_wins` | ☑ |
| Percentages over the setting | `calculate_percentages` true / false × no flag, `--percentages`, `--no-percentages` | exit 0; "Fumble %" header when the flag, else the setting, says so | `test_percentages_override_the_setting` `[P]` | ☑ |
| Progress, warnings and the OK line | golden league + `-o`/`-d` | exit 0; stderr: `Creating <file>`, then only `WARN` lines; stdout: `OK   <file>: <n> play(s)`, n from the golden | `test_progress_on_stderr_warnings_and_ok_line` | ☑ |
| Empty pool | league with no plays | exit 0; stderr: `WARN Play '...' is not in the play pool.` per play; stdout: `OK   <file>: 0 play(s)` | `test_empty_pool_warns_per_play_and_writes_no_play_rows` | ☑ |
| No league set | no athc.ini | exit 2; stderr: `FAIL League is not set ...`, one line; stdout empty | `test_cli_no_league_is_one_line_error` | ☑ |
| Config from the league folder | `league.toml` | `play_path` resolved; a missing `play_path` is a `ConfigFileError` naming `league.toml` | `test_config_play_path_from_league_folder` / `test_config_missing_play_path_is_an_error` | ☑ |
| Real subprocess `athc convert-pdb` | data + dir | exit 0; stdout: `OK   <file>: 0 play(s)`; stderr: `Creating <file>`, then `WARN` lines | `test_entry_point_subprocess` | ☑ |
| Workbook matches golden | `.pdb` + `data/plays/` + `-o`/`-d` + category sheets | every cell equal to `expected/2045-2047.workbook.json` | `test_workbook_matches_golden` | ☑ |
| `-o` alone, team set | `team` set, plans in place, `-o try3.pln` | exit 0; no plan line; offense Slot 1 shown and filled, the other three hidden | `test_plan_option_fills_its_slot_alone` | ☑ |
| Plan option reads no league file | `team` set, no `path`, `-d` | exit 0 | `test_plan_option_reads_no_league_file` | ☑ |
| `-o2` / `-d2` alone | `-o2`, `-d2` | exit 0; Slot 2 shown and filled, Slot 1 hidden | `test_second_half_option_alone_shows_slot_2` | ☑ |
| Named plan on the wrong side | defense plan under `-o`/`-o2`, offense under `-d`/`-d2` | exit 2; stderr: `FAIL <path>: Not an offense game plan.` (`Not a defense game plan.`); nothing written | `test_plan_option_on_the_wrong_side_fails` `[P]` | ☑ |
| `--team` / `--path` with a plan option | each flag alone, then with `-o` | alone exit 0; with `-o` exit 2, `Error: --team cannot be used with -o, -o2, -d or -d2.` (`--path` the same) | `test_team_and_path_never_mix_with_a_plan_option` `[P]` | ☑ |
| Both flags with a plan option | `--path`, `--team`, `-d2` | exit 2; the `--team` line | `test_team_is_checked_before_path` | ☑ |
| Team plans at the league location | `team = 'Denver'`, four plans there | exit 0; four `<path>: Denver 1st-half offense, Slot 1` lines in `.lg2` order; every Slot column shown and filled | `test_team_plans_fill_every_slot` | ☑ |
| Real league file | `pnfl_league`, `team = 'Denver'` | Denver's four lines from its 2049 folder | `test_team_plans_from_the_real_league` | ☑ |
| Shared plan | `--team "Las Vegas"` (one plan per side) | `<path>: Las Vegas offense, both halves, Slot 1` (defense too); Slot 2 hidden | `test_shared_plan_fills_slot_1_alone` | ☑ |
| Missing plan | `DEN-OGP2.pln` gone | exit 0; `WARN <path>: The system cannot find the file specified. Offense Slot 2 is hidden. Run 'athc config set ppp_path FOLDER' or pass --path.`; that column hidden | `test_missing_plan_warns_with_the_hint` | ☑ |
| Missing 1st-half plan | `DEN-OGP1.pln` gone | offense Slot 1 hidden; Slot 2 shown and filled | `test_missing_first_half_plan_keeps_slot_2` | ☑ |
| Shared plan missing | both offense halves name `SHARED.pln`, absent | one `WARN ... Offense Slot 1 is hidden.` with the hint; both offense columns hidden | `test_shared_plan_missing_is_one_warning` | ☑ |
| Team folder absent | no league location folder | one `WARN <folder>: The system cannot find the path specified.` with the hint; every Slot column hidden | `test_team_folder_absent_is_one_warning` | ☑ |
| Team folder empty | folder, no plans | one `WARN <folder>: No Denver game plans.` with the hint | `test_team_folder_with_none_of_the_plans_is_one_warning` | ☑ |
| Defaulted plan on the wrong side | defense plan as `DEN-OGP1.pln` | `WARN <path>: Not an offense game plan. Offense Slot 1 is hidden.`; column hidden | `test_plan_on_the_wrong_side_warns` | ☑ |
| Defaulted plan unreadable | 3 bytes as `DEN-DGP2.pln` | `WARN <path>: File too small to contain PLN header and offsets table. Defense Slot 2 is hidden.` | `test_unreadable_plan_warns` | ☑ |
| `--path` without case | lowercase names | the four lines with the on-disk names | `test_path_finds_the_plans_without_case` | ☑ |
| `--path` missing plan | three of four | `WARN ... Defense Slot 2 is hidden.`, no hint | `test_path_missing_plan_warns_without_the_hint` | ☑ |
| `--path` with 0 or 1 plans | none; `DEN-OGP1.pln` only | 0: one `WARN <folder>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.`; 1: its line plus a `WARN` per missing plan, no hint | `test_path_with_none_of_the_plans` `[P]` | ☑ |
| `--path` subfolders | plans only in `wk5\sub` | the "No Denver game plans" line | `test_path_searches_no_subfolder` | ☑ |
| `--path` beats `ppp_path` | both set | lines from `--path` | `test_path_wins_over_ppp_path` | ☑ |
| `--path` not a folder | missing; a file | exit 2; `FAIL <folder>: The system cannot find the path specified.` / `The directory name is invalid.`; nothing written | `test_path_must_be_a_folder` `[P]` | ☑ |
| `ppp_path` without case | uppercase names | the four lines from `ppp_path` | `test_ppp_path_finds_the_plans_without_case` | ☑ |
| Relative `ppp_path` | `ppp_path = 'plans'` | found under the league folder | `test_ppp_path_relative_to_the_league_folder` | ☑ |
| `ppp_path` missing plan | three of four | `WARN ... Offense Slot 1 is hidden.`, no hint | `test_ppp_path_missing_plan_warns_without_the_hint` | ☑ |
| `ppp_path` for your team only | `team = 'Denver'`, `--team "Las Vegas"` | Las Vegas's league location | `test_ppp_path_is_for_your_team_only` | ☑ |
| Your team named by `--team` | `--team Broncos` | lines from `ppp_path` | `test_ppp_path_for_your_team_named_with_the_option` | ☑ |
| `ppp_path` not a folder | missing; a file | exit 2; `FAIL <ppp_path>: <phrase> Run 'athc config set ppp_path FOLDER'.` | `test_ppp_path_must_be_a_folder` `[P]` | ☑ |
| Team by name, nickname or both | `Denver`, `Broncos`, `denver broncos` | Denver's four lines | `test_team_by_name_nickname_or_both` `[P]` | ☑ |
| `--team` beats `team` | `team = 'Las Vegas'`, `--team Denver` | Denver's lines | `test_team_option_beats_team` | ☑ |
| `--team` without `team` | `DEN-OGP2.pln` gone | its `WARN` has no hint (not your team) | `test_team_option_without_team` | ☑ |
| `team` matches no team | `team = 'Denvr'` | exit 2; `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: Denver Broncos.` | `test_team_matches_no_team` | ☑ |
| `--team` matches two teams | two New York teams | exit 2; usage error naming both; no `WARN` | `test_team_option_matches_two_teams` | ☑ |
| No team, nothing asked | no `team`, no flag | exit 0; no plan line; Slot columns hidden | `test_no_team_and_nothing_asked_for_is_silent` | ☑ |
| `--path` with no team | no `team` | exit 2; `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team.` | `test_path_without_a_team_fails` | ☑ |
| Team in play, no `path` | `team` set; `--team`; no team with `--path` | exit 2; `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass a game plan with -o, -o2, -d or -d2.`; with no team, the team line comes first | `test_team_in_play_needs_path` `[P]` | ☑ |
| `.lge` missing | `.lge` deleted | exit 2; `FAIL <lge>: The system cannot find the file specified.` | `test_league_lge_missing` | ☑ |
| League files disagree | `.lg2` 2 teams, `.lge` 1 | exit 2; `FAIL <lg2>: Lists 2 team(s), but test_league.lge has 1.` | `test_league_team_counts_differ` | ☑ |

---

# `athc generate-schedule`

In [test_generate_schedule.py](test_generate_schedule.py). Slow (a full solve per league) → `pytest -m slow`; not run by default. One test parametrized over two test leagues — `divisions` (the real 2048 PNFL season: `data/PNFL-2047-after-super-bowl.lge` and `data/PNFL-2048-after-week1.lge`) and `conferences` (2029: `data/conferences-previous.lge` and `data/conferences-upcoming.lge`, built by `league_files.py` from the test league's tables). For each it copies the two league files to `previous/<league>.lge` and `upcoming/<league>.lge`, installs the league in the config dir as `leagues/<league>/` — a `league.toml` whose `path` is the `upcoming/` folder (so the upcoming file is the default `--upcoming`) and the frozen `data/<league>.scheduler.toml` as `scheduler.toml` — then runs the scheduler end-to-end via the CLI (`athc generate-schedule --league <league> --previous previous/<league>.lge`) at a fixed seed (no `--time-limit`; the rules file drives the solve). **Golden regression**: validates the produced schedule against every rule that applies to that league (`schedule_validation.py`, the one validator), cross-checks that the `.html` schedule encodes the same games as the `.txt`, recomputes the report's ranks/SOS, then asserts the three output files byte-match the league's goldens in `expected/` (`schedule_<season>.*`; report run-info fields normalized). Depends on the fixed `solver_workers` reproducibility contract. Regenerate the built conference files and both golden sets with `python -m tests.integration.test_generate_schedule --bless`. Two fast tests guard the built files: they reproduce the conference test league exactly, and the committed bytes match the builder.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Schedule follows every rule + matches golden, per league | the two `.lge` files; `--league`, `--season --previous --seed` | exit 0; all rules pass; 3 files byte-equal to that league's `expected/` goldens | `test_generate_schedule_matches_golden[divisions]` / `[conferences]` | ☑ |
| Built conference files | `league_files.py` | reproduce the conference test league; committed bytes match | `test_conference_league_files_reproduce_the_test_league`, `test_committed_conference_league_files_match_the_builder` | ☑ |

---

# `athc.config` — league resolution (shared)

In [test_config.py](test_config.py). Direct tests of `load_league_config()` / `load_league()`, the shared resolver every `--league` tool calls. Reads an isolated `athc.ini` and `leagues/<NAME>/league.toml` (the `config_dir` / `make_league` fixtures) → integration tier, not unit. A league is a folder under `leagues/`; `[athc] league` names the default. `gameplan` / `profile` also exercise resolution through their CLIs.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Explicit `--league` arg | `leagues/<NAME>/league.toml` | `[league]` dict | `test_resolves_explicit_league_arg` | ☑ |
| From `[athc] league` | key + folder | `[league]` dict | `test_resolves_from_configured_league` | ☑ |
| `LeagueConfig` name / dir / values | folder | as on disk; missing `league.toml` → `{}` | `test_league_config_names_folder` / `test_missing_league_toml_gives_empty_values` | ☑ |
| Relative paths in `league.toml` | `play_path = 'plays'` | resolved against the league folder | `test_path_resolves_relative_against_league_dir` | ☑ |
| Fixed rules file / rule list | `gameplan.toml`, `gameplan_rules` array | fixed file when present, else `()`; array replaces it in order | `test_rules_file_only_when_present` / `test_rule_files_*` | ☑ |
| None resolvable → lists folders | two folders | `LeagueError`; names `athc config set league`; "Available: <both names, sorted>" | `test_no_league_resolvable_lists_available` / `test_no_league_and_no_folders` | ☑ |
| Unknown league name | ask missing | `LeagueError` "not found"; lists folders | `test_unknown_league_errors` | ☑ |
| Blank `league =` | key empty | "League is not set" | `test_empty_league_key_is_no_league` | ☑ |
| Path segments in a name (`..`, `a\b`) | bad names | `LeagueError` "not found" | `test_league_dir_rejects_path_segments` `[P]` | ☑ |
| Blank name (`""`, `"   "`) | blank | `LeagueError` "not found" (never the `leagues/` folder itself) | `test_league_dir_rejects_blank_names` `[P]` | ☑ |
| `resolve_league()` returns the name | arg / key; none; unknown | name; `LeagueError` | `test_resolve_league_returns_the_explicit_name` / `test_resolve_league_falls_back_to_configured` / `test_resolve_league_errors_*` | ☑ |
| Blank `--league` arg | `"   "` + `[athc] league` | configured league used | `test_resolve_league_blank_arg_is_no_arg` | ☑ |
| Malformed `athc.ini` / `league.toml` | bad INI / bad TOML | `ConfigFileError` names the file | `test_malformed_athc_ini_errors` / `test_malformed_league_toml_errors` | ☑ |
| `athc.ini` that cannot be opened | a folder named `athc.ini` | `<athc.ini>: Access is denied.`, never read as empty | `test_an_athc_ini_that_cannot_be_opened_fails_in_windows_words` | ☑ |
| UTF-8 BOM in `league.toml` | BOM-prefixed file | skipped; values read | `test_bom_in_league_toml_is_skipped` | ☑ |
| `%` in `league.toml` | `'%LOCALAPPDATA%\plays'` | loads literally (no interpolation) | `test_percent_in_league_toml_is_literal` / `test_no_interpolation_in_league_toml` | ☑ |
| `[league]` strings vs arrays | string + array | `values` / `lists` | `test_league_list_is_kept_apart_from_values` | ☑ |
| `[league]` wrong value type | int, array with int, inline table | `ConfigFileError` "expected a string or an array of strings", names the file | `test_league_value_wrong_type_errors` `[P]` | ☑ |
| `[league]` not a table | `league = 1` | `ConfigFileError` "[league]: Must be a table." | `test_league_section_not_a_table_errors` | ☑ |
| Known key in the wrong shape | `play_path = ['x']`; `gameplan_rules = 'x'` | `path()` / `rule_files()` raise `ConfigFileError` naming the file | `test_path_rejects_an_array_value` / `test_rule_files_rejects_a_string_value` | ☑ |
| `string()` | a value, spaces around it, blank, absent | the value without its spaces; `None` for blank and absent | `test_string_value` `[P]` | ☑ |
| `string()` of an array | `team = ['x']` | `ConfigFileError` `[league] team: Expected a string, got an array.` naming the file | `test_string_rejects_an_array_value` | ☑ |
| `[categories]` load | PNFL tables | `cfg.categories == PNFL_LABELS` | `test_categories_load` | ☑ |
| `[categories]` absent / one side | none; defense only | `CategoryLabels()`; offense empty | `test_categories_absent_is_no_labels` / `test_one_side_only_loads` | ☑ |
| `[categories]` errors | unknown key, empty / non-string label, duplicate, game-name label, non-table | `ConfigFileError` names the file | `test_categories_errors_name_the_file` `[P]` | ☑ |
| `play_dir()` of a folder | folder | the folder | `test_play_dir_is_the_folder` | ☑ |
| `play_dir()` missing / a file | no such folder; a file | `ConfigFileError` `<path>: <Windows' phrase> Run 'athc config set play_path FOLDER'.` | `test_play_dir_missing` / `test_play_dir_is_a_file` | ☑ |

## `--league` (per command)

In [test_cli_root.py](test_cli_root.py). `--league` is an option on each league-aware command (the shared `league_option`), not on the root group.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Root `--help` has no `--league` | `athc --help` | exit 0; stdout: `--league` absent | `test_root_help_has_no_league` | ☑ |
| Root rejects `--league` | `athc --league <NAME> profile check` | exit 2; stderr: Click's "No such option" | `test_root_rejects_league` | ☑ |
| Every league-aware command takes `--league` | `--help` per command | stdout: `--league NAME  League to use (default: the one set with athc config set league).` | `test_league_commands_take_league` `[P]` | ☑ |
| `-h` on every command and group | `-h` per command | exit 0; stdout: "Usage:" | `test_short_help_option_on_every_command` `[P]` | ☑ |
| Usage line is Click's own | `-h` on the root, a group and several commands | exact usage line: `[OPTIONS]`, then the arguments; a group ends in `COMMAND [ARGS]...` | `test_usage_is_clicks_own` `[P]` | ☑ |
| Help uses uppercase names | `--help` on `convert-pdb`, `gameplan check`, `find-play`, `replace-play`, `list-normals`, `set-normals`, `set-specials`, `generate-schedule`, `playpool check`, `profile check`, `profile copy`, `profile diff`, `check-ppp` | stdout: UPPERCASE placeholders (generate-schedule: `--season YEAR`, `--previous FILE`, `--upcoming FILE`, `--seed NUMBER`, `--time-limit LIMIT`); not the old names (generate-schedule: `INTEGER`, `--season year`) | `test_help_uses_uppercase_names` `[P]` | ☑ |
| One positional past the last | `convert-pdb`, `list-normals`, `list-specials`, `set-normals`, `set-specials`, `profile diff`, `config set`, `config get`, `config path`, `playpool check`, each with all its positionals + `x` | exit 2; stderr ends `Error: Got unexpected extra argument (x).` (the last positional accepted: each command's own tests) | `test_one_positional_past_the_last_is_rejected` `[P]` | ☑ |
| `-r` reads the same | `--help` on every command with `-r` | stdout: `-r, --recursive  Include subfolders.` | `test_recursive_option_reads_the_same` `[P]` | ☑ |
| Each command passes `--league` on | `--league NOPE` per command | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_league_flag_reaches_the_command` `[P]` | ☑ |
| `--league` after the command reaches `profile check` | two leagues | exit 1 (the other league's rules used) | `test_league_flag_picks_profile_rules` | ☑ |
| `ATHC_LEAGUE` is ignored | env set, no `[athc] league` | exit 2; stderr: `FAIL League is not set ...` | `test_root_ignores_athc_league_env` | ☑ |

## Help style (every command)

In [test_cli_help.py](test_cli_help.py). The ranges are checked on constructed text at their limits; the description and examples checks also run on every leaf command, and the summary check on every command and group (the one over 55 characters, `autocontinue`, is a strict expected failure until its 2.0.0 plan shortens it).

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Summary limit | 55 / 56 characters | fits / does not | `test_summary_limit` `[P]` | ☑ |
| Description range | 0, 1, 4, 5 lines | fails, fits, fits, fails | `test_description_range` `[P]` | ☑ |
| Description lines are wrapped lines | one long paragraph | 2 lines at 80 columns | `test_description_counts_wrapped_lines` | ☑ |
| Examples range | 0, 1, 6, 7 examples | fails, fits, fits, fails | `test_examples_range` `[P]` | ☑ |
| No epilog | `None` | 0 examples | `test_no_epilog_has_no_examples` | ☑ |
| Examples close the help | `--help` on `check-ppp` and the gameplan subcommands but `check` | stdout ends with `Examples:` and its lines; count in range | `test_examples_close_the_help` `[P]` | ☑ |
| Every summary fits the command list | each command and group | 55 characters or fewer | `test_summary_fits_the_command_list` `[P]` | ☑ |
| Every description and example count in range | each leaf command but `autocontinue` (its help comes with its 2.0.0 plan) | 1 to 4 description lines; 1 to 6 examples | `test_description_fits_the_range` / `test_examples_fit_the_range` `[P]` | ☑ |
| Argument help lines | `--help` | each argument's help in "Positional arguments", under its bare name (`PATH`, `FOLDER`) | `test_argument_help_line` `[P]` | ☑ |
| Whole help screens | `--help` on `gameplan` and each of its subcommands, 80-column console | stdout equals the screen exactly | `test_help_screen` `[P]` | ☑ |
| Windows words | `--help` on each command and group | no "directory", "stdout", "glob", "config dir", "CTRL-C", "file manager" | `test_help_uses_windows_words` `[P]` | ☑ |

## `athc config set`

In [test_config_set.py](test_config_set.py). `set_config_value` rewrites `athc.ini` through ConfigUpdater and `set_league_value` the league's `league.toml` through tomlkit; the CLI matches the key without case and checks the league folder.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Update keeps comments | commented ini | value changed; every comment kept | `test_set_updates_value_and_keeps_comments` | ☑ |
| Missing key / section / file | partial or no ini | created in place | `test_set_adds_missing_key` / `test_set_adds_missing_section` / `test_set_creates_missing_file` | ☑ |
| CLI sets league | folder exists | exit 0; stdout: `OK   <athc.ini>: league = <NAME>` | `test_cli_sets_league` | ☑ |
| CLI unknown league | no folder | usage error on stderr, exit 2; "not found"; file untouched | `test_cli_rejects_unknown_league` | ☑ |
| CLI blank league | `""` | usage error on stderr, exit 2; "not found"; file untouched | `test_cli_rejects_blank_league` | ☑ |
| CLI malformed `athc.ini` | `[athc` broken | exit 2; stderr: `FAIL` naming athc.ini, no traceback; stdout empty; file left as written | `test_cli_malformed_ini_is_clean_error` | ☑ |
| CLI unknown key | `colour` | exit 2; stderr: `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.`; file untouched | `test_cli_rejects_unknown_key` | ☑ |
| Help / group listing | `--help` | stdout lists `league` / `set` | `test_cli_help_lists_known_keys` / `test_group_lists_set` | ☑ |
| CLI key in any case | `League <NAME>` | exit 0; `league = <NAME>` written once; stdout: `OK   <athc.ini>: league = <NAME>` | `test_cli_sets_league_in_its_canonical_spelling` | ☑ |
| CLI league without VALUE | `league` | exit 2; stderr: `Error: Missing argument 'VALUE'.`; file untouched | `test_cli_league_needs_a_value` | ☑ |
| CLI no KEY | nothing | exit 2; stderr: `Error: Missing argument 'KEY'.` | `test_cli_needs_a_key` | ☑ |
| CLI a word too many | `league <NAME> x` | exit 2; stderr: `Error: Got unexpected extra argument (x).`; file untouched | `test_cli_a_word_too_many` | ☑ |
| CLI `set league` with `--league` | `league <A> --league <B>` | exit 2; stderr: `Error: --league cannot be used with set league.`; `athc.ini` untouched | `test_cli_set_league_refuses_a_named_league` | ☑ |
| CLI sets a `league.toml` key | `path`, `play_path`, `team`, `ppp_path` + value | exit 0; stdout: `OK   <league.toml>: <key> = <value>`; written under `[league]`; every other line kept | `test_cli_sets_a_league_key` `[P]` | ☑ |
| CLI new key after its example | the shipped `config/release/leagues/PNFL/league.toml`; `team Denver`, then `ppp_path D:\PNFL\Denver` | each line right after its `# <key> = ...` example; every old line kept, in order | `test_cli_adds_a_key_after_its_example` | ☑ |
| CLI new key, no example | `[league]` with a key, or with comments only, then a comment and the next table | the line after the last key line, or after the header; never under the next table's comment | `test_cli_adds_a_key_with_no_example` `[P]` | ☑ |
| CLI new key, no `[league]` header line | `league = { path = ... }` | written as tomlkit adds it | `test_cli_adds_a_key_to_an_inline_league_table` | ☑ |
| CLI `league.toml` key in any case | `Play_Path` | `play_path` written | `test_cli_writes_the_canonical_key` | ☑ |
| CLI folder as supplied | relative `ppp_path`; `path` that does not exist | exit 0; written as given | `test_cli_writes_a_folder_as_supplied` `[P]` | ☑ |
| CLI `--league NAME` | two leagues | that league's `league.toml` written; the other unchanged | `test_cli_league_key_in_the_named_league` | ☑ |
| CLI league key, no league set | no athc.ini | exit 2; stderr: `FAIL League is not set ...`; file unchanged | `test_cli_league_key_with_no_league_set` | ☑ |
| CLI league key, `--league NOPE` | no such folder | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_cli_league_key_with_an_unknown_league` | ☑ |
| CLI `league.toml` missing / no `[league]` | folder only; other tables only | exit 2; stderr: `FAIL <league.toml>: The system cannot find the file specified.`; nothing created or changed | `test_cli_league_key_with_no_league_toml` / `test_cli_league_key_with_no_league_section` | ☑ |
| CLI malformed `league.toml` | `[league` broken | exit 2; stderr: `FAIL <league.toml>: Not valid TOML: ...`; file unchanged | `test_cli_league_key_with_a_malformed_league_toml` | ☑ |
| Help screen | `config set --help` | stdout: the agreed screen, 78 wide; KEY lists the five keys; `--league NAME` | `test_help_screen` | ☑ |

## shipped `config/release/`

`ATHC_CONFIG_DIR` is pointed at `config/release/` itself (the `release_config_dir` fixture), so `athc.ini` and every `leagues/<NAME>/` are read exactly as installed. Every league folder runs the same tests: each loader must load, and every rule file it resolves must exist.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| At least one league ships | config/release/ | league folders found | `test_release_ships_leagues` | ☑ |
| `[athc] league` names a shipped league | config/release/ | loads | `test_release_selected_league_loads` | ☑ |
| Every league | config/release/ | play_path and path set; category labels present | `test_release_league_loads` `[P]` | ☑ |
| `[autocontinue]` | config/release/ | loads | `test_release_autocontinue_section_loads` | ☑ |
| gameplan, every league | config/release/ | loads; rule files exist | `test_release_gameplan_config_loads` `[P]` | ☑ |
| profile, every league | config/release/ | loads; rule files exist | `test_release_profile_config_loads` `[P]` | ☑ |
| convert-pdb, every league | config/release/ | loads; reads the league's `pdbtoexcel.toml` | `test_release_convert_pdb_config_loads` `[P]` | ☑ |
| `[convert-pdb]` options | config/release/ | spelled out in `athc.ini`; sacks counted as attempts | `test_release_convert_pdb_defaults` | ☑ |
| scheduler, every league | config/release/ | the rules path is the league folder's `scheduler.toml`; it loads | `test_release_scheduler_files_load` `[P]` | ☑ |
| `config/dev/` mirrors `config/release/` | both | same `athc.ini`, `league.toml` and rules files | `test_dev_mirrors_release_layout` | ☑ |

---

# `athc config`

In [test_config.py](test_config.py) (alongside the resolver tests above). Thin commands over the settings files, `athc.ini` and a league's `league.toml`; app / Explorer launches are mocked.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Group lists subcommands | `--help` | stdout: path / edit / reveal / get listed | `test_group_lists_subcommands` | ☑ |
| `path` prints the file path | config_dir | stdout: the full `athc.ini` path | `test_path_prints_config_file` | ☑ |
| `reveal` selects the file | existing ini | `launch(<athc.ini>, locate=True)` | `test_reveal_selects_existing_file` | ☑ |
| `reveal` opens the folder if absent | config_dir | `launch(<dir>)` | `test_reveal_opens_folder_when_absent` | ☑ |
| `edit` opens the default app | config_dir | file created; `os.startfile(<athc.ini>)` | `test_edit_opens_associated_app` | ☑ |
| `edit` ignores `$VISUAL`/`$EDITOR` | both set | `os.startfile(<athc.ini>)`; no `edit` | `test_edit_ignores_editor_env` | ☑ |
| `edit` keeps existing file | existing ini | content unchanged | `test_edit_preserves_existing_file` | ☑ |
| `edit`, no app for the file | `os.startfile` raises winerror 1155 | exit 2; stderr: `FAIL <athc.ini>: No application is associated with the specified file for this operation.` | `test_edit_reports_a_file_windows_cannot_open` | ☑ |
| `edit league.toml`, file missing | league folder only | exit 2; stderr: `FAIL <league.toml>: The system cannot find the file specified.`; nothing created or opened | `test_edit_league_toml_missing_fails` | ☑ |
| `edit league.toml` | file present | exit 0; `os.startfile(<league.toml>)`; content kept | `test_edit_league_toml_opens_it` | ☑ |
| `reveal league.toml` | file present / missing | `launch(<league.toml>, locate=True)` / `launch(<league folder>)` | `test_reveal_league_toml_selects_it` / `test_reveal_league_toml_missing_opens_the_league_folder` | ☑ |
| FILE `league.toml`, any case | `league.toml` / `League.TOML`, league set | stdout: that league's `league.toml` path | `test_league_toml_is_the_league_in_use` `[P]` | ☑ |
| `path league.toml`, file missing | league folder only | exit 0; stdout: the path; nothing created | `test_path_league_toml_missing_prints_the_path` | ☑ |
| FILE neither name | `PCFL` | exit 2; stderr: `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` | `test_file_rejects_another_word` | ☑ |
| A word too many | `path`, `edit`, `reveal`, `get` + `x` | exit 2; stderr: `Error: Got unexpected extra argument (x).`; nothing launched | `test_a_word_too_many` `[P]` | ☑ |
| `--league NAME`, no FILE or `league.toml` | `--league <OTHER>` | stdout: that league's `league.toml` path | `test_named_league_is_its_league_toml` `[P]` | ☑ |
| `athc.ini --league NAME` | a league / `NOPE` | stdout: the `athc.ini` path / exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_athc_ini_with_a_named_league_is_athc_ini` / `test_athc_ini_with_an_unknown_league_fails` | ☑ |
| `league.toml`, no league set | empty config | exit 2; stderr: `FAIL League is not set ...` | `test_league_toml_with_no_league_set` | ☑ |
| `--league NOPE` | no such folder | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_unknown_named_league` | ☑ |
| `--league` without a name | `--league` | exit 2; stderr: `Error: Option '--league' requires an argument.` | `test_league_without_a_name` | ☑ |
| `league.toml`, malformed `athc.ini` | `[athc` broken | exit 2; stderr: `FAIL <athc.ini>: Not valid INI: ...` | `test_league_toml_with_a_malformed_athc_ini` | ☑ |
| Help screens | `--help` on `config`, `path`, `edit`, `reveal`, `get` | stdout: the agreed screen, 78 wide; the group lists `get`; `--league NAME` on every verb, FILE on `path`, `edit`, `reveal` | `test_help_screen` `[P]` | ☑ |

## `athc config get`

In [test_config.py](test_config.py). `league` through `resolve_league()`; the other keys from the league's `league.toml`, paths through `LeagueConfig.path()`.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `get league`, any case | `league` / `League` / `LEAGUE`, league set | exit 0; stdout: the name; stderr empty | `test_get_league_prints_the_league_in_use` `[P]` | ☑ |
| `get league --league NAME` | two leagues | stdout: that name | `test_get_league_named` | ☑ |
| `get league`, unset or blank | no key / `league =` | exit 2; stderr: `FAIL League is not set ...`, the folders listed; stdout empty | `test_get_league_not_set` `[P]` | ☑ |
| `get league`, folder gone | key names a missing folder | exit 2; stderr: `FAIL League '<NAME>' not found ...` | `test_get_league_folder_gone` | ☑ |
| `get league --league NOPE` | no such folder | exit 2; stderr: `FAIL League 'NOPE' not found ...` | `test_get_league_named_unknown` | ☑ |
| `get league`, malformed `athc.ini` | `[athc` broken | exit 2; stderr: `FAIL <athc.ini>: Not valid INI: ...` | `test_get_league_malformed_athc_ini` | ☑ |
| Unknown KEY | `colour` | exit 2; stderr: `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` | `test_get_rejects_an_unknown_key` | ☑ |
| No KEY | nothing | exit 2; stderr: `Error: Missing argument 'KEY'.` | `test_get_needs_a_key` | ☑ |
| `get path` / `play_path` | absolute folder | stdout: as written | `test_get_absolute_folder_as_written` `[P]` | ☑ |
| `get ppp_path`, relative | `ppp_path = 'Denver'` | stdout: `<league folder>\Denver` | `test_get_relative_ppp_path_is_under_the_league_folder` | ☑ |
| `get team` | `team = 'Las Vegas'` | stdout: as written | `test_get_team_as_written` | ☑ |
| `get path` / `play_path` / `team`, not set | no value; no `league.toml` | exit 2; stderr: `FAIL <league.toml>: <what> is not set. Run 'athc config set <key> ...'.`; stdout empty | `test_get_required_key_not_set` `[P]` | ☑ |
| `get ppp_path`, not set | no value; no `league.toml` | exit 0; stdout empty; stderr: `WARN <league.toml>: Game plan and profile folder is not set. The folders the league file names are used.` | `test_get_ppp_path_not_set_is_a_warning` `[P]` | ☑ |
| Key written as an array | `play_path` / `team` = `['x']` | exit 2; stderr: `FAIL <league.toml>: [league] <key>: Expected a string, got an array.` | `test_get_array_value_fails` `[P]` | ☑ |
| `--league NAME` | two leagues | stdout: that league's value | `test_get_reads_the_named_league` | ☑ |
| League key, no league set | no athc.ini | exit 2; stderr: `FAIL League is not set ...`; stdout empty | `test_get_league_key_with_no_league_set` | ☑ |

---

# `athc standings`

In [test_standings.py](test_standings.py). The selected league's `path` holds `tests/unit/fbpro98_lge/data/PNFL-2048-after-week16.lge` as `test_league.lge` (an autouse fixture); a second league holds `PNFL-before-week1.lge`. Goldens in `expected/standings_{game,league,conference,division}.txt`. Exit 0 done / 2 error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Each view | mid-season | stdout equals the golden; stderr empty | `test_view_matches_golden` `[P]` | ☑ |
| Defaults | mid-season | same as `--view game --method scheduler` | `test_defaults_are_the_game_view_by_the_scheduler` | ☑ |
| Records match the file | mid-season | W, L, T, PF, PA equal `Team.record` | `test_records_match_the_file` | ☑ |
| League view numbered 1 to the team count | mid-season | 1-18 | `test_league_view_numbers_every_team` | ☑ |
| Conference view numbered per conference | mid-season | 1-9, 1-9 | `test_conference_view_numbers_each_conference` | ☑ |
| Each method orders the league view | mid-season | the library's `league()` order | `test_method_orders_the_league_view` `[P]` | ☑ |
| Before week 1 | before week 1 | every row 0, `.000`, `0-0`, `0`, `-` | `test_before_week_one_shows_every_team_at_zero` | ☑ |
| Same file, same order | before week 1 | five runs alike | `test_same_file_same_order` | ☑ |
| `--league` picks the league | second league | its name as the title | `test_league_option_picks_the_league` | ☑ |
| No league selected | athc.ini without league | exit 2; stderr: `FAIL League is not set ...`; stdout empty | `test_no_league_selected` | ☑ |
| No `path` | league.toml without `path` | exit 2; stderr: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER'.` | `test_no_path` | ☑ |
| Missing `.lge` | file removed | exit 2; stderr: `FAIL <file>: The system cannot find the file specified.` | `test_missing_lge` | ☑ |
| Broken `.lge` | empty file | exit 2; stderr: `FAIL <file>: Empty file.` | `test_broken_lge` | ☑ |
| Bad `--view` / `--method` | `bogus` | usage error on stderr, exit 2 | `test_bad_choice_is_a_usage_error` `[P]` | ☑ |
