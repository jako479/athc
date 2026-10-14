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
