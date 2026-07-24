# scheduler — Test Matrix: Phase 2 (Schedule Placement)

Cases for `schedule_builder.py`, derived from the code then reconciled with the suite. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). Design: [phase-2-schedule.md](../../../docs/scheduler/phase-2-schedule.md).

One row per behavior. Status: ☑ covered · ☐ no test yet. Solver-backed cases are `slow` (`pytest -m slow`).

These rules are also re-validated end-to-end by `test_schedule_structure.py` / `test_schedule_rules.py` in the `fixed_cpsat/` folder.

### Normal
| Case | Expected | Test | Status |
|---|---|---|---|
| One game per team per week | 16 games/team, one per week | `test_each_team_plays_exactly_one_game_each_week` | ☑ |
| Host exactly 8 | 8 home / 8 away | `test_each_team_hosts_exactly_eight_games` | ☑ |
| Total games | 144 (16 × 9) | `test_game_count`, `test_each_week_has_nine_games` | ☑ |
| Realizes phase-1 inventory | each pair 0/1/2× as selected | `test_two_phase_schedule_matches_phase_one_inventory` | ☑ |
| No team plays itself | — | `test_no_team_plays_itself` | ☑ |
| Divisional home split | each team hosts the rival once | `test_each_divisional_pair_is_split_one_home_one_away` | ☑ |
| Same-conf cross-division once | appears once | `test_same_conference_cross_division_pairs_appear_once` | ☑ |
| Conference home balance (fixed, not configurable) | 5-team host 2; 4-team 2,2,3,3 | `test_five_team_divisions_split_conference_home_games_evenly`, `test_four_team_divisions_split_conference_home_games_2_2_3_3` | ☑ |
| Non-conference home balance (fixed, not configurable) | 5-team host 2; 4-team 2,2,3,3 | `test_five_team_divisions_have_two_nonconference_home_games`, `test_four_team_divisions_split_nonconference_home_games_2_2_3_3` | ☑ |
| Non-conference counts | match division size | `test_nonconference_game_counts_match_division_size` | ☑ |
| Divisional front-load caps | 5-team ≤4/6wk, ≤5/8wk, ≤6/10wk; 4-team ≤2/4wk, ≤3/8wk, ≤4/10wk | `test_divisional_front_load_caps` | ☑ |
| Final week divisional | exactly 8 (toggle on) | `test_week_16_has_exactly_eight_divisional_games` | ☑ |
| Deterministic by seed | reproducible schedule | `test_schedule_is_deterministic_for_a_seed` | ☑ |

### Edge
| Case | Expected | Test | Status |
|---|---|---|---|
| No 4 straight home/away | every 4-week window mixed | `test_no_four_consecutive_home_or_away_games` | ☑ |
| 6-week home window | 2–4 home | `test_max_four_home_or_away_games_in_any_six_game_span` | ☑ |
| First/last 3 weeks | 1–2 home | `test_no_three_game_home_or_away_streak_to_start_or_end` | ☑ |
| ≤1 total 3-game home/away streak | per team | `test_max_one_total_home_or_away_three_game_streak` | ☑ |
| ≤3 straight divisional (never 4) | per team | `test_no_four_consecutive_divisional_games` | ☑ |
| Open weeks 1–2 divisional | ≤4 teams; ≤1 four-team, ≤2 five-team | `test_at_most_four_teams_open_with_back_to_back_divisional_games`, `test_at_most_one_four_team_opens_with_divisional_pair`, `test_at_most_two_five_team_open_with_divisional_pair` | ☑ |
| No 3 straight divisional at start/end | per team | `test_no_three_consecutive_divisional_games_to_start_or_end` | ☑ |
| ≤1 total 3-game divisional streak | per team | `test_max_one_total_three_game_divisional_streak` | ☑ |
| Divisional density | 5-team ≤6/9 (forces ≤7/10); 4-team ≤4/7 | `test_divisional_density_windows` | ☑ |
| ≤2 non-interleaved divisional opponents | per team | `test_at_most_two_divisional_opponents_are_non_interleaved` | ☑ |
| ≥1 divisional in last 2 weeks | per team | `test_each_team_has_divisional_game_in_last_two_weeks` | ☑ |
| No back-to-back pair meetings | — | `test_no_pair_of_teams_plays_in_back_to_back_weeks` | ☑ |
| League caps: 3-game streaks | ≤9 home, ≤3 away, ≤6 divisional teams | `test_league_caps_on_three_game_streaks` | ☑ |
| League cap: bunched rivals | ≤2 teams with 2 non-interleaved | `test_league_cap_on_teams_with_two_bunched_rivals` | ☑ |
| League cap: close rematches | ≤3 within a 3-week span | `test_league_cap_on_close_rematches` | ☑ |
| Soft objective wired | model minimizes 8 metrics (16 slack terms) | `test_soft_objective_is_added_to_the_model` | ☑ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| Phase-1 inventory has an unknown pair | raises | `test_unknown_pair_in_inventory_raises` | ☑ |
| No feasible schedule (empty inventory) | raises | `test_empty_inventory_is_infeasible` | ☑ |
