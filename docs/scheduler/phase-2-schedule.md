# scheduler — Phase 2: Schedule Placement

Phase 2 takes the fixed 144-pairing inventory from phase 1 and uses OR-Tools CP-SAT to assign every matchup a week (1–16) and a home team. Shared by both schedulers (C and D) — [`schedule_builder.py`](../../src/athc/scheduler/schedulers/schedule_builder.py).

## Model

- Decision var `x[home, away, week]` (bool) per ordered team pair and week. Helper bools: `h[team, week]` (home that week), `d[team, week]` (divisional game that week).
- Output: a `Schedule` of 16 weeks × 9 games.
- Solve: single worker, seeded + randomized search, under the configured time limit. No feasible solution (or timeout) errors.

## Constraints

The numeric amounts below come from `[phase2]` in `rules/PNFL.scheduler.toml` (defaults shown); the rules themselves, and league/conference sizes, are fixed.

Structure
- Each team plays exactly 1 game per week and hosts exactly 8.
- Each team pair is scheduled exactly as phase 1 selected it (0, 1, or 2 meetings).
- No pair of teams meets in back-to-back weeks.

Home / away
- No 4 straight home or away games.
- 2–4 home games in every 6-week window.
- Neither the first 3 nor the last 3 weeks are all-home or all-away.
- At most 1 total 3-game home/away streak per team.

Home balance
- Each divisional pair splits 1 home / 1 away each.
- Conference cross-division home games: 5-team-division teams host exactly 2; 4-team host 2–3.
- Non-conference home games: same split (5-team host 2; 4-team host 2–3).

Divisional sequencing
- At most 3 straight divisional games (never 4).
- At most 4 teams open weeks 1–2 with divisional games in both — of which ≤1 is a 4-team-division team and ≤2 are 5-team-division teams.
- No 3 straight divisional games to start or end the season.
- At most 1 total 3-game divisional streak per team.
- Density — 5-team: ≤6 in any 9 weeks (which also forces ≤7 in any 10); 4-team: ≤4 in any 7 (which also forces ≤5 in any 8).
- Front-load caps — 5-team: ≤4 in weeks 1–6, ≤5 in 1–8, ≤6 in 1–10; 4-team: ≤2 in 1–4, ≤3 in 1–8, ≤4 in 1–10.
- At most 2 divisional opponents are non-interleaved. Non-interleaved = no other divisional game falls between the two meetings with that rival (e.g. CHI, CHI, GB, GB — both rivals bunched). Keeps rival series spread across the season.
- Every team plays ≥1 divisional game in the last 2 weeks. Toggle: `require_divisional_in_final_two_weeks`.
- The final week is all-divisional: 8 of its 9 games (the max; each 5-team division strands one team). Toggle: `require_final_week_divisional`.

League-wide caps (per-team rules can't pile up across all teams at once)
- ≤9 teams with a 3-game home streak; ≤3 with a 3-game away streak.
- ≤6 teams with a 3-game divisional streak.
- ≤2 teams with 2 non-interleaved rivals.
- ≤3 rematches within a 3-week span (meetings 2 weeks apart).

## Objective (soft)

Without an objective the solver camps at the caps, so every season looks the same. Instead it minimizes a penalty that prefers NFL-typical schedules: each of 8 season metrics is penalized for landing outside a band `[lo, hi]` — zero cost inside, `weight` per step outside. Bands are the NFL per-season spread scaled to PNFL (4-team ×18/32 or ×8/32; 5-team ×10/25; rematches ×26/48); weights are rarity (1/scaled-SD). The hard caps above stay as backstops. Bands/weights are `[phase2]` settings (`soft_*_lo/_hi/_weight`); defaults:

| Metric | band [lo,hi] | weight |
|---|---|---|
| Teams with a 3-game home streak | 5–7 | 155 |
| Teams with a 3-game away streak | 0–4 | 115 |
| Teams with a 3-game divisional streak | 2–6 | 109 |
| 4-team teams at the front-load cap (3 divisional in first 8) | 3–5 | 111 |
| 5-team teams at the front-load ceiling (6 divisional in first 10) | 2–5 | 68 |
| Teams with 2 non-interleaved rivals | 0–3 | 116 |
| Close rematches (3-week span) | 0–2 | 215 |
| Teams opening weeks 1–2 divisional | 0–4 | 100 |

The 5-team frontload band comes from just 3 seasons (1999–2001) and is noisy — hence its low weight; treat it as provisional.

Rule provenance (NFL policy vs. measured NFL patterns): [nfl-schedules.md](../design/research/nfl-schedules.md). Rule design patterns (hard/soft, anti-pileup): [cpsat-rule-patterns.md](../design/research/cpsat-rule-patterns.md).
