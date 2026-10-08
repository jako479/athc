# pdbtoexcel — Architecture

`athc convert-pdb` — converts a WinLogStats `.pdb` (and optional FbPro '98 game
plans) into an Excel workbook. Plays are grouped by their category (from the
play file) and shown under the league's name for it; the category names, their
order, the deleted plays and the playpool rules are league data in the league
folder.

## Layout

```
src/athc/pdbtoexcel/       # tool logic (no Click)
├── __init__.py          # public API
├── config.py            # play_path, labels, playpool rules + pdbtoexcel.toml (order, deleted plays) from the league folder
├── pdb.py               # PDB binary format (ctypes) + parser
├── excel_workbook.py    # ExcelPdbWorkbook — xlsxwriter layouts + row writers
├── workbook_creator.py  # PdbWorkbookCreator — joins PDB stats to the play pool
├── main.py              # convert_pdb() orchestration
├── resources/           # vbaProject*.bin — XLSM macro blocks (package data)
└── excel-template/      # master .xlsm workbooks the .bin blocks are extracted from (not shipped)

src/athc/cli/convert_pdb.py   # Click leaf command
```

`specs/pdb.md` documents the on-disk byte layout; `specs/pdb.hexpat` (ImHex) and
`specs/pdb.hsl` (Hex Workshop) are the matching patterns.

## What it does

- Parses a WinLogStats `.pdb` into per-team per-play stats + down/distance tendencies.
- Builds a `playpool.PlayPool` from the league's `play_path` (with the league's
  category labels and an optional playpool rules TOML of filename filters). The
  rules' include / exclude names are checked against the pool
  (`playpool.rule_warnings`); each problem is logged as a warning. Joins each PDB
  play to its pool record by name.
- Groups / sorts plays by their category (`Play.category`), written as the
  league's label (`CategoryLabels.label`, the game name where the league has
  none). The row order within each team and the Options sheet lists are the
  league's `[category_order]` from `pdbtoexcel.toml`; a category not listed for
  its PDB play type is left out of the workbook.
- Skips a play named in `[deleted_plays]` with one info line instead of the
  "Play file not found" warning; one still in the pool is also skipped, with a
  warning that the entry is stale.
- Optionally cross-references up to two offensive + two defensive `.pln` game plans
  for the Slot columns.
- Always adds a Total Stats team summing every team.
- Writes `.xlsx` (plain) or `.xlsm` (with the VBA sort macros from `resources/`).

## PDB parser

`pdb.py`, internal to the tool:

- `PDB(filename)` parses the file on construction.
- `plays`: dict keyed by `PLAY_DATA.PLAY_TYPE`, then by `(team, play)`, holding a
  `PLAY_DATA`; `tendencies`: list of `TENDENCY_DATA`, sorted by team.
- Duplicate `(team, play)` records within one play type are summed
  (`PLAY_DATA.__iadd__`).
- `RUNCLOCK` and `STOPCLOK` records are dropped; names in `RENAMED_PLAYS` are
  rewritten on load (`WR47PT01` → `WR27PT01`, `WR48PT01` → `WR28PT01`).
- `InvalidPDBError`: a bad record-type byte.
- `convert_invalid_play_data(play_pool)` moves offensive run/pass records the
  engine logged under the wrong play type, judged by the pool's category
  (`specs/pdb.md` section 4).

## League data, not code

- The category names and their order, the deleted plays and the play tags are
  the league's files; nothing league-specific is in the code. The "Type" column
  reads the typed playpool attributes (`qb_draw`, `screen`, `defensive_front`)
  the pool sets from folder/filename; special-teams plays leave it blank.
- Not carried over from PdbToExcel: its `TOTAL_STATS_FILTER` thresholds and
  check (never reachable there; what to do with that filtering is a TODO item).

## Config

The league folder `leagues\<NAME>\`: `play_path` and the category labels from
`league.toml`, the optional `playpool.toml` (none when absent) and
`pdbtoexcel.toml`, which is required (`config.read_pdbtoexcel_toml`):

- `[category_order]`: `run`, `pass` and `defense`, each an array of category
  names for that side — a labeled category by its label, an unlabeled one by its
  game name, like the gameplan rule files. A missing key, a name that is not a
  category of that side (a pass category under `run` says so), a repeat, or a
  wrong type is a `ConfigFileError`; an empty array exports nothing of that
  type.
- `[deleted_plays] names`: optional array of play names, matched
  case-insensitively.

`Config.category_order` holds the resolved enum members per PDB play type;
`Config.categories` the league's `CategoryLabels`; `Config.deleted_plays` the
names as written (matched case-insensitively, reported as written). The league
is always resolved; no command-line option
replaces its play pool or rules. `play_path` must resolve to a real directory
at runtime. The workbook options (`calculate_percentages`,
`include_category_worksheets`, `exclude_sacks_from_pass_attempts`) are app-wide
settings in `[convert-pdb]` in `athc.ini`, read through
`athc.config.load_config()`; a missing key takes the `Config` default, a
non-boolean value is a `ConfigFileError`.

## CLI

`athc convert-pdb pdb_file output_file [-o/-o2 pln_file] [-d/-d2 pln_file] [--skip-calcs] [--league name]`. `--league` picks the league.
Extensions are validated (`.pdb` / `.xlsx`,`.xlsm` / `.pln`).

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — workbook written. |
| `1` | **Error** — input or I/O error (missing/invalid PDB, bad play path, an output folder that can't be created, a bad or missing `pdbtoexcel.toml`). |
| `2` | **Usage** — bad arguments or extensions. |

## Out of scope

- Parsing `.ply` / `.pln` (delegated to `playpool` / `fbpro98_gameplan`).
- Non-Excel output. The VBA `.bin` blocks are rebuilt by hand from the
  `excel-template/` workbooks; its README has the steps.

## Tests

- `tests/unit/pdbtoexcel/` — PDB parsing (real fixture + snapshot), config
  (`pdbtoexcel.toml` on both sides of every rule, the shipped files), workbook
  creation (synthetic PDB + injected pool, read back with openpyxl: labels,
  order, unlisted and deleted plays).
- `tests/unit/playpool/test_rule_warnings.py` — the include / exclude checks.
- `tests/integration/test_convert_pdb.py` — CLI end-to-end, plus a golden
  workbook: the real `.pdb` converted against the curated pool, the PNFL labels
  and order and both game plans, every cell compared to
  `expected/2045-2047.workbook.json`.
