# Research — CP-SAT rule design patterns

Why this matters: a solver with only hard rules returns an *arbitrary* legal schedule. Nature makes anomalies rare; a solver doesn't — if a weird schedule is legal, some seed will produce it. Preventing nonsense is a known design problem with known patterns.

## Standard constraint taxonomy (sports timetabling)

The field ([ITC2021 / Van Bulck et al.](https://www.sciencedirect.com/science/article/abs/pii/S0377221722009201), [overview paper](https://robinxval.ugent.be/ITC2021/images/MathSport_International_2021_paper_10.pdf)) classifies scheduling rules into five types:

- **Capacity** — counts in a window (home games, divisional games, totals)
- **Game** — force/forbid a specific matchup in a specific round
- **Break** — consecutive home/home or away/away games
- **Fairness** — balance across teams (hosting, travel, difficulty)
- **Separation** — rounds between meetings of the same pair

Each rule is **hard** (never violated) or **soft** (preference; violations penalized in the objective). The standard formulation: satisfy all hard rules, minimize weighted soft violations.

## Patterns for preventing nonsense, cheapest first

1. **Per-entity cap** — bound each team. Doesn't control pileups (all teams at the cap at once is legal).
2. **Aggregate cap** — bound the league-wide total directly.
3. **Count-of-extremes cap** — per-team flag for "at the boundary", cap the sum of flags. Cheap, composable; this is `max_teams_divisional_weeks_1_and_2` and the [quirk-budget](../quirk-budget.md) mechanism.
4. **Soft constraints + objective** — penalize atypical shapes so the solver *prefers* normal schedules ([OR-Tools pattern](https://github.com/google/or-tools/discussions/2488): add violation-flag × penalty to a minimize objective). The field's standard realism tool. Costs solve time and needs weight tuning.
5. **Batch sampling** — generate many schedules, measure, constrain what drifts. Impractical for athc (solve time).

Rule of thumb: hard caps for never-events, count-caps for rare events, soft objective for shape. When adding a per-entity cap, always ask "what if every entity hits it at once?" — if that's nonsense, pair it with a count or aggregate cap.

## Where athc stands

- Phase 2 is pure feasibility — all rules hard, **no objective** — so any legal corner can be returned. This is the main gap vs. the standard pattern.
- Existing rules map cleanly onto the taxonomy: Break = streak rules; Separation = no back-to-back rematch; Capacity = density windows, hosting counts, front-load caps; Fairness = hosting balance (phase 2), difficulty line (phase 1, which *is* a soft objective); Game = week-16 finale, fixed place pairs.
- Cheap next step when pileups worry us: count-of-extremes caps (pattern 3). A soft-objective layer (pattern 4) is the bigger, principled upgrade if schedules still look samey or corner-y.

## Same-looking schedules (open issue)

The solver sits at whatever the caps allow — the first capped schedule hit 4 of 6 caps exactly. So every season tends to produce the same numbers (always 3 close rematches, 6 streak teams), while real NFL seasons vary. Options:

1. **Random per-season targets** — before solving, randomly pick this season's numbers, weighted like the NFL's per-season spread; constrain to the picks. Cheap; feels contrived.
2. **Soft objective** — penalize deviation from NFL-typical values so the solver prefers the middle of the distribution. Target = median, tolerance = observed min–max, weight = rarity beyond it; data in [nfl-schedules.md](nfl-schedules.md) ("Per-season spread"). Standard practice; slower solves, weights need tuning.

Decision: try option 2. The hard caps stay as backstops.

## Implemented count-caps

Companion caps for per-team rules whose league-wide pileup would be nonsense. Sized at NFL per-season averages ([nfl-schedules.md](nfl-schedules.md)) scaled ×18/32, then ×1.5 breathing room (caps must sit above the average, or half of normal seasons would be illegal):

| Per-team rule | NFL (scaled) | Cap |
|---|---|---|
| 3-game home/away streak ≤1 | home 6.4, away 2.1 | `max_teams_with_home_streak = 9`, `max_teams_with_away_streak = 3` |
| 3-game divisional streak ≤1 | 4.1 | `max_teams_with_divisional_streak = 6` |
| Front-load caps | 1.6 at the wall | `max_teams_at_front_load_max = 3` |
| Non-interleaved rivals ≤2 | 1.5 at 2 | `max_teams_with_two_bunched_rivals = 2` |
| 3-week-span rematches | 1.8 | `max_close_rematches = 3` (league-wide) |
