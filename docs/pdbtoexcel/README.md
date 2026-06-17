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

`[convert-pdb]` in `athc.ini`:

```ini
[convert-pdb]
play_path = E:\SIERRA\FbPro98\PNFL
playpool_rules = C:\athc\rules\PNFL.playpool.toml
```

`play_path` (the `.ply` pool, required) and an optional `playpool_rules` TOML of
filename filters that tag plays (QB draws, screens, defensive fronts).
`--play-path` / `--playpool-rules` / `--config` override.
