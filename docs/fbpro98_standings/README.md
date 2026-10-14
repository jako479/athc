# fbpro98-standings

Library that ranks a Front Page Sports Football Pro '98 league's teams from its `.lge` files: division, conference and league standings, by the game's, the scheduler's or the NFL's tie-breakers.

## Features

- Division, conference and league (final) standings, best first
- Three tie-break methods: `game` (the manual's), `scheduler` (generate-schedule's), `nfl` (the NFL's)
- One season, or last season's results for this season's divisions and teams, with team moves for teams whose name changed
- A repeatable coin toss with a seed

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Standings

current = read_lge("PNFL", league_dir)
standings = Standings(current, method="game")
for conference in current.conferences:
    standings.conference(conference)           # its teams, best first
    for division in conference.divisions:
        standings.division(division)           # its teams, best first
standings.league()                             # every team, final order

previous = read_lge("PNFL", previous_dir)
standings = Standings(
    current, previous, {"Baltimore": "Los Angeles"}, method="scheduler", seed=1
)
```

## API

- `Standings(current, previous=None, team_moves=None, *, method, seed=None)`: standings by one method. With `previous`, last season's results for the current file's divisions and teams; `team_moves` maps a renamed team's previous name to its current one; `seed` repeats the coin toss.
- `Standings.division(division)`, `Standings.conference(conference)`, `Standings.league()`: the current file's teams, best first.
- `Method`: `"game"`, `"scheduler"` or `"nfl"`.
- `StandingsError`: the two files and the team moves do not fit together.
