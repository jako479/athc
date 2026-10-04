# pdbtoexcel

Export a WinLogStats database (`.pdb`) — FbPro '98 game stats — to an Excel
workbook. Built on `playpool` (play classification) and `fbpro98_gameplan`
(`.pln` parsing).

## Command

```bash
athc convert-pdb stats.pdb out.xlsm -o offense.pln -d defense.pln
athc convert-pdb stats.pdb out.xlsx --play-path E:\SIERRA\FbPro98\PNFL
```

- `out.xlsm` embeds VBA sort macros; `out.xlsx` is plain.
- Cross-reference up to two offensive (`-o`/`-o2`) and two defensive (`-d`/`-d2`)
  game plans to fill the Slot columns.
- `--skip-calcs` drops the percentage columns; `--skip-totals` drops the Total
  Stats team.
- Exit 0 ok, 1 on an input/I/O error, 2 on usage (bad extension, etc.).

Plays are grouped by their **game** category (e.g. "Pass Short Left").

## Config

The league folder `leagues\<NAME>\` (picked by `--league` / `ATHC_LEAGUE` /
`[athc] league`; see [../design/config.md](../design/config.md)):

```ini
; leagues\PNFL\league.ini
[league]
play_path = E:\SIERRA\FbPro98\PNFL
```

`play_path` (the `.ply` pool, required) plus the optional `rules\playpool.toml`
of filename filters that tag plays (QB draws, screens, defensive fronts).
Playpool rules resolve as `--playpool-rules`, else the league's
`rules\playpool.toml`, else the default `playpool.toml` next to `athc.ini`
(shipped: the PNFL filters), else none. `--play-path` skips the league, so it
uses the default file unless `--playpool-rules` is given. The workbook
options are app-wide settings in `[convert-pdb]` in `athc.ini`
(`calculate_total_stats`, `calculate_percentages`,
`include_category_worksheets`, `exclude_sacks_from_pass_attempts`);
`--skip-totals` / `--skip-calcs` turn the first two off for one run.
