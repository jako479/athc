# Proposal — stats library: net touchdowns and writing

Status: proposal; nothing implemented.

## Why

- The standings skip net touchdowns, the last step before the coin toss in the game's and the NFL's tie-breakers, because the `.lge` has no touchdowns; the `.dat` does.
- Stat corrections ([stat-corrections.md](stat-corrections.md)) need the stats library to write the `.dat`, not only read it.

## How: net touchdowns

- `athc standings` reads the `.lge` with `fbpro98_lge` and the `.dat` with `fbpro98_stats`, and passes both to `fbpro98_standings`, which reads no files itself.
- `fbpro98_standings` works out net touchdowns as one more step, next to net points; no separate package.
- A team's net touchdowns: its touchdowns in `team_season` minus those in `opponents_season`.
- Season records count regular-season games only, as the step does.
- The step goes where the game's and the NFL's lists put it ([standings-tie-breakers.md](../../research/standings-tie-breakers.md)); the scheduler's lists don't use it.
- Last season's standings need last season's `.dat` too: the game clears season records each season.
- `athc.standings`, which lays out the views, doesn't change.

## How: library layers

- Callers keep getting named stats, as today (`stats.team_season[3].rushing.touchdowns`), never slots, types or index entries.
- Inside the library, a record layer keeps each raw record: its type, id, all 20 bytes and its slot.
- Reading builds the named stats from the records, as now.
- Writing goes the other way: a changed named stat becomes a changed record.
  - Changing a value rewrites its record in place; nothing else in either file changes.
  - A stat with no record yet needs an add: a slot from the delete stack or past the used end, the header counts, and a new `.idx` entry, which can split nodes ([formats/stats.md](../../formats/stats.md), sections 6 and 7).
  - Bytes a change doesn't touch, leftover memory included, are written back as read.

## Steps

1. `fbpro98_standings`: take the stats and add the net-touchdowns step.
2. `athc standings`: read the `.dat` and pass it in.
3. `fbpro98_stats`: the record layer and in-place value changes.
4. `fbpro98_stats`: adds, with `.idx` inserts and splits.
5. Stat corrections, on top of steps 3 and 4.
