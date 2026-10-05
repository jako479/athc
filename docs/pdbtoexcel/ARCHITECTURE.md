# pdbtoexcel — Architecture

`athc convert-pdb` — converts a WinLogStats `.pdb` (and optional FbPro '98 game
plans) into an Excel workbook. League-agnostic: plays are grouped by their own
**game** category; the playpool rules are league data in each league's
`rules\playpool.toml`.

## Layout

```
src/athc/pdbtoexcel/       # tool logic (no Click)
├── __init__.py          # public API
├── config.py            # play_path + playpool rules from the league folder; default category order
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
- Groups / sorts plays by their **game category** (`Play.category`, e.g.
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

The league folder `leagues\<NAME>\`: `play_path` from `league.ini` and the
optional `rules\playpool.toml`. `--play-path` / `--playpool-rules` override; the
league is resolved unless both are given, so `--play-path` alone still reads
the league's rules. Playpool rules resolve as `--playpool-rules`, else the
league's `rules\playpool.toml`, else none. `play_path` must resolve to a real
directory at runtime. The workbook options (`calculate_total_stats`,
`calculate_percentages`, `include_category_worksheets`,
`exclude_sacks_from_pass_attempts`) are app-wide settings in `[convert-pdb]` in
`athc.ini`, read through `athc.config.load_config()` without resolving a league;
a missing key takes the `Config` default, a non-boolean value is a
`ConfigFileError`.

## CLI

`athc convert-pdb PDB.pdb OUT.{xlsx,xlsm} [-o/-o2 OFF.pln] [-d/-d2 DEF.pln] [--play-path DIR] [--playpool-rules R.toml] [--skip-calcs] [--skip-totals]`. `athc --league NAME` before the command picks the league.
Extensions are validated (`.pdb` / `.xlsx`,`.xlsm` / `.pln` / `.toml` / `.ini`).

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — workbook written. |
| `1` | **Error** — input or I/O error (missing/invalid PDB, bad play path). |
| `2` | **Usage** — bad arguments or extensions. |

## Out of scope

- Parsing `.ply` / `.pln` (delegated to `playpool` / `fbpro98_gameplan`).
- Non-Excel output; rebuilding the VBA `.bin` blobs.

## Tests

- `tests/unit/pdbtoexcel/` — PDB parsing (real fixture + snapshot), config, workbook
  creation (synthetic PDB + injected pool, read back with openpyxl).
- `tests/integration/test_convert_pdb.py` — CLI end-to-end.
