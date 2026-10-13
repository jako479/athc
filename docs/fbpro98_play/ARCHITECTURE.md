# fbpro98-play — Architecture

Library that parses FbPro '98 `.ply` play files into a typed, file-native model.

## Module layout

```
src/athc/fbpro98_play/
├── __init__.py    # public API re-exports
├── model.py       # PlayFile + play attributes, PlayerHeader, PlayerLogic, category enums + resolve_category, DefensiveFront
├── reader.py      # parse_play, read_play, InvalidPlayFileError
└── schema.py      # struct layouts, P95 block identifier, command and position codes
```

`specs/ply.md` documents the on-disk byte layout.

## What this package does

- Parses `.ply` files into `PlayFile` records, each player's logic boxes included
  (`player_logic`: `PlayerLogic` → `LogicBox` → `Command`)
- Tells the play attributes from the players' logic, on normal plays only:
  - offense: `is_timed_pass`, `is_qb_run` and `is_rollout(margin)` from the
    QB's boxes from the snap on (the caller picks the margin); with two QBs,
    either counts;
  - defense: `defensive_front` from the count of down linemen and the
    category (`None` when the category has no front).
- Exposes file-native classification:
  - `play_category` (raw integer from the file)
  - `special_category` (raw integer)
  - `user_category` (raw integer)
  - Properties: `is_offensive`, `is_defensive`, `is_special_teams`
- Names play categories: four per-side enums (`OffensiveCategory`, `DefensiveCategory`,
  `SpecialOffensiveCategory`, `SpecialDefensiveCategory`), each member carrying its
  `code` and `long` (game name), plus `is_run`/`is_pass`.
  `resolve_category(play_category, special_category, user_category)` and
  `PlayFile.category` name a category from the raw bytes; `category_name` is `category.long`.
  An unrecognized code resolves to `UNKNOWN_CATEGORY` (never `None`); `read_play`
  rejects the file.
- Holds a league's category labels: `CategoryLabels` (`labels.py`), built from the
  `[categories.offense]` / `[categories.defense]` tables of `league.toml` by
  `CategoryLabels.from_tables` (ValueError on a bad entry). `label(category)` is the
  league label, else the game name; `offense_by_label` / `defense_by_label` resolve a
  label within one side. Special-teams categories never have labels.
- Validates structural correctness of `.ply` bytes

## What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.ply` format

## What this package enforces

Raise `InvalidPlayFileError` for:
- File too small to contain a header
- Invalid block magic
- Stream length / offset table not internally consistent
- Player record prefix corruption
- A player record too short for its logic boxes
- An unrecognized play category (`read_play` only)

Invalid block magic and an unrecognized category say what was found; every
other case is one message, `The play file is invalid or corrupted.`, as most
file readers word a damaged file.

## What this package does NOT do

- Pool building, folder layout, and folder/file mismatch warnings (live in `playpool`)
- Mechanical run/pass — `is_run`/`is_pass` reflect the category *label*, not the play design

## Testing

- `tests/unit/fbpro98_play/` — parsing real `.ply` fixtures, structural error paths,
  play attributes

Fixtures are real game-produced `.ply` files; that is the authoritative ground truth for any wire-format question.
