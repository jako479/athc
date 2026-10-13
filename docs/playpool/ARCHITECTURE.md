# playpool — Architecture

Builds a league's play pool from a directory of FbPro '98 `.ply` files: parses
each play and classifies it into a typed record. **Side, category and the play
attributes come from the play file itself**, so any layout works — a PNFL tree,
an arbitrary tree, or a flat directory. Folders are optional and only add what
the bytes can't encode.

## Module layout

```
src/athc/playpool/
├── __init__.py   # public API re-exports
├── model.py      # Play + Offensive/Defensive/SpecialTeams subclasses; PassLogic; PlayPool
└── reader.py     # read_play_pool: walk, classify, add to the pool; folder_warnings
```

## What this package does

- `read_play_pool(root, *, labels=None)` → `PlayPool`: walks
  `root/**/*.ply` in sorted path order, parses each via `fbpro98_play`,
  classifies, indexes by name (case-insensitive; of two same-named plays the
  later in that order wins).
- Classifies each play **from its file**:
  - side from the category bytes (`is_offensive` / `is_defensive` /
    `is_special_teams`);
  - `category` (an `fbpro98_play` enum member; a file with an unrecognized
    category is skipped) from the play's `user_category`; run/pass is `category.is_run` / `category.is_pass`;
  - offense `qb_run` (run plays), `rollout` and `pass_logic` (pass plays) from
    the `PlayFile`'s `is_qb_run`, `is_rollout(ROLLOUT_MARGIN)` and
    `is_timed_pass` (Timed, else Check Receivers);
  - defense `defensive_front` from the `PlayFile`.
- Reads the one optional **PNFL folder** attribute the file can't carry:
  offense `screen` — a `Screens/` folder.
- **Warns** (never reclassifies) when a play sits in a recognized PNFL folder
  that contradicts its file: a wrong side, or — when the side matches — a category
  differing from the folder's. Each warning starts with the play's path, e.g.
  `Offense/PML/X.ply: Pass Short Left play in a Pass Medium Left folder.`. A wrong
  side is reported alone; unrecognized folders (flat / non-PNFL) never warn. A
  category with no PNFL folder (`User Specific`, Pass Long Left/Middle, Razzle
  Dazzle Run) warns only when filed inside a category folder, not when loose.
- Keeps every warning it logs (folder mismatches, duplicate names, invalid or
  unreadable files) in `PlayPool.issues`, word for word, so `playpool check`
  can print and count them.

## Records — fixed, typed attributes

`Play` (base): `name`, `play_file`; `category` (the `fbpro98_play` enum
member) from the play file. Subclasses add:

- `OffensivePlay`: `screen`, `rollout`, `qb_run`, `pass_logic`.
- `DefensivePlay`: `defensive_front`.
- `SpecialTeamsPlay`: nothing beyond the base.

Enums: `PassLogic` (Timed, Check Receivers); `defensive_front` is an
`fbpro98_play` `DefensiveFront` (3-4, 4-3, 2-DL, where 2-DL is the
Run-and-Shoot front).

Category folders are matched against the league's labels (`CategoryLabels`,
passed to `read_play_pool` / `folder_warnings`), the play's own side first; the
labels are league data.

## What this package enforces / does NOT do

- Invalid and unreadable `.ply` files are logged and skipped, never raised.
- No CLI or config reads — the caller resolves the pool root and passes it in.
- No `.ply` byte parsing or `.pln`/`.prf` I/O (other libraries).

## Testing

- `tests/unit/playpool/` — file-driven classification over three layouts
  (PNFL / non-PNFL / flat); attributes from the play file (rollout margin,
  category gates); folder attributes; mismatch warnings; `issues`; record
  classes.
- Matrix: `tests/unit/playpool/README.md`.
