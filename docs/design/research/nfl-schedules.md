# Research — NFL schedule patterns behind the phase-2 rules

Provenance for the week-placement rules in [phase-2-schedule.md](../../scheduler/phase-2-schedule.md): documented NFL policy vs. patterns measured from real schedules. PNFL context: 18 teams, 16 weeks, no byes. Opponent-selection prior art is separate: [nfl-formula.md](nfl-formula.md).

## Sources

- [nflverse games.csv](https://github.com/nflverse/nfldata) — every NFL game since 1999 (season, week, teams, `div_game`). All numbers below.
- [NFL Operations — Creating the NFL Schedule](https://operations.nfl.com/gameday/nfl-schedule/creating-the-nfl-schedule) — stated policy: opponent formula, home/away balance, byes, flex.
- [2026 NFL Schedule Announced](https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced) — all-divisional final week, "17th consecutive year".
- [Giants.com — Anatomy of the NFL Schedule](https://www.giants.com/news/nfl-schedule-2023-formula-how-its-made-eagles-chiefs-cowboys-commanders) — stated placement guidelines (consecutive road games, byes, travel).

## Documented NFL policy

- Opponent formula (6 divisional, rotations, same-place games) — operations.nfl.com.
- Final week is all divisional games, every year since 2010 — media.nfl.com.
- Consecutive road games limited to two where possible, "with emphasis at the beginning and end of the season" — giants.com.
- Everything else below is measured pattern, not stated policy.

## Measured patterns

nflverse regular-season games. Streaks use each team's played-game sequence (byes excluded). Eras: 1999–2001 (31 teams, 5/6-team divisions, 16 games) and 2016–2025 (32 teams, 4-team divisions, 16–17 games).

Units — per-season averages of what each row counts: "Teams …" rows count teams, "Rematches …" rows count pair-meetings, the windows row counts 6-game windows. Share, hosting, and max rows are as labeled.

| Pattern | 1999–2001 | 2016–2025 | athc rule |
|---|---|---|---|
| Rematch in back-to-back weeks | 0 | 0 | forbidden — matches NFL |
| Rematches exactly 2 weeks apart (3-week span) | 2.0 | 3.4 | allowed, ≤3 league-wide (`max_close_rematches`) |
| Rematches exactly 3 weeks apart (4-week span) | 4.7 | 2.8 | allowed |
| Teams starting or ending 3 straight home or away | 0.3 / 1.3 | 0 / 0 | forbidden — matches modern NFL |
| Teams with a 3-game home/away streak | 10.7 | 13.2 — home 11.4, away only 3.8 | allowed, max 1; league ≤9 home / ≤3 away teams |
| Teams with 2+ 3-game home/away streaks | 2.3 | 2.2 — two home streaks 0.4, two away never | forbidden — stricter than NFL |
| Teams with a 4-game home/away streak | 0 | 0.8 — all home; a 4-game road streak never happens | forbidden |
| 6-game windows outside 2–4 home (windows/season, of ~350) | 1.7 | 2.0 | forbidden |
| Teams opening weeks 1–2 both divisional | 8.3 | 3.4; per-season 2002–2025: 0×3, 1×3, 2×4, 3×4, 4×3, 5×3, 6×3, 7×1 — odd counts common, so no pairing pattern; 0 in only 12.5% of seasons | at most 4 teams (`max_teams_divisional_weeks_1_and_2`); NFL range 0–7 at 32 teams |
| Teams starting 3 straight divisional | 3.3 | 0.2 | forbidden |
| Teams ending 3 straight divisional | 2.0 | 2.6 | forbidden — stricter than NFL |
| Teams with a 3-game divisional streak | 27.0 | 7.2 | allowed, max 1; league ≤6 teams |
| Teams with 2+ 3-game divisional streaks | 5.3 | 0 | forbidden — matches modern NFL |
| Teams with a 4-game divisional streak | 11.0 | 0.9 | forbidden |
| Divisional share in 2nd half of weeks | 0.52–0.59 | 0.55–0.65 | no rule — replaced by front-load caps |
| Divisional share by week | — | 21–41% weeks 1–16 with no trend, then 69% (wk 17) and 100% (wk 18) — a finale spike, not a ramp | spike mimicked by week-16 + final-2-weeks rules |
| Teams under half divisional in final 8 games | — | 2.7 | allowed — the old second-half minimum was removed |
| Half of divisional games done early (2016–2020, 16 games) | — | within 6 games: 20% of teams; within 8: 52% | allowed — front-load caps permit it |
| Front-load walls (2016–2020, max div in first K games) | — | first 6: ≤3 (4 never); first 8: ≤4 (5 once); first 10: ≤5 (6 never); all 6 by game 12: never | caps: 4-team ≤3/6wk, ≤4/8wk; 5-team ≤4/6wk, ≤5/8wk, ≤6/10wk; league ≤3 teams at their max |
| Non-interleaved rivals (avg per team-season) | 0.24, max 2 | 0.54; teams at exactly 2: 2.6/season; at 3: 0.3/season | cap 2 per team; league ≤2 teams at 2 |
| Final-week divisional games | 5–10 of 15 | 16 of 16, all seasons | 8 of 9 (max possible) |
| Max divisional in a 10-game window (team max) | up to 8 (rare) | ≤ 6 | 5-team cap: 7 in 10, 6 in 9 |
| Max divisional in an 8-game window (team max) | up to 7 | 5 common, 6 rare | 4-team cap: 5 in 8, 4 in 7 |
| Conference non-division hosting | — | always 3 home / 3 away (318 of 320; the 2 short are 2022's cancelled game) | 5-team host exactly 2 of 4; 4-team 2–3 of 5 |
| Divisional game in final 2 weeks | — | 100% of teams (week 18 is all-divisional) | required — matches |
| Same-place pair hosting (2002–2025) | — | always 1 home / 1 away (768 of 768); 17th game hosted by one conference, alternating years | no athc rule — fixed-place pair may be 2-0 |
| 17th-game week placement (2021–2025) | — | any week 1–17: 5% week 1, 8.75% week 17 (~uniform); week 18 excluded only by the all-divisional finale | no athc rule needed |

## Per-season spread of the soft-candidate metrics (2016–2025)

Inputs for soft-objective weights (target = median, tolerance = min–max, weight = rarity outside it). Team counts scale ×18/32; close rematches scale by divisional pairs ×26/48.

| Metric (per season) | Values 2016→2025 | Min / med / max |
|---|---|---|
| Teams with 3-game home streak | 12, 13, 12, 10, 11, 9, 13, 13, 10, 11 | 9 / 11.5 / 13 |
| Teams with 3-game away streak | 2, 8, 3, 1, 5, 3, 4, 5, 4, 3 | 1 / 3.5 / 8 |
| Teams with 3-game divisional streak | 8, 7, 7, 12, 8, 7, 6, 4, 7, 6 | 4 / 7 / 12 |
| Teams with 4+ divisional in first 8 games | 2, 3, 2, 3, 5, 0, 1, 2, 2, 1 | 0 / 2 / 5 |
| Teams with 2+ non-interleaved rivals | 3, 1, 2, 3, 3, 4, 2, 4, 0, 7 | 0 / 3 / 7 |
| Close rematches (2 weeks apart) | 2, 3, 3, 3, 4, 4, 2, 5, 3, 5 | 2 / 3 / 5 |
| Teams opening weeks 1–2 divisional | 2, 3, 1, 4, 7, 2, 4, 5, 0, 6 | 0 / 3.5 / 7 |

## Rematch gap detail (should a 3-week-span ban exist?)

No. NFL minimum rematch gap is 2 weeks in every season checked; rematches 2 weeks apart happen ~3.4×/season (2016–2025, range 2–5). The no-back-to-back-weeks rule is the only hard line the data supports. By games (not weeks), 2 modern rematches were consecutive games — a bye sat between.

## PNFL-only policy choices

- Every team plays a divisional game in the final 2 weeks.
- Week 16 forced to 8 of 9 divisional (all-divisional finale, adapted to 5-team divisions).

## Caveats

- NFL byes distort week-based streak counts; game-sequence counts used where noted.
- 2021+ seasons have 17 games / 18 weeks; 1999–2001 had 16 games / 17 weeks.
- 1999–2001 mixes 5- and 6-team divisions (pre-realignment, 31 teams).

Method: pair meeting weeks and per-team game sequences from games.csv; window/streak scans per team-season.
