# pdbtoexcel — Architecture

`athc convert-pdb` — converts a WinLogStats `.pdb` (and optional FbPro '98 game
plans) into an Excel workbook. League-agnostic: plays are grouped by their own
**game** category; nothing PNFL-specific is baked in.

## Layout

```
src/athc/pdbtoexcel/       # tool logic (no Click)
├── __init__.py          # public API
├── config.py            # [convert-pdb] from athc.ini; default category order
├── pdb.py               # PDB binary format (ctypes) + parser
├── excel_workbook.py    # ExcelPdbWorkbook — xlsxwriter layouts + row writers
├── workbook_creator.py  # PdbWorkbookCreator — joins PDB stats to the play pool
├── main.py              # convert_pdb() orchestration
└── resources/           # vbaProject*.bin — XLSM macro blocks (package data)

src/athc/cli/convert_pdb.py   # Click leaf command
```

`specs/pdb.md` documents the on-disk byte layout.

## What it does

- Parses a WinLogStats `.pdb` into per-team per-play stats + down/distance tendencies.
- Builds a `playpool.PlayPool` from `--play-path` (with an optional playpool rules
  TOML of filename filters). Joins each PDB play to its pool record by name.
- Groups / sorts plays by their **game category** (`PlayRecord.category`, e.g.
  "Pass Short Left"); the row order + Options sheet come from a default order built
  from the game's own category vocabulary (`config.default_category_order`).
- Optionally cross-references up to two offensive + two defensive `.pln` game plans
  for the Slot columns.
- Writes `.xlsx` (plain) or `.xlsm` (with the VBA sort macros from `resources/`).

## League-agnostic notes

- No `pool_category` / PNFL labels: grouping is by game category. The "Type" column
  reads the typed playpool attributes (`qb_draw`, `screen`, `defensive_front`) the
  pool sets from folder/filename; special-teams plays leave it blank.
- Dropped from the pnfl version: the PNFL `TOTAL_STATS_FILTER` thresholds and
  `DELETED_PLAYS` (both league data, and the filter was already unreachable).

## Config

`[convert-pdb]` in `athc.ini`: `play_path`, `playpool_rules` (optional),
`calculate_total_stats`, `calculate_percentages`, `include_category_worksheets`,
`exclude_sacks_from_pass_attempts`. `--play-path` / `--playpool-rules` / `--config`
override. play_path must resolve to a real directory at runtime.

## CLI

`athc convert-pdb PDB.pdb OUT.{xlsx,xlsm} [-o/-o2 OFF.pln] [-d/-d2 DEF.pln] [--play-path DIR] [--playpool-rules R.toml] [--config INI] [--skip-calcs] [--skip-totals]`.
Extensions are validated (`.pdb` / `.xlsx`,`.xlsm` / `.pln` / `.toml` / `.ini`).
Exit 0 ok / 1 input or I/O error / 2 usage.

## Out of scope

- Parsing `.ply` / `.pln` (delegated to `playpool` / `fbpro98_gameplan`).
- Non-Excel output; rebuilding the VBA `.bin` blobs.

## Tests

- `tests/unit/pdbtoexcel/` — PDB parsing (real fixture + snapshot), config, workbook
  creation (synthetic PDB + injected pool, read back with openpyxl).
- `tests/integration/test_convert_pdb.py` — CLI end-to-end.
