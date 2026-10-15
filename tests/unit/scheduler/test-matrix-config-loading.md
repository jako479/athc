# scheduler — Test Matrix: Config Loading and League Files

Cases for `config.py` (`load_scheduler_config`, the rules path), `league_files.py` (the League from the previous and upcoming `.lge` files) and the `generate-schedule` CLI. Convention in [../../../docs/testing-unit.md](../../../docs/testing-unit.md).

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
| `[solver] phase1_time_limit` / `phase2_time_limit` (one validator) | 1 accepted; 0 → `[solver] phase2_time_limit: Must be a positive number.` | `test_solver_time_limit_must_be_positive` | ☑ |
| `[phase1]` | `difficulty_slope` and `random_nonconference` read; defaults 2.5 and false; an unknown key → `[phase1]: Unknown key(s): <key>.` | `test_load_scheduler_config_reads_values`, `test_load_scheduler_config_defaults_when_no_file`, `test_load_scheduler_config_rejects_unknown_phase1_key` | ☑ |
| Unknown table / `[solver]` key | `(top): Unknown key(s): <table>.` / `[solver]: Unknown key(s): <key>.`; no list of valid names | `test_load_scheduler_config_rejects_unknown_table`, `test_load_scheduler_config_rejects_unknown_solver_key` | ☑ |
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
| Previous season not finished | golden (an opening-week file) | `warn` hears `<file>: Season not finished. 142 game(s) not played.`; the League is built | `test_unfinished_season_is_a_warning` | ☑ |
| Renamed team not listed | golden, no renames | `Team(s) not in <upcoming>: Baltimore. List renamed teams under [renames.2048] in <rules>.` | `test_unmatched_previous_team_names_the_renames_table` | ☑ |
| Rename names an unknown or taken team | golden | `ConfigFileError` naming the rules file, table and key | `test_rename_naming_an_unknown_or_taken_team` `[P]` | ☑ |
| One division per conference | built | a league without divisions; the coin toss's order with no game | `test_one_division_per_conference_is_a_league_without_divisions` | ☑ |
| Three conferences / a conference of eight / a repeated name / a team only in the upcoming file | built | `SchedulerError` naming the file | `test_three_conferences_rejected`, `test_conference_of_eight_rejected`, `test_team_name_repeated_in_a_file_rejected`, `test_team_only_in_the_upcoming_file_is_reported` | ☑ |
| Overall order | built | playoff finish over record; champion, runner-up, then by round; a bye counts nothing; then strength of schedule; then point differential; then the coin toss | `test_playoff_finish_outranks_record`, `test_champion_then_runner_up_then_losers_by_round_and_record`, `test_bye_team_ranks_by_the_round_it_went_out`, `test_same_record_and_finish_ranked_by_strength_of_schedule`, `test_same_strength_ranked_by_point_differential`, `test_level_teams_go_by_the_coin_toss` | ☑ |
| Division finish in the overall order | built | level on playoff finish, win percentage and strength of schedule: the previous season's division finish decides, ahead of point differential | `test_division_finish_ranks_ahead_of_point_differential` | ☑ |
| A team that changed divisions | built | ranked overall by its place in its previous-season division, not the upcoming one | `test_a_team_that_moved_ranks_by_its_previous_division` | ☑ |
| Coin toss | built, no game played | each division's finish and the overall order follow `random.Random(seed)`'s shuffle of the previous teams; the same seed, the same order | `test_coin_toss_orders_a_season_with_no_game_played` | ☑ |
| Tied playoff game | built | `Playoff round 1: Tied game, A1 10, A2 10.` | `test_tied_playoff_game_rejected` | ☑ |
| Division finish after a membership change | built | the upcoming members ranked by previous records | `test_division_finish_ranks_the_upcoming_members_by_previous_season` | ☑ |
| Level division members | built | the coin toss's order, neither file's | `test_level_division_members_go_by_the_coin_toss` | ☑ |
| Moved teams tied | built | division record under the previous divisions, not the upcoming ones | `test_moved_teams_tie_broken_by_the_previous_seasons_divisions` | ☑ |

### Shipped files — every `config/dev/` and `config/release/` rules file
| Case | Expected | Test | Status |
|---|---|---|---|
| Each rules file fits a league of its shape | weeks, opening weeks, rivalries | `test_shipped_rules_file_fits_its_league_shape` | ☑ |
| config/dev/ and config/release/ ship the same set | 2 files each | `test_shipped_file_sets_match_between_dev_and_release` | ☑ |
| Conference league rules match the test league | expected rule values, slope 0.0, random off | `test_shipped_conference_league_rules_match_the_test_league` | ☑ |

### CLI — `generate-schedule`
| Case | Expected | Test | Status |
|---|---|---|---|
| Help screen | the help, word for word | `test_help_screen` | ☑ |
| No `--season` / non-integer `--phase2-time-limit` / `--workers` | exit 2 | `test_requires_season`, `test_rejects_non_integer_phase2_time_limit`, `test_no_worker_count_override` | ☑ |
| `--seed` (0 to 2147483647) | 0 and 2147483647 forwarded; -1 and 2147483648 exit 2 with `must be 0 to 2147483647, got <n>.`, never reaching the run | `test_seed_at_its_bounds_is_forwarded`, `test_seed_past_its_bounds_is_a_usage_error` `[P]` | ☑ |
| No `--seed` | a seed from 0 to 1,000,000 | `test_no_seed_draws_one_from_0_to_1000000` | ☑ |
| `--phase2-time-limit` (1 or more) | 1 forwarded; 0 exits 2 with `must be 1 or more, got 0.`; replaces only phase 2's limit | `test_phase2_time_limit_of_1_is_forwarded`, `test_phase2_time_limit_of_0_is_a_usage_error`, `test_phase2_time_limit_replaces_only_phase_2s_limit` | ☑ |
| No `--previous` | the upcoming file as both files | `test_without_previous_the_upcoming_file_gives_both` | ☑ |
| No `--previous`, `[renames.<season>]` set | the table is ignored; the run reaches the solver | `test_without_previous_the_renames_are_ignored` | ☑ |
| No league resolvable | exit 2 + "No league selected" | `test_errors_when_no_league_is_configured` | ☑ |
| `--league` without a league folder | exit 2 + "not found" | `test_errors_when_league_has_no_folder` | ☑ |
| `--previous` file missing (its folder absent / its folder there) | exit 2 naming the file, Windows' path / file phrase | `test_errors_when_previous_file_missing`, `test_errors_when_previous_file_missing_from_its_folder` | ☑ |
| No `--upcoming` and no `path` | exit 2: `League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.` naming `league.toml` | `test_errors_when_the_league_has_no_path` | ☑ |
| `--upcoming` | overrides `path` | `test_upcoming_option_overrides_the_league_path` | ☑ |
| CLI resolves both files and the rules; output to cwd | league, files, cwd | `test_league_and_season_resolve_files_and_output_to_cwd`, `test_season_resolves_files_for_the_configured_league` | ☑ |
| Previous season not finished (main / CLI) | `warn` hears the line / `WARN` naming the file; the run reaches the solver | `test_main_errors_when_the_previous_season_is_not_finished`, `test_cli_errors_when_the_previous_season_is_not_finished` | ☑ |
| Renamed team not listed (CLI) | exit 2 with the `[renames.<season>]` hint | `test_cli_errors_when_a_renamed_team_is_not_listed` | ☑ |
| League built (main) | pre-checks pass, solver reached with the season and league | `test_main_builds_the_league_and_reaches_the_solver` | ☑ |
| No feasible schedule (`SchedulerError`) | exit 2 + message | `test_errors_when_no_feasible_schedule` | ☑ |
| `OSError` / solver dep missing | exit 2, no traceback / names the module | `test_errors_on_oserror`, `test_errors_when_dependency_missing` | ☑ |
| Ctrl+C while the files are written | all three files written, then `FAIL Interrupted.`, exit 130 | `test_ctrl_c_during_the_writes_writes_all_three_then_interrupts` | ☑ |
