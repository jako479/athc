# scheduler — Test Matrix: League Without Divisions (PCFL)

Cases for the conference-only format, end to end on solved schedules (`conftest.py`: even season, odd season, rotation off). Convention in [../../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-2-schedule.md](../../../../docs/scheduler/phase-2-schedule.md).

| Case | Expected | Test | Status |
|---|---|---|---|
| Structure | 108 games, 9 a week, 12 per team, 6 home | `test_structure` | ☑ |
| Inventory realized | matches phase 1 | `test_matches_phase_one_inventory` | ☑ |
| Conference round robin | every conference team once, 4 home / 4 away | `test_conference_round_robin_four_home_four_away` | ☑ |
| Non-conference hosting | 4 games, 2 home / 2 away | `test_nonconference_two_home_two_away` | ☑ |
| Opening weeks | weeks 1-3 all non-conference | `test_opening_weeks_are_all_nonconference` | ☑ |
| Idle-team game | weeks 4-12 hold one cross-conference game each | `test_later_weeks_hold_exactly_one_cross_conference_game` | ☑ |
| Home/away streaks | ≤3 straight | `test_max_three_consecutive_home_or_away` | ☑ |
| Conference-sequence streaks | ≤2 straight along conference games | `test_max_two_consecutive_conference_home_or_away` | ☑ |
| Rivalry week | week 12 is exactly the nine pairs | `test_final_week_is_rivalry_week` | ☑ |
| Rivalry hosting | even: first listed hosts; odd: second; off: free | `test_even_season_first_listed_hosts`, `test_odd_season_second_listed_hosts`, `test_rotation_off_still_plays_rivalries_in_the_final_week` | ☑ |
| Report | builds for a division-less league | `test_report_builds_for_a_league_without_divisions` | ☑ |
| Entry rejects a bad config before solving | weeks 8, opening weeks 4, unknown rivalry team → `ConfigError` | `test_entry_rejects_weeks_that_do_not_fit_the_league`, `test_entry_rejects_opening_weeks_that_leave_no_room`, `test_entry_rejects_an_unknown_rivalry_team` | ☑ |
| Inventory solves fast by default | shared plan at spread 2.5; flat-line target case is `slow` | `test_inventory.py` | ☑ |
