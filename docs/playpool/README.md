# playpool

Library + CLI for a league's play pool: builds it from a folder of Front Page Sports Football Pro '98 play (`.ply`) files, each classified from its own bytes, and checks it with `athc playpool check`.

## Features

- Walks a folder tree of `.ply` files, any layout
- Side and category from the play file; folders only add what the bytes can't carry
- Typed `OffensivePlay` / `DefensivePlay` / `SpecialTeamsPlay` records
- Filename-derived attributes from a league's rules TOML
- Warns on league folders (side folders, and category folders named by the league's labels) that contradict a play's file, duplicate names and invalid files

## Setup

```bash
uv sync
```

## Usage

```python
from athc.config import load_league_config
from athc.playpool import load_rules, read_play_pool

rules = load_rules("playpool.toml")          # optional
labels = load_league_config().categories     # optional: the league's folder names
pool = read_play_pool("plays", rules=rules, labels=labels)

len(pool.offensive_plays), len(pool.defensive_plays), len(pool.special_teams_plays)
play = pool.find_by_name("AF3ArshZ")        # case-insensitive
play.category.long                           # the game's category name
play.file_path
pool.issues                                  # every warning logged while building
```

Without rules, the filename-derived attributes stay off.

## API

- `read_play_pool(root_dir, *, rules=None, labels=None)` walks `root_dir/**/*.ply` in sorted path order and returns a `PlayPool`; invalid and unreadable files are logged and skipped, never raised, and of two same-named plays the later in that order wins. `labels` is the league's `CategoryLabels`; without it no folder name means a category.
- `folder_warnings(rel_path, play, labels)`: the folder/file mismatch warnings for one play, as the pool reports them.
- `rule_warnings(pool, rules)`: what is wrong with the exact names a rules file lists under `include` / `exclude`, checked against `pool` — not in the pool, a play the section cannot apply to (a run play under a pass attribute, a pass play under `[QBRun]`, a defensive or special-teams play anywhere), or under both lists of one section. Returned, not logged; `read_play_pool` does not call it (`convert-pdb` does).
- `PlayPool`: `root_dir`, `offensive_plays`, `defensive_plays`, `special_teams_plays`, `issues` (every warning, word for word); `find_by_name(name)` (case-insensitive); `add(play)` files an `OffensivePlay` / `DefensivePlay` / `SpecialTeamsPlay` under its side and indexes it.
- `Play`: `name`, `play_file` (the parsed `PlayFile`), `file_path`, `category` (an `fbpro98_play` enum member), `play_category`, `special_category`, `user_category`; `to_dict()`. `OffensivePlay` adds `screen`, `rollout`, `qb_draw`, `pass_logic` (`PassLogic.TIMED` / `CHECK_RECEIVERS`); `DefensivePlay` adds `defensive_front` (`DefensiveFront.THREE_FOUR` / `FOUR_THREE` / `TWO_DL`); `SpecialTeamsPlay` adds nothing.
- `load_rules(path)` parses a rules TOML into a `PlaypoolRules`; `build_rules(data, *, source)` builds one from a mapping. `PlaypoolRules`: `timed`, `rollout`, `qb_draw`, each a `FilenameFilter` whose `matches(name)` is true when the name hits any of `suffix_any` / `regex_any` / `include` and none of `suffix_none` / `regex_none` / `exclude`.
- `RulesFileError`: an unreadable or malformed rules file; `errors` lists every problem found.

## CLI

`athc playpool check` checks the play pool for problems: plays in the wrong
folder, duplicate play names, and invalid play files.

```bash
athc playpool check
athc playpool check E:\SIERRA\FbPro98\PNFL
athc playpool check --league PCFL
```

With no folder, it checks the league's `play_path` (from `--league`, or
`[athc] league` in `athc.ini`). A given folder needs no league; a league that
resolves still lends its category names to the folders, and without one no
folder name means a category.

It checks the same things pool loading checks for every other command, with
the same messages:

- A play in a side folder, or a category folder named by the league's labels,
  that contradicts its file (wrong side or category).
- A play name used more than once.
- A `.ply` file that isn't a valid play file.

Each problem prints on its own line, then one summary line with the number of
plays checked and issues found.

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no issues. |
| `1` | **Findings** — one or more issues. |
| `2` | **Error** — couldn't run: no league, no `play_path`, a missing folder, or a file or folder the system can't read. |

`src/athc/cli/playpool/check.py` is the leaf command of the
`src/athc/cli/playpool/` group. It loads the pool with the gameplan group's
`build_pool`, and the library keeps its warnings in `PlayPool.issues`. Tests:
`tests/integration/test_playpool_check.py`.

## Testing

```bash
pytest
```
