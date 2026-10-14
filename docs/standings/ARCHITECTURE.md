# standings — Architecture

`athc standings` shows a league's standings as played so far, read from its
current `.lge` file, as the game's standings screen or ESPN's League,
Conference and Division tabs.

## Layout

```
src/athc/standings/        # tool logic (no Click)
├── __init__.py            # public API
├── records.py             # Split, Row, rows_of(): each team's row values
└── views.py               # render(): the four views as lines of text

src/athc/cli/standings.py  # Click leaf command
```

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

## Boundaries

- Reads the `.lge` only; never writes a file.
- The game writes one or two conferences; an unnamed one shows as AFC (first)
  or NFC (second).
- The tool package never prints and never touches Click; the command does
  both.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — the view printed. |
| `2` | **Error** — a `FAIL` line: no league, no `path` in `league.toml`, a missing or broken `.lge`; or a bad option (Click). |

The shared scheme: [architecture.md](../design/architecture.md#console-run-log-and-errors).

## Tests

- `tests/unit/standings/` — row values and the four views on small leagues
  built in code, and the rows checked against real `.lge` files' own records.
- `tests/integration/test_standings.py` — the command end to end on a real
  mid-season PNFL `.lge`, each view against a golden in `expected/`.
