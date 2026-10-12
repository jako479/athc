# fbpro98-lge — Architecture

Library that reads the FbPro '98 `.lge` league file: its conferences, divisions, teams and standings.

## Module layout

```
src/athc/fbpro98_lge/
├── __init__.py    # public API re-exports
├── model.py       # LgeFile, Conference, Division, Team, Record; standings order
├── schema.py      # chunk tags, sizes, field offsets, mask factor, schedule layout
└── reader.py      # read_lge / parse_lge; InvalidLgeError
```

The model nests teams in divisions and divisions in conferences, the way the file's chunk tree does. Each team carries its record; `standings` on a division or conference sorts its teams.

## What this package does

- Reads any league's `.lge`, stock or custom, into a typed model in file order.
- Knows the `.lge` extension: `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge`.
- Walks the chunks in order with one small cursor (`_Chunks`): each chunk must be the one the tree expects next and the size the spec gives; the conference, division and team counts drive the walk.
- Reads both chunk orders: nested (each team followed by its roster) and grouped by kind (every conference, division, team, then roster). A first team chunk followed by another team chunk means grouped.
- Unmasks each team chunk with its clear team number.
- Reads the schedule after the tree and tallies each team's played regular-season games; nothing may follow it, so a tree with more parts than its counts say is caught.
- Ranks standings by win percentage, then point differential, then file order.

## What this package does NOT do

- Read any other field: league settings, ids, abbreviations, colors, rosters, the schedule's overtime flag and weeks played.
- Count playoff games, seed the playoffs, or apply NFL tiebreak steps.
- Write `.lge` files.
- Know where a league's files are; the caller supplies the folder.

See [specs/lge.md](specs/lge.md) for the format.

## Testing

- `tests/unit/fbpro98_lge/test_reader.py` — real fixtures for every league size and both chunk orders, a season's weekly files for standings, built bytes for each check and limit.
- `tests/unit/fbpro98_lge/test_model.py` — nesting, official name, records, standings order, immutability.
- `tests/unit/fbpro98_lge/test_schema.py` — layout constants.

Fixtures in `tests/unit/fbpro98_lge/data/` are real game files.
