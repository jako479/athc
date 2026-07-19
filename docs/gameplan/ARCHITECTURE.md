# gameplan — Architecture

Library + CLI over `fbpro98_gameplan` + `playpool`. Validates `.pln` gameplans against league rules supplied as **external files** — no rules are baked in; the tool is league-agnostic.

## Layout

```
src/athc/gameplan/        # tool logic (no Click)
├── __init__.py           # public API
├── model.py              # Violation, RuleName
├── rules.py              # Rules, OffenseCategoryRule, DefenseCategoryRule, load_rules
├── validators.py         # validate_gameplan
├── writer.py             # apply_normal_plays / apply_special_plays (name -> slot)
└── config.py             # Config (athc.ini [gameplan] + league section)

src/athc/cli/gameplan/    # CLI group
├── __init__.py           # `athc gameplan` group
├── _common.py            # shared helpers (files, search, rules, pool, listing, backup)
├── check.py              # `athc gameplan check`
├── find_play.py          # `athc gameplan find-play`
├── list_normals.py       # `athc gameplan list-normals`
├── list_specials.py      # `athc gameplan list-specials`
├── replace_play.py       # `athc gameplan replace-play`
├── set_normals.py        # `athc gameplan set-normals`
└── set_specials.py       # `athc gameplan set-specials`
```

`list-*` and `find-play` read a `.pln` and report names/slots — no pool, rules, or config. `set-*` and `replace-play` need the pool (to resolve names) but not the rules — they edit; `check` validates. `find_in_gameplan` (the case-insensitive normal + custom-special slot search) lives in `_common.py`; `find-play` and `replace-play` share it.

## Three layers

- `fbpro98_gameplan` — `.pln` read/write, no league knowledge.
- `playpool` — classifies `.ply` files from the play file (side + category); folders/filename add attributes: offense `screen` / `qb_draw` / `rollout` / `pass_logic`, defense `defensive_front`.
- `gameplan` — applies league rules; needs the pool because rules check per-play attributes that aren't in the `.pln`.

## Rules — external, optional, league-agnostic

No rules ship inside the package. `load_rules(paths)` parses one or more external TOML files into a `Rules` value; later files layer over earlier (per-category replace, scalar overwrite). Rules are validation-only — reading a gameplan never needs them.

- `OffenseCategoryRule(required, min_count, max_count, max_qb_draws, max_rollouts, max_timed_percent)`
- `DefenseCategoryRule(required, min_count, max_count, max_two_dl_percent)`
- Aggregate counts over the 64 normal slots: min/max plays per game category + per-category attribute caps; required special categories; disallowed categories; optional `custom_special_play_required`.

Section labels are short category labels — `[offense.RM]` (Run Middle), `[defense.RunDazzle]` (Run Dazzle). Every per-category key is optional (`required` defaults false, `min_count` 0), but a section must set at least one. The loader rejects unknown labels, and subkeys applied to the wrong category type. `disallowed_offensive_categories` / `disallowed_defensive_categories` list full category names a gameplan must not contain. Percentages are exact `Fraction`s (`"1/2"` in TOML).

Loading reports every problem at once (`RulesFileError.errors`); any error aborts `check` with each logged (exit 2).

The PNFL rule set is in [RULES_PNFL.md](RULES_PNFL.md) — data a coach supplies as a file, not code.

## Config

Shared `athc.ini` (see [../design/config.md](../design/config.md)):

- `[gameplan] rule_files` — one rule-TOML path per line.
- League section (`[league.PNFL]`, chosen by `--league` / `ATHC_LEAGUE` / `[athc] default_league`) — `PlayPath` (play pool dir) and optional `PlayPoolRules` (a playpool filename-filter TOML).

`check` also takes `--play-path`, `--playpool-rules`, and repeatable `--rules` to override; given all three it skips league resolution. With no rules resolvable there's nothing to validate → log an error, exit 2.

## check

`athc gameplan check PATH...` walks the PATHs, builds one `PlayPool` from `PlayPath` (plus optional playpool rules), loads the gameplan `Rules`, and runs `validate_gameplan(read_gameplan(file), rules, pool)` per `.pln`. Exit `0` = clean, `1` = violations, `2` = usage/config error.

## list-normals / list-specials

`athc gameplan list-normals FILE [OUTPUT]` and `list-specials FILE [OUTPUT]` read one `.pln` and emit play names — no pool, rules, or config. `list-normals` takes `--sort slot|name` (slot keeps the 64 positions with blanks; name drops blanks, sorts case-insensitively); `list-specials` is source order. No `OUTPUT` prints to stdout; with `OUTPUT` it writes a `:: <source>` header then the names (`-f` to overwrite). Exit `0` = ok, `1` = read error or refused overwrite, `2` = usage.

## find-play

`athc gameplan find-play PLAY... PATH` searches one or more case-insensitive names across the normal + custom-special slots of each `.pln` (file, directory, or tree with `-r`); stock specials and clock plays are skipped. Normal hits show `'NAME' (short-cat) [G-C][G-C]` (slots bracketed at the end); custom-special hits keep the long category and `in special slot N`. Single file: a miss prints `not found`; directory/tree: misses are silent unless `--verbose`, with a per-play summary footer. Exit `0` = every play hit somewhere, `1` = a play missed everywhere, `2` = I/O error.

## set-normals / set-specials

`gameplan.writer` resolves a play list against the pool into `.pln` slot entries (`apply_normal_plays` / `apply_special_plays`), aggregating every per-line problem into one `InvalidPlayInputError`. Side and special-teams classification come from each play's `.ply` header, not the rules. The list format is one name per line, `::` comment lines, ` ::` inline trailers (`parse_play_list`). A timestamped `.bak` is written before any update (`make_backup`, unless `--no-backup`); input or read failures abort before any backup or write. The backup is named `<file>.<YYYY-MM-DD-HHMM>.bak`; backups accumulate, but two edits of the same file in the same minute reuse one name, so the second silently overwrites the first.

- `set-normals GAMEPLAN [INPUT]` replaces all 64 normal slots of one `.pln`. Special-teams plays are rejected (use set-specials). Exit `0` = updated, `1` = error, `2` = usage.
- `set-specials TARGET [INPUT]` merges the custom special slots (unlisted categories preserved) of one `.pln`, or every `.pln` in a directory/tree (`-r`). Each play self-slots by its special category; wrong-side files are skipped silently (offense `.pln` are even-sized, defense odd). Exit `0` = all updated, `1` = some files failed, `2` = setup error.

Both read `INPUT` or `--stdin`, and resolve the pool like `check` (`--play-path` / `--playpool-rules` / league config).

## replace-play

`gameplan replace-play PLAY REPLACEMENT PATH` swaps every instance of `PLAY` for
`REPLACEMENT` across one `.pln`, a directory, or a tree (`-r`) — `find-play`'s
case-insensitive search (normal + custom-special slots) plus `set-normals`'
pool-resolution + `.bak`. `PLAY` is a single play (unlike `find-play`, which takes
several); both `PLAY` and `REPLACEMENT` are fixed positionals. `REPLACEMENT` must resolve in the pool (checked once,
up front; a miss logs an error and exits 2); `PLAY` need not (it may already be
gone — the rename case). Only matched slots are swapped (surgical, unlike
`set-normals`); the rest are preserved. The pool is built **without** playpool
rules — the swap uses each play's category bytes, not the filename-derived
attributes those rules add — so `replace-play` takes `--play-path` / `--league`
but no `--playpool-rules` and no `--rules`. The `GamePlan` model validates each
swap (side parity; a special play's category must match its slot); an invalid
swap fails that file (reported, not written, no `.bak`). A timestamped `.bak` is
written next to each updated file (unless `--no-backup`). Run `check` afterward
to validate against league rules.

Output uses the short game-category label. A play's normal-slot hits collapse to
one line, slots bracketed in order at the end: `<file>: 'OLD' (cat) replaced with
'NEW' (cat) [1-3][4-2]` (a play can fill many normal slots). Special hits print one
line each: `<file>: Replaced 'OLD' (cat) in special slot N with 'NEW' (cat)`
(`special slot N` like `find-play`; a play fills only one special slot).

## Exit codes

Two classes (see [../design/cli.md](../design/cli.md#exit-codes)). `check`,
`find-play`, `set-specials`, and `replace-play` bear a **findings** tier;
`list-normals`, `list-specials`, and `set-normals` are utilities.

| Exit | `check` / `find-play` / `set-specials` / `replace-play` | `list-*` / `set-normals` |
|---|---|---|
| `0` | clean / all updated | ok / updated |
| `1` | violations, a missed play, nothing replaced, or some files failed | error (read, write, or invalid input) |
| `2` | couldn't run: usage, config, I/O, no rules, or replacement not in pool | usage (bad arguments) |

## .pln format

G95 (plays + 86 offsets), J95 (profile_type + counts), S98 (`STOCK98.MAP\0`); size parity even = offense / odd = defense. Byte-level docs: [../fbpro98_gameplan/specs/pln.md](../fbpro98_gameplan/specs/pln.md).
