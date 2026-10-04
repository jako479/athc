# scheduler — Test Matrix: Config Loading

Cases for `config.py` (`load_scheduler_config`, `load_league`) and the `generate-schedule` CLI error paths. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

In `test_config.py` and `test_cli.py`. One row per behavior. Status: ☑ covered · ☐ no test yet.

### Scheduler tunables — `rules/PNFL.scheduler.toml` (optional)
| Case | Expected | Test | Status |
|---|---|---|---|
| Reads values | parsed floats/ints | `test_load_scheduler_config_reads_values` | ☑ |
| No file | all defaults | `test_load_scheduler_config_defaults_when_no_file` | ☑ |
| Missing keys | per-key defaults | `test_load_scheduler_config_defaults_when_keys_missing` | ☑ |
| Non-numeric value | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_value` | ☑ |
| Non-integer `solver_workers` | `ConfigError` | `test_load_scheduler_config_errors_on_non_integer_workers` | ☑ |
| Non-numeric `spread` | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_spread` | ☑ |
| Invalid TOML | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_toml` | ☑ |
| `[phase2]` amounts | parsed; others default | `test_load_scheduler_config_reads_phase2_amounts` | ☑ |
| Unknown `[phase2]` key | `ConfigError` | `test_load_scheduler_config_rejects_unknown_phase2_key` | ☑ |
| Non-integer `[phase2]` | `ConfigError` | `test_load_scheduler_config_errors_on_non_integer_phase2` | ☑ |

### `[league]` / `[rivalries]` / league-resolved checks
| Case | Expected | Test | Status |
|---|---|---|---|
| `[league] weeks` | parsed (min 2 accepted); default 16; odd/zero/non-int/unknown key error | `test_load_scheduler_config_reads_weeks`, `test_weeks_defaults_to_sixteen`, `test_load_scheduler_config_rejects_bad_weeks`, `test_load_scheduler_config_rejects_unknown_league_key` | ☑ |
| Explicit path | reads it; missing errors | `test_load_scheduler_config_from_explicit_path`, `test_load_scheduler_config_explicit_path_must_exist` | ☑ |
| New `[phase2]` keys | parsed; PNFL defaults; 0 off, -1 error | `test_load_scheduler_config_reads_new_phase2_keys`, `test_new_phase2_keys_default_to_pnfl_behaviour`, `test_zero_is_off_and_negative_is_rejected` | ☑ |
| `[rivalries]` | pairs + toggle parsed, names stripped; bad shapes error | `test_load_scheduler_config_reads_rivalries`, `test_rivalries_default_to_none`, `test_load_scheduler_config_rejects_bad_rivalries` | ☑ |
| `check_weeks` | PCFL 10/16 ok, 8/18/11 error; PNFL 14/20 ok, 12/22 error | `test_check_weeks_*` | ☑ |
| `check_opening_weeks` | 0/3 ok, 4 error | `test_check_opening_weeks_*` | ☑ |
| `resolve_rivalries` | listed order; 8/10 pairs, repeat, unknown, 3 cross error | `test_resolve_rivalries_*` | ☑ |

### Path resolution — `--season` selects the league file
| Case | Expected | Test | Status |
|---|---|---|---|
| `<season>.league.ini` missing | `ConfigError` | `test_find_league_path_errors_when_none_exist` | ☑ |
| Resolves `<season>.league.ini` | config-dir path | `test_find_league_path_resolves_season_prefixed_file` | ☑ |
| CLI: `--season` resolves file; output to cwd | resolved path + cwd | `test_season_resolves_files_and_outputs_to_cwd` | ☑ |

### League — `<season>.league.ini` (required)
| Case | Expected | Test | Status |
|---|---|---|---|
| Valid file | `League`, 18 teams, overall set | `test_load_league_reads_valid_config` | ☑ |
| Conference rank from `[OverallStandings]` | derived 1–9 ranks | `test_load_league_derives_conference_rank_from_standings` | ☑ |
| `[OverallStandings]` missing | `ConfigError` "OverallStandings" | `test_load_league_errors_when_standings_section_missing` | ☑ |
| Duplicate team | `ConfigError` | `test_load_league_errors_on_duplicate_team` | ☑ |
| `[OverallStandings]` team not in `[DivisionStandings]` | `ConfigError` | `test_load_league_errors_when_standings_team_not_in_divisions` | ☑ |
| `Order` key missing | `ConfigError` | `test_load_league_errors_when_order_key_missing` | ☑ |
| `Order` empty | `ConfigError` | `test_load_league_errors_when_order_empty` | ☑ |
| Wrong division size | `ConfigError` | `test_load_league_errors_on_invalid_league_data` | ☑ |
| Unknown division key | `ConfigError` | `test_load_league_errors_on_unknown_division_key` | ☑ |
| `[OverallStandings]` duplicate team | `ConfigError` | `test_load_league_errors_on_standings_duplicate` | ☑ |
| Malformed INI | `ConfigError` | `test_load_league_errors_on_invalid_ini` | ☑ |
| File missing | `ConfigError` | `test_load_league_errors_when_file_missing` | ☑ |
| Shipped `release/2048.league.ini` | loads, 18 teams | `test_release_example_league_loads` | ☑ |
| `[ConferenceStandings]` | loads a division-less league | `test_load_league_reads_conference_standings` (Task 4) | ☑ |
| Both / neither section | `ConfigError` naming both | `test_load_league_errors_with_both_sections`, `test_load_league_errors_when_division_standings_section_missing` (Task 4) | ☑ |

### `[DivisionStandings]` — defines division membership + finish order
| Case | Expected | Test | Status |
|---|---|---|---|
| Valid section | per-division ordered teams | `test_load_league_reads_division_standings` | ☑ |
| Teams alphabetical within division | canonical teams tuple | `test_load_league_teams_are_alphabetical_within_division` | ☑ |
| Section absent | `ConfigError` "DivisionStandings" | `test_load_league_errors_when_division_standings_section_missing` | ☑ |
| A division missing | `ConfigError` | `test_load_league_errors_when_division_missing` | ☑ |
| Duplicate team | `ConfigError` | `test_load_league_errors_on_division_standings_duplicate` | ☑ |
| Shipped release file has section | 4 divisions | `test_release_league_has_division_standings` | ☑ |

### CLI — `generate-schedule` error paths
| Case | Expected | Test | Status |
|---|---|---|---|
| No `--season` | exit 2 | `test_requires_season` | ☑ |
| Non-integer `--time-limit` | exit 2 | `test_rejects_non_integer_time_limit` | ☑ |
| No `--workers` override (config-only) | exit 2 | `test_no_worker_count_override` | ☑ |
| League file missing | exit 1 + "league" | `test_errors_when_league_file_missing` | ☑ |
| No `[DivisionStandings]` (main) | `ConfigError` names section | `test_main_errors_without_division_standings` | ☑ |
| `[DivisionStandings]` present (main) | pre-checks pass, solver reached | `test_main_accepts_division_standings` | ☑ |
| No `[DivisionStandings]` (CLI) | exit 1 + names section | `test_cli_errors_without_division_standings` | ☑ |
| `OSError` (read/write) | exit 1, no traceback | `test_errors_on_oserror` | ☑ |
| Solver dep missing | exit 1 + names module | `test_errors_when_dependency_missing` | ☑ |
