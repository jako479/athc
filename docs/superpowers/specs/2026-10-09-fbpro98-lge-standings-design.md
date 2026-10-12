# fbpro98_lge: standings — design

Date: 2026-10-09. Status: approved by the user in chat.

## Goal

Callers get each team's regular-season record (W-L-T, PF, PA) and each
division's and conference's teams in standings order. Builds on
[2026-10-09-fbpro98-lge-design.md](2026-10-09-fbpro98-lge-design.md).

## Current state (branch `worktree-fbpro98-lge`)

- `fbpro98_lge` reads conference, division and team names; the S03 schedule
  chunk is required but not read.
- S03 holds every game: home and away team numbers, scores, overtime flag,
  status (`0` played, `2` not). Records computed from it match the game's
  Week Seven standings screen for `PNFL.lge`.
- Weekly samples from the user (season 2047): before week 1, after week 16,
  after the Super Bowl. Weeks played reads `255` after the Super Bowl.

## Decisions (the user's)

- "Divisional and conference standings" means rank order: each division's
  teams, and each conference's teams, in standings order.
- Teams with the same record are ordered by point differential.

Taken as the mainstream default, in the approved design:

- Rank by win percentage, a tie counting as half a win; then point
  differential; then file order.
- Only regular-season games marked played count; playoff games never do.

## API and model

```python
lge = read_lge("PNFL", r"E:\SIERRA\FbPro98")
team.record                  # Record(wins=5, losses=1, ties=0, points_for=164, points_against=112)
team.record.win_percentage   # 0.833...
team.record.point_differential  # 52
division.standings           # its teams, best first
conference.standings         # every team in its divisions, best first
```

- `Record(wins, losses, ties, points_for, points_against)`, properties
  `games`, `win_percentage` (0.0 before any game), `point_differential`.
- `Team(name, nickname, record)`.
- `Division.standings`, `Conference.standings`: tuples of `Team`.

## Reader

- The walks collect conference and division heads and team names; the
  schedule is read next; then the model is built, numbering teams 1..N in
  file order.
- New `InvalidLgeError` checks on S03:
  - shorter than its 3-byte header;
  - cut short inside a week;
  - data after the last week;
  - a played regular-season game naming a team outside 1..N.
- Unplayed and playoff games are skipped unread, so their `0xFF` team numbers
  pass.

## Tests

- Fixtures added: `PNFL-before-week1.lge`, `PNFL-after-week16.lge`,
  `PNFL-after-super-bowl.lge`.
- `PNFL.lge`: every record, and division order as on the Week Seven screen.
- After week 16: tie games, conference order using point differential.
- After the Super Bowl: records equal to after week 16.
- Before week 1: all records zero, standings in file order.
- Model: ranking by win percentage with ties, point differential, file order.
- Built bytes for each new limit, at the limit and one past it.

## Docs

- `lge.md`: weeks played `255` after the season.
- Library README, ARCHITECTURE, test matrix; `fbpro98-files.md`, `STATUS.md`,
  `CHANGELOG.md`.

## Out of scope

- Playoff seeding, NFL tiebreak steps, division or conference W-L-T splits.
