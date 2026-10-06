# fbpro98-lg2 — Architecture

Library that reads the FbPro '98 `.lg2` league file: which profile and game plan files each team uses.

## Module layout

```
src/athc/fbpro98_lg2/
├── __init__.py    # public API re-exports
├── model.py       # Lg2File, TeamFiles, HalfFiles, FilePair
├── schema.py      # field and record sizes, stock signatures
└── reader.py      # read_lg2 / parse_lg2; InvalidLg2Error, UnsupportedLg2Error
```

The model nests each team's eight files by half, then side, then profile and game plan. A location is a string, `folder\filename` relative to the game folder, like the gameplan library's play filenames.

## What this package does

- Reads a custom league's `.lg2` into a typed model, one `TeamFiles` per team in file order.
- Validates structure: whole team records, a NUL in every field, no empty filename.
- Ignores text left after each NUL and the 9 unknown bytes that end each team record.

## What this package does NOT do

- Read stock leagues — modern (`STOCK` folder) or old (empty folder) → `UnsupportedLg2Error`.
- Write `.lg2` files.
- Know the `.lg2` extension or where the game folder is; the caller supplies the path.

See [specs/lg2.md](specs/lg2.md) for the format and the reader contract.

## Testing

- `tests/unit/fbpro98_lg2/test_reader.py` — real fixtures (custom, modern stock, old stock), stock signatures, limits.
- `tests/unit/fbpro98_lg2/test_model.py` — model nesting and immutability.
- `tests/unit/fbpro98_lg2/test_schema.py` — layout constants.

Fixtures in `tests/unit/fbpro98_lg2/data/` are real game files.
