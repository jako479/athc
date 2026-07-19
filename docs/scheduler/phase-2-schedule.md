# scheduler — Phase 2: Schedule Placement

Phase 2 takes the fixed 144-pairing inventory from phase 1 and uses OR-Tools CP-SAT to assign every matchup a week (1–16) and a home team. Shared by all three schedulers (A, B, and C) — [`schedule_builder.py`](../../src/athc/scheduler/schedulers/schedule_builder.py).

## Model

- Decision var `x[home, away, week]` (bool) per ordered team pair and week. Helper bools: `h[team, week]` (home that week), `d[team, week]` (divisional game that week).
- Output: a `Schedule` of 16 weeks × 9 games.
- Solve: single worker, seeded + randomized search, under the configured time limit. No feasible solution (or timeout) errors.

## Constraints

The numeric amounts below come from `[phase2]` in `rules/PNFL.scheduler.toml` (defaults shown); the rules themselves, and league/conference sizes, are fixed.

Structure
- Each team plays exactly 1 game per week and hosts exactly 8.
- Each team pair is scheduled exactly as phase 1 selected it (0, 1, or 2 meetings).

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
- 0 or exactly 2 teams open weeks 1–2 with back-to-back divisional games.
- No 3 straight divisional games to start or end the season.
- At most 1 total 3-game divisional streak per team.
- Density — 5-team: ≤7 in any 10 weeks, ≤6 in any 9; 4-team: ≤5 in any 8, ≤3 in any 7.
- At least half of each team's divisional games fall in weeks 9–16.
- At most 2 divisional opponents are non-interleaved (no rival meeting between the two meetings).
- Every team plays ≥1 divisional game in the last 2 weeks. Toggle: `require_divisional_in_final_two_weeks`.
- The final week is all-divisional: 8 of its 9 games (the max; each 5-team division strands one team). Toggle: `require_final_week_divisional`.

The NFL-data rationale and PNFL policy behind these limits live in the `schedule_builder.py` module docstring.
