# Proposal — schedule quirk budget

Status: idea for later; nothing implemented.

## Why

Real NFL seasons always contain a few rare scheduling one-offs. athc bans them all, so every athc schedule is more uniform than any real NFL season. A small league-wide budget would restore that texture without loosening any rule for everyone.

NFL rates (2016–2025, 32 teams; teams per season — see [research/nfl-schedules.md](research/nfl-schedules.md)):

- Ends the season with 3 straight divisional games: 2.6
- Has a second 3-game home/away streak: 2.2
- 5 divisional games in a 7-week span (4-team divisions): 2.1 (6.6% of teams)
- 5-of-6 home (or away) window: 2.0
- Exactly 2 non-interleaved rivals: 2.6 (typical NFL team has 0–1) — tighten the normal cap from 2 to 1; quirk allows a team a second

~2–3 per 32 teams scales to ~2 per 18, so a default budget of 2 fits.

Rarer events (~1 team per season or less) stay hard-banned: 4-game divisional streak (0.9), 4-game home/away streak (0.8), 6 divisional in 8 weeks (0.3). Never-events (back-to-back rematches, 5-game streaks) stay banned regardless.

## How

- Per team and quirk type, a solver flag; a flagged team's cap for that one rule is raised one step.
- Sum of all flags across the league ≤ `quirk_budget`.
- `quirk_budget = 0` reproduces current behavior exactly.

## Config sketch

```toml
[phase2]
quirk_budget = 2

[phase2.quirks]
end_with_three_divisional = true
second_three_game_streak = true
five_divisional_in_7 = true
five_home_in_6 = true
second_non_interleaved_rival = true  # with max_non_interleaved_divisional_opponents lowered to 1
```

## Open decisions

- Budget is a ceiling, not a target — the solver may spend none. Add a small objective reward if quirks should usually appear.
- Final list of quirk types and the default budget.
