# playpool — Architecture

Builds a league's play pool from a directory of FbPro '98 `.ply` files: parses
each play and classifies it into a typed record. **Side and category come from
the play file itself**, so any layout works — a PNFL tree, an arbitrary tree, or
a flat directory. Folders are optional and only add what the bytes can't encode.

## Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── model.py      # Play + Offensive/Defensive/SpecialTeams subclasses; enums; PlayPool
├── rules.py      # FilenameFilter, PlaypoolRules, load_rules (filename filters)
└── reader.py     # read_play_pool: walk, classify, add to the pool; folder_warnings; rule_warnings
```

## What this package does

- `read_play_pool(root, *, rules=None, labels=None)` → `PlayPool`: walks
  `root/**/*.ply` in sorted path order, parses each via `fbpro98_play`,
  classifies, indexes by name (case-insensitive; of two same-named plays the
  later in that order wins).
- Classifies each play **from its file**:
  - side from the category bytes (`is_offensive` / `is_defensive` /
    `is_special_teams`);
  - `category` (an `fbpro98_play` enum member; a file with an unrecognized
    category is skipped) from the play's `user_category`; run/pass is `category.is_run` / `category.is_pass`.
- Reads optional **PNFL folder** attributes the file can't carry:
  - offense `screen` — a `Screens/` folder;
  - defense `defensive_front` — `34…` → 3-4, `43…` → 4-3, an `R&SDefs/`
    ancestor → 2-DL.
- Reads optional **filename** attributes via the rules' `FilenameFilter`s:
  offense `rollout`, `qb_draw`, `pass_logic` (Timed via `TimedPass`, else Check
  Receivers). With no rules these stay off.
- **Warns** (never reclassifies) when a play sits in a recognized PNFL folder
  that contradicts its file: a wrong side, or — when the side matches — a category
  differing from the folder's. Each warning ends with the play's path, e.g.
  `Pass Short Left play in a Pass Medium Left folder: Offense/PML/X.ply`. A wrong
  side is reported alone; unrecognized folders (flat / non-PNFL) never warn. A
  category with no PNFL folder (`User Specific`, Pass Long Left/Middle, Razzle
  Dazzle Run) warns only when filed inside a category folder, not when loose.
- Keeps every warning it logs (folder mismatches, duplicate names, invalid or
  unreadable files) in `PlayPool.issues`, word for word, so `playpool check`
  can print and count them.
- `rule_warnings(pool, rules)` checks the exact names a rules file lists under
  `include` / `exclude` against a built pool: not in the pool, a play the
  section cannot apply to (wrong side), or under both lists of one section. It
  returns the lines; the caller decides whether to log them (`convert-pdb`
  does; `read_play_pool` and `playpool check` do not call it).

## Records — fixed, typed attributes

`Play` (base): `name`, `play_file`; `category` (the `fbpro98_play` enum
member) from the play file. Subclasses add:

- `OffensivePlay`: `screen`, `rollout`, `qb_draw`, `pass_logic`.
- `DefensivePlay`: `defensive_front`.
- `SpecialTeamsPlay`: nothing beyond the base.

Enums: `PassLogic` (Timed, Check Receivers); `DefensiveFront` (3-4, 4-3, 2-DL,
where 2-DL is the Run-and-Shoot front).

## Rules (rules.py)

`load_rules(path)` parses a TOML of filename filters into a `PlaypoolRules` —
one `FilenameFilter` per filename-derived attribute (`[TimedPass]`,
`[RolloutPass]`, `[QBRun]`). Each filter is **case-sensitive**: a name matches
when it hits ANY of `suffix_any` / `regex_any` / `include` and NONE of
`suffix_none` / `regex_none` / `exclude` (vetoes win). Unknown section/key, bad
regex, or wrong types raise `RulesFileError`; the loader reports every problem at
once (`RulesFileError.errors`) and any error aborts the caller (the gameplan
command, exit 2). Category folders are matched against the league's labels
(`CategoryLabels`, passed to `read_play_pool` / `folder_warnings`), the play's
own side first; the filename filters and the labels are league data. The shipped set is
`config/release/leagues/PNFL/playpool.toml`.

## What this package enforces / does NOT do

- Invalid and unreadable `.ply` files are logged and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root (and optional rules
  path) and passes them in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

## Testing

- `tests/unit/playpool/` — rules parsing + `FilenameFilter.matches`; file-driven
  classification over three layouts (PNFL / non-PNFL / flat); folder attributes;
  mismatch warnings; `issues`; record classes.
- Matrix: `tests/unit/playpool/README.md`.
