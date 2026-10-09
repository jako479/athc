# scheduler — Phase 1: Matchup Inventory

Phase 1 — [`matchup_builder.py`](../../src/athc/scheduler/schedulers/matchup_builder.py). Structure fixes the same-conference games; the rest of each team's weeks are non-conference. Some non-conference games are fixed — the same-place pairs (a league with divisions) and any cross-conference rivalry — and one CP-SAT solve picks the rest along the difficulty line. Produces the full inventory (`weeks` × 9 pairings) and feeds [Phase 2](phase-2-schedule.md).

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.
- Without divisions: every conference team once.

## Non-conference

Each team's non-conference count is `weeks` minus its structural games (a 4-team-division team has one more than a 5-team-division team).

1. **Same-place pairs** — each place in a division plays the same place in every other-conference division that has that place. With two 4-team and two 5-team divisions that is 17 pairs: places 1-4 get two games each, the two 5th places play each other. Places come from the standings file's finish order.

2. **Rivalries** — a cross-conference `[rivalries]` pair is a fixed non-conference game.

3. **CP-SAT for the rest** — one solve fills the remaining games with the fixed pairs forced in. Objective: each team's average opponent conference rank (1-9, whole slate) lands on a line — best team hardest, worst easiest:

   `target(rank) = 5 + spread × (rank − 5) / 4`

   `spread` (rules toml, default 2.5): 0 = flat, 2.5 = max useful tilt. The target is soft (minimax on the worst miss, then total); worst observed miss across the test leagues is 0.75 ranks. Each team also draws ≥1 top-half and ≥1 bottom-half opponent. The solve runs like phase 2's — multithreaded across `solver_workers` (a number, or `"auto"` = fast threads minus 2), stopping on `phase1_time_limit` in deterministic time — so it is reproducible per seed (at the same worker count); when several matchup sets tie at the optimum, the seed picks one.

## Validation

`weeks × 9` total pairings and the league's non-conference total, no unfilled slots, and the solution must keep every forced pair, or it errors. An infeasible or timed-out solve errors (`SchedulerError`, exit 2).
