# standings — Test Matrix

Cases covered for the standings command's tool package. Convention in [../../../docs/testing-unit.md](../../../docs/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `built` = a league built in code; `golden` = a real `.lge` from `tests/unit/fbpro98_lge/data/`. Status: ☑ done.

## records.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Overall wins, losses, ties | built | 1-1-1 | `test_overall_counts_wins_losses_and_ties` | ☑ |
| Home and away | built | home 1-0, away 0-1 | `test_home_and_away` | ☑ |
| Division and conference | built | division 1-0, conference 1-1 | `test_division_and_conference` | ☑ |
| Points for and against | built | 27, 47 | `test_points_for_and_against` | ☑ |
| Streak: wins, losses, tie last, tie ends the run, no games | built | `W2`, `L2`, `-`, `W1`, `-` | `test_streak` `[P]` | ☑ |
| Playoff games not counted | built | regular season only | `test_playoff_games_not_counted` | ☑ |
| Every team has a row | built | one per team | `test_every_team_has_a_row` | ☑ |
| Rows match the file's own records | golden | W, L, T, PF, PA equal `Team.record` | `test_rows_match_the_file_records` `[P]` | ☑ |

## views.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Game view: conference columns, divisions stacked, the shorter block padded | built | exact lines | `test_game_view` | ☑ |
| League view: title, header, every team numbered | built | exact lines | `test_league_view` | ☑ |
| Conference view: each conference numbered from 1 | built | exact lines | `test_conference_view` | ☑ |
| Division view: conference titles, division headers | built | exact lines | `test_division_view` | ☑ |
| One named conference: one column, its own name | built | exact lines | `test_game_view_one_conference` | ☑ |
| PCT: no games, no wins, half, a tie, above a half, below a half, a half rounds up (two), all wins | values | `.000` `.000` `.500` `.500` `.667` `.333` `.813` `.563` `1.000` | `test_percentage` `[P]` | ☑ |
| Record: no ties, ties, no games | values | `2-1` `0-1-1` `0-0` | `test_record` `[P]` | ☑ |
| DIFF: ahead, behind, even | values | `+23` `-8` `0` | `test_difference` `[P]` | ☑ |
