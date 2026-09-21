# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](../fbpro98_gameplan/) (`.pln` I/O) and [playpool](../playpool/) (per-play attributes).

**Status:** six pnfl subcommands ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials` — plus `replace-play` (new).

## Results and exit codes

| Exit | `check` / `find-play` / `set-specials` / `replace-play` | `list-*` / `set-normals` |
|---|---|---|
| `0` | **Clean** — no violations, all found, all updated | ok / updated |
| `1` | **Findings** — violations, a play missed, nothing replaced, or some files failed | error (read, write, or invalid input) |
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
athc gameplan check plans/ -r                 # directory tree
athc gameplan check OFF.pln --play-path C:/PNFL/plays \
    --playpool-rules PNFL.playpool.toml --rules gameplan.toml

athc gameplan list-normals OFF.pln                 # 64 normal plays to stdout
athc gameplan list-normals OFF.pln plays.txt --sort name
athc gameplan list-specials OFF.pln spec.txt -f    # custom special teams
athc gameplan find-play OR45RL01 OFF.pln           # slot(s) + game category
athc gameplan find-play OR45RL01 BCFGPAT plans/ -r # many plays across a tree
athc gameplan set-normals OFF.pln plays.txt        # replace 64 normal slots (+ .bak)
athc gameplan set-normals OFF.pln --stdin --no-backup
athc gameplan set-specials plans/ spec.txt -r      # merge specials across a tree
athc gameplan replace-play OLDRUN NEWRUN plans/ -r # swap one play for another (+ .bak)
```

`list-*` and `find-play` just read a `.pln` — no pool, rules or config. `set-*` need the pool (like `check`, minus `--rules`) and edit in place after a `.bak`. `replace-play OLDNAME NEWNAME PATH` swaps one play for another wherever `find-play` would find it (`--play-path`/`--league`, no `--rules`/`--playpool-rules`); `NEWNAME` must be in the pool. `athc gameplan <command> --help` for flags.

## Config

Shared `athc.ini` (see [../design/config.md](../design/config.md)):

- `[gameplan] rule_files` — one gameplan-rules path per line.
- League section (`[league.PNFL]`, picked by `--league` / `ATHC_LEAGUE` / `[athc] default_league`) — `play_path` (pool dir) and optional `playpool_rules` (a playpool filename-filter TOML).

`--play-path`, `--playpool-rules`, and repeatable `--rules` override config; given all three, no league is needed. No rules resolvable ⇒ exit 2 (nothing to validate).

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, layout, violation format.
- [release/rules/PNFL.gameplan.toml](../../release/rules/PNFL.gameplan.toml) — the PNFL rule set.

## Tests

`pytest tests/integration/test_gameplan_check.py`
