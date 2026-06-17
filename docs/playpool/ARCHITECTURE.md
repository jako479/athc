# playpool — Architecture

Builds a league's play pool from a directory tree of FbPro '98 `.ply` files:
parses each play and classifies it into a typed record. The **folder names** below
are a fixed convention (PNFL's) baked into the code — every pool must use them;
only the **filename filters** are league data, supplied in a rules TOML.

## Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── records.py    # PlayRecord + Offensive/Defensive/SpecialTeams subclasses; enums; play_type
├── rules.py      # FilenameFilter, PlaypoolRules, load_rules (filename filters)
└── pool.py       # PlayPool, read_play_pool: walk tree, classify, index
```

## What this package does

- `read_play_pool(root, *, rules=None)` → `PlayPool`: walks `root/**/*.ply`,
  parses each via `fbpro98_play`, classifies, indexes by name (case-insensitive).
- Classifies by **folder** — these names are required, not configurable:
  - side from an `Offense` / `Defense` / `Special` ancestor folder;
  - pool category from the play's folder (e.g. `PSM`, `RunLeft`);
  - offense `screen` (a `Screens/` subfolder; category from its parent);
  - defense `defensive_front`: folder prefix `34` → 3-4, `43` → 4-3 (category is the
    rest, e.g. `34RunLeft` → Run Left); a `R&SDefs/` ancestor → 2-DL.
- And by **filename**, via the rules' `FilenameFilter`s (gated by pool category):
  - offense pass categories: `rollout`, `pass_logic` (Timed via `TimedPass`, else
    Check Receivers); offense run categories: `qb_draw` (`QBRun`). With no rules,
    these stay off.

## Records — fixed, typed attributes

`PlayRecord` (base: `name`, `play_file`; `category` / `play_type` from the play's
`user_category`). Subclasses add real fields:

- `OffensivePlayRecord`: `pool_category`, `screen`, `rollout`, `qb_draw`,
  `pass_logic`, plus `is_run` / `is_pass`.
- `DefensivePlayRecord`: `pool_category`, `defensive_front`.
- `SpecialTeamsPlayRecord`: nothing beyond the base.

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
command, exit 2). A league with the same folder
layout but different play names just edits these filters; the shipped set is
`release/rules/PNFL.playpool.toml`.

## What this package enforces / does NOT do

- Invalid `.ply` files are logged and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root (and optional rules
  path) and passes them in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

## Testing

- `tests/unit/playpool/` — rules parsing + `FilenameFilter.matches`, classification
  over committed play-tree fixtures, record classes.
- Matrix: `tests/unit/playpool/README.md`.
