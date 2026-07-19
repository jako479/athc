# scheduler — Phase 1: Matchup Inventory

**Scheduler B** (full CP-SAT) phase 1. Builds the full 144-pairing season inventory before placement; the primary matchup generator (and ultimately the only one) — [`matchup_builder.py`](../../src/athc/scheduler/schedulers/matchup_builder.py). Output feeds [Phase 2](phase-2-schedule.md). [Scheduler C](phase-1-matchups-fixed-cpsat.md) reuses this same rank-based difficulty model with three table-fixed opponents per team forced in first.

## Fixed by league structure

- Divisional: every divisional opponent twice (home and away).
- Conference: every same-conference team outside the division once.

## Non-conference (the only flexibility)

All 40 AFC×NFC games are chosen together in one OR-Tools CP-SAT model. Per-team counts: 5 for 4-team divisions, 4 for 5-team divisions.

Difficulty is shaped through each team's **opponent-strength score** — the sum of its opponents' overall ranks (1–18). The model:
- fixes each team's non-conference count,
- requires each team to draw at least 1 top-half and 1 bottom-half opponent,
- pulls each team's strength of schedule toward a rank-based target (soft, no hard caps; see below).

## Difficulty curve

The strength-of-schedule **curve** shapes fairness as a **soft target**: each team is pulled toward a rank-based average-opponent-rank target (the #1 team aims for the toughest slate, the #18 for the easiest, the rest between, on a sine-on-a-slope curve). The solver minimizes the largest deviation from target (minimax), then the total (tie-break). These are targets, not hard caps, so difficulty never makes the schedule infeasible. Values default in `config.py`, overridable in `rules/PNFL.scheduler.toml`. The score uses overall rank; the one-strong/one-weak floor uses derived conference rank. See [Difficulty Tuning](phase-1-difficulty-tuning.md) for the formula, objective, and sample tables.

## Design basis (prior art)

- The monotonic rank gradient mirrors the NFL "same-place finisher" rule (stronger teams draw stronger opponents). The NFL rank-binds only ~3 of 17 games and caps nothing; this scheduler is more rank-driven, so the curve and limits matter more here.
- Established practice shapes difficulty with a soft objective — minimize strength-of-schedule variance, or penalize deviation from a target — not hard caps. The soft target follows that; hard caps are optional guardrails.
- The top/bottom-half floor is the standard round-robin "strength group" device: guarantee each team a mix of strong and weak opponents.
- No standard numeric limits exist; difficulty is controlled structurally or via the objective, so our values are tuning knobs, not industry constants.

Sources: [NFL formula](https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule) (summary in [nfl-formula.md](nfl-formula.md)), [Bouzarth et al. 2020](https://content.iospress.com/articles/journal-of-sports-analytics/jsa200428), [round-robin strength groups](https://www.sciencedirect.com/science/article/abs/pii/S0377221707010053).

## Validation

The inventory must total 144 pairings with exactly 40 non-conference and no unfilled slots, or it errors. An infeasible or timed-out solve errors.
