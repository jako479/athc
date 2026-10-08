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

Plays are grouped by their **game** category (e.g. "Pass Short Left").

## Config

The league folder `leagues\<NAME>\` (picked by `--league` /
`[athc] league`; see [../design/config.md](../design/config.md)):

```toml
# leagues\PNFL\league.toml
[league]
play_path = 'E:\SIERRA\FbPro98\PNFL'
```

`play_path` (the `.ply` pool, required) plus the optional `playpool.toml`
of filename filters that tag plays (QB draws, screens, defensive fronts). The
workbook options are app-wide settings in `[convert-pdb]` in `athc.ini`
(`calculate_percentages`, `include_category_worksheets`,
`exclude_sacks_from_pass_attempts`); `--skip-calcs` turns the first off for one
run.
