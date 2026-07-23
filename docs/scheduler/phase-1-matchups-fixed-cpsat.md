# scheduler — Phase 1: Fixed-Place + CP-SAT Matchup Inventory

**Scheduler C** phase 1 — [`fixed_cpsat_builder.py`](../../src/athc/scheduler/schedulers/fixed_cpsat_builder.py). NFL-like: division standings fix two non-conference games per team; one CP-SAT solve picks the rest along a configurable difficulty line. Produces the same 144-pairing inventory as A and B and feeds [Phase 2](phase-2-schedule.md). Needs the league file's `[DivisionStandings]` section; no history file.

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.

## Non-conference

4-team divisions play 5 non-conference games, 5-team divisions play 4.

1. **Fixed games (17 pairs)** — each team plays the same-place finisher in both other-conference divisions (AE1 vs NE1 and NW1, etc.). The two 5th places play each other, one game.

2. **CP-SAT for the rest (23 pairs)** — one solve fills the remaining 2-3 games per team (5ths get 3). The fixed pairs are forced into the model. Objective: each team's average opponent conference rank (1-9, whole slate) lands on a line — best team hardest, worst easiest:

   `target(rank) = 5 + c_spread × (rank − 5) / 4`

   `c_spread` (rules toml, default 2.5): 0 = flat, 2.5 = max useful tilt (#1's slate saturates at opponents ranked 1-5). The target is soft (minimax on the worst miss, then total); worst observed miss across the test leagues is 0.75 ranks. Each team also draws ≥1 top-half and ≥1 bottom-half opponent. Reproducible per seed; when several matchup sets tie at the optimum, the seed picks one.

## Validation

144 total, exactly 40 non-conference, no unfilled slots, and the solution must keep all forced pairs, or it errors. A missing `[DivisionStandings]`, an infeasible solve, or a timed-out solve errors.
