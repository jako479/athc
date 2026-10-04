# scheduler — Phase 1: Fixed-Place + CP-SAT Matchup Inventory

Phase 1 — [`fixed_cpsat_builder.py`](../../src/athc/scheduler/schedulers/fixed_cpsat_builder.py). Structure fixes the same-conference games; the rest of each team's weeks are non-conference. Fixed non-conference games are the PNFL's same-place pairs (a league with divisions) and any cross-conference rivalry; one CP-SAT solve picks the rest along the difficulty line. Produces the full inventory (`weeks` × 9 pairings: 144 for the PNFL, 108 for the PCFL) and feeds [Phase 2](phase-2-schedule.md). A league with divisions needs `[DivisionStandings]` for the place table; no history file.

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.
- Without divisions: every conference team once (the PCFL: 8 games, leaving 4 non-conference in 12 weeks).

## Non-conference

PNFL: 4-team divisions play 5 non-conference games, 5-team divisions play 4. PCFL: every team plays 4 (36 pairs); only the cross-conference rivalry is fixed, the solver picks the rest.

1. **Fixed games (17 pairs)** — each team plays the same-place finisher in both other-conference divisions (AE1 vs NE1 and NW1, etc.). The two 5th places play each other, one game.

2. **CP-SAT for the rest (23 pairs)** — one solve fills the remaining 2-3 games per team (5ths get 3). The fixed pairs are forced into the model. Objective: each team's average opponent conference rank (1-9, whole slate) lands on a line — best team hardest, worst easiest:

   `target(rank) = 5 + spread × (rank − 5) / 4`

   `spread` (rules toml, default 2.5): 0 = flat, 2.5 = max useful tilt (#1's slate saturates at opponents ranked 1-5). The target is soft (minimax on the worst miss, then total); worst observed miss across the test leagues is 0.75 ranks. Each team also draws ≥1 top-half and ≥1 bottom-half opponent. Reproducible per seed; when several matchup sets tie at the optimum, the seed picks one.

## Validation

`weeks × 9` total pairings and the league's non-conference total (40 for the PNFL, 36 for the PCFL), no unfilled slots, and the solution must keep all forced pairs, or it errors. An infeasible or timed-out solve errors.
