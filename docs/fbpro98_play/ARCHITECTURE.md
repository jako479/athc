# fbpro98-play — Architecture

Library that parses FbPro '98 `.ply` play files into a typed, file-native model.

## Module layout

```
src/athc/fbpro98_play/
├── __init__.py    # public API re-exports
├── model.py       # PlayFile, PlayerHeader, category enums + resolve_category
├── reader.py      # parse_play, read_play, InvalidPlayFileError
└── schema.py      # struct layouts and P95 block identifier
```

`specs/ply.md` documents the on-disk byte layout.

## What this package does

- Parses `.ply` files into `PlayFile` records
- Exposes file-native classification:
  - `play_category` (raw integer from the file)
  - `special_category` (raw integer)
  - `user_category` (raw integer)
  - Properties: `is_offensive`, `is_defensive`, `is_special_teams`
- Names play categories: four per-side enums (`OffensiveCategory`, `DefensiveCategory`,
  `SpecialOffensiveCategory`, `SpecialDefensiveCategory`), each member carrying its
  `code`, `short` (league label) and `long` (game name), plus `is_run`/`is_pass`.
  `short` falls back to `long` where a league has no abbreviation.
  `resolve_category(play_category, special_category, user_category)` and
  `PlayFile.category` name a category from the raw bytes; `category_name` is `category.long`.
  An unrecognized code resolves to `UNKNOWN_CATEGORY` (never `None`); `read_play`
  logs an error and continues. `category_by_short(label)` resolves a league short
  label back to its category (`None` if the label isn't one).
- Validates structural correctness of `.ply` bytes

## What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.ply` format

## What this package enforces

Raise `InvalidPlayFileError` for:
- File too small to contain a header
- Invalid block magic
- Stream length / offset table not internally consistent
- Player record prefix corruption

## What this package does NOT do

- Pool building, folder layout, and folder/file mismatch warnings (live in `playpool`)
- Mechanical run/pass — `is_run`/`is_pass` reflect the category *label*, not the play design

## Testing

- `tests/unit/fbpro98_play/` — parsing real `.ply` fixtures, structural error paths

Fixtures are real game-produced `.ply` files; that is the authoritative ground truth for any wire-format question.
