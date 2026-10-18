# pdbtoexcel

Export a WinLogStats database (`.pdb`) — FbPro '98 game stats — to an Excel
workbook. Built on `playpool` (play classification) and `fbpro98_gameplan`
(`.pln` parsing).

## Command

```bash
athc convert-pdb 49W6.pdb
athc convert-pdb 49W6.pdb reports\week6.xlsx
athc convert-pdb 49W6.pdb --team Broncos
athc convert-pdb 49W6.pdb -o try3.pln -o2 plans\DEN-OGP1.pln
athc convert-pdb 49W5.pdb --path plans\wk5
athc convert-pdb 2045-2047.pdb --no-percentages --league PCFL
for %f in (*.pdb) do athc convert-pdb "%f"
```

- One PDB per run; the Windows `for` loop above converts several.
- The workbook is `OUTPUT`, else the PDB's name with `.xlsm`, beside the PDB.
  A folder (one that exists, or a path ending in `\`) gets that name inside
  it; a name with no extension gets `.xlsm`. Missing folders are created; an
  existing file is replaced.
- `.xlsm` has the sorting macros and outlines the selected row; `.xlsx` is
  plain. Excel opens an `.xlsm`
  with its macros disabled until you click Enable Content, and a copy sent by
  email opens with them blocked (unblock it in the file's Properties, or send
  an `.xlsx`).
- The workbook always includes the Total Stats team.
- `--percentages` / `--no-percentages` turn the percentage columns on or off
  for one run, over `calculate_percentages` in `athc.toml`.

Plays are grouped by their category, shown under the league's name for it
(`PSL`, `RunLeft`) and sorted in the league's order.

### Slot columns

Slot 1 and Slot 2 show where each play sits in your team's 1st- and 2nd-half
game plans, per side.

| Game plan options | `--path` | The plans come from | A missing plan |
|---|---|---|---|
| any of `-o`, `-o2`, `-d`, `-d2` | not allowed | the files given; the other columns hidden | `FAIL`, exit 2 |
| none | a folder | that folder, each plan by its league-file name, without case | `WARN`, its column hidden |
| none | none; `ppp_path` set, your team | `ppp_path`, the same way | `WARN`, its column hidden |
| none | none | where the game reads them: `path` joined with the `.lg2` folder | `WARN` with the `ppp_path` hint, its column hidden |
| none, no team | none | nothing | the Slot columns hidden, no line |

- The team is `team` in `league.toml`, or `--team NAME` for one run: its name,
  nickname or both, without case. `--team` and `--path` cannot be used with a
  game plan option.
- `ppp_path` is for your team only (the one `team` names).
- `--path` is a folder; its subfolders are not searched.
- Each plan taken from the league file prints a line:
  `<path>: Denver 1st-half offense, Slot 1`. One plan for both halves fills
  Slot 1 alone: `<path>: Las Vegas offense, both halves, Slot 1`.
- A plan on the wrong side is `Not an offense game plan.` (or defense): a
  `FAIL` when named, a `WARN` with its column hidden when taken from the
  league file. So is one that can't be read.
- None of the team's plans in a folder is one `WARN`
  (`No Denver game plans. ...`), not four.
- `athc gameplan check` checks the game plans; convert-pdb only reads their
  slots.

### Lines and exit codes

- Progress on stderr: the game plans' lines, then `Creating <workbook>`.
- A `WARN` line per notice (a missing game plan, a play not in the
  play pool, a stale `deleted_plays` entry, invalid PDB data, a play-pool
  issue), each naming its file first where one is to blame; then
  `OK   <workbook>: <n> play(s)`. `athc playpool check` lists the play-pool
  issues on their own, with an exit code.
- A setting that is wrong (`team`, `path`, `ppp_path`, the league files, a
  `[convert-pdb]` key) is a `FAIL` naming the file it came from, as in [check-ppp](check_ppp.md); without
  `path` the line suggests a game plan option instead.
- Exit 0 done (warnings included), 2 on an error (a missing or bad file,
  config, no `play_path`, I/O) or usage (bad extension, `--team` with `-o`,
  etc.); `FAIL <why>` names the problem. Shared console and codes:
  [architecture](architecture.md#console-run-log-and-errors).

## Config

The league folder `leagues\<NAME>\` (picked by `--league` /
`[athc] league`; see [architecture.md](architecture.md#config)):

- `league.toml`: `play_path` (the `.ply` pool, required) and the league's
  category names (`[categories.*]`); for the Slot columns, `team` (your team),
  `path` (the folder with the league's `.lg2` and `.lge`) and, optionally,
  `ppp_path` (where you keep your game plans).

The Type column comes from the play pool: QB run and the defensive front from
each play file, Screen from a `Screens` folder.

The settings are `[convert-pdb]` in `athc.toml`:

```toml
[convert-pdb]
calculate_percentages = true
exclude_sacks_from_pass_attempts = false
# Plays removed from the league's play pool: their stat lines are skipped
# quietly instead of warning "Play file not found".
deleted_plays = ["ATF0ELOB"]

# The order of the play categories in the workbook, named by the league's
# category names from league.toml (the game name for a category the league
# leaves unnamed). A category not listed stays out of the workbook.
[convert-pdb.category_order]
run = ["RL", "RM", "RR", "GLR"]
pass = ["PSL", "PSM", "PSR", "PML", "PMM", "PMR", "PLR", "PRD", "GLP"]
defense = ["RunLeft", "RunMiddle", "RunRight", "RunDazzle", "PassShort", "PassMedium", "PassLong", "PassDazzle", "GLrun", "GLpass"]
```

A league that differs puts the same tables in its `league.toml` with only the
keys that differ; each key it sets replaces athc.toml's, a list whole (see
[architecture.md](architecture.md#config)). Every key is optional: a missing
option keeps its default (`include_category_worksheets` is off and left out of
the shipped file), a missing list is empty. `--percentages` /
`--no-percentages` override `calculate_percentages` for one run.

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
  errors), plus a golden workbook: a real week's `.pdb` (`48W17.pdb`, every
  play in the curated pool) converted against that pool, the PNFL labels and
  order and both game plans, every cell compared to
  `expected/48W17.workbook.json`.
