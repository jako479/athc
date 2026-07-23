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
- At most 4 teams open weeks 1–2 with divisional games in both.
- No 3 straight divisional games to start or end the season.
- At most 1 total 3-game divisional streak per team.
- Density — 5-team: ≤7 in any 10 weeks, ≤6 in any 9; 4-team: ≤5 in any 8, ≤4 in any 7.
- Front-load caps — 5-team: ≤4 in weeks 1–6, ≤5 in 1–8, ≤6 in 1–10; 4-team: ≤3 in 1–6, ≤4 in 1–8.
- At most 2 divisional opponents are non-interleaved. Non-interleaved = no other divisional game falls between the two meetings with that rival (e.g. CHI, CHI, GB, GB — both rivals bunched). Keeps rival series spread across the season.
- Every team plays ≥1 divisional game in the last 2 weeks. Toggle: `require_divisional_in_final_two_weeks`.
- The final week is all-divisional: 8 of its 9 games (the max; each 5-team division strands one team). Toggle: `require_final_week_divisional`.

League-wide caps (per-team rules can't pile up across all teams at once)
- ≤9 teams with a 3-game home streak; ≤3 with a 3-game away streak.
- ≤6 teams with a 3-game divisional streak.
- ≤3 teams at their largest front-load cap.
- ≤2 teams with 2 non-interleaved rivals.
- ≤3 rematches within a 3-week span (meetings 2 weeks apart).

Rule provenance (NFL policy vs. measured NFL patterns): [nfl-schedules.md](../design/research/nfl-schedules.md). Rule design patterns (hard/soft, anti-pileup): [cpsat-rule-patterns.md](../design/research/cpsat-rule-patterns.md).
