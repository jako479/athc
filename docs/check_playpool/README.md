# check-playpool

Check the play pool for problems: plays in the wrong folder, duplicate play
names, and invalid play files.

## Usage

```bash
athc check-playpool
athc check-playpool E:\SIERRA\FbPro98\PNFL
athc check-playpool --league PCFL
```

With no folder, it checks the league's `play_path` (from `--league`, or
`[athc] league` in `athc.ini`). A given folder needs no league.

## What it checks

The same things pool loading checks for every other command, with the same
messages:

- A play in a PNFL folder that contradicts its file (wrong side or category).
- A play name used more than once.
- A `.ply` file that isn't a valid play file.

Each problem prints on its own line, then one summary line with the number of
plays checked and issues found.

## Results and exit codes

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no issues. |
| `1` | **Findings** — one or more issues. |
| `2` | **Error** — couldn't run: no league, no `play_path`, a missing folder, or a file or folder the system can't read. |

## Code

`src/athc/cli/check_playpool.py` is a leaf command. It loads the pool with
the gameplan group's `build_pool`, and the `playpool` library keeps its
warnings in `PlayPool.issues`. Tests:
`tests/integration/test_check_playpool.py`.
