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
| Non-numeric `spread` | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_spread` | ☑ |
| Invalid TOML | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_toml` | ☑ |
| `[phase2]` amounts | parsed; others default | `test_load_scheduler_config_reads_phase2_amounts` | ☑ |
| Unknown `[phase2]` key | `ConfigError` | `test_load_scheduler_config_rejects_unknown_phase2_key` | ☑ |
| Non-integer `[phase2]` | `ConfigError` | `test_load_scheduler_config_errors_on_non_integer_phase2` | ☑ |

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
| Conference rank from `[Standings]` | derived 1–9 ranks | `test_load_league_derives_conference_rank_from_standings` | ☑ |
| `[Divisions]` missing | `ConfigError` | `test_load_league_errors_when_divisions_section_missing` | ☑ |
| `[Standings]` missing | `ConfigError` "Standings" | `test_load_league_errors_when_standings_section_missing` | ☑ |
| Duplicate team | `ConfigError` | `test_load_league_errors_on_duplicate_team` | ☑ |
| `[Standings]` team not in `[Divisions]` | `ConfigError` | `test_load_league_errors_when_standings_team_not_in_divisions` | ☑ |
| `Order` key missing | `ConfigError` | `test_load_league_errors_when_order_key_missing` | ☑ |
| `Order` empty | `ConfigError` | `test_load_league_errors_when_order_empty` | ☑ |
| Wrong division size | `ConfigError` | `test_load_league_errors_on_invalid_league_data` | ☑ |
| Unknown division key | `ConfigError` | `test_load_league_errors_on_unknown_division_key` | ☑ |
| `[Standings]` duplicate team | `ConfigError` | `test_load_league_errors_on_standings_duplicate` | ☑ |
| Malformed INI | `ConfigError` | `test_load_league_errors_on_invalid_ini` | ☑ |
| File missing | `ConfigError` | `test_load_league_errors_when_file_missing` | ☑ |
| Shipped `release/2048.league.ini` | loads, 18 teams | `test_release_example_league_loads` | ☑ |

### `[DivisionStandings]` (required by both schedulers)
| Case | Expected | Test | Status |
|---|---|---|---|
| Valid section | per-division ordered teams | `test_load_league_reads_division_standings` | ☑ |
| Section absent | `division_standings` None | `test_load_league_division_standings_none_when_section_absent` | ☑ |
| Division key missing | `ConfigError` | `test_load_league_errors_when_division_standings_incomplete` | ☑ |
| Unknown team | `ConfigError` | `test_load_league_errors_on_unknown_division_standings_team` | ☑ |
| Team in wrong division | `ConfigError` | `test_load_league_errors_when_division_standings_team_misplaced` | ☑ |
| Duplicate team | `ConfigError` | `test_load_league_errors_on_division_standings_duplicate` | ☑ |
| Team missing | `ConfigError` | `test_load_league_errors_when_division_standings_team_missing` | ☑ |
| Shipped release file has section | non-None, 4 divisions | `test_release_league_has_division_standings` | ☑ |

### CLI — `generate-schedule` error paths
| Case | Expected | Test | Status |
|---|---|---|---|
| No `--season` | exit 2 | `test_requires_season` | ☑ |
| Non-integer `--time-limit` | exit 2 | `test_rejects_non_integer_time_limit` | ☑ |
| League file missing | exit 1 + "league" | `test_errors_when_league_file_missing` | ☑ |
| No `[DivisionStandings]` (main) | `ConfigError` names section | `test_main_errors_without_division_standings` | ☑ |
| `[DivisionStandings]` present (main) | pre-checks pass, solver reached | `test_main_accepts_division_standings` | ☑ |
| No `[DivisionStandings]` (CLI) | exit 1 + names section | `test_cli_errors_without_division_standings` | ☑ |
| `OSError` (read/write) | exit 1, no traceback | `test_errors_on_oserror` | ☑ |
| Solver dep missing | exit 1 + names module | `test_errors_when_dependency_missing` | ☑ |
