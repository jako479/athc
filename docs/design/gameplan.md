# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](fbpro98_gameplan.md) (`.pln` I/O) and [playpool](playpool.md) (per-play attributes).

**Status:** six pnfl subcommands ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials` — plus `replace-play` (new).

Usage, the keys and sources, settings, lines and exit codes: [usage/gameplan.txt](../usage/gameplan.txt).

## Setup

```bash
uv sync
```

## Library

```python
from athc.fbpro98_gameplan import read_gameplan
from athc.gameplan import load_rules, validate_gameplan
from athc.playpool import read_play_pool

pool = read_play_pool("C:/PNFL/plays")
rules = load_rules(["gameplan.toml"])           # validation-only; pass more to layer
gp = read_gameplan("OFF.pln")
violations = validate_gameplan(gp, rules, pool)  # tuple[RuleViolation, ...]
```

## See also

- `config/release/leagues/<NAME>/gameplan.toml` — each league's rule set.

## Tests

`tests/unit/gameplan/` and `tests/integration/test_gameplan_*.py`; each folder's `README.md` lists the cases.

## How it works

### Layout

```
src/athc/gameplan/        # tool logic (no Click)
├── __init__.py           # public API
├── model.py              # RuleViolation, RuleName
├── rules.py              # Rules, OffenseCategoryRule, DefenseCategoryRule, load_rules
├── validators.py         # validate_gameplan
├── writer.py             # apply_normal_plays / apply_special_plays (name -> slot)
└── config.py             # Config (play_path + rules from the league folder)

src/athc/cli/gameplan/    # CLI group
├── __init__.py           # `athc gameplan` group
├── _common.py            # shared helpers (your team's game plans, files, search, rules, pool, listing)
├── check.py              # `athc gameplan check`
├── find_play.py          # `athc gameplan find-play`
├── list_normals.py       # `athc gameplan list-normals`
├── list_specials.py      # `athc gameplan list-specials`
├── replace_play.py       # `athc gameplan replace-play`
├── set_normals.py        # `athc gameplan set-normals`
└── set_specials.py       # `athc gameplan set-specials`

src/athc/cli/_team.py     # shared team layer (check-ppp, gameplan, profile, convert-pdb): league files, team, file locations
```

`list-specials` and `find-play` with a path read a `.pln` and report names/slots — no pool, rules, or config; `list-normals` reads the league too, for the category labels its `--sort category` headers use. `set-*` need the pool (to resolve names) but not the rules — they edit; `check` validates; `replace-play` edits with both, picking a replacement that keeps the rules. `find_in_gameplan` (the case-insensitive normal + custom-special slot search) and `category_of` (a gameplan play's category from its `.pln` bytes) live in `_common.py`; `find-play`, `replace-play` and `list-normals` share them.

### Your team's game plans

Every subcommand takes your team's four game plans by name: `off1`, `def1`, `off2`, `def2` (the `.lg2`'s 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense game plan, any case). An existing file or folder of that name is that path. `--team NAME` picks another team for one run (default: `team` in `league.toml`); with a path and no name it is a usage error (`require_a_key` for a name among the operands; `require_key_path` on the batch commands, whose `--path` must be a name or left out).

`_common.py` builds on `_team.py`:

- `team_game_plans` reads `team` (before the league files), `path`, the `.lg2` and `.lge`, resolves the team and decides where its game plans are: `ppp_path` for your own team, else the league locations (`path` joined with the `.lg2` folder).
- `scope` is the batch commands' `--path`: a real path goes through `collect_files` as before; a name is one game plan; none is the team's four, each once, in `.lg2` order. At the league locations a missing one is a `FAIL`; in `ppp_path` a `WARN` (each folder of the tree on its own with `-r`), and none at all is one line for the scope.
- `collect_entries` is `check`'s PATHs: names and paths, left to right, each file once.
- `one_game_plan` is the one-file commands' `GAME_PLAN`: `named_file` for a path, the team's file for a name; a missing one is the run's error.
- `read_play_list` reads a play list; a file that is not text is `Not a valid play list.`

A wrong `--league` fails first on every subcommand; the team and league files are read before the pool and rules.

### Three layers

- `fbpro98_gameplan` — `.pln` read/write, no league knowledge.
- `playpool` — classifies `.ply` files from the play file: side, category and the attributes the rules cap (offense `qb_run` / `rollout` / `pass_logic`, defense `defensive_front`); a `Screens` folder adds offense `screen`.
- `gameplan` — applies league rules; needs the pool because rules check per-play attributes that aren't in the `.pln`.

### Rules — external, optional, league-agnostic

No rules ship inside the package. `load_rules(paths)` parses one or more external TOML files into a `Rules` value; later files layer over earlier (per-category replace, scalar overwrite). Rules are validation-only — reading a gameplan never needs them.

- `OffenseCategoryRule(required, min_count, max_count, max_qb_runs_*, max_rollouts_*, max_timed_*)`
- `DefenseCategoryRule(required, min_count, max_count, max_two_dl_*)`
- Aggregate counts over the 64 normal slots: min/max plays per game category + per-category attribute caps; required special categories (1-12, clock categories included); allowed categories; optional `custom_special_play_required` (categories 1-10, the ones with a custom slot).
- `[profile_compatibility]` — `require_all_gameplan_categories_in_profile`, read only by `athc check-ppp` ([check_ppp.md](check_ppp.md)); `validate_gameplan` ignores it.

Section labels are the league's category labels from `league.toml` (`load_rules(paths, labels=...)`) — `[offense.RM]` (Run Middle), `[defense.RunDazzle]` (Razzle Dazzle Run); a category the league does not label is named by its game name, quoted (`[offense."Pass Long Left"]`, `[defense."User Specific"]`). Every per-category key is optional (`required` defaults false, `min_count` 0), but a section must set at least one. The loader rejects unknown labels, subkeys applied to the wrong category type, and an `offense` / `defense` value or section that is not a table. `allowed_offensive_categories` / `allowed_defensive_categories` list, by the league's labels only, the categories a gameplan may contain; a play in any other category is a violation, and an omitted or empty list allows every category.

Each capped attribute (`qb_runs`, `rollouts`, `timed`, `two_dl`) takes one of three forms — `max_<attr>_count` (whole plays), `max_<attr>_ratio` (`"n/m"` only, like `"1/2"`, an exact `Fraction`) or `max_<attr>_percent` (whole number 0-100). A section may set at most one form per attribute; a second is a rules-file error. Ratio and percent compare the exact play ratio, so nothing rounds.

Loading reports every problem at once (`RulesFileError.errors`); any error aborts `check` with each logged (exit 2).

Each league's rule set is `config/release/leagues/<NAME>/gameplan.toml` — data a coach supplies as a file, not code.

### check

`athc gameplan check [PATH]...` walks the PATHs (`.pln` files, folders, wildcards or the four names; the current folder when none is given), builds one `PlayPool` from `play_path`, loads the gameplan `Rules`, and runs `validate_gameplan(read_gameplan(file), rules, pool)` per `.pln`. A name's missing game plan is a failed item. Exit `0` = clean, `1` = violations, `2` = usage/config error. `athc check-ppp` checks your team's game plans with their profiles.

### list-normals / list-specials

`athc gameplan list-normals GAME_PLAN [OUTPUT]` and `list-specials GAME_PLAN [OUTPUT]` read one `.pln` (a path or one of the four names, through `one_game_plan`) and emit play names — no pool or rules. `list-normals` resolves the league like every league-reading command (`--league`, else `[athc] league`) for its category labels; `list-specials` reads the league only for a name. `list-normals` takes `--sort slot|name|category` (slot keeps the 64 positions with blanks; name drops blanks, sorts case-insensitively; category drops blanks and groups the plays in the league's reading order — offense Run Left, Run Middle, Run Right, Pass Short Left/Middle/Right, Pass Medium Left/Middle/Right, Pass Long Left/Middle/Right, Razzle Dazzle Run, Razzle Dazzle Pass, Goal Line Run, Goal Line Pass; defense Run Left, Run Middle, Run Right, Pass Short, Pass Medium, Pass Long, Razzle Dazzle Pass, Razzle Dazzle Run, Goal Line Run, Goal Line Pass; then User Specific — each group under a `:: <label>` header carrying the league's label, else the game name, slot order within a group, no header for an empty category); `list-specials` is source order. Each writes `<name>.normals.txt` / `<name>.specials.txt` next to the `.pln`, or to `OUTPUT`: a folder (one that exists, or a path ending in `\`) gets that name inside it, and a name with no extension gets `.txt` ([architecture.md](architecture.md#output-files)); an existing file is replaced; an `OUTPUT` of `-` prints to stdout (the POSIX convention for `-` as a file). A written file has a `:: <source>` header then the names; the count in the `OK` line leaves out blanks and `::` headers. Exit `0` = ok, `2` = error or usage.

### find-play

`athc gameplan find-play PLAY...` searches one or more case-insensitive names across the normal + custom-special slots of your team's four game plans, or of what `--path` names (a `.pln`, a folder, a tree with `-r`, a wildcard, or one of the four names); every argument is a play. Stock specials and clock plays are skipped. Normal hits read `'NAME' found in slots G-C, G-C` (`slot` for one); a custom-special hit reads `'NAME' found in special slot N (long-cat)`. A set (the four, a folder, a tree, a wildcard) lists hits only, then a per-play summary footer; one file gets its hit or its `not found` line and no footer. Exit codes follow grep: `0` = at least one play found, `1` = none found, `2` = I/O error.

### set-normals / set-specials

`gameplan.writer` resolves a play list against the pool into `.pln` slot entries (`apply_normal_plays` / `apply_special_plays`), aggregating every per-line problem into one `InvalidPlayListError`. Side and special classification come from each play's `.ply` header, not the rules. A play in a stock-only special category (11-12) is rejected per line. The list format is one name per line, `::` comment lines, ` ::` inline trailers; a blank line is an empty entry, and blank lines after the last name are dropped (`parse_play_list`); `read_play_list` reads a list file, and one that is not text (a `.pln` given by mistake) is `FAIL <list>: Not a valid play list.` Input or read failures abort before any write. Each slot's play path is the play pool's folder name, then the play's path inside the pool (`<pool folder>\Offense\RL\OR45RL01.ply`).

- `set-normals GAME_PLAN INPUT_FILE` clears all 64 normal slots of one `.pln` (a path or one of the four names), then fills them in list order: a blank line leaves its slot empty, and a list shorter than 64 lines leaves the slots after it empty. An `INPUT_FILE` of `-` reads the console. The pool comes from the league. No backup is made, and there is no quiet flag (`> nul` hides the `OK` line). Special plays are rejected (`'X' is a special play. Run 'athc gameplan set-specials'.`). Exit `0` = updated, `2` = usage or error.
- `set-specials INPUT_FILE` merges the custom special slots (unlisted categories preserved) of your team's four game plans, or of what `--path` names (one `.pln`, a name, every `.pln` in a folder/tree with `-r`, a wildcard); an `INPUT_FILE` of `-` reads the console. The list is read and counted before the league; blank lines are skipped. Each play self-slots by its special category; wrong-side files are skipped with a `SKIP` line (offense `.pln` are even-sized, defense odd). The pool comes from the league. No backup is made. Exit `0` = all updated, `2` = usage, setup error or a failed file.

### replace-play

`gameplan replace-play PLAY REPLACEMENT...` swaps every instance of `PLAY`
across your team's four game plans, or what `--path` names (one `.pln`, a
name, a folder, a tree with `-r`, a wildcard) — `find-play`'s case-insensitive
search (normal + custom-special slots) plus `set-normals`' pool-resolution.
`PLAY` is a single play (unlike `find-play`, which takes several); the
replacements are tried in order, each a backup for the one before it. Nothing
else is positional. A set (the four, a folder, a tree, a wildcard) gets a
tally and its misses are silent; one file gets its `not found` line. A
replacement listed twice, in any case, is tried once. Every replacement must
resolve in the pool (checked once, up front;
a miss is an error, exit 2); `PLAY` need not (it may already be gone — the
rename case). Only matched slots are swapped (surgical, unlike `set-normals`);
the rest are preserved.

`pick_replacement` chooses per gameplan: a replacement already in it (other
than as `play` itself) is skipped; otherwise it is swapped in memory and the
result validated (`validate_gameplan`). A replacement with which the gameplan
would fail `check` is skipped — so a play in several slots, which becomes a
duplicate, never fits — and the first one with which it passes is written.
None fitting leaves the file untouched (a finding).
The rules are the league's, as `check` reads them (none configured: no league
rule is checked); the pool is built as `check` builds it, so the attribute
caps (rollouts, QB runs, timed, 2-DL) apply. The `GamePlan` model still validates each swap (side parity; a special
play's category must match its slot); a refused swap fails that file
(reported, not written), after the `SKIP` lines before it, and names the
replacement when several are listed (`FAIL <file>: 'NEW' does not fit:
<why>`). No backup is made.

Output uses the short game-category label. A play's normal-slot hits collapse to
one line, slots bracketed in order at the end: `<file>: 'OLD' (cat) replaced with
'NEW' (cat) [1-3][4-2]` (a play can fill many normal slots). Special hits print one
line each: `<file>: Replaced 'OLD' (cat) in special slot N with 'NEW' (cat)`
(`special slot N` like `find-play`; a play fills only one special slot). A
skipped replacement prints `SKIP <file>: 'NEW' already in the game plan`, or
`SKIP <file>: 'NEW' fails check: [cat] message` once per violation (the
`check` text, from the shared `format_violation`); a gameplan none fits prints
`<file>: 'OLD' not replaced, no valid replacement`.

### Exit codes

Each command's lines and codes: [usage/gameplan.txt](../usage/gameplan.txt). Two classes (see
[architecture.md](architecture.md#exit-codes)): `check`, `find-play`
and `replace-play` bear a **findings** tier; `list-normals`, `list-specials`,
`set-normals` and `set-specials` are utilities (a failed file is exit 2).

### .pln format

G95 (plays + 86 offsets), J95 (profile_type + counts), S98 (`STOCK98.MAP\0`); size parity even = offense / odd = defense. Byte-level docs: [formats/pln.md](../formats/pln.md).
