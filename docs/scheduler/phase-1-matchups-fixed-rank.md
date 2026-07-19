# scheduler — Phase 1: Fixed-Rank Matchup Inventory

**Scheduler A** (fixed-rank) phase 1 — [`fixed_matchup_builder.py`](../../src/athc/scheduler/schedulers/fixed_matchup_builder.py). A prototype: it produces the same 144-pairing inventory as [Scheduler B](phase-1-matchups.md) and differs only in how non-conference games are chosen. Output feeds [Phase 2](phase-2-schedule.md).

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.

## Non-conference (three steps)

Teams are ranked **1–9 within each conference** (not by division), so every team has a rank — there is no missing-rank gap from the uneven 4-/5-team divisions. The size difference only changes the per-team count: **4-team divisions play 5 non-conference games, 5-team divisions play 4** (4-team divisions have fewer divisional/conference games, so they get one extra).

1. **Fixed rank table** — 3 opponents per team from a symmetric conference-rank table:

   | Rank | Opponents | Rank | Opponents |
   |---|---|---|---|
   | 1 | 1, 2, 3 | 6 | 4, 6, 8 |
   | 2 | 1, 2, 4 | 7 | 5, 7, 9 |
   | 3 | 1, 3, 5 | 8 | 6, 8, 9 |
   | 4 | 2, 4, 6 | 9 | 7, 8, 9 |
   | 5 | 3, 5, 7 |   |   |

2. **Extra East pairing** (4-team divisions only) — the 5th game: one AFC-East × NFC-East pairing by minimum-cost assignment on rank gap, skipping pairs already chosen.
3. **Final H2H pairing** — each team's remaining single slot is matched by minimum-cost assignment. Cost equally weights head-to-head recency (longer since last played = cheaper, measured against the most recent recorded season) and a rank target (1↔6, 2↔7, 3↔8, 4↔9, 5↔5), the rank term carrying a 3× penalty that steers top teams away from harder opponents and bottom teams away from easier ones.

The assignment steps use OR-Tools LinearSumAssignment.

## Validation

Same as the main generator: 144 total, exactly 40 non-conference, no unfilled slots, or it errors.
