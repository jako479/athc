# scheduler — Test Matrix: Phase 1 (Matchups)

Cases for `matchup_builder.py`, in `test_matchups.py`. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md). Design: [phase-1-matchups.md](../../../docs/scheduler/phase-1-matchups.md).

Every row runs for each distinct league (two divisional standings variants, the conference league) unless noted. Status: ☑ covered · ☐ no test yet. The phase-1 solve is fast at spread 2.5; the flat line on the conference league is `slow`.

### Structure
| Case | Expected | Test | Status |
|---|---|---|---|
| Total inventory | `weeks × 9` pairings, `weeks` per team | `test_inventory_totals` | ☑ |
| Divisional twice, conference once, non-conference ≤ once | per pair | `test_divisional_twice_conference_once_nonconference_at_most_once` | ☑ |
| Non-conference degree | distinct opponents = `league.nonconference_games` | `test_nonconference_degree_matches_the_league` | ☑ |
| Canonical pair ordering | (lower-metro, higher-metro) | `test_inventory_uses_canonical_pair_ordering` | ☑ |
| Deterministic | same inventory each run | `test_inventory_is_deterministic` | ☑ |
| Fewer weeks (no divisions) | fewer non-conference games per team | `test_fewer_weeks_give_fewer_nonconference_games` | ☑ |

### Fixed non-conference games
| Case | Expected | Test | Status |
|---|---|---|---|
| Fixed pairs | same-place pairs ∪ cross-conference rivalries, all in the inventory | `test_fixed_pairs_are_same_place_pairs_and_cross_rivalries` | ☑ |
| Same-place rule | each place vs the same place in every other-conference division that has it; cross-conference; none without divisions | `test_same_place_pairs_match_the_divisions` | ☑ |
| Two 4-team + two 5-team divisions | 17 pairs | `test_same_place_pair_count_for_two_4_and_two_5_team_divisions` | ☑ |
| Fixed degree per team | one per other-conference division with the place, plus the cross rivalry | `test_fixed_pair_degree_follows_the_places` | ☑ |
| Standings drive the pairs | division place used, not conference rank | `test_fixed_pairs_follow_division_standings_not_rank` | ☑ |

### Difficulty line
| Case | Expected | Test | Status |
|---|---|---|---|
| ≥1 top-half & ≥1 bottom-half opponent | per team | `test_each_team_draws_a_top_and_bottom_half_opponent` | ☑ |
| Teams near line target | within 1.0 at spread 0 / 1.8 / 2.5 (flat conference case `slow`) | `test_difficulty_is_near_line_target` | ☑ |
| Difficulty ordered by rank | top seed's avg < bottom's, both conferences | `test_orders_difficulty_by_conference_rank` | ☑ |
| Line target values | 2.5/5/7.5; 0 flat; symmetric; monotonic | `test_difficulty_target_line` | ☑ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| CP-SAT drops a forced pair / unfilled slots / infeasible model | raises | — | ☐ |

## Gaps

Untested: the forced-pair / totals / infeasibility error paths (hard to trigger without mocking the solver). The CLI maps a `SchedulerError` to exit 1 (`test_cli.py`).
