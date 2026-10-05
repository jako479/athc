# scheduler — Phase 2: Schedule Placement

Phase 2 takes the fixed inventory from phase 1 (`weeks` × 9 pairings) and uses OR-Tools CP-SAT to assign every matchup a week (1–`weeks`) and a home team — [`schedule_builder.py`](../../src/athc/scheduler/schedulers/schedule_builder.py).

## Model

- Decision var `x[home, away, week]` (bool) per ordered team pair and week. Helper bools: `h[team, week]` (home that week), `d[team, week]` (divisional game that week).
- Output: a `Schedule` of `weeks` × 9 games.
- Solve: seeded + randomized interleaved search across `solver_workers` workers (default `"auto"` = this CPU's fast threads minus 2), stopping on deterministic time — not wall-clock — so results are machine-speed independent. Reproducible only for the same seed *and* the same worker count; the report shows both. No feasible solution (or timeout) errors.

## Which rules apply

| Rule group | Applies when |
|---|---|
| One game a week, host half the weeks, the phase-1 inventory | always |
| Max consecutive home/away (`max_consecutive_home_or_away`) | always |
| Balanced hosting: each team hosts half its conference games and half its non-conference games (2 of 4, 2-3 of 5, 4 of 8) | always |
| Every divisional rule, the divisional league caps, no back-to-back rematch, the soft objective | the league has divisions |
| 2-4 home in every 6 weeks | `require_home_balance_per_six_weeks` |
| ≤1 three-game home/away streak per team; league caps on such streaks | `require_home_away_streak_caps` (required with divisions) |
| First and last 3 weeks mix home and away | `require_mixed_home_away_at_season_ends` |
| Weeks 1..N hold no same-conference game | `opening_nonconference_weeks` (0 = off) |
| No cap + 1 straight home or away *conference* games, counted along the conference games only | `max_consecutive_conference_home_or_away` (0 = off) |
| Rivalry week: every `[rivalries]` pair meets in the last week; `rotate_home_by_season` makes the first-listed team host in even seasons and the second in odd | `[rivalries]` present |

A league without divisions uses the first three rows plus the last three; its rules file turns the three `require_*` toggles off.

## Constraints

The numeric amounts below come from `[phase2]` in the league's `rules\scheduler.toml` (defaults shown); the rules themselves, and league/conference sizes, are fixed.

Structure
- Each team plays exactly 1 game per week and hosts `weeks / 2`.
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
- No pair of teams meets in back-to-back weeks.
- At most 3 straight divisional games (never 4).
- At most 4 teams open weeks 1–2 with divisional games in both — of which ≤1 is a 4-team-division team and ≤2 are 5-team-division teams.
- No 3 straight divisional games to start or end the season.
- At most 1 total 3-game divisional streak per team.
- Density — 5-team: ≤6 in any 9 weeks (which also forces ≤7 in any 10); 4-team: ≤4 in any 7 (which also forces ≤5 in any 8).
- Front-load caps — 5-team: ≤3 in weeks 1–5, ≤4 in 1–6, ≤5 in 1–8, ≤6 in 1–10; 4-team: ≤2 in 1–4, ≤3 in 1–8, ≤4 in 1–10.
- At most 2 divisional opponents are non-interleaved. Non-interleaved = no other divisional game falls between the two meetings with that rival (e.g. CHI, CHI, GB, GB — both rivals bunched). Keeps rival series spread across the season.
- Every team plays ≥1 divisional game in the last 2 weeks. Toggle: `require_divisional_in_final_two_weeks`.
- The final week is all-divisional: 8 of its 9 games (the most a week can hold: each 5-team division strands one team). Toggle: `require_final_week_divisional`.

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
