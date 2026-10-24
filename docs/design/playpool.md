# playpool

Library + CLI for a league's play pool: builds it from a folder of Front Page Sports Football Pro '98 play (`.ply`) files, each classified from its own bytes, and checks it with `athc playpool check`.

The command's usage, lines and exit codes: [usage/playpool.txt](../usage/playpool.txt).

## Features

- Walks a folder tree of `.ply` files, any layout
- Side, category and play attributes (rollout, QB run, timed pass, defensive front) from the play file; folders only add what the bytes can't carry (screen)
- Typed `OffensivePlay` / `DefensivePlay` / `SpecialPlay` records
- Reports, as issues on the pool, league folders (side folders, and category folders named by the league's labels) that contradict a play's file, duplicate names and invalid files

## Setup

```bash
uv sync
```

## Usage

```python
from athc.config import load_league_config
from athc.playpool import read_play_pool

labels = load_league_config().categories     # optional: the league's folder names
pool = read_play_pool("plays", labels=labels)

len(pool.offensive_plays), len(pool.defensive_plays), len(pool.special_plays)
play = pool.find_by_name("AF3ArshZ")        # case-insensitive
play.category.long                           # the game's category name
play.file_path
pool.issues                                  # every problem found while building
```

## How athc reads a play

athc reads these from the play file itself; a play's folder doesn't count,
except `Screens`. "The QB" is any player at QB.

| Attribute | A play has it when |
|---|---|
| Rollout pass | It's a pass play, and between the snap and his Timed pass or Check receivers the QB gets beyond 100 units (about 1.1 yards) outside the outermost offensive lineman (C, G or T, never a TE) on that side, where that lineman stands at the snap. Exactly 100 is not a rollout. |
| Timed pass | It's a pass play, and the QB throws a Timed pass after the snap. Any other pass is Check Receivers. |
| QB run | It's a run play, and the QB runs the ball after the snap. |
| 3-4 / 4-3 | It's a Run Left, Run Middle or Run Right defense with 3 / 4 down linemen (DT, DE). |
| 2-DL | It's a pass defense with 2 down linemen. |
| Screen | It's a pass play in a `Screens` folder. |

A pass can be both a rollout and a timed pass.

## API

- `read_play_pool(root_dir, *, labels=None)` walks `root_dir/**/*.ply` in sorted path order and returns a `PlayPool`; invalid and unreadable files are noted in `issues` and skipped, never raised, and nothing is logged, and of two same-named plays the later in that order wins. `labels` is the league's `CategoryLabels`; without it no folder name means a category.
- `folder_warnings(rel_path, play, labels)`: the folder/file mismatch warnings for one play, as the pool reports them.
- `PlayPool`: `root_dir`, `offensive_plays`, `defensive_plays`, `special_plays`, `issues` (every problem, word for word); `find_by_name(name)` (case-insensitive); `add(play)` files an `OffensivePlay` / `DefensivePlay` / `SpecialPlay` under its side and indexes it.
- `Play`: `name`, `play_file` (the parsed `PlayFile`), `file_path`, `category` (an `fbpro98_play` enum member), `play_category`, `special_category`, `user_category`; `to_dict()`. `OffensivePlay` adds `screen`, `rollout`, `qb_run`, `pass_logic` (`PassLogic.TIMED` / `CHECK_RECEIVERS`); `DefensivePlay` adds `defensive_front` (an `fbpro98_play` `DefensiveFront`: `THREE_FOUR` / `FOUR_THREE` / `TWO_DL`, or `None`); `SpecialPlay` adds nothing. Each attribute is set as [How athc reads a play](#how-athc-reads-a-play) describes; the rollout margin is `ROLLOUT_MARGIN` in `playpool.reader`.

## Testing

```bash
pytest
```

## How it works

### Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── model.py      # Play + Offensive/Defensive/Special subclasses; PassLogic; PlayPool
└── reader.py     # read_play_pool: walk, classify, add to the pool; folder_warnings
```

### What this package does

- `read_play_pool(root, *, labels=None)` → `PlayPool`: walks
  `root/**/*.ply` in sorted path order, parses each via `fbpro98_play`,
  classifies, indexes by name (case-insensitive; of two same-named plays the
  later in that order wins).
- Classifies each play **from its file**:
  - side from the category bytes (`is_offensive` / `is_defensive` /
    `is_special`);
  - `category` (an `fbpro98_play` enum member; a file with an unrecognized
    category is skipped) from the play's category bytes; run/pass is `category.is_run` / `category.is_pass`;
  - offense `qb_run` (run plays), `rollout` and `pass_logic` (pass plays) from
    the `PlayFile`'s `is_qb_run`, `is_rollout(ROLLOUT_MARGIN)` and
    `is_timed_pass` (Timed, else Check Receivers);
  - defense `defensive_front` from the `PlayFile`.
- Reads the one optional **PNFL folder** attribute the file can't carry:
  offense `screen` — a pass play in a `Screens/` folder.
- **Warns** (never reclassifies) when a play sits in a recognized PNFL folder
  that contradicts its file: a wrong side, or — when the side matches — a category
  differing from the folder's. Each warning starts with the play's path, e.g.
  `Offense/PML/X.ply: Pass Short Left play in a Pass Medium Left folder.`. A wrong
  side is reported alone; unrecognized folders (flat / non-PNFL) never warn. A
  category with no PNFL folder (`User Specific`, Pass Long Left/Middle, Razzle
  Dazzle Run) warns only when filed inside a category folder, not when loose.
- Keeps every warning (folder mismatches, duplicate names, invalid or
  unreadable files) in `PlayPool.issues`, word for word, so `playpool check`
  can print and count them; it never logs.

### Records — fixed, typed attributes

`Play` (base): `name`, `play_file`; `category` (the `fbpro98_play` enum
member) from the play file. Subclasses add:

- `OffensivePlay`: `screen`, `rollout`, `qb_run`, `pass_logic`.
- `DefensivePlay`: `defensive_front`.
- `SpecialPlay`: nothing beyond the base.

Enums: `PassLogic` (Timed, Check Receivers); `defensive_front` is an
`fbpro98_play` `DefensiveFront` (3-4, 4-3, 2-DL, where 2-DL is the
Run-and-Shoot front).

Category folders are matched against the league's labels (`CategoryLabels`,
passed to `read_play_pool` / `folder_warnings`), the play's own side first; the
labels are league data.

### What this package enforces / does NOT do

- Invalid and unreadable `.ply` files are noted in `issues` and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root and passes it in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

### Testing

- `tests/unit/playpool/` — file-driven classification over three layouts
  (PNFL / non-PNFL / flat); attributes from the play file (rollout margin,
  category gates); folder attributes; mismatch warnings; `issues`; record
  classes.
- Matrix: `tests/unit/playpool/README.md`.
