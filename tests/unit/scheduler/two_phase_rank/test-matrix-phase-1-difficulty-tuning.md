# scheduler — Test Matrix: Phase 1 Difficulty Tuning

Cases for the strength-of-schedule curve and bounds in `matchup_builder.py` (the new scheduler). Convention in [../../../docs/design/testing-unit.md](../../../../docs/design/testing-unit.md). Design: [phase-1-difficulty-tuning.md](../../../../docs/scheduler/phase-1-difficulty-tuning.md). Status: ☑ covered · ☐ no test yet.

### Normal
| Case | Expected | Test | Status |
|---|---|---|---|
| Curve target values | rank 1 → ~6.3, rank 18 → ~12.7 (overall 1–18 scale) | `test_difficulty_target_curve` | ☑ |
| Curve monotonic & symmetric about 9.5 | targets sorted; `target(r) + target(19−r) = 19` | `test_difficulty_target_curve` | ☑ |
| Teams land near the curve targets | each team's avg opponent rank within ~1.5 of its target (soft; not enforced) | `test_rank_only_difficulty_is_near_curve_target` | ☑ |
| Difficulty ordered by rank | top overall seed's average < bottom seed's | `test_rank_only_orders_difficulty_by_rank` | ☑ |

### Edge / Error
| Case | Expected | Test | Status |
|---|---|---|---|
| All three playoff-split configs build | `5/6/7-free-slots` = 4-team division supplies 1/2/3 playoff teams; all solve | parametrized `league` configs | ☑ |
| Difficulty never blocks a schedule | soft target — never raises (no hard cap) | by design | ☑ |
