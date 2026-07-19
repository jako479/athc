# scheduler — Test Matrix: Phase 1 Fixed-Rank (Matchups)

Cases for `fixed_matchup_builder.py` (Scheduler A), derived from the code then reconciled with the suite. Convention in [../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-1-matchups-fixed-rank.md](../../../../docs/scheduler/phase-1-matchups-fixed-rank.md).

One row per behavior. Status: ☑ covered · ☐ no test yet. Solver-backed cases are `slow` (`pytest -m slow`).

### Normal
| Case | Expected | Test | Status |
|---|---|---|---|
| Divisional inventory | every divisional opponent twice | `test_phase_one_inventory_has_expected_divisional_and_conference_counts` | ☑ |
| Conference inventory | every same-conf cross-division team once | (same) | ☑ |
| Fixed-rank opponents | 3 per team from the rank table | `test_phase_one_inventory_contains_fixed_rank_table_pairs` | ☑ |
| Extra East pairing (4-team divs) | exactly 4 AFC-East × NFC-East pairs | `test_phase_one_inventory_adds_extra_east_sos_pairs` | ☑ |
| Remaining slots filled | non-fixed opponent counts correct | `test_phase_one_inventory_history_fills_remaining_nonconference_slots` | ☑ |
| Non-conference counts | 4-team div 5; 5-team div 4 | `test_phase_one_inventory_assigns_expected_nonconference_degree` | ☑ |
| Total inventory | 144 pairings, per-team 16 | `test_phase_one_inventory_has_expected_total_counts` | ☑ |
| Canonical pair ordering | (lower-metro, higher-metro) | `test_phase_one_inventory_uses_canonical_pair_ordering` | ☑ |
| History cost | most recent recorded season 0, older lower | `test_opponent_cost_is_seasons_since_most_recent_recorded`, `test_nonconf_history_file_has_expected_h2h_costs_for_all_pairs` | ☑ |
| Final H2H pairing shaping | rank target (1↔6 … 5↔5) + 3× unfavorable picks opponent | — | ☐ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| Fixed rank table shape invalid | raises | — | ☐ |
| East division not exactly 4 teams | raises | — | ☐ |
| Unbalanced assignment sides | raises | — | ☐ |
| Assignment leaves a team unmatched | raises | — | ☐ |
| History step sees a multi-slot team | raises | — | ☐ |
| Unfilled slots / wrong totals | raises | — | ☐ |

## Gaps

Untested: the H2H/rank cost shaping (pseudo-inverse target + 3× multiplier) and every error path. The raw history costs are covered.
