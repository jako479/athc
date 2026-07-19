# scheduler — Test Matrix: Config Loading

Cases for `config.py` (`load_scheduler_config`, `load_league`, `load_history`) and the `generate-schedule` CLI error paths. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

In `test_config.py` and `test_cli.py`. One row per behavior. Status: ☑ covered · ☐ no test yet.

### Scheduler tunables — `rules/PNFL.scheduler.toml` (optional)
| Case | Expected | Test | Status |
|---|---|---|---|
| Reads values | parsed floats/ints | `test_load_scheduler_config_reads_values` | ☑ |
| No file | all defaults | `test_load_scheduler_config_defaults_when_no_file` | ☑ |
| Missing keys | per-key defaults | `test_load_scheduler_config_defaults_when_keys_missing` | ☑ |
| Non-numeric value | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_value` | ☑ |
| Invalid TOML | `ConfigError` | `test_load_scheduler_config_errors_on_invalid_toml` | ☑ |
| `[phase2]` amounts | parsed; others default | `test_load_scheduler_config_reads_phase2_amounts` | ☑ |
| Unknown `[phase2]` key | `ConfigError` | `test_load_scheduler_config_rejects_unknown_phase2_key` | ☑ |
| Non-integer `[phase2]` | `ConfigError` | `test_load_scheduler_config_errors_on_non_integer_phase2` | ☑ |

### Path resolution — `--season` selects config files
| Case | Expected | Test | Status |
|---|---|---|---|
| `<season>.league.ini` missing | `ConfigError` | `test_find_league_path_errors_when_none_exist` | ☑ |
| Resolves `<season>.league.ini` | config-dir path | `test_find_league_path_resolves_season_prefixed_file` | ☑ |
| `<season>.nonconf_history.json` missing | `ConfigError` | `test_find_history_path_errors_when_missing` | ☑ |
| Resolves `<season>.nonconf_history.json` | config-dir path | `test_find_history_path_resolves_season_prefixed_file` | ☑ |
| CLI: `--season` picks both files; output to cwd | resolved paths + cwd | `test_season_resolves_files_and_outputs_to_cwd` | ☑ |

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

### History — `<season>.nonconf_history.json` (required, all 81 pairs)
| Case | Expected | Test | Status |
|---|---|---|---|
| Valid, complete | loads; pair readable | `test_load_history_reads_valid_aligned_file` | ☑ |
| Absent / empty | `ConfigError` (incomplete) | `test_load_history_errors_when_absent_or_empty` | ☑ |
| Incomplete (missing pairs) | `ConfigError` "missing" | `test_load_history_errors_when_incomplete` | ☑ |
| Invalid JSON | `ConfigError` | `test_load_history_errors_on_invalid_json` | ☑ |
| Bad structure (no `matchups` object) | `ConfigError` | `test_load_history_errors_on_bad_structure` | ☑ |
| Non-integer season | `ConfigError` | `test_load_history_errors_on_non_integer_season` | ☑ |
| Unknown team | `ConfigError` "unknown or misplaced" | `test_load_history_errors_on_unknown_team` | ☑ |
| Wrong conference side | `ConfigError` "unknown or misplaced" | `test_load_history_errors_on_wrong_conference_side` | ☑ |
| Shipped `release/2048.nonconf_history.json` | aligns with `release/2048.league.ini` | `test_release_example_history_aligns_with_release_league` | ☑ |

### CLI — `generate-schedule` error paths
| Case | Expected | Test | Status |
|---|---|---|---|
| No `--season` | exit 2 | `test_requires_season` | ☑ |
| Non-integer `--time-limit` | exit 2 | `test_rejects_non_integer_time_limit` | ☑ |
| Unknown `--scheduler` | exit 2 | `test_rejects_unknown_scheduler` | ☑ |
| League file missing | exit 1 + "league" | `test_errors_when_league_file_missing` | ☑ |
| History missing (Scheduler A) | exit 1 + "history" | `test_errors_when_history_missing_for_scheduler_a` | ☑ |
| Scheduler B ignores history | exit 0; `history_path` None | `test_scheduler_b_does_not_require_history` | ☑ |
| Scheduler C ignores history | exit 0; `history_path` None | `test_scheduler_c_does_not_require_history` | ☑ |
| `OSError` (read/write) | exit 1, no traceback | `test_errors_on_oserror` | ☑ |
| Solver dep missing | exit 1 + names module | `test_errors_when_dependency_missing` | ☑ |
| `--scheduler` pass-through | chosen scheduler used | `test_scheduler_passes_through` `[P]` | ☑ |
| `--season` resolves files; output to cwd | resolved paths + cwd | `test_season_resolves_files_and_outputs_to_cwd` | ☑ |
