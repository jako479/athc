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
└── config.py             # Config (play_path + rules from the league folder)

src/athc/cli/gameplan/    # CLI group
├── __init__.py           # `athc gameplan` group
├── _common.py            # shared helpers (files, search, rules, pool, listing)
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

- `OffenseCategoryRule(required, min_count, max_count, max_qb_draws_*, max_rollouts_*, max_timed_*)`
- `DefenseCategoryRule(required, min_count, max_count, max_two_dl_*)`
- Aggregate counts over the 64 normal slots: min/max plays per game category + per-category attribute caps; required special categories; disallowed categories; optional `custom_special_play_required`.
- `[profile_compatibility]` — `require_all_gameplan_categories_in_profile`, read only by `athc check-ppp` ([../check_ppp/README.md](../check_ppp/README.md)); `validate_gameplan` ignores it.

Section labels are short category labels — `[offense.RM]` (Run Middle), `[defense.RunDazzle]` (Run Dazzle). Every per-category key is optional (`required` defaults false, `min_count` 0), but a section must set at least one. The loader rejects unknown labels, and subkeys applied to the wrong category type. `disallowed_offensive_categories` / `disallowed_defensive_categories` list full category names a gameplan must not contain.

Each capped attribute (`qb_draws`, `rollouts`, `timed`, `two_dl`) takes one of three forms — `max_<attr>_count` (whole plays), `max_<attr>_ratio` (`"1/2"`, an exact `Fraction`) or `max_<attr>_percent` (whole number 0-100). A section may set at most one form per attribute; a second is a rules-file error. Ratio and percent compare the exact play ratio, so nothing rounds.

Loading reports every problem at once (`RulesFileError.errors`); any error aborts `check` with each logged (exit 2).

Each league's rule set is `config/release/leagues/<NAME>/rules/gameplan.toml` — data a coach supplies as a file, not code.

## Config

The league folder `leagues\<NAME>\` (see [../design/config.md](../design/config.md)), chosen by `--league` / `[athc] league`:

- `rules\gameplan.toml` — the rules (or a `gameplan_rules` list in `league.ini`, one path per line, later files layering over earlier).
- `league.ini` `play_path` (play pool dir) and `rules\playpool.toml` (optional filename-filter TOML).

`check` reads all of these from the league folder only. With no rules resolvable there's nothing to validate → log an error, exit 2.

## check

`athc gameplan check PATH...` walks the PATHs, builds one `PlayPool` from `play_path` (plus optional playpool rules), loads the gameplan `Rules`, and runs `validate_gameplan(read_gameplan(file), rules, pool)` per `.pln`. Exit `0` = clean, `1` = violations, `2` = usage/config error.

## list-normals / list-specials

`athc gameplan list-normals gameplan [output_file]` and `list-specials gameplan [output_file]` read one `.pln` and emit play names — no pool, rules, or config. `list-normals` takes `--sort slot|name` (slot keeps the 64 positions with blanks; name drops blanks, sorts case-insensitively); `list-specials` is source order. Each writes `<name>.normals.txt` / `<name>.specials.txt` next to the `.pln`, or `output_file`; an existing file is replaced; an `output_file` of `-` prints to stdout (the POSIX convention for `-` as a file). A written file has a `:: <source>` header then the names. Exit `0` = ok, `1` = read or write error, `2` = usage.

## find-play

`athc gameplan find-play play... path` searches one or more case-insensitive names across the normal + custom-special slots of each `.pln` (file, directory, or tree with `-r`); stock specials and clock plays are skipped. Normal hits read `'NAME' found in slots G-C, G-C` (`slot` for one); a custom-special hit reads `'NAME' found in special slot N (long-cat)`. Every file missing a play prints `not found`; directory/tree mode adds a per-play summary footer. Exit codes follow grep: `0` = at least one play found, `1` = none found, `2` = I/O error.

## set-normals / set-specials

`gameplan.writer` resolves a play list against the pool into `.pln` slot entries (`apply_normal_plays` / `apply_special_plays`), aggregating every per-line problem into one `InvalidPlayInputError`. Side and special-teams classification come from each play's `.ply` header, not the rules. The list format is one name per line, `::` comment lines, ` ::` inline trailers (`parse_play_list`). Input or read failures abort before any write. Each slot's play path is the play pool's folder name, then the play's path inside the pool (`<pool folder>\Offense\RL\OR45RL01.ply`).

- `set-normals gameplan input_file` replaces all 64 normal slots of one `.pln`; an `input_file` of `-` reads stdin. The pool and its playpool rules come from the league. No backup is made. Special-teams plays are rejected (use set-specials). Exit `0` = updated, `1` = error, `2` = usage.
- `set-specials path input_file` merges the custom special slots (unlisted categories preserved) of one `.pln`, or every `.pln` in a directory/tree (`-r`); an `input_file` of `-` reads stdin. Each play self-slots by its special category; wrong-side files are skipped silently (offense `.pln` are even-sized, defense odd). The pool and its playpool rules come from the league. No backup is made. Exit `0` = all updated, `1` = some files failed, `2` = setup error.

## replace-play

`gameplan replace-play play replacement path` swaps every instance of `play` for
`replacement` across one `.pln`, a directory, or a tree (`-r`) — `find-play`'s
case-insensitive search (normal + custom-special slots) plus `set-normals`'
pool-resolution. `play` is a single play (unlike `find-play`, which takes
several); both `play` and `replacement` are fixed positionals. `replacement` must resolve in the pool (checked once,
up front; a miss logs an error and exits 2); `play` need not (it may already be
gone — the rename case). Only matched slots are swapped (surgical, unlike
`set-normals`); the rest are preserved. The pool is the league's `play_path`,
built **without** playpool rules — the swap uses each play's category bytes, not
the filename-derived attributes those rules add. The
`GamePlan` model validates each swap (side parity; a special play's category
must match its slot); an invalid
swap fails that file (reported, not written). No backup is made. Run `check`
afterward to validate against league rules.

Output uses the short game-category label. A play's normal-slot hits collapse to
one line, slots bracketed in order at the end: `<file>: 'OLD' (cat) replaced with
'NEW' (cat) [1-3][4-2]` (a play can fill many normal slots). Special hits print one
line each: `<file>: Replaced 'OLD' (cat) in special slot N with 'NEW' (cat)`
(`special slot N` like `find-play`; a play fills only one special slot).

## Exit codes

See [README.md](README.md#results-and-exit-codes). Two classes (see
[../design/cli.md](../design/cli.md#exit-codes)): `check`, `find-play`,
`set-specials`, and `replace-play` bear a **findings** tier; `list-normals`,
`list-specials`, and `set-normals` are utilities.

## .pln format

G95 (plays + 86 offsets), J95 (profile_type + counts), S98 (`STOCK98.MAP\0`); size parity even = offense / odd = defense. Byte-level docs: [../fbpro98_gameplan/specs/pln.md](../fbpro98_gameplan/specs/pln.md).
