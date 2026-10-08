# pdbtoexcel

Export a WinLogStats database (`.pdb`) — FbPro '98 game stats — to an Excel
workbook. Built on `playpool` (play classification) and `fbpro98_gameplan`
(`.pln` parsing).

## Command

```bash
athc convert-pdb stats.pdb out.xlsm -o offense.pln -d defense.pln
athc convert-pdb stats.pdb out.xlsx --league PCFL
```

- `out.xlsm` embeds VBA sort macros; `out.xlsx` is plain.
- Cross-reference up to two offensive (`-o`/`-o2`) and two defensive (`-d`/`-d2`)
  game plans to fill the Slot columns.
- The workbook always includes the Total Stats team.
- `--skip-calcs` drops the percentage columns.
- Exit 0 ok, 1 on an input/I/O error, 2 on usage (bad extension, etc.).

Plays are grouped by their category, shown under the league's name for it
(`PSL`, `RunLeft`) and sorted in the league's order.

## Config

The league folder `leagues\<NAME>\` (picked by `--league` /
`[athc] league`; see [../design/config.md](../design/config.md)):

- `league.toml`: `play_path` (the `.ply` pool, required) and the league's
  category names (`[categories.*]`).
- `pdbtoexcel.toml` (required): `[category_order]`, the `run`, `pass` and
  `defense` lists of category names in the order the rows sort and the Options
  sheet lists them (a category not listed stays out of the workbook);
  `[deleted_plays] names`, plays removed from the pool, skipped quietly.
- `playpool.toml` (optional): filename filters that tag plays (QB draw, rollout,
  timed pass). The exact names it lists under include / exclude are checked
  against the pool; each problem is a warning.

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
`exclude_sacks_from_pass_attempts`); `--skip-calcs` turns the first off for one
run.
