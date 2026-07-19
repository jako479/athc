# playpool — Architecture

Builds a league's play pool from a directory of FbPro '98 `.ply` files: parses
each play and classifies it into a typed record. **Side and category come from
the play file itself**, so any layout works — a PNFL tree, an arbitrary tree, or
a flat directory. Folders are optional and only add what the bytes can't encode.

## Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── records.py    # Play + Offensive/Defensive/SpecialTeams subclasses; enums
├── rules.py      # FilenameFilter, PlaypoolRules, load_rules (filename filters)
└── pool.py       # PlayPool, read_play_pool: walk, classify, index; folder_warnings
```

## What this package does

- `read_play_pool(root, *, rules=None)` → `PlayPool`: walks `root/**/*.ply`,
  parses each via `fbpro98_play`, classifies, indexes by name (case-insensitive).
- Classifies each play **from its file**:
  - side from the category bytes (`is_offensive` / `is_defensive` /
    `is_special_teams`);
  - `category` (an `fbpro98_play` enum member, `UNKNOWN_CATEGORY` if unrecognized)
    from the play's `user_category`; run/pass is `category.is_run` / `category.is_pass`.
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
command, exit 2). PNFL category folders are matched against the league short
labels on `fbpro98_play`'s category enum (via `category_by_short`); only these
filename filters are league data. The shipped set is
`release/rules/PNFL.playpool.toml`.

## What this package enforces / does NOT do

- Invalid `.ply` files are logged and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root (and optional rules
  path) and passes them in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

## Testing

- `tests/unit/playpool/` — rules parsing + `FilenameFilter.matches`; file-driven
  classification over three layouts (PNFL / non-PNFL / flat); folder attributes;
  mismatch warnings; record classes.
- Matrix: `tests/unit/playpool/README.md`.
