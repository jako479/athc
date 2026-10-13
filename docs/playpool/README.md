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

Each issue prints on its own line (a result, on stdout, never a `WARN`), then a
blank line and `<n> play(s) checked in '<dir>', <n> issue(s)`. Shared console
and codes: [architecture](../design/architecture.md#console-run-log-and-errors).

| Exit | Meaning |
|---|---|
| `0` | Done: no issues. |
| `1` | Findings: one or more issues. |
| `2` | Error: no league, no `play_path`, a missing folder (`FAIL <folder>: The system cannot find the path specified.`), a file in its place (`FAIL <path>: The directory name is invalid.`), or a file or folder the system can't read (`FAIL <why>`). |

`src/athc/cli/playpool/check.py` is the leaf command of the
`src/athc/cli/playpool/` group. It loads the pool with `read_play_pool`, and
the library keeps its findings in `PlayPool.issues`. Tests:
`tests/integration/test_playpool_check.py`.

## Testing

```bash
pytest
```
