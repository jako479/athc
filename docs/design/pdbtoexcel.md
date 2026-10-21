# pdbtoexcel

Export a WinLogStats database (`.pdb`) — FbPro '98 game stats — to an Excel
workbook. Built on `playpool` (play classification) and `fbpro98_gameplan`
(`.pln` parsing).

Usage, the Slot columns, settings, lines and exit codes: [usage/convert-pdb.txt](../usage/convert-pdb.txt).

## How it works

### Layout

```
src/athc/pdbtoexcel/       # tool logic (no Click)
├── __init__.py          # public API
├── config.py            # play_path and labels from the league folder; [convert-pdb] from athc.toml under league.toml
├── pdb.py               # PDB binary format (ctypes) + parser
├── excel_workbook.py    # ExcelPdbWorkbook — xlsxwriter layouts + row writers
├── workbook_creator.py  # PdbWorkbookCreator — joins PDB stats to the play pool
├── main.py              # convert_pdb() orchestration
├── resources/           # vbaProject*.bin — XLSM macro blocks (package data)
└── excel-template/      # master .xlsm workbooks the .bin blocks are extracted from (not shipped)

src/athc/cli/convert_pdb.py   # Click leaf command: config, team, game plans
src/athc/cli/_team.py         # shared team layer: league files, team, file locations
```

`formats/pdb.md` documents the on-disk byte layout; `formats/pdb.hexpat` (ImHex) and
`formats/pdb.hsl` (Hex Workshop) are the matching patterns.

### What it does

- Parses a WinLogStats `.pdb` into per-team per-play stats + down/distance tendencies.
- Builds a `playpool.PlayPool` from the league's `play_path` (with the league's
  category labels). Joins each PDB play to its pool record by name.
- Groups / sorts plays by their category (`Play.category`), written as the
  league's label (`CategoryLabels.label`, the game name where the league has
  none). The row order within each team and the Options sheet lists are
  `[convert-pdb.category_order]`; a category not listed for its PDB play type
  is left out of the workbook.
- Skips a play named in `deleted_plays` quietly instead of the
  "is not in the play pool" warning; one still in the pool is also
  skipped, with a warning, naming the file the list came from, that the
  entry is stale.
- Every message about a setting names the file its value came from
  (`athc.toml` or the league's `league.toml`).
- Fills the Slot columns from game plans: with no game plan option, your
  team's four from the league file (Slot 1 the 1st-half plan, Slot 2 the
  2nd-half plan, per side); with any of `-o`, `-o2`, `-d`, `-d2`, only the
  files given, and the league file is not read.
- Hides each Slot column whose own plan is absent; both halves of a side on
  one file fill Slot 1 alone.
- Checks each plan's side: a named plan on the wrong side fails the run; one
  from the league file is a warning and its column is hidden, as is one that
  is missing or can't be read.
- Always adds a Total Stats team summing every team.
- Writes `.xlsx` (plain) or `.xlsm` (with the VBA sort macros from `resources/`).
- In an `.xlsm`, the macros set the workbook name `HighlightRow` to the
  selected row, and a conditional format on every data sheet outlines that
  row; it starts at 0, so nothing is outlined until a cell is selected.
- The Options sheet holds the category order lists (named
  `RunCategoryOrder`, `PassCategoryOrder`, `DefenseCategoryOrder` for the
  sort macros) and the sorting notes.

### PDB parser

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
  (`formats/pdb.md` section 4).

### League data, not code

- The category names are the league's file and their order and the deleted
  plays are settings, a league's own where it differs; nothing league-specific
  is in the code. The "Type" column reads the
  typed playpool attributes (`qb_run`, `screen`, `defensive_front`): `screen`
  from the play's folder, the others from its play file; special plays
  leave it blank.
- Not carried over from PdbToExcel: its `TOTAL_STATS_FILTER` thresholds and
  check (never reachable there; what to do with that filtering is a TODO item).

### Config

- `load_config` reads `layered_settings("convert-pdb", league)`: athc.toml's
  `[convert-pdb]` with the league's laid over it a key at a time, and the file
  each key came from, which every message names.
- `[convert-pdb.category_order]`: `run`, `pass` and `defense`, each an array of
  category names for that side — a labeled category by its label, an unlabeled
  one by its game name, like the gameplan rule files. A missing list is empty
  (nothing of that type exported, like an empty array); a name that is not a
  category of that side (a pass category under `run` says so), a repeat, or a
  wrong type is a `ConfigFileError`. A list the league replaces is never
  checked.
- `deleted_plays`: optional array of play names, matched case-insensitively;
  `Config.deleted_plays_file` is the file it came from, for the stale-entry
  warning.
- An unknown key in `[convert-pdb]` or its `category_order` is a
  `ConfigFileError` naming the file that has it.

`Config.category_order` holds the resolved enum members per PDB play type;
`Config.categories` the league's `CategoryLabels`; `Config.deleted_plays` the
names as written (matched case-insensitively, reported as written). The league
is always resolved; no command-line option
replaces its play pool. `play_path` must resolve to a real directory
at runtime. The workbook options (`calculate_percentages`,
`include_category_worksheets`, `exclude_sacks_from_pass_attempts`) are TOML
booleans; a missing key takes the `Config` default, any other value is a
`ConfigFileError`.

The command loads the config: `load_config(league)` and `play_dir` run before
the team, so a bad `play_path` or `[convert-pdb]` setting shows first; `convert_pdb()`
takes the loaded `Config`, the four game plans already read (`GamePlan | None`)
and `percentages` (None takes `calculate_percentages`). The `[league]` keys
`team`, `path` and `ppp_path` come from `load_league_config(league)`, read by
the command through the shared team layer (`src/athc/cli/_team.py`), as
check-ppp does.

### CLI

`athc convert-pdb [OPTIONS] PDB_FILE [OUTPUT]` with `-o`, `-o2`, `-d`,
`-d2 GAME_PLAN`, `--path FOLDER`, `--team NAME`,
`--percentages/--no-percentages` and `--league NAME`. Extensions are validated
(`.pdb` / `.xlsx`,`.xlsm` / `.pln`); `--team` or `--path` with a game plan
option is a usage error. `OUTPUT` follows the rules in
[architecture.md](architecture.md#output-files).

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — workbook written (warnings included). |
| `2` | **Error or usage** — a missing or invalid PDB or named game plan, a named plan on the wrong side, bad play path, a bad `[convert-pdb]` setting, a bad `team`, `path` or `ppp_path` or league file, an output that can't be written; bad arguments or extensions. |

### Out of scope

- Parsing `.ply` / `.pln` (delegated to `playpool` / `fbpro98_gameplan`).
- Non-Excel output. The VBA `.bin` blocks are rebuilt by hand from the
  `excel-template/` workbooks; its README has the steps.

### Tests

- `tests/unit/pdbtoexcel/` — PDB parsing (real fixture + snapshot), config
  (every key from athc.toml alone, from league.toml alone and mixed a key at
  a time, each message naming its file, the shipped files), workbook
  creation (synthetic PDB + injected pool, read back with openpyxl: labels,
  order, unlisted and deleted plays, Slot columns by presence, filter ranges,
  the Options sheet's names, the row highlight).
- `tests/integration/test_convert_pdb.py` — CLI end-to-end (the default
  output, the options, the team's game plans from each source, the setting
  errors), plus a golden workbook: a real week's `.pdb` (`48W17.pdb`)
  converted against its own play pool, which holds every play in it, the PNFL
  labels and order and both game plans, every cell compared to
  `expected/48W17.workbook.json`.
