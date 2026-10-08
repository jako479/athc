# scheduler — Test Matrix: Config Loading

Cases for `config.py` (`load_scheduler_config`, `load_league`, file resolution) and the `generate-schedule` CLI. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

In `test_config.py` and `test_cli.py`. The test league is named `divisions`. Status: ☑ covered · ☐ no test yet.

### Scheduler rules — `leagues/<league>/scheduler.toml` (optional)
| Case | Expected | Test | Status |
|---|---|---|---|
| Reads values | parsed floats/ints | `test_load_scheduler_config_reads_values` | ☑ |
| No file | all defaults | `test_load_scheduler_config_defaults_when_no_file` | ☑ |
| Missing keys | per-key defaults | `test_load_scheduler_config_defaults_when_keys_missing` | ☑ |
| Bad value / TOML / unknown key | `ConfigError` | `test_load_scheduler_config_errors_*`, `test_load_scheduler_config_rejects_*` | ☑ |
| `solver_workers` | default and `"auto"` → `"auto"`; 1 accepted; 0 and other text rejected | `test_solver_workers_*` | ☑ |
| `[phase2]`, `[league]`, `[rivalries]` | parsed; defaults; 0 off, -1 error; bad shapes error | `test_load_scheduler_config_reads_*`, `test_zero_is_off_and_negative_is_rejected` | ☑ |
| Explicit path missing | `ConfigError`; `required=False` → defaults; present → read | `test_load_scheduler_config_explicit_path_must_exist`, `test_load_scheduler_config_optional_path_*` | ☑ |
| `check_weeks` / `check_opening_weeks` / `resolve_rivalries` | both sides of each limit | `test_check_weeks_*`, `test_check_opening_weeks_*`, `test_resolve_rivalries_*` | ☑ |

### File resolution — `--league` and `--season`
| Case | Expected | Test | Status |
|---|---|---|---|
| Rules path | `leagues/<league>/scheduler.toml` | `test_scheduler_rules_path_is_named_by_league` | ☑ |
| League has no folder | `LeagueError` | `test_scheduler_rules_path_needs_the_league_folder` | ☑ |
| Standings missing | `ConfigError` naming `leagues/<league>/standings/<season>.league.ini` | `test_find_league_path_errors_when_none_exist` | ☑ |
| Standings present (another league's ignored) | that file | `test_find_league_path_resolves_league_and_season_file` | ☑ |
| CLI resolves both files; output to cwd | league, paths, cwd | `test_league_and_season_resolve_files_and_output_to_cwd` | ☑ |
| CLI without `--league` | the league named in `athc.ini` | `test_season_resolves_files_for_the_configured_league` | ☑ |

### Standings — `leagues/<league>/standings/<season>.league.ini` (required)
| Case | Expected | Test | Status |
|---|---|---|---|
| Valid file | `League`, 18 teams, overall set; ranks derived | `test_load_league_reads_valid_config`, `test_load_league_derives_conference_rank_from_standings` | ☑ |
| Conferences and sizes from the keys | `<CONFERENCE>_<DIVISION>`; sizes = line counts; any division name | `test_load_league_derives_conferences_and_sizes_from_the_keys`, `test_load_league_accepts_any_division_name` | ☑ |
| Key without a conference | `ConfigError` | `test_load_league_errors_on_division_key_without_conference` | ☑ |
| Missing / both standings sections; missing `[OverallStandings]` / `Order` | `ConfigError` naming the section | `test_load_league_errors_when_*`, `test_load_league_errors_with_both_sections` | ☑ |
| Duplicate team, unknown team, wrong sizes, malformed INI, missing file | `ConfigError` | `test_load_league_errors_on_*` | ☑ |
| Division finish order kept; teams canonical | per-division order; alphabetical teams | `test_load_league_reads_division_standings`, `test_load_league_teams_are_alphabetical_within_division` | ☑ |
| `[ConferenceStandings]` | a division-less league; wrong size errors | `test_load_league_reads_conference_standings`, `test_load_league_errors_on_wrong_conference_size` | ☑ |

### Shipped files — every `config/dev/` and `config/release/` standings and rules file
| Case | Expected | Test | Status |
|---|---|---|---|
| Each standings file loads | 18 teams | `test_shipped_standings_file_loads` | ☑ |
| Each rules file fits its league's standings | weeks, opening weeks, rivalries | `test_shipped_rules_file_fits_its_leagues_standings` | ☑ |
| config/dev/ and config/release/ ship the same set | 8 files each | `test_shipped_file_sets_match_between_dev_and_release` | ☑ |
| Conference league files match the test league | equal league; expected rule values | `test_shipped_conference_league_files_match_the_test_league` | ☑ |

### CLI — `generate-schedule`
| Case | Expected | Test | Status |
|---|---|---|---|
| No `--season` / non-integer `--time-limit` / `--workers` | exit 2 | `test_requires_season`, `test_rejects_non_integer_time_limit`, `test_no_worker_count_override` | ☑ |
| No league resolvable | exit 1 + "no league selected" | `test_errors_when_no_league_is_configured` | ☑ |
| `--league` without a league folder | exit 1 + "not found" | `test_errors_when_league_has_no_folder` | ☑ |
| Standings file missing | exit 1 naming the file | `test_errors_when_league_file_missing` | ☑ |
| No feasible schedule (`SchedulerError`) | exit 1 + message | `test_errors_when_no_feasible_schedule` | ☑ |
| No standings section (main / CLI) | `ConfigError` / exit 1 naming the section | `test_main_errors_without_division_standings`, `test_cli_errors_without_division_standings` | ☑ |
| Standings present (main) | pre-checks pass, solver reached with the season | `test_main_accepts_division_standings` | ☑ |
| `OSError` / solver dep missing | exit 1, no traceback / names the module | `test_errors_on_oserror`, `test_errors_when_dependency_missing` | ☑ |
