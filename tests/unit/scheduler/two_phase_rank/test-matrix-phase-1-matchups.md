# scheduler — Test Matrix: Phase 1 (Matchups)

Cases for `matchup_builder.py` (Scheduler B), derived from the code then reconciled with the suite. Convention in [../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-1-matchups.md](../../../../docs/scheduler/phase-1-matchups.md).

One row per behavior. Status: ☑ covered · ☐ no test yet. Solver-backed cases are `slow` (`pytest -m slow`).

### Normal
| Case | Expected | Test | Status |
|---|---|---|---|
| Divisional inventory | every divisional opponent twice | `test_rank_only_inventory_has_expected_divisional_and_conference_counts` | ☑ |
| Conference inventory | every same-conf cross-division team once | (same) | ☑ |
| Non-conference counts | 4-team div 5; 5-team div 4 | `test_rank_only_inventory_assigns_expected_nonconference_degree` | ☑ |
| Total inventory | 144 pairings, per-team 16 | `test_rank_only_inventory_has_expected_total_counts` | ☑ |
| Canonical pair ordering | (lower-metro, higher-metro) | `test_rank_only_inventory_uses_canonical_pair_ordering` | ☑ |
| ≥1 top-half opponent (rank ≤5) | holds per team | — | ☐ |
| ≥1 bottom-half opponent (rank ≥5) | holds per team | — | ☐ |
| Strength ordered by rank | stronger team's normalized opponent-rank-sum ≤ weaker's | — | ☐ |
| Similar-rank objective | smaller rank gaps preferred | — | ☐ |
| Deterministic | same inventory each run | — | ☐ |

### Edge
| Case | Expected | Test | Status |
|---|---|---|---|
| 4-team & 5-team division layouts | both solve | parametrized `league` configs | ☑ |

### Error
| Case | Expected | Test | Status |
|---|---|---|---|
| Unfilled non-conference slots | raises | — | ☐ |
| Non-conference total ≠ 40 | raises | — | ☐ |
| Total ≠ 144 | raises | — | ☐ |
| Infeasible rank model | raises | — | ☐ |

## Gaps

Untested: the rank/difficulty logic (top/bottom floor, rank-ordered strength, objective) and every error path.
