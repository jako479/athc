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
- The workbook is `OUTPUT_FILE`, else the PDB's name with `.xlsm`, beside the
  PDB. Missing folders are created; an existing file is replaced.
- `.xlsm` has the sorting macros; `.xlsx` is plain. Excel opens an `.xlsm`
  with its macros disabled until you click Enable Content, and a copy sent by
  email opens with them blocked (unblock it in the file's Properties, or send
  an `.xlsx`).
- The workbook always includes the Total Stats team.
- `--percentages` / `--no-percentages` turn the percentage columns on or off
  for one run, over `calculate_percentages` in `athc.ini`.

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

- Progress on stderr: the game plans' lines, then `Creating '<workbook>'`.
- A `WARN` line per notice (a missing game plan, a play with no play file in
  the pool, a stale `[deleted_plays]` entry, invalid PDB data, a play-pool
  issue), each naming its file first where one is to blame; then
  `OK   <workbook>: <n> play(s)`. `athc playpool check` lists the play-pool
  issues on their own, with an exit code.
- A setting that is wrong (`team`, `path`, `ppp_path`, the league files) is a
  `FAIL` naming the file, as in [check-ppp](../check_ppp/README.md); without
  `path` the line suggests a game plan option instead.
- Exit 0 done (warnings included), 2 on an error (a missing or bad file,
  config, no `play_path`, I/O) or usage (bad extension, `--team` with `-o`,
  etc.); `FAIL <why>` names the problem. Shared console and codes:
  [architecture](../design/architecture.md#console-run-log-and-errors).

## Config

The league folder `leagues\<NAME>\` (picked by `--league` /
`[athc] league`; see [../design/architecture.md](../design/architecture.md#config)):

- `league.toml`: `play_path` (the `.ply` pool, required) and the league's
  category names (`[categories.*]`); for the Slot columns, `team` (your team),
  `path` (the folder with the league's `.lg2` and `.lge`) and, optionally,
  `ppp_path` (where you keep your game plans).
- `pdbtoexcel.toml` (required): `[category_order]`, the `run`, `pass` and
  `defense` lists of category names in the order the rows sort and the Options
  sheet lists them (a category not listed stays out of the workbook);
  `[deleted_plays] names`, plays removed from the pool, skipped quietly.

The Type column comes from the play pool: QB run and the defensive front from
each play file, Screen from a `Screens` folder.

```toml
# leagues\PNFL\pdbtoexcel.toml
[category_order]
run = ["RL", "RM", "RR", "GLR"]
pass = ["PSL", "PSM", "PSR", "PML", "PMM", "PMR", "PLR", "PRD", "GLP"]
defense = ["RunLeft", "RunMiddle", "RunRight", "RunDazzle", "PassShort", "PassMedium", "PassLong", "PassDazzle", "GLrun", "GLpass"]

[deleted_plays]
names = ["ATF0ELOB"]
```

The workbook options are app-wide settings in `[convert-pdb]` in `athc.ini`
(`calculate_percentages`, `include_category_worksheets`,
`exclude_sacks_from_pass_attempts`); `--percentages` / `--no-percentages`
override the first for one run.
