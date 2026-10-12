# fbpro98-lge

Library for reading the conferences, divisions, teams and standings from a Front Page Sports Football Pro '98 league (`.lge`) file.

## Features

- `.lge` reader for every league size, stock and custom (8 to 30 teams), chunks nested or grouped by kind
- Conference names, each conference's division names, each division's teams
- Team name, nickname and official name, as on the game's Team Settings screen
- Each team's regular-season record: W-L-T, points for, points against
- Division and conference standings, best first
- Unmasks the team chunks while reading
- In-memory parser (`parse_lge`)

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_lge import read_lge

lge = read_lge("PNFL", r"E:\SIERRA\FbPro98")     # reads PNFL.lge in that folder

for conference in lge.conferences:
    print(conference.name)                       # "" in PNFL.lge
    for division in conference.divisions:
        print(division.name)                     # "East"
        for team in division.standings:          # best first
            team.official_name                   # "Jacksonville Jaguars"
            team.record                          # Record(wins=5, losses=1, ties=0, points_for=164, points_against=112)
    conference.standings                         # every team in the conference, best first
```

`parse_lge(buffer)` is the bytes-in entry point; `read_lge` builds the path from the league name and its folder and wraps file I/O.

## API

- `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge` and returns an `LgeFile`; `parse_lge(buffer, path)` parses raw bytes, `path` only naming the source in errors (`<path>: <reason>`).
- `LgeFile.conferences` → `Conference.name`, `Conference.divisions` → `Division.name`, `Division.teams` → `Team`, all in file order. Walking them in order gives the team numbers 1..N that key the other league files.
- `Team.name` ("Team Name"), `Team.nickname`, `Team.official_name` (the two joined by a space; just the one present when the other is empty), `Team.record`.
- `Record`: `wins`, `losses`, `ties`, `points_for`, `points_against`, `games`, `win_percentage` (a tie counts as half a win; 0.0 before any game), `point_differential`. Only regular-season games marked played count.
- `Division.standings`, `Conference.standings`: teams best first, by win percentage, then point differential, then file order.
- A name is the text up to its NUL, or the whole field when it has none; an empty name is `""`.
- `InvalidLgeError`: empty file, a chunk header cut short, a chunk running past the end, a chunk other than the one expected next, a chunk of the wrong size, a schedule cut short or followed by data, data after the schedule, or a played game naming a team outside 1..N. The first problem in file order is reported.

## Testing

```bash
uv run pytest
```
