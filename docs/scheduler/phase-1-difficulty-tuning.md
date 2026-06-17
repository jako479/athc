# scheduler — Phase 1: Difficulty Tuning

Addendum to [phase-1-matchups.md](phase-1-matchups.md). How the rank-only generator shapes non-conference strength of schedule, on the overall 1–18 ranking. **Implemented**; defaults in `config.py`, overridable in `rules/PNFL.scheduler.toml` `[difficulty]`: spread `A = 3.19` (endpoints ~6.3/12.7), shape `p = 2`. The targets are soft — never hard caps, so difficulty can't make a schedule infeasible.

## Measure

A team's difficulty = its **average opponent rank** — the overall ranks (1–18) of its non-conference opponents, averaged. 1 = toughest opponents, 18 = easiest, 9.5 = average. The model tracks `opponent_rank_sum`; the average is that divided by the team's 4 or 5 non-conference games.

## Spread (curve endpoints)

Spread `A` sets the curve's endpoints, symmetric about 9.5:

- the #1 team's target (toughest) = `9.5 − A`
- the #18 team's target (easiest) = `9.5 + A`

Current `A = 3.19` → ~6.3 and ~12.7. (`A = 8.5` = maximum spread; `A = 0` = everyone targets 9.5, pure parity.) These are **targets, not caps** — a team is never forbidden from landing outside them, so difficulty can never make the schedule infeasible.

## Curve

Within the band, shape `p` sets where each rank aims:

```
target(r) = 9.5 + A * sign(r - 9.5) * (|r - 9.5| / 8.5) ** p
```

- `r` = team's overall rank, 1–18. `9.5` = center; `8.5` = half the rank range, so `(r−9.5)/8.5` runs −1…+1.
- `p = 1` → straight gradient. Higher `p` → flatter middle, only the top/bottom teams diverge (a "bell"). Current `p = 2`.

## Enforcement

Each team's deviation from its target is scored in 1/20-rank units (20 = LCM of the 4- and 5-game counts, so every team shares one unit, measured against the exact target). The solver minimizes the **largest** deviation (minimax), then the total as a tie-break (minisum). No hard caps, so a schedule is always produced — minimax keeps every team close to its target and the tie-break tightens the rest.

## Sample targets

Target average opponent rank by team rank (current `A = 3.19`, `p = 2`):

| Rank | 1 | 5 | 9 | 10 | 14 | 18 |
|---|---|---|---|---|---|---|
| Target | 6.3 | 8.6 | 9.5 | 9.5 | 10.4 | 12.7 |

`p` flattens the middle (mid-ranked teams stay near 9.5); `A` widens or narrows the whole band. Config: `[difficulty] spread` = `A`, `shape` = `p`, in `rules/PNFL.scheduler.toml`.

## Test configs

The unit tests run three ranking variants (`5/6/7-free-slots`) spanning the playoff-distribution splits: each conference has 4 playoff teams (2 division winners + 2 wild cards), and the 4-team division supplies 1, 2, or 3 of them (the 5-team division the rest). This varies how many 5-non-conference-game teams rank near the top — the case that most stresses these targets. Each league is given as an overall 1–18 standings (the two conference orders interleaved).
