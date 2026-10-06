# fbpro98-lg2

Library for reading the profile and game plan files each team uses from a Front Page Sports Football Pro '98 league (`.lg2`) file.

## Features

- `.lg2` reader for custom leagues
- Eight files per team: offense and defense profile and game plan, for each half
- Rejects stock leagues, modern and old
- In-memory parser (`parse_lg2`)

## Setup

```bash
uv sync
```

## Usage

```python
from pathlib import PureWindowsPath

from athc.fbpro98_lg2 import read_lg2

lg2 = read_lg2(r"E:\SIERRA\FbPro98\PNFL.lg2")

lg2.teams                                  # tuple of TeamFiles, in file order
team = lg2.teams[0]
team.first_half.offense.profile            # "PNFL\\2049\\Plans\\Jacksonville (Matt)\\JAGS-O1.prf"
team.second_half.defense.gameplan          # "PNFL\\2049\\Plans\\Jacksonville (Matt)\\JAGS-D2.pln"
PureWindowsPath(team.first_half.offense.profile).name  # "JAGS-O1.prf"
```

Locations are relative to the game folder. `parse_lg2(buffer)` is the bytes-in entry point; `read_lg2` wraps file I/O.

## Unsupported variants

Stock leagues raise `UnsupportedLg2Error`, judged by the first file entry:

- **Modern stock** — folder field `STOCK\0A\FBPRO97\STOCK\0` (e.g. `NFLPI97.LG2`).
- **Old stock** — empty folder field (e.g. `08_TEAMS.LG2`).

The stock check runs before the field checks, so it decides on the first folder field alone. `InvalidLg2Error` covers everything else that is malformed.

## Testing

```bash
uv run pytest
```
