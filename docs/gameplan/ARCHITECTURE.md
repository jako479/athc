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
├── _common.py            # shared helpers (files, rules, pool, listing, backup)
├── check.py              # `athc gameplan check`
├── find_play.py          # `athc gameplan find-play`
├── list_normals.py       # `athc gameplan list-normals`
├── list_specials.py      # `athc gameplan list-specials`
├── set_normals.py        # `athc gameplan set-normals`
└── set_specials.py       # `athc gameplan set-specials`
```

`list-*` and `find-play` read a `.pln` and report names/slots — no pool, rules, or config. `set-*` need the pool (to resolve names) but not the rules — they edit; `check` validates.

## Three layers

- `fbpro98_gameplan` — `.pln` read/write, no league knowledge.
- `playpool` — classifies `.ply` files by folder/filename into typed records: offense `qb_draw` / `rollout` / `pass_logic`, defense `defensive_front`.
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

`athc gameplan list-normals FILE [OUTPUT]` and `list-specials FILE [OUTPUT]` read one `.pln` and emit play names — no pool, rules, or config. `list-normals` takes `--sort slot|name` (slot keeps the 64 positions with blanks; name drops blanks, sorts case-insensitively); `list-specials` is source order. No `OUTPUT` prints to stdout; with `OUTPUT` it writes a `:: <source>` header then the names (`-f` to overwrite). Exit `0` = ok, `1` = read error or refused overwrite.

## find-play

`athc gameplan find-play PLAY... PATH` searches one or more case-insensitive names across the normal + custom-special slots of each `.pln` (file, directory, or tree with `-r`); stock specials and clock plays are skipped. Hits show the game-grid slot(s) (`1-1`…`16-4`) and game category. Single file: a miss prints `not found`; directory/tree: misses are silent unless `--verbose`, with a per-play summary footer. Exit `0` = every play hit somewhere, `1` = a play missed everywhere, `2` = I/O error.

## set-normals / set-specials

`gameplan.writer` resolves a play list against the pool into `.pln` slot entries (`apply_normal_plays` / `apply_special_plays`), aggregating every per-line problem into one `InvalidPlayInputError`. Side and special-teams classification come from each play's `.ply` header, not the rules. The list format is one name per line, `::` comment lines, ` ::` inline trailers (`parse_play_list`). A timestamped `.bak` is written before any update (`make_backup`, unless `--no-backup`); input or read failures abort before any backup or write.

- `set-normals GAMEPLAN [INPUT]` replaces all 64 normal slots of one `.pln`. Special-teams plays are rejected (use set-specials). Exit `0` = updated, `2` = error.
- `set-specials TARGET [INPUT]` merges the custom special slots (unlisted categories preserved) of one `.pln`, or every `.pln` in a directory/tree (`-r`). Each play self-slots by its special category; wrong-side files are skipped silently (offense `.pln` are even-sized, defense odd). Exit `0` = all updated, `1` = some files failed, `2` = setup error.

Both read `INPUT` or `--stdin`, and resolve the pool like `check` (`--play-path` / `--playpool-rules` / league config).

## .pln format

G95 (plays + 86 offsets), J95 (profile_type + counts), S98 (`STOCK98.MAP\0`); size parity even = offense / odd = defense. Byte-level docs: [../fbpro98_gameplan/specs/pln.md](../fbpro98_gameplan/specs/pln.md).
