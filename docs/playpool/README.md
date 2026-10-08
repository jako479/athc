# playpool

Library for building a league's play pool from a folder of Front Page Sports Football Pro '98 play (`.ply`) files, each classified from its own bytes.

## Features

- Walks a folder tree of `.ply` files, any layout
- Side and category from the play file; folders only add what the bytes can't carry
- Typed `OffensivePlay` / `DefensivePlay` / `SpecialTeamsPlay` records
- Filename-derived attributes from a league's rules TOML
- Warns on PNFL folders that contradict a play's file, duplicate names and invalid files

## Setup

```bash
uv sync
```

## Usage

```python
from athc.playpool import load_rules, read_play_pool

rules = load_rules("playpool.toml")          # optional
pool = read_play_pool("plays", rules=rules)

len(pool.offensive_plays), len(pool.defensive_plays), len(pool.special_teams_plays)
play = pool.find_by_name("AF3ArshZ")        # case-insensitive
play.category.long                           # the game's category name
play.file_path
pool.issues                                  # every warning logged while building
```

Without rules, the filename-derived attributes stay off.

## API

- `read_play_pool(root_dir, *, rules=None)` walks `root_dir/**/*.ply` and returns a `PlayPool`; invalid files are logged and skipped, never raised.
- `PlayPool`: `root_dir`, `rules`, `offensive_plays`, `defensive_plays`, `special_teams_plays`, `issues` (every warning, word for word); `find_by_name(name)` (case-insensitive); `to_dict(relative_to=None)`.
- `Play`: `name`, `play_file` (the parsed `PlayFile`), `file_path`, `category` (an `fbpro98_play` enum member), `play_category`, `special_category`, `user_category`; `to_dict()`. `OffensivePlay` adds `screen`, `rollout`, `qb_draw`, `pass_logic` (`PassLogic.TIMED` / `CHECK_RECEIVERS`); `DefensivePlay` adds `defensive_front` (`DefensiveFront.THREE_FOUR` / `FOUR_THREE` / `TWO_DL`); `SpecialTeamsPlay` adds nothing.
- `load_rules(path)` parses a rules TOML into a `PlaypoolRules`; `build_rules(data, *, source)` builds one from a mapping. `PlaypoolRules`: `timed`, `rollout`, `qb_draw`, each a `FilenameFilter` whose `matches(name)` is true when the name hits any of `suffix_any` / `regex_any` / `include` and none of `suffix_none` / `regex_none` / `exclude`.
- `RulesFileError`: an unreadable or malformed rules file; `errors` lists every problem found.

## Testing

```bash
pytest
```
