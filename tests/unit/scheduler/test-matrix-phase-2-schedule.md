# scheduler — Test Matrix: Phase 2 (Schedule Placement)

Cases for `schedule_builder.py`. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). Design: [phase-2-schedule.md](../../../docs/scheduler/phase-2-schedule.md).

Two layers. Model wiring in `test_schedule_builder.py` (fast, no solve). Every rule on a solved schedule in `test_schedule_rules.py`, through the one validator (`tests/integration/schedule_validation.py`), for every league case: two divisional standings variants, the conference league in an even season, an odd season, and with rotation off. Solved cases are `slow` (`pytest -m slow`). Status: ☑ covered · ☐ no test yet.

### Solved schedules — the validator (every case)
| Rule group | Applies when | Status |
|---|---|---|
| Structure: `weeks × 9` games, 9 a week, one game per team per week, `weeks / 2` home, no self play | always | ☑ |
| Inventory: divisional pairs twice (split home/away), conference pairs once, non-conference ≤ once, counts from the league | always | ☑ |
| Hosting: half the conference games, half the non-conference games (odd game either way) | always | ☑ |
| Max consecutive home/away (`max_consecutive_home_or_away`) | always | ☑ |
| 2–4 home in every 6 weeks | `require_home_balance_per_six_weeks` | ☑ |
| First / last 3 weeks mix home and away | `require_mixed_home_away_at_season_ends` | ☑ |
| ≤ N three-game home/away streaks per team; league caps on streak teams | `require_home_away_streak_caps` | ☑ |
| Opening weeks all non-conference | `opening_nonconference_weeks` > 0 | ☑ |
| Conference-sequence streak cap | `max_consecutive_conference_home_or_away` > 0 | ☑ |
| Rivalry week is exactly the pairs; host by season parity | `[rivalries]`; `rotate_home_by_season` | ☑ |
| No back-to-back rematch | divisions | ☑ |
| Divisional streaks, start/end, density and front-load by division size, non-interleaved cap, opening-pair caps | divisions | ☑ |
| League caps: divisional streak teams, bunched rivals, close rematches | divisions | ☑ |
| Final week all-divisional; a divisional game in the last two weeks | divisions + toggles | ☑ |

Tests: `test_solved_schedule_obeys_every_rule`, `test_solved_schedule_realizes_the_phase_one_inventory`, `test_even_season_first_listed_rival_hosts`, `test_odd_season_second_listed_rival_hosts`, `test_rotation_off_still_plays_rivalries_in_the_final_week`.

### Model wiring (`test_schedule_builder.py`)
| Case | Expected | Test | Status |
|---|---|---|---|
| Soft objective wired | 8 metrics, 16 slack terms | `test_soft_objective_is_added_to_the_model` | ☑ |
| Reproducible parallel search | fixed workers, interleave, deterministic time (the solver setup shared with phase 1, in `test_utils.py`) | `test_solver_is_configured_for_reproducible_parallel_search` | ☑ |
| Worker count resolved | `"auto"` → fast threads minus 2; a number as given (`test_utils.py`) | `test_auto_workers_resolve_to_this_machines_fast_threads_minus_two`, `test_a_fixed_worker_count_is_used_as_given` | ☑ |
| Fast threads (`test_cpu.py`) | hybrid → P-core threads only; uniform → every thread; minus 2, never below 1; this machine's count and CPU name | `test_cpu.py` | ☑ |
| Rule gating (no divisions) | no `d_`/streak/objective parts; toggles add only when on; window follows the cap | `test_league_without_divisions_has_no_divisional_model_parts`, `test_home_away_toggles_add_constraints_only_when_on`, `test_streak_caps_on_without_divisions_is_allowed`, `test_max_consecutive_window_follows_the_cap` | ☑ |
| Opening non-conference weeks | one constraint per team-week | `test_opening_nonconference_weeks_add_one_constraint_per_team_week` | ☑ |
| Conference-sequence cap | two constraints per window | `test_conference_streak_cap_adds_two_constraints_per_window` | ☑ |
| Rivalry week | one constraint per pair; host pinned by parity; season required | `test_rivalry_week_adds_one_constraint_per_pair`, `test_rivalry_rotation_pins_the_host_by_season_parity`, `test_rivalry_rotation_needs_a_season` | ☑ |
| Models pinned per league | phase-1 and phase-2 proto hashes unchanged | `test_phase_models_are_unchanged` (`test_model_checksum.py`) | ☑ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| Phase-1 inventory has an unknown pair | raises | `test_unknown_pair_in_inventory_raises` | ☑ |
| No feasible schedule (empty inventory) | raises | `test_empty_inventory_is_infeasible` | ☑ |
| Streak caps off with divisions | `ConfigError` | `test_streak_caps_off_with_divisions_is_a_config_error` | ☑ |
