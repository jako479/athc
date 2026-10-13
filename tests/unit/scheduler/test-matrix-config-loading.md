# scheduler — Test Matrix: Config Loading and League Files

Cases for `config.py` (`load_scheduler_config`, the rules path), `league_files.py` (the League from the previous and upcoming `.lge` files) and the `generate-schedule` CLI. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

In `test_config.py`, `test_league_files.py` and `test_cli.py`. The test league is named `divisions`; the real league files are the PNFL's 2046-2048 season files in `tests/integration/data/`. Status: ☑ covered · ☐ no test yet.

### Scheduler rules — `leagues/<league>/scheduler.toml` (optional)
| Case | Expected | Test | Status |
|---|---|---|---|
| Reads values | parsed floats/ints | `test_load_scheduler_config_reads_values` | ☑ |
| No file | all defaults | `test_load_scheduler_config_defaults_when_no_file` | ☑ |
| Missing keys | per-key defaults | `test_load_scheduler_config_defaults_when_keys_missing` | ☑ |
| UTF-8 BOM | skipped; values read | `test_load_scheduler_config_skips_bom` | ☑ |
| Bad value / TOML / unknown key | `ConfigFileError` | `test_load_scheduler_config_errors_*`, `test_load_scheduler_config_rejects_*` | ☑ |
| `solver_workers` | default and `"auto"` → `"auto"`; 1 accepted; 0 and other text rejected | `test_solver_workers_*` | ☑ |
| `[phase2]`, `[league]`, `[rivalries]` | parsed; defaults; 0 off, -1 error; bad shapes error | `test_load_scheduler_config_reads_*`, `test_zero_is_off_and_negative_is_rejected` | ☑ |
| `[renames.<season>]` | parsed per season, names stripped; default `{}` | `test_load_scheduler_config_reads_renames`, `test_renames_default_to_none` | ☑ |
| Bad `[renames]` | not a table; key not a year; season not a table; value not a name; blank name; renamed to itself; two teams to one name | `test_bad_renames_name_the_table_and_key` `[P]` | ☑ |
| Explicit path missing | `ConfigFileError`; `required=False` → defaults; present → read | `test_load_scheduler_config_explicit_path_must_exist`, `test_load_scheduler_config_optional_path_*` | ☑ |
| `check_weeks` / `check_opening_weeks` / `resolve_rivalries` | both sides of each limit | `test_check_weeks_*`, `test_check_opening_weeks_*`, `test_resolve_rivalries_*` | ☑ |
| Rules path | `leagues/<league>/scheduler.toml`; `LeagueError` without the league folder | `test_scheduler_rules_path_*` | ☑ |

### League files — `load_league` / `league_from_files`
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Real 2047 -> 2048 | golden | the league's published 2048 order and division finishes; empty conference names; divisions by position | `test_2048_league_matches_the_real_final_standings` | ☑ |
| Real 2046 -> 2047 | golden | a realignment and four renames: divisions from the upcoming file, finish and overall from the 2046 records | `test_2047_league_follows_realignment_and_renames` | ☑ |
| Previous season not finished | golden (an opening-week file) | `Season not finished: 142 game(s) not played.` naming the file | `test_previous_season_must_be_finished` | ☑ |
| Renamed team not listed | golden, no renames | `Team(s) not in <upcoming>: Baltimore. List renamed teams under [renames.2048] in <rules>.` | `test_unmatched_previous_team_names_the_renames_table` | ☑ |
| Rename names an unknown or taken team | golden | `ConfigFileError` naming the rules file, table and key | `test_rename_naming_an_unknown_or_taken_team` `[P]` | ☑ |
| One division per conference | built | a league without divisions; file order with no game | `test_one_division_per_conference_is_a_league_without_divisions` | ☑ |
| Three conferences / a conference of eight / a repeated name / a team only in the upcoming file | built | `SchedulerError` naming the file | `test_three_conferences_rejected`, `test_conference_of_eight_rejected`, `test_team_name_repeated_in_a_file_rejected`, `test_team_only_in_the_upcoming_file_is_reported` | ☑ |
| Overall order | built | playoff finish over record; champion, runner-up, then by round; a bye counts nothing; then strength of schedule; then point differential; then file order | `test_playoff_finish_outranks_record`, `test_champion_then_runner_up_then_losers_by_round_and_record`, `test_bye_team_ranks_by_the_round_it_went_out`, `test_same_record_and_finish_ranked_by_strength_of_schedule`, `test_same_strength_ranked_by_point_differential`, `test_level_teams_keep_the_previous_file_order` | ☑ |
| Tied playoff game | built | `Playoff round 1: Tied game, A1 10, A2 10.` | `test_tied_playoff_game_rejected` | ☑ |
| Division finish after a membership change | built | the upcoming members ranked by previous records | `test_division_finish_ranks_the_upcoming_members_by_previous_season` | ☑ |
| Level division members | built | previous-file order, not the upcoming file's | `test_level_division_members_keep_the_previous_file_order` | ☑ |
| Moved teams tied | built | division record under the previous divisions, not the upcoming ones | `test_moved_teams_tie_broken_by_the_previous_seasons_divisions` | ☑ |

### Shipped files — every `config/dev/` and `config/release/` rules file
| Case | Expected | Test | Status |
|---|---|---|---|
| Each rules file fits a league of its shape | weeks, opening weeks, rivalries | `test_shipped_rules_file_fits_its_league_shape` | ☑ |
| config/dev/ and config/release/ ship the same set | 2 files each | `test_shipped_file_sets_match_between_dev_and_release` | ☑ |
| Conference league rules match the test league | expected rule values | `test_shipped_conference_league_rules_match_the_test_league` | ☑ |

### CLI — `generate-schedule`
| Case | Expected | Test | Status |
|---|---|---|---|
| No `--season` / no `--previous` / non-integer `--time-limit` / `--workers` | exit 2 | `test_requires_season`, `test_requires_previous`, `test_rejects_non_integer_time_limit`, `test_no_worker_count_override` | ☑ |
| No league resolvable | exit 2 + "No league selected" | `test_errors_when_no_league_is_configured` | ☑ |
| `--league` without a league folder | exit 2 + "not found" | `test_errors_when_league_has_no_folder` | ☑ |
| Previous folder has no `<league>.lge` | exit 2 naming the file, Windows' words | `test_errors_when_previous_file_missing` | ☑ |
| No `--upcoming` and no `path` | exit 2 naming `league.toml` | `test_errors_when_the_league_has_no_path` | ☑ |
| `--upcoming` | overrides `path` | `test_upcoming_option_overrides_the_league_path` | ☑ |
| CLI resolves both folders and the rules; output to cwd | league, folders, cwd | `test_league_and_season_resolve_files_and_output_to_cwd`, `test_season_resolves_files_for_the_configured_league` | ☑ |
| Previous season not finished (main / CLI) | `SchedulerError` / exit 2 naming the file | `test_main_errors_when_the_previous_season_is_not_finished`, `test_cli_errors_when_the_previous_season_is_not_finished` | ☑ |
| Renamed team not listed (CLI) | exit 2 with the `[renames.<season>]` hint | `test_cli_errors_when_a_renamed_team_is_not_listed` | ☑ |
| League built (main) | pre-checks pass, solver reached with the season and league | `test_main_builds_the_league_and_reaches_the_solver` | ☑ |
| No feasible schedule (`SchedulerError`) | exit 2 + message | `test_errors_when_no_feasible_schedule` | ☑ |
| `OSError` / solver dep missing | exit 2, no traceback / names the module | `test_errors_on_oserror`, `test_errors_when_dependency_missing` | ☑ |
