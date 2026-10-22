# Proposal — net touchdowns in the standings

Status: proposal; nothing implemented.

## Why

- The standings skip net touchdowns, the step before the coin toss in the game's and the NFL's tie-breakers, because the `.lge` has no touchdowns; the `.dat` does ([formats/stats.md](../../formats/stats.md)).
- Stat corrections ([game-stats-correction.md](game-stats-correction.md)) share the stats library and its layout; this doc covers the standings.

## Layout

- Tools and libraries stay separate packages: `athc.standings`, the tool, with its command in `athc.cli`, orchestrates; `fbpro98_lge`, `fbpro98_stats` and `fbpro98_standings` are libraries. A library several tools import never lives inside a tool package.
- `fbpro98_stats` is one package with two subpackages side by side: `ctree/`, the database layer, reads and writes the `.dat` and `.idx` as headers and raw records and knows nothing of football; `stats/`, the football layer, turns records into named stats and holds the game's rules.
- `fbpro98_stats/__init__.py` exposes the football functions; tools never see `ctree`.

```
src/athc/fbpro98_stats/
├── __init__.py     # the library's API
├── ctree/          # the database layer: the files as headers and raw records; no football knowledge
└── stats/          # the football layer: named stats and the game's rules
```

- Callers keep getting named stats, as today (`stats.team_season[3].rushing.touchdowns`), never slots, types or index entries.

## How: reading

- Both uses of the library read the whole file into memory; it is small. The standings take what they need from the named stats; corrections change records in memory and write the file back ([game-stats-correction.md](game-stats-correction.md#one-way-in)).
- `athc standings` reads the `.lge` with `fbpro98_lge` and the `.dat` with `fbpro98_stats`; `fbpro98_standings` reads no files itself.

## How: net touchdowns

- `fbpro98_standings` takes only what it needs, one record per team, so a change to the stats file never reaches it:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamTouchdownRecord:
    team_id: int
    touchdowns_scored: int
    touchdowns_allowed: int

    @property
    def net_touchdowns(self) -> int:
        return self.touchdowns_scored - self.touchdowns_allowed
```

- `athc standings` builds the records: a team's touchdowns scored are its touchdowns in `team_season`, those allowed its opponents' in `opponents_season`, each added up across the categories that count touchdowns (receiving repeats passing, so one of the two counts).
- Season records count regular-season games only, as the step does: playoff games update the last-game blocks only ([formats/stats.md](../../formats/stats.md)).
- The step works like net points, scored minus allowed, higher better, and goes where the game's and the NFL's lists put it, last before the coin toss ([standings-tie-breakers.md](../../research/standings-tie-breakers.md)); the scheduler's lists don't use it.
- Last season's standings (`Standings` with `previous`) need last season's `.dat` too, beside its `.lge`: the game clears season records each season.
- `athc.standings`, which lays out the views, doesn't change.

## Steps

1. `fbpro98_standings`: take the records and add the net-touchdowns step.
2. `athc standings`: read the `.dat`, build the records and pass them in.
3. `fbpro98_stats`: the `ctree/` and `stats/` split, with the writer ([game-stats-correction.md](game-stats-correction.md)); the standings don't wait for it.
