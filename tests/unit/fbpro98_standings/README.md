# fbpro98_standings — Test Matrix

Cases covered for the standings library. Convention in [../../../docs/testing-unit.md](../../../docs/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `built` = a league built in code (`leagues.py`); `golden` = a real `.lge` from `tests/unit/fbpro98_lge/data/` or `tests/integration/data/`. Status: ☑ done. **Implemented** — `pytest tests/unit/fbpro98_standings` → 105 passing.

## season.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Teams numbered in file order, with division and conference | built | numbers, divisions, conferences | `test_teams_numbered_in_file_order_with_their_division_and_conference` | ☑ |
| A game counts for both teams | built | both results | `test_a_game_counts_for_both_teams` | ☑ |
| Division and conference games marked | built | flags | `test_games_marked_division_and_conference` | ☑ |
| Won, lost, tied | built | `won` / `lost` | `test_won_and_lost` | ☑ |
| Playoff round reached; champion and runner-up | built | rounds | `test_playoff_round_reached_and_the_final` | ☑ |
| A bye counts by the later round | built | rounds | `test_a_bye_counts_by_the_later_round` | ☑ |
| No champion before the final | built | None | `test_no_champion_before_the_final_is_played` | ☑ |
| Real season | golden | 18 teams, 16 games, Miami over Minnesota | `test_real_season` | ☑ |

## steps.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Percentage: tie half a win, no game 0 | built | 3/4, 0 | `test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero` | ☑ |
| W-L-T % | built | values | `test_win_percentage_counts_every_game` | ☑ |
| Head-to-head among the level teams only | built | values | `test_head_to_head_counts_only_games_among_the_level_teams` | ☑ |
| Sweep: two teams, beat all, lost to all, cycle, not all played | built | values / None | `test_sweep_*`, `test_no_sweep_*` | ☑ |
| Division and conference % | built | values | `test_division_and_conference_percentage` | ☑ |
| Net points: division, conference, all | built | values | `test_net_points_by_kind_of_game` | ☑ |
| Common games: four accepted, three skipped | built | values / None | `test_common_games_at_the_minimum_apply`, `test_common_games_one_short_of_the_minimum_skipped` | ☑ |
| Net points in common games | built | values | `test_common_net_points` | ☑ |
| Strength of victory, every win | built | 2/9 | `test_strength_of_victory_counts_every_win` | ☑ |
| Strength of schedule, each opponent once or every game | built | 1/6, 2/9 | `test_strength_of_schedule_each_opponent_once_or_every_game` | ☑ |
| Combined ranking, conference and league, shared ranks | built | values | `test_combined_ranking_within_the_conference_or_the_league` | ☑ |
| Division finish: one division, different divisions | built | values / None | `test_division_finish_*` | ☑ |
| Playoff round; champion then runner-up | built | values | `test_playoff_round_and_champion_then_runner_up` | ☑ |

## moves.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Match by name wherever a team moved | built | numbers | `test_teams_match_by_name_wherever_they_moved` | ☑ |
| A renamed team | built | numbers | `test_a_team_move_matches_a_renamed_team` | ☑ |
| Two teams swap names | built | numbers | `test_team_moves_may_swap_names` | ☑ |
| Repeated name, bad move, missing or extra team | built | `StandingsError` | `test_mismatch_rejected` `[P]` | ☑ |

## standings.py and the methods

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Regroup: placed teams and the rest ranked again | built | A, B, C | `test_regroup_ranks_the_placed_teams_and_the_rest_again` | ☑ |
| Coin toss: a seed repeats it, request order does not matter, answers kept, conference agrees with division | built | equal orders | `test_a_seed_repeats_the_coin_toss`, `test_the_coin_toss_does_not_depend_on_what_was_asked_before`, `test_without_a_seed_the_same_question_gets_the_same_answer`, `test_conference_standings_agree_with_division_standings` `[P]` | ☑ |
| Caller mistakes | built | `ValueError` | `test_unknown_method_rejected`, `test_team_moves_need_the_previous_file`, `test_a_division_of_another_file_rejected`, `test_a_conference_of_another_file_rejected` | ☑ |
| Empty division; teams that look alike | built | `()`; by position | `test_an_empty_division_has_no_standings`, `test_teams_that_look_alike_stay_apart` | ☑ |
| Every method before week 1 and before the playoffs | golden | each team once | `test_every_method_on_a_season_not_finished` `[P]` | ☑ |
| Game: division standings as the game shows them | golden | 2043, 2046, 2048 orders | `test_game_division_standings_match_the_game` `[P]` | ☑ |
| Game: conference standings, division winners first | golden | 2047 orders | `test_game_conference_standings_put_division_winners_first` | ☑ |
| Game: regroup after a step places one team | built | T1, T2, T3 | `test_game_ranks_the_placed_teams_and_the_rest_again` | ☑ |
| Game: league standings | built | orders | `test_game_league_*` | ☑ |
| Game: league without divisions | built | winner first | `test_game_conference_without_divisions` | ☑ |
| Scheduler: league standings as the 2048 and 2047 standings files | golden | orders | `test_scheduler_league_matches_the_2048_standings_file`, `test_scheduler_league_breaks_a_division_tie_on_division_finish` | ☑ |
| Scheduler: division finish skipped across divisions, or over point differential | built | orders | `test_scheduler_division_finish_*` | ☑ |
| Scheduler: conference in league order | golden | orders | `test_scheduler_conference_standings_follow_the_league_order` | ☑ |
| NFL: one team advances; each division's and conference's best | built | orders | `test_nfl_sends_the_teams_a_step_dropped_back_to_the_first_tie_breaker`, `test_nfl_conference_keeps_only_each_divisions_best`, `test_nfl_league_keeps_each_divisions_then_each_conferences_best` | ☑ |
| NFL: real season | golden | Miami, Minnesota first; each team once | `test_nfl_on_a_real_season` | ☑ |
| Two seasons: 2047 -> 2048 as the 2048 standings file; current teams; a team that changed division; a missing move | golden | orders, error | `test_two_seasons.py` | ☑ |
