# fbpro98-lg2 — Architecture

Library that reads the FbPro '98 `.lg2` league file: which profile and game plan files each team uses.

## Module layout

```
src/athc/fbpro98_lg2/
├── __init__.py    # public API re-exports
├── model.py       # Lg2File, LeagueType, TeamFiles, HalfFiles, FilePair
├── schema.py      # field and record sizes, stock signatures
└── reader.py      # read_lg2 / parse_lg2; InvalidLg2Error
```

The model nests each team's eight files by half, then side, then profile and game plan. A location is a string, `folder\filename` relative to the game folder, like the gameplan library's play filenames.

## What this package does

- Reads any league's `.lg2` (custom, modern stock, old stock) into a typed model, one `TeamFiles` per team in file order; one parser serves all three, since they differ only in the folder field.
- Tells the three apart by the first file entry's folder field: `Lg2File.league_type`.
- Knows the `.lg2` extension: `read_lg2(league, league_dir)` reads `<league_dir>/<league>.lg2`.
- Validates structure: whole team records, a NUL in every field, no empty filename.
- Ignores text left after each NUL and the 9 unknown bytes that end each team record.

## What this package does NOT do

- Write `.lg2` files.
- Know where a league's files are; the caller supplies the folder.

See [specs/lg2.md](specs/lg2.md) for the format and the reader contract.

## Testing

- `tests/unit/fbpro98_lg2/test_reader.py` — real fixtures (custom, modern stock, old stock), league type, limits.
- `tests/unit/fbpro98_lg2/test_model.py` — model nesting and immutability.
- `tests/unit/fbpro98_lg2/test_schema.py` — layout constants.

Fixtures in `tests/unit/fbpro98_lg2/data/` are real game files.
