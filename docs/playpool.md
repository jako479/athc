# playpool

Library + CLI for a league's play pool: builds it from a folder of Front Page Sports Football Pro '98 play (`.ply`) files, each classified from its own bytes, and checks it with `athc playpool check`.

## Features

- Walks a folder tree of `.ply` files, any layout
- Side, category and play attributes (rollout, QB run, timed pass, defensive front) from the play file; folders only add what the bytes can't carry (screen)
- Typed `OffensivePlay` / `DefensivePlay` / `SpecialTeamsPlay` records
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

len(pool.offensive_plays), len(pool.defensive_plays), len(pool.special_teams_plays)
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
- `PlayPool`: `root_dir`, `offensive_plays`, `defensive_plays`, `special_teams_plays`, `issues` (every problem, word for word); `find_by_name(name)` (case-insensitive); `add(play)` files an `OffensivePlay` / `DefensivePlay` / `SpecialTeamsPlay` under its side and indexes it.
- `Play`: `name`, `play_file` (the parsed `PlayFile`), `file_path`, `category` (an `fbpro98_play` enum member), `play_category`, `special_category`, `user_category`; `to_dict()`. `OffensivePlay` adds `screen`, `rollout`, `qb_run`, `pass_logic` (`PassLogic.TIMED` / `CHECK_RECEIVERS`); `DefensivePlay` adds `defensive_front` (an `fbpro98_play` `DefensiveFront`: `THREE_FOUR` / `FOUR_THREE` / `TWO_DL`, or `None`); `SpecialTeamsPlay` adds nothing. Each attribute is set as [How athc reads a play](#how-athc-reads-a-play) describes; the rollout margin is `ROLLOUT_MARGIN` in `playpool.reader`.

## CLI

`athc playpool check [OPTIONS] [FOLDER]` checks the play pool for problems:
plays in the wrong folder, duplicate play names, and invalid play files.

```bash
athc playpool check
athc playpool check .
athc playpool check newplays
athc playpool check --league PCFL
```

With no FOLDER, it checks the league's `play_path` (from `--league`, or
`[athc] league` in `athc.ini`). A `play_path` that is missing on disk ends its
line with `Run 'athc config set play_path FOLDER'.`; no `play_path` at all says
`Play pool folder is not set. Run 'athc config set play_path FOLDER' or pass the
folder.`

With a FOLDER (`.` for the current one), it checks that folder's whole tree
instead and never reads `play_path`. A FOLDER needs no league; a league that
resolves still lends its category names to the folders, and without one no
folder name means a category. A FOLDER that is missing gets Windows' plain
line, with no hint.

It checks the same things pool loading checks for every other command, with
the same messages:

- A play in a side folder, or a category folder named by the league's labels,
  that contradicts its file (wrong side or category).
- A play name used more than once.
- A `.ply` file that isn't a valid play file.

Each issue prints on its own line (a result, on stdout, never a `WARN`), then a
blank line and `<folder>: <n> play(s) checked, <n> issue(s)`, the folder
as typed. Shared console and codes:
[architecture](architecture.md#console-run-log-and-errors).

| Exit | Meaning |
|---|---|
| `0` | Done: no issues. |
| `1` | Findings: one or more issues. |
| `2` | Error: no league; no `play_path` (`FAIL <league.toml>: Play pool folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.`); a `play_path` that is not a folder, with the hint (`FAIL <play_path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.`); a missing FOLDER (`FAIL <folder>: The system cannot find the path specified.`) or a file in its place (`FAIL <folder>: The directory name is invalid.`); a second FOLDER (Click's usage error); or a file or folder the system can't read (`FAIL <why>`). |

`src/athc/cli/playpool/check.py` is the leaf command of the
`src/athc/cli/playpool/` group. It loads the pool with `read_play_pool`, and
the library keeps its findings in `PlayPool.issues`. Tests:
`tests/integration/test_playpool_check.py`.

## Testing

```bash
pytest
```

## How it works

### Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── model.py      # Play + Offensive/Defensive/SpecialTeams subclasses; PassLogic; PlayPool
└── reader.py     # read_play_pool: walk, classify, add to the pool; folder_warnings
```

### What this package does

- `read_play_pool(root, *, labels=None)` → `PlayPool`: walks
  `root/**/*.ply` in sorted path order, parses each via `fbpro98_play`,
  classifies, indexes by name (case-insensitive; of two same-named plays the
  later in that order wins).
- Classifies each play **from its file**:
  - side from the category bytes (`is_offensive` / `is_defensive` /
    `is_special_teams`);
  - `category` (an `fbpro98_play` enum member; a file with an unrecognized
    category is skipped) from the play's `user_category`; run/pass is `category.is_run` / `category.is_pass`;
  - offense `qb_run` (run plays), `rollout` and `pass_logic` (pass plays) from
    the `PlayFile`'s `is_qb_run`, `is_rollout(ROLLOUT_MARGIN)` and
    `is_timed_pass` (Timed, else Check Receivers);
  - defense `defensive_front` from the `PlayFile`.
- Reads the one optional **PNFL folder** attribute the file can't carry:
  offense `screen` — a `Screens/` folder.
- **Warns** (never reclassifies) when a play sits in a recognized PNFL folder
  that contradicts its file: a wrong side, or — when the side matches — a category
  differing from the folder's. Each warning starts with the play's path, e.g.
  `Offense/PML/X.ply: Pass Short Left play in a Pass Medium Left folder.`. A wrong
  side is reported alone; unrecognized folders (flat / non-PNFL) never warn. A
  category with no PNFL folder (`User Specific`, Pass Long Left/Middle, Razzle
  Dazzle Run) warns only when filed inside a category folder, not when loose.
- Keeps every warning it logs (folder mismatches, duplicate names, invalid or
  unreadable files) in `PlayPool.issues`, word for word, so `playpool check`
  can print and count them.

### Records — fixed, typed attributes

`Play` (base): `name`, `play_file`; `category` (the `fbpro98_play` enum
member) from the play file. Subclasses add:

- `OffensivePlay`: `screen`, `rollout`, `qb_run`, `pass_logic`.
- `DefensivePlay`: `defensive_front`.
- `SpecialTeamsPlay`: nothing beyond the base.

Enums: `PassLogic` (Timed, Check Receivers); `defensive_front` is an
`fbpro98_play` `DefensiveFront` (3-4, 4-3, 2-DL, where 2-DL is the
Run-and-Shoot front).

Category folders are matched against the league's labels (`CategoryLabels`,
passed to `read_play_pool` / `folder_warnings`), the play's own side first; the
labels are league data.

### What this package enforces / does NOT do

- Invalid and unreadable `.ply` files are logged and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root and passes it in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

### Testing

- `tests/unit/playpool/` — file-driven classification over three layouts
  (PNFL / non-PNFL / flat); attributes from the play file (rollout margin,
  category gates); folder attributes; mismatch warnings; `issues`; record
  classes.
- Matrix: `tests/unit/playpool/README.md`.
