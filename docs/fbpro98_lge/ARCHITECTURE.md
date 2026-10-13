# fbpro98-lge — Architecture

Library that reads the FbPro '98 `.lge` league file: its conferences, divisions, teams and standings.

## Module layout

```
src/athc/fbpro98_lge/
├── __init__.py    # public API re-exports
├── model.py       # LgeFile, Conference, Division, Team, Record, Game; ranked()
├── standings.py   # the game's tie-breakers: rank() over team numbers and results
├── schema.py      # chunk tags, sizes, field offsets, mask factor, schedule layout
└── reader.py      # read_lge / parse_lge; InvalidLgeError
```

The model nests teams in divisions and divisions in conferences, the way the file's chunk tree does. Each team carries its record; each division and conference carries its standings, ranked by the reader from the file's games with `standings.py`; `ranked(lge, teams)` ranks any teams of the file the same way. The file's played games hang off `LgeFile`, by regular-season week and by playoff round, each naming the file's own team objects.

## What this package does

- Reads any league's `.lge`, stock or custom, into a typed model in file order.
- Knows the `.lge` extension: `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge`.
- Walks the chunks in order with one small cursor (`_Chunks`): each chunk must be the one the tree expects next and the size the spec gives; the conference, division and team counts drive the walk.
- Reads both chunk orders: nested (each team followed by its roster) and grouped by kind (every conference, division, team, then roster). A first team chunk followed by another team chunk means grouped.
- Unmasks each team chunk with its clear team number.
- Reads the schedule after the tree: every played game, regular season or playoff, must name teams 1..N; the regular-season ones tally each team's record; the unplayed ones are counted. Nothing may follow it, so a tree with more parts than its counts say is caught.
- Ranks standings the way the game orders a finished season: won-lost-tied percentage, then the manual's tie-breakers among level teams (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule with each opponent once), then file order. Once a step separates some of a level group, the placed teams and the rest are each ranked again from the first step. Exact arithmetic (`Fraction`), so equal records compare equal.

## What this package does NOT do

- Read any other field: league settings, ids, abbreviations, colors, rosters, the schedule's overtime flag and weeks played.
- Count playoff games in the records, seed the playoffs, rank a playoff finish, or apply the last two tie-breakers (net touchdowns, coin toss), which the file cannot give.
- Reproduce the in-season standings screen, which sorts tied teams by points for.
- Write `.lge` files.
- Know where a league's files are; the caller supplies the folder.

See [specs/lge.md](specs/lge.md) for the format.

## Testing

- `tests/unit/fbpro98_lge/test_reader.py` — real fixtures for every league size and both chunk orders, a season's weekly files for standings, built bytes for each check and limit.
- `tests/unit/fbpro98_lge/test_model.py` — nesting, official name, records, games, immutability, `ranked` on built files.
- `tests/unit/fbpro98_lge/test_standings.py` — each tie-breaker on built seasons, the restart after a placement, level teams keeping their order.
- `tests/unit/fbpro98_lge/test_schema.py` — layout constants.

Fixtures in `tests/unit/fbpro98_lge/data/` are real game files.
