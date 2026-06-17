# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](../fbpro98_gameplan/) (`.pln` I/O) and [playpool](../playpool/) (per-play attributes).

**Status:** all six pnfl subcommands are ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials`.

## Setup

```bash
uv pip install -e ".[dev]"
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
```

`check` exits `0` clean / `1` violations / `2` usage, config error, or no rules. `list-*` and `find-play` just read a `.pln` (no pool/rules/config): `list-*` exit `0`, or `1` on a read error or refused overwrite; `find-play` exits `0` all found / `1` a play missed everywhere / `2` I/O error. `set-*` need the pool (like `check`, minus `--rules`) and edit in place after a `.bak`: `set-normals` exits `0` / `2`, `set-specials` exits `0` all updated / `1` some failed / `2` setup error. `athc gameplan <command> --help` for flags.

## Config

Shared `athc.ini` (see [../design/config.md](../design/config.md)):

- `[gameplan] rule_files` — one gameplan-rules path per line.
- League section (`[league.PNFL]`, picked by `--league` / `ATHC_LEAGUE` / `[athc] default_league`) — `PlayPath` (pool dir) and optional `PlayPoolRules` (a playpool filename-filter TOML).

`--play-path`, `--playpool-rules`, and repeatable `--rules` override config; given all three, no league is needed. No rules resolvable ⇒ exit 2 (nothing to validate).

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, layout, violation format.
- [RULES_PNFL.md](RULES_PNFL.md) — the PNFL rule set, and [release/rules/PNFL.gameplan.toml](../../release/rules/PNFL.gameplan.toml).

## Tests

`pytest tests/integration/test_gameplan_check.py`
