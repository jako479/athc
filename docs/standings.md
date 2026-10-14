# standings

Show a league's standings as played so far, from its current `.lge` file.

## Usage

```bash
athc standings
athc standings --view league
athc standings --view division --method nfl --league PCFL
```

The league comes from `--league name`, or from `[athc] league` in
`athc.ini`. Its `.lge`, named after the league, is read from the folder
`path` names in its `league.toml`.

## Views

- `game` (default): the game's standings screen. One column per conference,
  its divisions stacked down it; each division under a header like
  `AFC EAST`; W, L, T, PF, PA; city names.
- `league`: ESPN's League tab. The league's name, then every team numbered
  from 1.
- `conference`: ESPN's Conference tab. Each conference's teams, numbered
  from 1.
- `division`: ESPN's Division tab. Each conference, then each division under
  its header.

The ESPN views show W, L, T, PCT, HOME, AWAY, DIV, CONF, PF, PA, DIFF and
STRK, with full team names. A record reads `2-1`, or `0-1-1` with ties;
STRK is `-` when the latest game was a tie or none was played.

A conference the file leaves unnamed shows as AFC (first) or NFC (second).

## Order

`--method` picks the tie-breakers: `scheduler` (default), `game` or `nfl`,
from the standings library. Teams still level at the end are ordered by one
fixed coin toss, so the same file always shows the same order.

Only regular-season games count.

## Output and exit codes

The view goes to stdout. Exit 0; 2 on an error: no league, no `path` in
`league.toml`, a missing or broken `.lge`, a bad option.

## How it works

- The command finds the league's folder from `path` in its `league.toml` and
  reads `<league>.lge` with `fbpro98_lge`.
- `fbpro98_standings` orders the teams by `--method`; the command passes one
  fixed coin-toss seed, so the same file always shows the same order.
- `records.py` builds each team's row from the regular-season games only:
  overall, home, away, division and conference records, points for and
  against, and the streak. Playoff games never count.
- `views.py` lays the rows out as plain text: each column as wide as its
  widest entry, names left-aligned, numbers right-aligned. The game view puts
  each conference in its own column, side by side.
- The command prints each line through the console.

### Layout

```
src/athc/standings/        # tool logic (no Click)
├── __init__.py            # public API
├── records.py             # Split, Row, rows_of(): each team's row values
└── views.py               # render(): the four views as lines of text

src/athc/cli/standings.py  # Click leaf command
```

### Boundaries

- Reads the `.lge` only; never writes a file.
- The game writes one or two conferences; an unnamed one shows as AFC (first)
  or NFC (second).
- The tool package never prints and never touches Click; the command does
  both.

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — the view printed. |
| `2` | **Error** — a `FAIL` line: no league, no `path` in `league.toml`, a missing or broken `.lge`; or a bad option (Click). |

The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).

### Tests

- `tests/unit/standings/` — row values and the four views on small leagues
  built in code, and the rows checked against real `.lge` files' own records.
- `tests/integration/test_standings.py` — the command end to end on a real
  mid-season PNFL `.lge`, each view against a golden in `expected/`.
