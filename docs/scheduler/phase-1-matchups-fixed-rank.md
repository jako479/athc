# scheduler — Phase 1: Fixed-Rank Matchup Inventory

Alternate phase-1 generator — [`fixed_matchup_builder.py`](../../src/athc/scheduler/schedulers/fixed_matchup_builder.py). A prototype: it produces the same 144-pairing inventory as the [main generator](phase-1-matchups.md) and differs only in how non-conference games are chosen. Output feeds [Phase 2](phase-2-schedule.md).

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.

## Non-conference (three steps)

1. **Fixed rank table** — 3 opponents per team from a fixed rank→opponent table (symmetric; e.g. rank 1 draws ranks 1–3, rank 9 draws ranks 7–9).
2. **Extra East pairing** (4-team divisions only) — one AFC-East × NFC-East game by minimum-cost assignment on rank gap, skipping pairs already chosen.
3. **Final H2H pairing** — each remaining single-slot team is matched by minimum-cost assignment. Cost equally weights two terms: head-to-head history (longer since last played = cheaper; never-played is the cheapest) and a rank target (1↔6, 2↔7, 3↔8, 4↔9, 5↔5), the rank term carrying a 3× penalty that steers top teams away from harder opponents and bottom teams away from easier ones.

Per-team counts: 5 for 4-team divisions, 4 for 5-team divisions. The assignment steps use OR-Tools LinearSumAssignment.

## Validation

Same as the main generator: 144 total, exactly 40 non-conference, no unfilled slots, or it errors.
