# fbpro98-lg2

Library for reading the profile and game plan files each team uses from a Front Page Sports Football Pro '98 league (`.lg2`) file.

## Features

- `.lg2` reader for custom and stock leagues, modern and old
- Eight files per team: offense and defense profile and game plan, for each half
- Says which kind of league it read (`league_type`)
- In-memory parser (`parse_lg2`)

## Setup

```bash
uv sync
```

## Usage

```python
from pathlib import PureWindowsPath

from athc.fbpro98_lg2 import read_lg2

lg2 = read_lg2("PNFL", r"E:\SIERRA\FbPro98")      # reads PNFL.lg2 in that folder

lg2.league_type                            # LeagueType.CUSTOM
lg2.teams                                  # tuple of TeamFiles, in file order
team = lg2.teams[0]
team.first_half.offense.profile            # "PNFL\\2049\\Plans\\Jacksonville (Matt)\\JAGS-O1.prf"
team.second_half.defense.gameplan          # "PNFL\\2049\\Plans\\Jacksonville (Matt)\\JAGS-D2.pln"
PureWindowsPath(team.first_half.offense.profile).name  # "JAGS-O1.prf"
```

Locations are relative to the game folder. `parse_lg2(buffer)` is the bytes-in entry point; `read_lg2` builds the path from the league name and its folder and wraps file I/O.

## API

- `read_lg2(league, league_dir)` reads `<league_dir>/<league>.lg2` and returns an `Lg2File`; `parse_lg2(buffer, path)` parses raw bytes, `path` only naming the source in errors (`<path>: <reason>`).
- `Lg2File.league_type`: a `LeagueType`, judged by the first file entry's folder field alone: `STOCK\0A\FBPRO97\STOCK\0` is `MODERN_STOCK` (`NFLPI97.LG2`), an empty folder is `OLD_STOCK` (`08_TEAMS.LG2`), anything else `CUSTOM` (`PNFL.lg2`).
- `Lg2File.teams`: one `TeamFiles` per team, in the league's `.lge` order; `first_half` / `second_half` → `offense` / `defense` → `profile` / `gameplan`, each a string `folder\filename` relative to the game folder, or just `filename` when the folder is empty (`STOCK\BILLSO1.PRF` in a modern stock league, `OFF1.PRF` in an old one).
- `InvalidLg2Error`: empty file, a size that is not a whole number of team records, a folder or filename field without a NUL, or an empty filename; every kind of league gets the same checks.
- Checks run in order: size, then fields.

## Testing

```bash
uv run pytest
```
