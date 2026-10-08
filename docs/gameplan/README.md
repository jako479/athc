# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](../fbpro98_gameplan/) (`.pln` I/O) and [playpool](../playpool/) (per-play attributes).

**Status:** six pnfl subcommands ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials` — plus `replace-play` (new).

## Results and exit codes

| Exit | `check` / `find-play` / `set-specials` / `replace-play` | `list-*` / `set-normals` |
|---|---|---|
| `0` | **Clean** — no violations, a play found, all updated | ok / updated |
| `1` | **Findings** — violations, no play found, nothing replaced, or some files failed | error (read, write, or invalid input) |
| `2` | **Error** — couldn't run: usage, config, I/O, no rules, or replacement not in pool | usage (bad arguments) |

An **error** means the command couldn't run; a **finding** is a real problem to
fix. Every check runs to the end — one bad file or violation does not stop the
rest.

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

`list-*` and `find-play` just read a `.pln` — no pool, rules or config. `set-*` need the pool (like `check`, minus the gameplan rules) and edit in place with no backup. `replace-play play replacement path` swaps one play for another wherever `find-play` would find it, using the league's play pool; `replacement` must be in the pool. `athc gameplan <command> --help` for flags.

## Config

The league folder `leagues\<NAME>\` (see [../design/config.md](../design/config.md)), picked by `--league` / `[athc] league`:

- `gameplan.toml` — the rules (or a `gameplan_rules` array in `league.toml`, later files layering over earlier).
- `league.toml` `play_path` (pool dir), its `[categories.*]` labels, and `playpool.toml` (optional filename-filter TOML).

`check` reads all of these from the league folder only. No rules resolvable ⇒ exit 2 (nothing to validate).

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, layout, violation format.
- `config/release/leagues/<NAME>/gameplan.toml` — each league's rule set.

## Tests

`pytest tests/integration/test_gameplan_check.py`
