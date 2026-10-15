# scheduler — Phase 1: Matchup Inventory

Phase 1 — [`matchup_builder.py`](../src/athc/scheduler/schedulers/matchup_builder.py). Structure fixes the same-conference games; the rest of each team's weeks are non-conference. Some non-conference games are fixed — the same-place pairs (a league with divisions) and any cross-conference rivalry — and one CP-SAT solve picks the rest, along the difficulty line or at random. Produces the full inventory (`weeks` × 9 pairings) and feeds [Phase 2](scheduler-phase-2-schedule.md).

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.
- Without divisions: every conference team once.

## Non-conference

Each team's non-conference count is `weeks` minus its structural games (a 4-team-division team has one more than a 5-team-division team).

1. **Same-place pairs** — each place in a division plays the same place in every other-conference division that has that place. With two 4-team and two 5-team divisions that is 17 pairs: places 1-4 get two games each, the two 5th places play each other. Places come from each division's finish order: its teams ranked by their previous-season records (see [scheduler.md](scheduler.md#the-standings)).

2. **Rivalries** — a cross-conference `[rivalries]` pair is a fixed non-conference game.

3. **CP-SAT for the rest** — one solve fills the remaining games with the fixed pairs forced in: along the difficulty line, or at random with `random_nonconference`.

## The difficulty line

Each team's target is a sum: the conference ranks (1-9) of its non-conference opponents, fixed pairs included, added up. Best team hardest, worst easiest, linear between:

`target = 5 × games + tilted × slope × (rank − 5) / 4`

- `games` is the team's non-conference count; `tilted` is the league's smallest (4 in both shipped leagues).
- `slope` is `[phase1] difficulty_slope` (default 2.5; 0 = flat).
- The slope tilts `tilted` games, and each game past them adds a neutral rank 5, so a team with an extra game gets no extra tilt.
- At 2.5, rank 1 aims at 10 over 4 games (ranks 1-4) and 15 over 5 (ranks 1-5); rank 9 at 30 and 35.

The target is soft: the solve minimizes the worst team's miss, then the total, in 1/20-rank units. In the tests every team lands within 4 of its target.

## Random non-conference games

With `[phase1] random_nonconference = true` (the PCFL's option; off by default), every fixed pair is still forced and the rest are random: each possible pairing gets a weight drawn from the run's seed, and the solve keeps the set with the highest total weight. `difficulty_slope` is ignored.

Why seeded weights in the solver: the same seed then repeats its matchups on any machine, like the rest of the run, and the solve already enforces the fixed pairs and game counts. A shuffle-and-fill picker in Python would need its own search and restarts on dead ends; the solver with no objective returns its first valid set, which looks alike from seed to seed and changes with the worker count.

## The solve

Like phase 2's: multithreaded across `solver_workers` (a number, or `"auto"` = fast threads minus 2), stopping on `[solver] phase1_time_limit` in deterministic time, so it is reproducible per seed at the same worker count; when several matchup sets tie at the optimum, the seed picks one.

## Validation

`weeks × 9` total pairings and the league's non-conference total, no unfilled slots, and the solution must keep every forced pair, or it errors. An infeasible or timed-out solve errors (`SchedulerError`, exit 2).
