# standings command — design

Date: 2026-10-13. Status: implemented.

## Goal

`athc standings`: show a league's standings as played so far, from its
current `.lge` file.

## Scope

- In: the command, its tool package, tests, docs.
- Out: the standings library and generate-schedule stay as they are.

## Command

```
athc standings [-h] [--view game|league|conference|division]
               [--method scheduler|game|nfl] [--league name]
```

- `--league` picks the league, as on every league-aware command; the command
  reads `<league>.lge` from the league's `path` in league.toml.
- `--method`: the tie-breakers, the standings library's three methods;
  default `scheduler`.
- `--view`: default `game`.
- Prints the view on stdout. Exit 0; 2 on an error (no league, no `path`, a
  missing or broken `.lge`, a bad option).

## Views

### game (the game's standings screen)

- One column per conference, side by side; its divisions stacked down it.
  Division N of each conference starts on the same line.
- Each division: a header line (`AFC EAST`, then W, L, T, PF, PA), then its
  teams best first.
- Each team: its name (`Miami`), W, L, T, PF, PA.
- A blank line between divisions.

### league (ESPN's League tab)

- The league's name as title, one header line, then every team in league
  order, numbered 1 to the league's team count.

### conference (ESPN's Conference tab)

- Each conference, one under the other: its name as title, a header line,
  then its teams in conference order, numbered 1 to its team count.

### division (ESPN's Division tab)

- Each conference: its name as title; then each division: a header line
  (`AFC EAST`, then the column names), then its teams best first, not
  numbered.

### ESPN columns

Team, W, L, T, PCT, HOME, AWAY, DIV, CONF, PF, PA, DIFF, STRK.

| Column | Shows |
| :--- | :--- |
| Team | Name and nickname: `Miami Dolphins` |
| PCT | (W + T / 2) / games, three decimals, no leading zero below one: `.800`, `1.000`; `.000` before any game |
| HOME, AWAY | Record in home games, in away games |
| DIV, CONF | Record against the team's division, against its conference |
| PF, PA | Points for, points against |
| DIFF | PF minus PA, signed: `+23`, `-8`, `0` |
| STRK | `W3`, `L2`: the run of wins or losses ending with the latest game; `-` when the latest game was a tie or none was played |

A record reads `W-L`, or `W-L-T` when there are ties: `2-1`, `0-1-1`. Every
value counts regular-season games only.

## Names

- Conference: its name in the file; an unnamed one is `AFC` (first
  conference) or `NFC` (second).
- Division header: the conference and division names in capitals:
  `AFC EAST`.
- Team: the team name in the game view, name and nickname in the others.

## Layout

Plain text, no borders. Names left-aligned, numbers right-aligned; each
column as wide as its widest entry.

## Order

Every view orders teams by `--method` through the standings library:
`division()` for divisions, `conference()` for the conference view,
`league()` for the league view.

## Modules

| Module | Job |
| :--- | :--- |
| `src/athc/cli/standings.py` | The Click command: options, league config, reads the `.lge`, builds the standings, prints the view |
| `src/athc/standings/records.py` | Each team's row values from one `LgeFile` |
| `src/athc/standings/views.py` | The four views as lines of text |
| `pyproject.toml` | Entry point `standings = "athc.cli.standings:standings"` |

## Tests

- Unit, `tests/unit/standings/`, on small leagues built in code:
  - records: PCT (`.000`, below one, `1.000`), records with and without
    ties, home and away, division and conference, DIFF (`+`, `-`, `0`), STRK
    (wins, losses, a tie last, no games);
  - views: each layout, column widths, numbering, divisions of different
    sizes side by side, a one-conference league, an unnamed conference.
- Integration, `tests/integration/test_standings.py`, CliRunner on a real
  mid-season PNFL `.lge` as the league's file:
  - each view against a golden in `tests/integration/expected/`; W, L, T,
    PF and PA checked against the file's own records;
  - defaults (game view, scheduler method); each `--method`; `--league`
    picks the league;
  - no `path`, a missing `.lge`, a bad `--view` or `--method`: exit 2.

## Docs

- New `docs/standings/README.md`: options, views, columns, exit codes.
- `docs/design/architecture.md`: project layout, league-aware command list.
- `README.md`, `config/release/docs/COMMANDS.txt` and `README.txt`.
- `tests/integration/README.md` and a new `tests/unit/standings/README.md`
  (test matrices).
- `STATUS.md`, `CHANGELOG.md`.
