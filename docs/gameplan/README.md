# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](../fbpro98_gameplan/) (`.pln` I/O) and [playpool](../playpool/) (per-play attributes).

**Status:** six pnfl subcommands ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials` — plus `replace-play` (new).

## Results and exit codes

Every command prints through the shared console ([architecture](../design/architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines, progress and usage errors on stderr; every status line also in the run log. The same codes everywhere: `0` done (warnings included), `1` findings, `2` error (usage, config, a bad or missing file, a file that failed inside a batch, a bug). A batch processes every file and exits with the worst outcome. A named file that does not exist is `FAIL <file>: not found`.

| Command | Lines | Exit 1 (findings) |
|---|---|---|
| `check` | `WARN` per play-pool issue and rules notice, then per file `OK   <file>: <side>, <n> normal` or the headline `<file>: <n> violation(s) (<side>, <n> normal)` with its indented detail lines; a blank line; `<n> file(s) checked, <n> with violations, <n> failed` | violations |
| `find-play` | per file and play `<file>: 'play' found in slot(s) ...` or `<file>: 'play' not found`; in directory mode a tally per play, `'play': found <n> instance(s) in <m> gameplan(s)`; a single path, found or not, gets no tally | a play found nowhere (2 if any file failed) |
| `list-normals` / `list-specials` | the play names (with `-`), else `OK   <file>: <n> normal play(s)` / `... special play(s)` | never |
| `replace-play` | `OK   <file>: 'old' (cat) replaced with 'new' (cat) [1-1][2-2]` per updated file; a single file without the play prints `<file>: 'play' not found`; in directory mode `'old' -> 'new': replaced <n> instance(s) in <m> gameplan(s), <f> failed` | nothing replaced anywhere; a replacement not in the pool is an error |
| `set-normals` | `OK   <gameplan>: <n> normal play(s)` (`-q` skips it); a bad play list is one `FAIL <input_file> <what is wrong>` per bad line (`FAIL <what is wrong>` when the list came from the console), the game plan untouched, exit 2 | never |
| `set-specials` | `OK   <file>: updated (<n> special play(s))`, `SKIP <file>: <other side> gameplan`, `FAIL <file>: <why>` for a file the list does not fit; a tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed` | never (a failed file is exit 2) |

## Setup

```bash
uv sync
```

## Library

```python
from athc.fbpro98_gameplan import read_gameplan
from athc.gameplan import load_rules, validate_gameplan
from athc.playpool import load_rules as load_pool_rules
from athc.playpool import read_play_pool

pool = read_play_pool("C:/PNFL/plays", rules=load_pool_rules("playpool.toml"))
rules = load_rules(["gameplan.toml"])           # validation-only; pass more to layer
gp = read_gameplan("OFF.pln")
violations = validate_gameplan(gp, rules, pool)  # tuple[Violation, ...]
```

## CLI

```bash
athc gameplan check OFF.pln Def.pln           # league from config
athc gameplan check                           # every .pln in the current directory
athc gameplan check plans/ -r                 # directory tree
athc gameplan check OFF.pln --league PCFL     # another league

athc gameplan list-normals OFF.pln                 # 64 normal plays to OFF.normals.txt
athc gameplan list-normals OFF.pln plays.txt --sort name
athc gameplan list-normals OFF.pln --sort category # grouped under `:: <category>` headers
athc gameplan list-normals OFF.pln -               # to stdout
athc gameplan list-specials OFF.pln                # custom special teams to OFF.specials.txt
athc gameplan find-play OR45RL01                   # every .pln in the current directory
athc gameplan find-play OR45RL01 OFF.pln           # slot(s) holding the play
athc gameplan find-play OR45RL01 BCFGPAT plans/ -r # many plays across a tree
athc gameplan set-normals OFF.pln plays.txt        # replace 64 normal slots
athc gameplan set-normals OFF.pln -                # play list from stdin
athc gameplan set-specials plans/ spec.txt -r      # merge specials across a tree
athc gameplan replace-play OLDRUN NEWRUN plans/ -r # swap one play for another
```

`list-specials` and `find-play` just read a `.pln` — no pool, rules or config; `list-normals` also reads the league's category names (`--league`). `list-*` create the output file's missing folders. `set-*` need the pool (like `check`, minus the gameplan rules) and edit in place with no backup. `replace-play play replacement path` swaps one play for another wherever `find-play` would find it, using the league's play pool; `replacement` must be in the pool. `athc gameplan <command> --help` for flags.

## Config

The league folder `leagues\<NAME>\` (see [../design/architecture.md](../design/architecture.md#config)), picked by `--league` / `[athc] league`:

- `gameplan.toml` — the rules (or a `gameplan_rules` array in `league.toml`, later files layering over earlier).
- `league.toml` `play_path` (pool dir), its `[categories.*]` labels, and `playpool.toml` (optional filename-filter TOML).

`check` reads all of these from the league folder only. No rules resolvable ⇒ exit 2 (nothing to validate).

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, layout, violation format.
- `config/release/leagues/<NAME>/gameplan.toml` — each league's rule set.

## Tests

`pytest tests/integration/test_gameplan_check.py`
