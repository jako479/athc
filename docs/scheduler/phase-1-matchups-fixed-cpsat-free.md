# scheduler — Phase 1: Fixed-Place + CP-SAT Free-Only Matchup Inventory

**Scheduler D** phase 1 — [`fixed_cpsat_free_builder.py`](../../src/athc/scheduler/schedulers/fixed_cpsat_free_builder.py). Identical to [Scheduler C](phase-1-matchups-fixed-cpsat.md) — same 17 fixed same-place games, same CP-SAT fill — except the difficulty line targets **only the picked games**; the fixed games don't count toward it. Needs `[DivisionStandings]`; no history file.

## Difference from C

C steers each team's whole non-conference slate onto its line, so tough fixed games are offset with easy picks. D leaves the fixed games out: the picks themselves follow the line, and whatever the fixed games add rides on top.

`target(rank) = 5 + d_spread × (rank − 5) / 4`

`d_spread` (rules toml, default 1.5): 0 = flat picks, higher = steeper. The target is soft (minimax on the worst miss, then total), and steep tilts saturate -- the picked-opponent pool is fixed by game counts, so the worst miss grows with the tilt (about 0.9 x d_spread across the test leagues). Each team also draws ≥1 top-half and ≥1 bottom-half opponent. Reproducible per seed; when several matchup sets tie at the optimum, the seed picks one.

## Validation

Same as C: 144 total, exactly 40 non-conference, no unfilled slots, all forced pairs kept, or it errors. A missing `[DivisionStandings]`, an infeasible solve, or a timed-out solve errors.
