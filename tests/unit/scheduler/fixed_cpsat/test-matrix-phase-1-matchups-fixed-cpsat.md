# scheduler — Test Matrix: Phase 1 Fixed-Place + CP-SAT (Matchups)

Cases for `fixed_cpsat_builder.py` (Scheduler C), derived from the code then reconciled with the suite. Convention in [../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-1-matchups-fixed-cpsat.md](../../../../docs/scheduler/phase-1-matchups-fixed-cpsat.md).

One row per behavior. Status: ☑ covered · ☐ no test yet. The phase-1 solve is fast, so these run in the default suite.

### Normal
| Case | Expected | Test | Status |
|---|---|---|---|
| Divisional inventory | every divisional opponent twice | `test_inventory_has_expected_divisional_and_conference_counts` | ☑ |
| Conference inventory | every same-conf cross-division team once | (same) | ☑ |
| Fixed-place opponents | 2 per team (5ths 1) from table + standings | `test_inventory_contains_fixed_place_table_pairs` | ☑ |
| Fixed pairs recorded | 17 pairs, right count per team | `test_inventory_records_fixed_pairs_per_team` | ☑ |
| Standings drive fixed pairs | division place used, not conference rank | `test_fixed_pairs_follow_division_standings_not_rank` | ☑ |
| Non-conference counts | 4-team div 5; 5-team div 4 | `test_inventory_assigns_expected_nonconference_degree` | ☑ |
| Total inventory | 144 pairings, per-team 16 | `test_inventory_has_expected_total_counts` | ☑ |
| Canonical pair ordering | (lower-metro, higher-metro) | `test_inventory_uses_canonical_pair_ordering` | ☑ |
| ≥1 top-half & ≥1 bottom-half opponent | holds per team | `test_gives_each_team_a_top_and_bottom_half_opponent` | ☑ |
| Deterministic | same inventory each run | `test_inventory_is_deterministic` | ☑ |
| Line target values | 1.5 → 3.5/5/6.5; 0 flat; symmetric; monotonic | `test_difficulty_target_line` | ☑ |
| Teams near line target | within 1.0 of target at spread 0/1.5/2.5 (worst observed 0.75) | `test_difficulty_is_near_line_target` | ☑ |
| Difficulty ordered by rank | top conference seed's avg < bottom's, both conferences | `test_orders_difficulty_by_conference_rank` | ☑ |

### Place table
| Case | Expected | Test | Status |
|---|---|---|---|
| Covers every slot | one entry per (division, place) | `test_place_table_covers_every_division_place` | ☑ |
| Symmetric, cross-conference | distinct opponents, reverse edges exist | `test_place_table_is_symmetric_and_cross_conference` | ☑ |
| 17 unique pairs | pair set size 17 | `test_place_table_defines_17_unique_pairs` | ☑ |
| Same-place only | places 1-4 both same-place finishers; 5ths each other | `test_place_table_is_same_place_only` | ☑ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| Place table shape invalid | raises (missing slots / wrong count / asymmetric / same-conference) | `test_place_table_validation_rejects_invalid_table` | ☑ |
| Missing division standings | raises, names [DivisionStandings] | `test_builder_errors_without_division_standings` | ☑ |
| CP-SAT drops a forced table pair | raises | — | ☐ |
| Unfilled slots / wrong totals | raises | — | ☐ |
| Infeasible CP-SAT model | raises | — | ☐ |

## Gaps

Untested: the forced-pair / totals / infeasibility error paths (hard to trigger without mocking the solver). The place-table validation is covered.
